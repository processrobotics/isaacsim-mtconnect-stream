# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import omni.ui as ui
from isaacsim.gui.components.element_wrappers import CollapsableFrame, StateButton, TextBlock
from isaacsim.gui.components.ui_utils import get_style

from .global_variables import DEFAULT_AGENT_ADDRESS
from .mtconnect_client import MTConnectClient, MTCONNECT_AVAILABLE


class UIBuilder:
    def __init__(self):
        self._mtconnect_client = MTConnectClient()
        self._agent_address_model: ui.SimpleStringModel = None
        self._status_label: ui.Label = None
        self._data_label: ui.Label = None
        self._stream_btn: StateButton = None
        
        # Set up callbacks
        self._mtconnect_client.set_callbacks(
            on_data_update=self._on_data_update,
            on_error=self._on_error,
            on_status_change=self._on_status_change
        )

    @property
    def mtconnect_client(self):
        """Public accessor for the MTConnect client."""
        return self._mtconnect_client

    def cleanup(self):
        """Clean up resources when extension is closed."""
        self._mtconnect_client.disconnect()

    def build_ui(self):
        """Build the MTConnect streaming UI."""
        
        # Connection Settings Frame
        connection_frame = CollapsableFrame("Connection Settings", collapsed=False)
        with connection_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                # Agent Address Input
                with ui.HStack(height=0, spacing=5):
                    ui.Label("Agent Address:", width=100)
                    self._agent_address_model = ui.SimpleStringModel(DEFAULT_AGENT_ADDRESS)
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
                
                # Check if mtconnect is available
                if not MTCONNECT_AVAILABLE:
                    self._stream_btn.enabled = False
        
        # Status Frame
        status_frame = CollapsableFrame("Status", collapsed=False)
        with status_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                self._status_label = ui.Label(
                    "Ready" if MTCONNECT_AVAILABLE else "Error: mtconnect package not installed",
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
                self._data_label = ui.Label(
                    "No data",
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
        if self._data_label:
            summary = self._mtconnect_client.get_data_summary()
            self._data_label.text = summary

    def _on_error(self, error: str):
        """Callback when an error occurs."""
        self._update_status(f"Error: {error}")

    def _on_status_change(self, status: str):
        """Callback when status changes."""
        self._update_status(status)
        if self._stream_btn:
            if "Streaming stopped" in status or "Disconnected" in status:
                self._stream_btn.reset()

    def _update_status(self, status: str):
        """Update the status label."""
        if self._status_label:
            self._status_label.text = status
