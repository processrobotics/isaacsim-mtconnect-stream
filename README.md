# MTConnect Stream Extension for Isaac Sim

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

An NVIDIA Isaac Sim extension that enables real-time streaming of MTConnect data from MTConnect Agents into Isaac Sim simulations. This extension bridges the gap between MTConnect-enabled manufacturing equipment and robotic simulations, allowing for digital twin implementations, robot training, and simulation-based validation.

## Overview

This extension provides MTConnect integration for Isaac Sim through:

- **MTConnect Client Library**: A boiler plate swagger python client generated from cppagent's openapi.json
- **Isaac Sim Extension**: A simple user-friendly UI for connecting to and streaming data from an MTConnect Agent
- **OmniGraph Node**: Integration with Isaac Sim's visual scripting system. Quickly connect your assets to MTConnect data via ActionGraphs

## Features

- ✅ **Real-time Streaming**: Efficient HTTP streaming using multipart/x-mixed-replace protocol
- ✅ **Data Caching**: Local cache of MTConnect observations with automatic updates
- ✅ **Visual UI**: Intuitive interface for connection management and data monitoring
- ✅ **OmniGraph Integration**: Custom node for incorporating MTConnect data into action graphs
- ✅ **Flexible Callbacks**: Event-driven architecture for data updates, errors, and status changes
- ✅ **Device Monitoring**: Example implementation showing visual feedback based on device state

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Usage](#usage)
  - [Extension UI](#extension-ui)
  - [Programmatic Access](#programmatic-access)
  - [OmniGraph Node](#omnigraph-node)
- [Examples](#examples)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Installation

### Prerequisites

- NVIDIA Isaac Sim 4.0 or later
- Python 3.10+
- Access to an MTConnect Agent (or use a public demo agent)

### Install Dependencies

The extension requires the `mtconnect-rest-python` library:

```bash
pip install git+https://github.com/processrobotics/mtconnect-rest-python.git
```

### Install Extension

1. Clone this repository:
   ```bash
   git clone https://github.com/processrobotics/isaacsim-mtconnect-stream.git
   cd isaacsim-mtconnect-stream
   ```

2. Enable the extension in Isaac Sim:
   ```bash
   # Method 1: Using command line
   ./isaac-sim.sh --ext-folder /path/to/isaacsim-mtconnect-stream --enable isaacsim.mtconnect.stream

   # Method 2: Using Extension Manager in Isaac Sim UI
   # Window -> Extensions -> Add Extension Search Path -> Browse to extension folder
   ```

## Quick Start

### Using the Extension UI

1. Launch Isaac Sim and open the MTConnect Stream extension from the menu:
   - **Isaac Examples** → **MTConnect Stream**

2. In the extension window:
   - Enter your MTConnect Agent address (e.g., `http://192.168.0.247:5000`)
   - Click **START STREAM** to begin streaming data
   - Monitor the data cache in real-time

3. The extension will:
   - Connect to the agent
   - Fetch the current state with `/current`
   - Start streaming updates with `/sample?interval=100&from={nextSequence}`
   - Display cached observations and metadata

### Programmatic Example

```python
from isaacsim.mtconnect.stream.impl.mtconnect_client import MTConnectClient

# Create client
client = MTConnectClient()

# Set up callbacks
def on_data_update(data):
    print(f"Received {len(data)} observations")
    
client.set_callbacks(on_data_update=on_data_update)

# Connect and stream
if client.connect("http://localhost:5000"):
    client.start_streaming()
    
    # Get specific observation
    obs = client.get_observation("avail")
    if obs:
        print(f"Device availability: {obs['value']}")
```

## Architecture

### Component Overview

```
isaacsim-mtconnect-stream/
├── isaacsim/mtconnect/stream/          # Extension package
│   ├── impl/                             # Core implementation
│   │   ├── mtconnect_client.py          # MTConnect client library
│   │   ├── extension.py                 # Extension initialization
│   │   ├── ui_builder.py                # UI components
│   │   └── global_variables.py          # Configuration and client registry
│   ├── ogn/                             # OmniGraph integration
│   │   └── python/nodes/                # OmniGraph node definitions
│   │       ├── OgnIsaacsimMtconnectStreamPy.py
│   │       └── OgnIsaacsimMtconnectStreamPy.ogn
│   └── __init__.py
├── config/                               # Extension metadata
│   └── extension.toml                   # Extension configuration
├── mtconnect_device_monitor.py          # Standalone example script
└── docs/                                # Documentation
```

### MTConnect Client Architecture

The `MTConnectClient` class provides:

1. **Connection Management**: HTTP client configuration and connection to MTConnect Agents
2. **Data Acquisition**: Initial state fetch via `/current` endpoint
3. **Streaming**: Continuous updates via `/sample?interval=X` with multipart streaming
4. **Data Processing**: JSON parsing and observation extraction
5. **Caching**: In-memory storage indexed by `dataItemId`
6. **Event System**: Callbacks for data updates, errors, and status changes

### Extension Architecture

The extension follows a singleton pattern where a single extension instance owns and manages the MTConnect client:

1. **Extension Startup**: Creates MTConnect client and registers itself globally
2. **Global Access**: `get_extension_instance()` provides access to the extension
3. **Public API**: Extension exposes methods like `connect()`, `start_streaming()`, `stop_streaming()`
4. **OmniGraph Integration**: Nodes access client through the extension instance
5. **Extension Shutdown**: Cleans up client and clears global reference

This design provides a single source of truth where the extension owns all state and exposes a clean public API for external access.

### OmniGraph Integration

The OmniGraph node accesses the MTConnect client through the global extension instance:

1. **Extension Registration**: Extension registers itself globally in `extension.py`
2. **Node Access**: OmniGraph node calls `get_extension_instance()` to get extension
3. **Client Access**: Node accesses `extension.mtconnect_client` to query data
4. **Data Retrieval**: Node queries client's data cache and returns values

This design allows the OmniGraph node (which runs in a separate execution context) to access the same MTConnect client instance owned by the extension.

### Data Flow

```
MTConnect Agent → HTTP Stream → MTConnect Client → Data Cache → UI/OmniGraph/Scripts
                                      ↓               ↑
                                   Extension      Callbacks
                                (Global Instance)    ↓
                                      ↓          UI Updates
                                OmniGraph Node
                              (get_extension_instance)
```

## Usage

### Extension UI

The extension provides a docked window with three main sections:

#### 1. Connection Settings
- **Agent Address**: URL of the MTConnect Agent (e.g., `http://192.168.0.247:5000`)
- **START STREAM / STOP STREAM**: Toggle button for stream control

#### 2. Status
- Displays current connection status
- Shows error messages and installation instructions if dependencies are missing

#### 3. Data Cache
- **Instance ID**: MTConnect agent instance identifier
- **Next Sequence**: Next sequence number for streaming
- **Buffer**: Current buffer range (first-last sequence)
- **Cached Items**: Number of observations in cache
- **Devices**: Breakdown of observations by device

### Programmatic Access

#### Using the Extension API

The recommended way to access MTConnect functionality is through the extension instance:

```python
from isaacsim.core.utils.extensions import enable_extension
from isaacsim.mtconnect.stream.impl.extension import get_extension_instance

# Enable the extension first
enable_extension("isaacsim.mtconnect.stream")

# Get the extension instance
extension = get_extension_instance()

# Connect to agent using extension API
if extension.connect("http://192.168.0.247:5000"):
    extension.start_streaming()
    print(f"Connected to: {extension.agent_address}")
    print(f"Streaming: {extension.is_streaming}")
    
    # Access data cache
    for data_item_id, obs in extension.data_cache.items():
        print(f"{data_item_id}: {obs['value']}")
```

#### Direct Client Access (Advanced)

You can also access the client directly for more control:

```python
from isaacsim.mtconnect.stream.impl.extension import get_extension_instance

extension = get_extension_instance()
client = extension.mtconnect_client

# Direct client operations
if client.connect("http://192.168.0.247:5000"):
    print("Connected successfully")
    print(client.get_data_summary())
```

#### Streaming with Callbacks

```python
from isaacsim.mtconnect.stream.impl.extension import get_extension_instance

extension = get_extension_instance()
client = extension.mtconnect_client

def on_data(data_cache):
    """Called when new data arrives"""
    for data_item_id, obs in data_cache.items():
        print(f"{data_item_id}: {obs['value']}")

def on_error(error_msg):
    """Called on errors"""
    print(f"Error: {error_msg}")

def on_status(status_msg):
    """Called on status changes"""
    print(f"Status: {status_msg}")

client.set_callbacks(
    on_data_update=on_data,
    on_error=on_error,
    on_status_change=on_status
)

# Use extension API to connect and stream
extension.connect("http://192.168.0.247:5000")
extension.start_streaming()

# Later...
extension.stop_streaming()
extension.disconnect()
```

#### Querying Cached Data

```python
from isaacsim.mtconnect.stream.impl.extension import get_extension_instance

extension = get_extension_instance()
client = extension.mtconnect_client

# Get specific observation by dataItemId
observation = client.get_observation("mxi_m001_avail")
if observation:
    print(f"Value: {observation['value']}")
    print(f"Timestamp: {observation['timestamp']}")
    print(f"Sequence: {observation['sequence']}")

# Search by name pattern
temp_observations = client.get_observations_by_name("temperature")
for obs in temp_observations:
    print(f"{obs['name']}: {obs['value']}")

# Access entire cache via extension property
for data_item_id, obs in extension.data_cache.items():
    print(f"{data_item_id}: {obs['value']} @ {obs['timestamp']}")
```

### OmniGraph Node

The extension includes an OmniGraph node for visual scripting integration:

**Node**: `MTConnect Stream Node`

**Inputs**:
- `dataItemIds` (token[]): Array of MTConnect dataItem IDs to retrieve (e.g., `["spindle_speed", "mxi_m001_avail"]`)

**Outputs**:
- `values` (double[]): Array of numeric values corresponding to the dataItem IDs
- `timestamps` (token[]): Array of ISO 8601 timestamps for each value

**How it Works**:
1. The node queries the MTConnect client's data cache for each specified dataItemId
2. Values are converted to numeric format:
   - Numeric values are used directly
   - String "AVAILABLE" → 1.0
   - String "UNAVAILABLE" → 0.0
   - Other non-numeric strings → 0.0
3. If a dataItemId is not found, returns 0.0 with empty timestamp

**Usage in Action Graph**:
1. Ensure the MTConnect Stream extension is enabled and connected to an agent
2. Add the **MTConnect Stream Node** to your action graph
3. Connect an array of dataItemId strings to the `dataItemIds` input
4. Use the `values` and `timestamps` outputs to drive simulation behavior

**Example Action Graph Flow**:
```
[Constant Token Array: ["spindle_speed", "feed_rate"]] 
    → [MTConnect Stream Node] 
        → values → [Set Prim Attribute / Control Joint / etc.]
        → timestamps → [Display in UI / Log]
```

**Important Notes**:
- The node accesses the shared MTConnect client from the extension
- Make sure to start streaming data in the extension UI before using the node
- The node updates on every graph evaluation tick
- Returns empty arrays if the client is not connected or data is unavailable

## Examples
### Action Graph
- **`mtc-cube-demo.usd`**: `mtc-cube-demo.usd` is a pre-built scene demonstrating the use of ActionGraphs to connect X/Y/Z position from the OKUMA device at demo.mtconnect.org tot he position of a cube
- **`mtconnect_cube_demo.py`**: A convenient standalone python script that handles launching IsaacSim, loading `mtc-cube-demo.usd`, starting streaming from demo.mtconnect.org, and running the simulation

### Device Availability Monitor

The included `mtconnect_device_monitor.py` script demonstrates a standalone IsaacSim script:
- Connecting to an MTConnect Agent
- Monitoring device availability
- Visual feedback via colored cube (GREEN=AVAILABLE, RED=UNAVAILABLE)

**To run**:
```bash
# From Isaac Sim Python environment
python mtconnect_device_monitor.py
```

**What it does**:
1. Creates an Isaac Sim world with a cube
2. Connects to MTConnect Agent at `192.168.0.247:5000`
3. Monitors the `mxi_m001_avail` dataItem
4. Changes cube color based on device state
5. Updates every physics step

**Key Code**:
```python
class MTConnectDeviceMonitor:
    DATAITEM_ID = "mxi_m001_avail"
    
    def update_cube_from_mtconnect(self):
        obs = self.mtconnect_client.get_observation(self.DATAITEM_ID)
        if obs:
            if obs.get("value") == "AVAILABLE":
                self.set_cube_color(self.GREEN)
            elif obs.get("value") == "UNAVAILABLE":
                self.set_cube_color(self.RED)
```

### Custom Integration Example

Here's how to integrate MTConnect data into your own Isaac Sim application:

```python
from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": False})

from isaacsim.core.api import World
from isaacsim.core.utils.extensions import enable_extension
from isaacsim.mtconnect.stream.impl.extension import get_extension_instance

# Enable the extension
enable_extension("isaacsim.mtconnect.stream")

# Create world
world = World()
world.scene.add_default_ground_plane()

# Get extension and setup MTConnect
extension = get_extension_instance()
extension.connect("http://192.168.0.247:5000")
extension.start_streaming()

# Physics callback
def physics_step(step_size):
    # Get MTConnect data via extension
    client = extension.mtconnect_client
    spindle_speed = client.get_observation("spindle_speed")
    if spindle_speed:
        speed_value = float(spindle_speed['value'])
        # Use the data to control simulation
        # e.g., update robot joint velocities
        
world.add_physics_callback("mtconnect_update", physics_step)

# Run simulation
world.reset()
while simulation_app.is_running():
    world.step(render=True)

# Cleanup
extension.stop_streaming()
simulation_app.close()
```

## API Reference

### Extension API

The extension provides a high-level API for MTConnect operations:

#### `get_extension_instance() -> Extension`
Get the global extension instance.

```python
from isaacsim.mtconnect.stream.impl.extension import get_extension_instance
extension = get_extension_instance()
```

#### Extension Methods

##### `connect(agent_address: str) -> bool`
Connect to an MTConnect Agent.

**Parameters**:
- `agent_address`: URL of the MTConnect Agent (e.g., `"http://192.168.0.247:5000"`)

**Returns**: `True` if successful, `False` otherwise

##### `start_streaming() -> bool`
Start streaming data from the connected agent.

**Returns**: `True` if successful, `False` otherwise

##### `stop_streaming()`
Stop streaming data.

##### `disconnect()`
Disconnect from the agent and stop streaming.

#### Extension Properties

##### `is_streaming: bool`
Whether currently streaming data.

##### `is_connected: bool`
Whether connected to an agent.

##### `agent_address: str`
The currently connected agent address.

##### `data_cache: dict`
The current data cache from the MTConnect stream.

##### `mtconnect_client: MTConnectClient`
Direct access to the underlying MTConnect client.

### MTConnectClient

The client provides low-level MTConnect operations:

#### Constructor
```python
# Note: Usually accessed via extension.mtconnect_client
client = extension.mtconnect_client
```

#### Methods

##### `connect(agent_address: str) -> bool`
Connect to an MTConnect Agent and fetch initial state.

**Parameters**:
- `agent_address`: URL of the MTConnect Agent (e.g., `"http://192.168.0.247:5000"`)

**Returns**: `True` if successful, `False` otherwise

##### `start_streaming() -> bool`
Start streaming data from the agent.

**Returns**: `True` if streaming started, `False` otherwise

##### `stop_streaming()`
Stop the streaming loop.

##### `disconnect()`
Disconnect from the agent and clean up resources.

##### `get_observation(data_item_id: str) -> Optional[dict]`
Get a specific observation from the cache.

**Parameters**:
- `data_item_id`: The MTConnect dataItemId

**Returns**: Dictionary with observation data or `None`

##### `get_observations_by_name(name: str) -> list`
Get all observations matching a name pattern (case-insensitive).

**Parameters**:
- `name`: Name or partial name to search for

**Returns**: List of matching observation dictionaries

##### `get_data_summary() -> str`
Get a formatted string summary of cached data.

##### `set_callbacks(on_data_update, on_error, on_status_change)`
Set callback functions for events.

**Parameters**:
- `on_data_update`: `Callable[[dict], None]` - Called when data is updated
- `on_error`: `Callable[[str], None]` - Called on errors
- `on_status_change`: `Callable[[str], None]` - Called on status changes

#### Properties

##### `is_streaming: bool`
Returns `True` if currently streaming data.

##### `data_cache: dict`
Dictionary of all cached observations, keyed by `dataItemId`.

##### `header: MTConnectHeader`
MTConnect header information (instance ID, sequence numbers, etc.).

### Observation Dictionary Format

Each observation in the cache is a dictionary with:

```python
{
    "device": str,           # Device name
    "category": str,         # "Samples", "Events", or "Condition"
    "dataItemId": str,       # Unique identifier
    "name": str,            # Human-readable name
    "value": Any,           # Current value
    "timestamp": str,       # ISO 8601 timestamp
    "sequence": int,        # Sequence number
    # Additional fields may include:
    "subType": str,         # DataItem subType
    "units": str,          # Units of measurement
    # ... other MTConnect attributes
}
```

## Configuration

### Extension Configuration

Edit `config/extension.toml` to customize:

```toml
[package]
version = "0.1.0"
category = "simulation"
title = "MTConnect Stream"
description = "Streams data from an MTConnect Agent"

[dependencies]
"omni.graph" = {}
"omni.graph.tools" = {}

[settings]
exts."isaacsim.mtconnect.stream".timeout = 5
```

### Default Agent Address

Modify in `isaacsim/mtconnect/stream/impl/global_variables.py`:

```python
DEFAULT_AGENT_ADDRESS = "http://localhost:5000"
```

### Streaming Parameters

Adjust in `MTConnectClient.__init__()`:

```python
self._stream_interval_ms = 100      # Polling interval in milliseconds
self._stream_heartbeat_ms = 10000   # Heartbeat interval in milliseconds
```

## Troubleshooting

### Common Issues

#### "mtconnect package not installed"

**Solution**: Install the required dependency:
```bash
pip install git+https://github.com/processrobotics/mtconnect-rest-python.git
```

#### Connection Timeout

**Symptoms**: Extension shows "Connection failed" or times out

**Solutions**:
1. Verify the MTConnect Agent is running: Open `http://your-agent:5000/current` in a browser
2. Check network connectivity: `ping your-agent-ip`
3. Ensure the agent URL includes the protocol: `http://` or `https://`
4. Check firewall settings on both client and agent sides

#### No Data in Cache

**Symptoms**: Connected successfully but data cache remains empty

**Solutions**:
1. Verify the agent has devices configured: Check `http://your-agent:5000/probe`
2. Ensure data is available: Check `http://your-agent:5000/current` for observations
3. Review Isaac Sim console for JSON parsing errors

#### Streaming Stops Unexpectedly

**Symptoms**: Stream starts but stops after a short time

**Solutions**:
1. Check MTConnect Agent logs for errors
2. Verify network stability
3. Increase `_stream_heartbeat_ms` for unstable connections
4. Review console output for exceptions

#### OmniGraph Node Returns Zeros

**Symptoms**: OmniGraph node outputs all zeros or empty arrays

**Solutions**:
1. Ensure the extension is connected and streaming: Open the MTConnect Stream extension UI and verify connection status
2. Check that the dataItemIds match exactly what's in the agent: Use `/probe` endpoint to verify dataItem IDs
3. Verify data is in the cache: Check the "Data Cache" section in the extension UI
4. Review console logs for OmniGraph node errors
5. Make sure the dataItemIds input is properly connected in the action graph

#### OmniGraph Node Value Conversion

The OmniGraph node converts MTConnect values to numeric format:
- **Numeric values**: Used directly (e.g., `123.45` → `123.45`)
- **"AVAILABLE"**: Converted to `1.0`
- **"UNAVAILABLE"**: Converted to `0.0`
- **Other strings**: Attempt numeric conversion, default to `0.0` if not possible
- **Missing data**: Returns `0.0` with empty timestamp

If you need different conversion logic, you can process the values further in your action graph or modify the node's compute function.

### Debug Logging

The extension uses Isaac Sim's `carb` logging system. Enable detailed logs:

```python
import carb
carb.settings.get_settings().set("/log/level", "verbose")
```

Logs will show:
- Connection attempts and responses
- JSON parsing details
- Sequence number progression
- Stream events and errors

### Testing Without Hardware

Use a public MTConnect Agent demo:
```
http://agent.mtconnect.org
```

Or run a local simulator:
```bash
# Using mtconnect/agent Docker image
docker run -p 5000:5000 mtconnect/agent
```

## Contributing

We welcome contributions! To contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes with clear commit messages
4. Add tests if applicable
5. Submit a pull request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/processrobotics/isaacsim-mtconnect-stream.git
cd isaacsim-mtconnect-stream

# Install development dependencies
pip install -r requirements-dev.txt  # if available

# Enable extension in development mode
# Follow installation instructions above
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Document public APIs with docstrings
- Keep functions focused and concise

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

```
Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0
```

## Acknowledgments

- Built for [NVIDIA Isaac Sim](https://developer.nvidia.com/isaac-sim)
- Uses [mtconnect-rest-python](https://github.com/processrobotics/mtconnect-rest-python) library
- Implements [MTConnect](https://www.mtconnect.org/) standard protocol

## Support

- **Issues**: Report bugs and request features via [GitHub Issues](https://github.com/processrobotics/isaacsim-mtconnect-stream/issues)
- **Documentation**: Additional docs in the `docs/` directory
- **MTConnect Standard**: [https://www.mtconnect.org/](https://www.mtconnect.org/)
- **Isaac Sim Docs**: [https://docs.omniverse.nvidia.com/isaacsim/](https://docs.omniverse.nvidia.com/isaacsim/)

## Roadmap

Future enhancements under consideration:

- [ ] Support for MTConnect Assets streaming
- [ ] WebSocket transport option
- [ ] Data persistence and replay functionality
- [ ] Advanced filtering and data transformation
- [ ] Performance metrics and monitoring
- [ ] Additional OmniGraph nodes for common use cases
- [ ] Integration examples with ROS2 bridges
- [ ] Multi-agent support for coordinated systems

---

**Version**: 0.1.0  
**Last Updated**: February 2026  
**Maintainer**: Process Robotics
