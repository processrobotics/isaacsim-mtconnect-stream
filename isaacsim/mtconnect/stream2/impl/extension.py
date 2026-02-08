# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import asyncio
import gc

import omni
import omni.kit.commands
import omni.ui as ui
from isaacsim.gui.components.element_wrappers import ScrollingWindow
from isaacsim.gui.components.menu import MenuItemDescription
from omni.kit.menu.utils import add_menu_items, remove_menu_items

<<<<<<< HEAD
from .global_variables import EXTENSION_TITLE, set_mtconnect_client, clear_mtconnect_client
from .ui_builder import UIBuilder
from .mtconnect_client import MTConnectClient

=======
from .global_variables import EXTENSION_TITLE
from .ui_builder import UIBuilder
from .mtconnect_client import MTConnectClient

# Global reference to the extension instance for external access
_extension_instance = None


def get_extension_instance():
    """Get the current extension instance."""
    return _extension_instance
>>>>>>> extension-instance


class Extension(omni.ext.IExt):
    def on_startup(self, ext_id: str):
        """Initialize extension and UI elements"""
<<<<<<< HEAD
        self.ext_id = ext_id

=======
        global _extension_instance
        _extension_instance = self
        
        self.ext_id = ext_id

        # Create the MTConnect client (owned by extension)
        self.mtconnect_client = MTConnectClient()

>>>>>>> extension-instance
        # Build Window
        self._window = ScrollingWindow(
            title=EXTENSION_TITLE, width=400, height=300, visible=False, dockPreference=ui.DockPreference.LEFT_BOTTOM
        )
        self._window.set_visibility_changed_fn(self._on_window)

        action_registry = omni.kit.actions.core.get_action_registry()
        action_registry.register_action(
            ext_id,
            f"CreateUIExtension:{EXTENSION_TITLE}",
            self._menu_callback,
            description=f"Open {EXTENSION_TITLE} Extension",
        )
        self._menu_items = [
            MenuItemDescription(name=EXTENSION_TITLE, onclick_action=(ext_id, f"CreateUIExtension:{EXTENSION_TITLE}"))
        ]

        add_menu_items(self._menu_items, EXTENSION_TITLE)

<<<<<<< HEAD
        # UI Builder
        self.ui_builder = UIBuilder()
        self.mtconnect_client = self.ui_builder.mtconnect_client
        
        # Register the MTConnect client for OmniGraph node access
        set_mtconnect_client(self.mtconnect_client)

    def on_shutdown(self):
=======
        # UI Builder - pass the extension reference so UI can access all state
        self.ui_builder = UIBuilder(self)

    # -------------------------------------------------------------------------
    # Public API for external scripts and UI
    # -------------------------------------------------------------------------
    
    def connect(self, agent_address: str) -> bool:
        """
        Connect to an MTConnect agent.
        
        Args:
            agent_address: The base URL of the MTConnect agent (e.g., "http://192.168.0.247:5000")
            
        Returns:
            True if connection successful, False otherwise
        """
        return self.mtconnect_client.connect(agent_address)
    
    def start_streaming(self) -> bool:
        """
        Start streaming data from the connected agent.
        
        Returns:
            True if streaming started successfully, False otherwise
        """
        return self.mtconnect_client.start_streaming()
    
    def stop_streaming(self):
        """Stop streaming data."""
        self.mtconnect_client.stop_streaming()
    
    def disconnect(self):
        """Disconnect from the agent and stop streaming."""
        self.mtconnect_client.disconnect()
    
    @property
    def is_streaming(self) -> bool:
        """Whether the client is currently streaming data."""
        return self.mtconnect_client.is_streaming
    
    @property
    def is_connected(self) -> bool:
        """Whether the client is connected to an agent."""
        return self.mtconnect_client.is_connected
    
    @property
    def agent_address(self) -> str:
        """The currently connected agent address."""
        return self.mtconnect_client.agent_address
    
    @property
    def data_cache(self) -> dict:
        """The current data cache from the MTConnect stream."""
        return self.mtconnect_client.data_cache

    def on_shutdown(self):
        global _extension_instance
        _extension_instance = None
        
>>>>>>> extension-instance
        remove_menu_items(self._menu_items, EXTENSION_TITLE)

        action_registry = omni.kit.actions.core.get_action_registry()
        action_registry.deregister_action(self.ext_id, f"CreateUIExtension:{EXTENSION_TITLE}")

        if self._window:
            self._window = None
<<<<<<< HEAD
        
        # Clear the global client reference
        clear_mtconnect_client()
        
        self.ui_builder.cleanup()
=======
        self.ui_builder.cleanup()
        
        # Cleanup client
        if self.mtconnect_client:
            self.mtconnect_client.stop_streaming()
            self.mtconnect_client = None
            
>>>>>>> extension-instance
        gc.collect()

    def _on_window(self, visible):
        if self._window.visible:
            self._build_ui()
        else:
            self.ui_builder.cleanup()

    def _build_ui(self):
        with self._window.frame:
            with ui.VStack(spacing=5, height=0):
                self.ui_builder.build_ui()

        async def dock_window():
            await omni.kit.app.get_app().next_update_async()

            def dock(space, name, location, pos=0.5):
                window = omni.ui.Workspace.get_window(name)
                if window and space:
                    window.dock_in(space, location, pos)
                return window

            tgt = ui.Workspace.get_window("Viewport")
            dock(tgt, EXTENSION_TITLE, omni.ui.DockPosition.LEFT, 0.33)
            await omni.kit.app.get_app().next_update_async()

        self._task = asyncio.ensure_future(dock_window())

    def _menu_callback(self):
<<<<<<< HEAD
        self._window.visible = not self._window.visible
=======
        self._window.visible = not self._window.visible
>>>>>>> extension-instance
