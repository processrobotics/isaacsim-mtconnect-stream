# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
MTConnect Client for streaming data from an MTConnect Agent.

Uses the mtconnect-rest-python library:
    pip install git+https://github.com/processrobotics/mtconnect-rest-python.git
"""

import json
import threading
from typing import Callable, Optional

import carb

try:
    import mtconnect
    from mtconnect.rest import ApiException
    MTCONNECT_AVAILABLE = True
except ImportError:
    MTCONNECT_AVAILABLE = False
    carb.log_warn("mtconnect package not installed. Install with: pip install git+https://github.com/processrobotics/mtconnect-rest-python.git")


class MTConnectHeader:
    """Stores MTConnect header information from responses."""
    
    def __init__(self):
        self.instance_id: Optional[int] = None
        self.version: Optional[str] = None
        self.json_version: Optional[int] = None
        self.sender: Optional[str] = None
        self.buffer_size: Optional[int] = None
        self.first_sequence: Optional[int] = None
        self.last_sequence: Optional[int] = None
        self.next_sequence: Optional[int] = None
        
    def update_from_dict(self, response: dict):
        """Extract header info from a parsed MTConnect JSON response."""
        if not response:
            return
            
        header = None
        
        # MTConnect JSON structure: {"MTConnectStreams": {"Header": {...}, "Streams": {...}}}
        if "MTConnectStreams" in response:
            streams = response["MTConnectStreams"]
            if isinstance(streams, dict):
                header = streams.get("Header")
                self.json_version = self._parse_int(streams.get("jsonVersion"))
        elif "Header" in response:
            header = response["Header"]
                
        if isinstance(header, dict):
            self.instance_id = self._parse_int(header.get("instanceId"))
            self.version = header.get("version")
            self.sender = header.get("sender")
            self.buffer_size = self._parse_int(header.get("bufferSize"))
            self.first_sequence = self._parse_int(header.get("firstSequence"))
            self.last_sequence = self._parse_int(header.get("lastSequence"))
            self.next_sequence = self._parse_int(header.get("nextSequence"))
    
    def _parse_int(self, value) -> Optional[int]:
        """Parse a value to int, returning None if not possible."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
            
    def __repr__(self):
        return (f"MTConnectHeader(instance_id={self.instance_id}, "
                f"json_version={self.json_version}, "
                f"next_sequence={self.next_sequence}, "
                f"last_sequence={self.last_sequence})")


