# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations
from typing import TYPE_CHECKING

import omni.kit.app
import omni.ui as ui
from isaacsim.gui.components.element_wrappers import CollapsableFrame, StateButton, TextBlock
from isaacsim.gui.components.ui_utils import get_style

from .global_variables import DEFAULT_AGENT_ADDRESS
from .mtconnect_client import MTCONNECT_AVAILABLE

if TYPE_CHECKING:
    from .extension import Extension


class UIBuilder:
    def __init__(self, extension: "Extension"):
        self._extension = extension
        self._mtconnect_client = extension.mtconnect_client
        self._agent_address_model: ui.SimpleStringModel = None
        self._status_label: ui.Label = None
        self._data_label: ui.Label = None
        self._stream_btn: StateButton = None
        
        # Set up callbacks for UI updates
        self._mtconnect_client.set_callbacks(
            on_data_update=self._on_data_update,
            on_error=self._on_error,
            on_status_change=self._on_status_change
        )

    def cleanup(self):
        """Clean up resources when extension window is closed."""
        # Clear callbacks to break circular references
        if self._mtconnect_client:
            self._mtconnect_client.set_callbacks(
                on_data_update=None,
                on_error=None,
                on_status_change=None
            )
        
        # Clear all UI element references
        self._agent_address_model = None
        self._status_label = None
        self._data_label = None
        self._stream_btn = None
        
        # Clear client and extension references to allow garbage collection
        self._mtconnect_client = None
        self._extension = None

    def build_ui(self):
        """Build the MTConnect streaming UI."""
        
        # Get current state from client
        current_address = self._mtconnect_client.agent_address or DEFAULT_AGENT_ADDRESS
        is_streaming = self._mtconnect_client.is_streaming
        
        # Connection Settings Frame
        connection_frame = CollapsableFrame("Connection Settings", collapsed=False)
        with connection_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                # Agent Address Input
                with ui.HStack(height=0, spacing=5):
                    ui.Label("Agent Address:", width=100)
                    self._agent_address_model = ui.SimpleStringModel(current_address)
                    ui.StringField(model=self._agent_address_model, height=22)
                
                ui.Spacer(height=5)
                
                # Start/Stop Stream Button
                self._stream_btn = StateButton(
                    "Stream Control",
                    "START STREAM",
                    "STOP STREAM",
                    on_a_click_fn=self._on_start_stream,
                    on_b_click_fn=self._on_stop_stream,
                )
                
                # Sync button state with current streaming state
                if is_streaming:
                    # Set to B state by updating button text (StateButton tracks state via text)
                    self._stream_btn.state_button.text = "STOP STREAM"
                
                # Check if mtconnect is available
                if not MTCONNECT_AVAILABLE:
                    self._stream_btn.enabled = False
        
        # Status Frame
        status_frame = CollapsableFrame("Status", collapsed=False)
        with status_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                # Determine initial status text based on current state
                if not MTCONNECT_AVAILABLE:
                    initial_status = "Error: mtconnect package not installed"
                elif is_streaming:
                    initial_status = f"Streaming from {current_address}"
                elif self._mtconnect_client.is_connected:
                    initial_status = f"Connected to {current_address}"
                else:
                    initial_status = "Ready"
                
                self._status_label = ui.Label(
                    initial_status,
                    height=20,
                    word_wrap=True
                )
                
                if not MTCONNECT_AVAILABLE:
                    ui.Label(
                        "Install with: pip install git+https://github.com/processrobotics/mtconnect-rest-python.git",
                        height=40,
                        word_wrap=True,
                        style={"color": 0xFF888888}
                    )
        
        # Data Display Frame
        data_frame = CollapsableFrame("Data Cache", collapsed=False)
        with data_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                # Show current data cache if available
                initial_data = self._mtconnect_client.get_data_summary() if self._mtconnect_client.data_cache else "No data"
                self._data_label = ui.Label(
                    initial_data,
                    height=100,
                    word_wrap=True,
                    alignment=ui.Alignment.LEFT_TOP
                )

    def _on_start_stream(self):
        """Called when Start Stream button is clicked."""
        try:
            import carb
            carb.log_warn("MTConnect UI: Start clicked")
        except Exception:
            pass
        print("MTConnect UI: Start clicked")
        agent_address = self._agent_address_model.get_value_as_string()
        
        if not agent_address:
            self._update_status("Error: Please enter an agent address")
            self._stream_btn.reset()
            return
        
        # Connect and start streaming
        if self._mtconnect_client.connect(agent_address):
            if not self._mtconnect_client.start_streaming():
                self._stream_btn.reset()
        else:
            self._stream_btn.reset()

    def _on_stop_stream(self):
        """Called when Stop Stream button is clicked."""
        try:
            import carb
            carb.log_warn("MTConnect UI: Stop clicked")
        except Exception:
            pass
        print("MTConnect UI: Stop clicked")
        self._mtconnect_client.stop_streaming()

    def _on_data_update(self, data: dict):
        """Callback when new data is received."""
        # Update UI directly
        self._update_data_label()

    def _update_data_label(self):
        """Update the data label with current summary."""
        if self._data_label:
            summary = self._mtconnect_client.get_data_summary()
            self._data_label.text = summary

    def _on_error(self, error: str):
        """Callback when an error occurs."""
        self._update_status(f"Error: {error}")

    def _on_status_change(self, status: str):
        """Callback when status changes."""
        self._update_status_and_button(status)

    def _update_status_and_button(self, status: str):
        """Update the status label and button state."""
        self._update_status(status)
        if self._stream_btn:
            if "Streaming stopped" in status or "Disconnected" in status:
                self._stream_btn.reset()

    def _update_status(self, status: str):
        """Update the status label."""
        if self._status_label:
            self._status_label.text = status