class MTConnectClient:
    """
    Client for streaming MTConnect data from an agent (JSON only).
    
    Workflow:
    1. Connect to agent and fetch /current response
    2. Store data in cache dict and capture header info (sequence numbers, etc.)
    3. Start streaming with /sample?interval=X&from={nextSequence}
    4. On each update, merge incoming data with cached data
    """
    
    def __init__(self):
        self._agent_address: str = ""
        self._path: str = ""
        self._api_instance: Optional["mtconnect.DefaultApi"] = None
        self._api_client: Optional["mtconnect.ApiClient"] = None
        self._streaming: bool = False
        self._stream_thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        
        # Data cache - stores flattened observations by dataItemId
        self._data_cache: dict = {}
        self._header: MTConnectHeader = MTConnectHeader()
        
        # Callbacks
        self._on_data_update: Optional[Callable[[dict], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._on_status_change: Optional[Callable[[str], None]] = None
        
        # Streaming parameters
        self._stream_interval_ms: int = 100  # Interval in ms for streaming mode
        self._stream_heartbeat_ms: int = 10000  # Heartbeat in ms
        
    @property
    def is_streaming(self) -> bool:
        return self._streaming
    
    @property
    def is_connected(self) -> bool:
        return self._api_instance is not None
    
    @property
    def agent_address(self) -> str:
        """The currently connected agent address."""
        return self._agent_address
        
    @property
    def data_cache(self) -> dict:
        return self._data_cache
        
    @property
    def header(self) -> MTConnectHeader:
        return self._header
        
    def set_callbacks(self, 
                      on_data_update: Optional[Callable[[dict], None]] = None,
                      on_error: Optional[Callable[[str], None]] = None,
                      on_status_change: Optional[Callable[[str], None]] = None):
        """Set callback functions for data updates, errors, and status changes."""
        self._on_data_update = on_data_update
        self._on_error = on_error
        self._on_status_change = on_status_change
        
    def _notify_status(self, status: str):
        """Notify status change."""
        carb.log_warn(f"MTConnect: {status}")
        if self._on_status_change:
            self._on_status_change(status)
            
    def _notify_error(self, error: str):
        """Notify error."""
        carb.log_error(f"MTConnect Error: {error}")
        if self._on_error:
            self._on_error(error)
            
    def _notify_data_update(self):
        """Notify data update."""
        if self._on_data_update:
            self._on_data_update(self._data_cache)
    
    def connect(self, agent_address: str, xpath: str = "") -> bool:
        """
        Connect to an MTConnect agent and fetch initial /current data.
        
        Args:
            agent_address: The base URL of the MTConnect agent (e.g., "http://192.168.0.247:5000")
            xpath: Optional XPath query to filter the data items from the agent.
            
        Returns:
            True if connection successful, False otherwise
        """
        if not MTCONNECT_AVAILABLE:
            self._notify_error("mtconnect package not installed")
            return False
            
        self._agent_address = agent_address.rstrip("/")
        self._path = xpath
        
        try:
            # Configure the API client
            configuration = mtconnect.Configuration()
            configuration.host = self._agent_address
            
            self._api_client = mtconnect.ApiClient(configuration)
            # Request JSON responses
            self._api_client.default_headers["Accept"] = "application/json"
            self._api_instance = mtconnect.DefaultApi(self._api_client)
            
            # Fetch /current to get initial state
            self._notify_status(f"Connecting to {self._agent_address}...")
            
            # Use _preload_content=False to get raw response, then parse JSON ourselves
            if self._path != "":
                response = self._api_instance.current_get_with_http_info(_preload_content=False, path=self._path)
            else:
                response = self._api_instance.current_get_with_http_info(_preload_content=False)
            http_response = response[0]
            
            # Read and parse JSON
            response_data = http_response.read()
            if isinstance(response_data, bytes):
                response_data = response_data.decode('utf-8')
            
            response_dict = json.loads(response_data)
            carb.log_verbose(f"MTConnect: /current response received, keys: {list(response_dict.keys())}")
            
            # Process the response
            self._process_json_response(response_dict, source="current")
            self._notify_data_update()
            self._notify_status(f"Connected. Next sequence: {self._header.next_sequence}")
            
            return True
            
        except ApiException as e:
            self._notify_error(f"API Exception: {e}")
            return False
        except json.JSONDecodeError as e:
            self._notify_error(f"JSON parse error: {e}")
            return False
        except Exception as e:
            self._notify_error(f"Connection failed: {e}")
            return False
    
    def _process_json_response(self, response_dict: dict, source: str = "unknown"):
        """Process a parsed MTConnect JSON response and update cache."""
        if not response_dict:
            carb.log_warn(f"MTConnect: Empty response from {source}")
            return
        
        carb.log_verbose(f"MTConnect: _process_json_response from {source}, keys={list(response_dict.keys())}")
        
        # Update header info
        self._header.update_from_dict(response_dict)
        
        # Extract Streams data
        streams_data = None
        if "MTConnectStreams" in response_dict:
            mtc_streams = response_dict["MTConnectStreams"]
            if isinstance(mtc_streams, dict):
                streams_data = mtc_streams.get("Streams")
                carb.log_verbose(f"MTConnect: Found Streams data: {type(streams_data)}")
        else:
            carb.log_warn(f"MTConnect: No MTConnectStreams in response from {source}")
        
        if streams_data:
            old_count = len(self._data_cache)
            self._merge_streams_data(streams_data)
            if source == "current" or len(self._data_cache) > old_count:
                carb.log_verbose(f"MTConnect: {source} - cache now has {len(self._data_cache)} items, seq={self._header.next_sequence}")
    
    def _merge_streams_data(self, streams_data):
        """
        Merge Streams data into the cache.
        
        MTConnect JSON structure depends on jsonVersion:
        - jsonVersion 1: Streams is [{"DeviceStream": {...}}]
        - jsonVersion 2: Streams is {"DeviceStream": [...]}
        """
        if not streams_data:
            carb.log_warn("MTConnect: _merge_streams_data got empty streams_data")
            return
        
        carb.log_verbose(f"MTConnect: _merge_streams_data processing {type(streams_data)}, jsonVersion={self._header.json_version}")
        
        json_version = self._header.json_version
        if json_version == 1:
            # Version 1: Streams is a list of {"DeviceStream": ...}
            if isinstance(streams_data, list):
                device_streams = []
                for item in streams_data:
                    if isinstance(item, dict) and "DeviceStream" in item:
                        device_streams.append(item["DeviceStream"])
                    else:
                        self._notify_error(f"Unexpected structure in jsonVersion {json_version}: expected list of dicts with 'DeviceStream', got {type(item)}")
                        return
            else:
                self._notify_error(f"Unexpected structure in jsonVersion {json_version}: expected list, got {type(streams_data)}")
                return
        elif json_version == 2 or json_version is None:
            # Version 2 or unknown: Streams is {"DeviceStream": [...]}
            if isinstance(streams_data, dict):
                device_streams = streams_data.get("DeviceStream", [])
            else:
                self._notify_error(f"Unexpected structure in jsonVersion {json_version}: expected dict, got {type(streams_data)}")
                return
        else:
            self._notify_error(f"Unsupported jsonVersion {json_version}")
            return
            
        if not device_streams:
            carb.log_warn("MTConnect: No device_streams found, returning early")
            return
        if not isinstance(device_streams, list):
            device_streams = [device_streams]
        
        carb.log_verbose(f"MTConnect: Processing {len(device_streams)} device_streams")
        
        for device_stream in device_streams:
            if not isinstance(device_stream, dict):
                continue
                
            device_name = device_stream.get("name", "unknown")
            
            # Check jsonVersion to determine structure
            json_version = self._header.json_version
            
            # Get component streams based on version
            if json_version == 2 or json_version is None:
                # jsonVersion 2 or unknown: "ComponentStream" (singular) is a direct array
                component_streams = device_stream.get("ComponentStream", [])
            else:
                # jsonVersion 1: "ComponentStreams" (plural) is array of {"ComponentStream": {...}}
                component_streams = device_stream.get("ComponentStreams", [])
            
            if not isinstance(component_streams, list):
                component_streams = [component_streams]
            
            carb.log_verbose(f"MTConnect:   Processing {len(component_streams)} ComponentStream(s) for device '{device_name}' (jsonVersion={json_version})")
            
            for comp_stream_item in component_streams:
                if not isinstance(comp_stream_item, dict):
                    continue
                
                # Unwrap based on version
                if json_version == 2 or json_version is None:
                    # jsonVersion 2 or unknown: comp_stream_item is the component stream directly
                    comp_stream = comp_stream_item
                else:
                    # jsonVersion 1: comp_stream_item is {"ComponentStream": {...}}
                    comp_stream = comp_stream_item.get("ComponentStream")
                    if not comp_stream:
                        continue
                
                comp_name = comp_stream.get("name", "unknown")
                
                # Process Samples, Events, and Condition
                for category in ["Samples", "Events", "Condition"]:
                    category_data = comp_stream.get(category)
                    if not category_data:
                        continue
                    
                    cached_count = 0
                    
                    if json_version == 2 or json_version is None:
                        # jsonVersion 2 or unknown: category_data is dict {"DataType": [observations]}
                        if not isinstance(category_data, dict):
                            continue
                        
                        for data_type, observations in category_data.items():
                            if not isinstance(observations, list):
                                observations = [observations]
                            
                            for obs in observations:
                                if isinstance(obs, dict):
                                    self._cache_observation(obs, device_name, category)
                                    cached_count += 1
                    else:
                        # jsonVersion 1: category_data is list [{"DataType": {observation}}]
                        if not isinstance(category_data, list):
                            category_data = [category_data]
                        
                        for item in category_data:
                            if not isinstance(item, dict):
                                continue
                            
                            # Each item has one key (the data type like "Position", "Load", etc.)
                            for data_type, obs in item.items():
                                if isinstance(obs, dict):
                                    self._cache_observation(obs, device_name, category)
                                    cached_count += 1
                    
                    if cached_count > 0:
                        carb.log_verbose(f"MTConnect:       Cached {cached_count} {category} observations from '{comp_name}'")
    
    def _cache_observation(self, obs: dict, device_name: str, category: str):
        """Cache a single observation by its dataItemId."""
        data_item_id = obs.get("dataItemId")
        if not data_item_id:
            return
        
        # Store in cache with metadata
        self._data_cache[data_item_id] = {
            "device": device_name,
            "category": category,
            "dataItemId": data_item_id,
            "name": obs.get("name", data_item_id),
            "value": obs.get("value"),
            "timestamp": obs.get("timestamp"),
            "sequence": obs.get("sequence"),
            # Include any additional fields (like subType, units, etc.)
            **{k: v for k, v in obs.items() if k not in ["dataItemId", "name", "value", "timestamp", "sequence"]}
        }
        carb.log_verbose(f"MTConnect: Cached '{data_item_id}' (name={obs.get('name')}) = {obs.get('value')}")
                
    def start_streaming(self) -> bool:
        """
        Start streaming data from the agent using the interval parameter.
        
        Returns:
            True if streaming started, False otherwise
        """
        if self._streaming:
            self._notify_status("Already streaming")
            return True
            
        if self._api_instance is None:
            self._notify_error("Not connected to agent")
            return False
            
        self._stop_event.clear()
        self._streaming = True
        
        # Start streaming in background thread
        self._stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._stream_thread.start()
        
        self._notify_status("Streaming started")
        return True
        
    def _stream_loop(self):
        """
        Background thread loop for HTTP streaming.
        
        Uses the mtconnect library's sample_get with interval parameter,
        which returns a multipart/x-mixed-replace response.
        """
        carb.log_info(f"MTConnect: Stream loop started, next_sequence={self._header.next_sequence}")
        
        while not self._stop_event.is_set():
            try:
                from_seq = max(1, self._header.next_sequence or 1)
                
                carb.log_warn(f"MTConnect: Opening stream from sequence {from_seq}")
                
                if self._path != "":
                    # Use sample_get_with_http_info with _preload_content=False to get raw streaming response
                    # The interval parameter triggers multipart streaming mode
                    response = self._api_instance.sample_get_with_http_info(
                        _from=from_seq,
                        interval=self._stream_interval_ms,
                        heartbeat=self._stream_heartbeat_ms,
                        path=self._path,
                        _preload_content=False
                    )
                else:
                    response = self._api_instance.sample_get_with_http_info(
                        _from=from_seq,
                        interval=self._stream_interval_ms,
                        heartbeat=self._stream_heartbeat_ms,
                        _preload_content=False
                    )
                
                http_response = response[0]
                content_type = http_response.headers.get("Content-Type", "")
                
                carb.log_warn(f"MTConnect: Stream response Content-Type: {content_type}")
                
                if "multipart" in content_type.lower():
                    # Parse multipart streaming response
                    carb.log_warn("MTConnect: Detected multipart response, starting stream parse")
                    self._parse_multipart_stream(http_response, content_type)
                else:
                    # Single response (non-streaming fallback)
                    carb.log_warn(f"MTConnect: NOT multipart! Content-Type={content_type}, falling back to single response")
                    self._parse_single_response(http_response)
                    
            except Exception as e:
                import traceback
                carb.log_warn(f"MTConnect: Stream error: {e}")
                carb.log_warn(f"MTConnect: Traceback: {traceback.format_exc()}")
                if not self._stop_event.is_set():
                    carb.log_warn("MTConnect: Reconnecting in 2s...")
                    self._stop_event.wait(2.0)
        
        carb.log_warn(f"MTConnect: Stream loop EXITED. stop_event.is_set()={self._stop_event.is_set()}")
        self._streaming = False
        self._notify_status("Streaming stopped")
    
    def _parse_multipart_stream(self, http_response, content_type: str):
        """Parse a multipart/x-mixed-replace streaming response."""
        # Extract boundary from Content-Type header
        boundary = self._extract_boundary(content_type)
        if not boundary:
            carb.log_error("MTConnect: No boundary found in multipart response")
            return
        
        carb.log_warn(f"MTConnect: Multipart boundary: {boundary}")
        
        # Read the stream in chunks and parse multipart frames
        buffer = b""
        boundary_bytes = boundary.encode('utf-8')
        
        chunk_count = 0
        # Use read_chunked or iterate to avoid buffering delays
        try:
            # Try using stream() generator first (urllib3)
            if hasattr(http_response, 'stream'):
                chunk_iter = http_response.stream(4096)
            else:
                # Fallback: create generator using read with smaller chunks
                def read_iter():
                    while True:
                        data = http_response.read(4096, decode_content=False)
                        if not data:
                            break
                        yield data
                chunk_iter = read_iter()
            
            for chunk in chunk_iter:
                if self._stop_event.is_set():
                    break
                if not chunk:
                    continue
                
                chunk_count += 1
                buffer += chunk
                
                # Process complete frames from buffer
                buffer = self._process_multipart_buffer(buffer, boundary_bytes)
        except Exception as e:
            import traceback
            carb.log_warn(f"MTConnect: Stream error: {e}")
            carb.log_warn(f"MTConnect: Traceback: {traceback.format_exc()}")
        
        if self._stop_event.is_set():
            carb.log_warn(f"MTConnect: Stream stopped by user after {chunk_count} chunks")
    
    def _extract_boundary(self, content_type: str) -> Optional[str]:
        """Extract boundary string from Content-Type header."""
        for part in content_type.split(";"):
            part = part.strip()
            if part.lower().startswith("boundary="):
                boundary = part[9:].strip('"').strip("'")
                # Ensure boundary starts with --
                if not boundary.startswith("--"):
                    boundary = "--" + boundary
                return boundary
        return None
    
    def _process_multipart_buffer(self, buffer: bytes, boundary: bytes) -> bytes:
        """Process multipart frames from buffer, return remaining unprocessed bytes."""
        frames_processed = 0
        while True:
            # Find boundary
            boundary_idx = buffer.find(boundary)
            if boundary_idx < 0:
                carb.log_verbose(f"MTConnect: No boundary found in buffer (len={len(buffer)}), waiting for more data")
                return buffer
            
            # Find end of headers (double CRLF)
            header_end = buffer.find(b"\r\n\r\n", boundary_idx)
            if header_end < 0:
                carb.log_error(f"MTConnect: Found boundary at {boundary_idx} but no header end yet")
                return buffer  # Incomplete headers
            
            # Parse headers to get Content-Length
            header_section = buffer[boundary_idx + len(boundary):header_end].decode('utf-8', errors='ignore')
            content_length = self._parse_content_length(header_section)
            carb.log_verbose(f"MTConnect: Frame headers: {header_section[:200]}, Content-Length={content_length}")
            
            if content_length is None:
                # No Content-Length, try to find next boundary
                next_boundary = buffer.find(boundary, header_end + 4)
                if next_boundary < 0:
                    return buffer  # Wait for more data
                body = buffer[header_end + 4:next_boundary]
                buffer = buffer[next_boundary:]
            else:
                body_start = header_end + 4
                body_end = body_start + content_length
                
                if len(buffer) < body_end:
                    return buffer  # Incomplete body
                
                body = buffer[body_start:body_end]
                buffer = buffer[body_end:]
            
            # Parse the JSON body
            if body.strip():
                try:
                    json_str = body.decode('utf-8').strip()
                    if json_str:
                        response_dict = json.loads(json_str)
                        
                        # Extract sequence for logging
                        sequence = None
                        if "MTConnectStreams" in response_dict:
                            mtc_streams = response_dict["MTConnectStreams"]
                            if isinstance(mtc_streams, dict):
                                header = mtc_streams.get("Header")
                                if isinstance(header, dict):
                                    sequence = header.get("nextSequence") or header.get("lastSequence")
                        
                        carb.log_verbose(f"MTConnect: Parsing multipart frame, body length={len(json_str)}, seq={sequence}")
                        self._process_json_response(response_dict, source="stream")
                        self._notify_data_update()
                except json.JSONDecodeError as e:
                    carb.log_warn(f"MTConnect: JSON parse error in stream: {e}")
                    carb.log_warn(f"MTConnect: Failed body preview: {body[:500]}")
        
        return buffer
    
    def _parse_content_length(self, header_section: str) -> Optional[int]:
        """Parse Content-Length from header section."""
        for line in header_section.split("\r\n"):
            if line.lower().startswith("content-length:"):
                try:
                    return int(line.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    pass
        return None
    
    def _parse_single_response(self, http_response):
        """Parse a single (non-streaming) response."""
        try:
            response_data = http_response.read()
            if isinstance(response_data, bytes):
                response_data = response_data.decode('utf-8')
            
            carb.log_warn(f"MTConnect: Single response received, length={len(response_data)}")
            response_dict = json.loads(response_data)
            
            # Extract sequence for logging
            sequence = None
            if "MTConnectStreams" in response_dict:
                mtc_streams = response_dict["MTConnectStreams"]
                if isinstance(mtc_streams, dict):
                    header = mtc_streams.get("Header")
                    if isinstance(header, dict):
                        sequence = header.get("nextSequence") or header.get("lastSequence")
            
            carb.log_warn(f"MTConnect: Processing single response, seq={sequence}")
            self._process_json_response(response_dict, source="sample")
            self._notify_data_update()
            
        except json.JSONDecodeError as e:
            carb.log_warn(f"MTConnect: JSON parse error: {e}")
            carb.log_warn(f"MTConnect: Failed data preview: {response_data[:500] if response_data else 'empty'}")
        
    def stop_streaming(self):
        """Stop the streaming loop."""
        if not self._streaming:
            return
            
        carb.log_warn("MTConnect: Stopping stream...")
        self._stop_event.set()
        
        if self._stream_thread and self._stream_thread.is_alive():
            self._stream_thread.join(timeout=3.0)
            
        self._streaming = False
        self._notify_status("Streaming stopped")
        
    def disconnect(self):
        """Disconnect from the agent and clean up."""
        self.stop_streaming()
        self._api_instance = None
        self._api_client = None
        self._data_cache.clear()
        self._header = MTConnectHeader()
        self._notify_status("Disconnected")
        
    def get_data_summary(self) -> str:
        """Get a summary of cached data for display."""
        if not self._data_cache:
            return "No data"
        
        lines = [
            f"Instance ID: {self._header.instance_id}",
            f"JSON Version: {self._header.json_version}",
            f"Next Sequence: {self._header.next_sequence}",
            f"Buffer: {self._header.first_sequence} - {self._header.last_sequence}",
            f"Cached Items: {len(self._data_cache)}",
        ]
        
        # Group by device
        devices = {}
        for item_id, data in self._data_cache.items():
            device = data.get("device", "unknown")
            if device not in devices:
                devices[device] = 0
            devices[device] += 1
        
        if devices:
            lines.append(f"Devices: {dict(devices)}")
        
        return "\n".join(lines)
    
    def get_observation(self, data_item_id: str) -> Optional[dict]:
        """Get a single observation from the cache by dataItemId."""
        result = self._data_cache.get(data_item_id)
        if result:
            carb.log_verbose(f"MTConnect: get_observation('{data_item_id}') FOUND: {result.get('value')}")
        else:
            available_keys = list(self._data_cache.keys())
            carb.log_warn(f"MTConnect: get_observation('{data_item_id}') NOT FOUND. Available keys ({len(available_keys)}): {available_keys[:10]}...")
        return result
    
    def get_observations_by_name(self, name: str) -> list:
        """Get all observations matching a name pattern."""
        return [
            data for data in self._data_cache.values()
            if name.lower() in data.get("name", "").lower()
        ]
