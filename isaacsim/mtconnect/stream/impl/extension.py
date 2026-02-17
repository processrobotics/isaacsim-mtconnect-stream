# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import asyncio
import gc

import omni
import omni.kit.commands
import omni.ui as ui
import omni.usd
from isaacsim.gui.components.element_wrappers import ScrollingWindow
from isaacsim.gui.components.menu import MenuItemDescription
from omni.kit.menu.utils import add_menu_items, remove_menu_items
from pxr import Sdf

from .global_variables import EXTENSION_TITLE
from .ui_builder import UIBuilder
from .mtconnect_client import MTConnectClient

# Global reference to the extension instance for external access
_extension_instance = None


def get_extension_instance():
    """Get the current extension instance."""
    return _extension_instance


class Extension(omni.ext.IExt):
    def on_startup(self, ext_id: str):
        """Initialize extension and UI elements"""
        global _extension_instance
        _extension_instance = self
        
        self.ext_id = ext_id
        self._last_agent_url = None

        # Create the MTConnect client (owned by extension)
        self.mtconnect_client = MTConnectClient()
        
        # Load settings from USD if available
        self._load_settings_from_usd()

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

        # UI Builder - pass the extension reference so UI can access all state
        self.ui_builder = UIBuilder(self)

    # -------------------------------------------------------------------------
    # USD Settings Persistence
    # -------------------------------------------------------------------------
    
    def _get_settings_prim(self):
        """Get or create the MTConnect settings prim in USD."""
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return None
        
        settings_path = "/World/MTConnectSettings"
        prim = stage.GetPrimAtPath(settings_path)
        
        if not prim.IsValid():
            # Create if doesn't exist
            prim = stage.DefinePrim(settings_path)
        
        return prim
    
    def _load_settings_from_usd(self):
        """Load saved settings from USD on startup."""
        stage = omni.usd.get_context().get_stage()
        if not stage:
            print("[MTConnect] No stage available on startup")
            return
        
        settings_path = "/World/MTConnectSettings"
        prim = stage.GetPrimAtPath(settings_path)
        
        if not prim or not prim.IsValid():
            print(f"[MTConnect] No settings prim found at {settings_path}")
            return
        
        # Read agent URL if it exists
        if prim.HasAttribute("mtconnect:agentUrl"):
            url_attr = prim.GetAttribute("mtconnect:agentUrl")
            saved_url = url_attr.Get()
            if saved_url:
                self._last_agent_url = saved_url
                print(f"[MTConnect] Loaded saved agent URL from USD: {saved_url}")
            else:
                print("[MTConnect] Agent URL attribute exists but is empty")
        else:
            print("[MTConnect] No saved agent URL found in USD")
    
    def _save_agent_url_to_usd(self, agent_address: str):
        """Save the agent URL to USD for persistence."""
        stage = omni.usd.get_context().get_stage()
        if not stage:
            print("[MTConnect] ERROR: No stage available to save agent URL")
            return
        
        settings_path = "/World/MTConnectSettings"
        
        try:
            from pxr import Usd
            
            # Get or create the prim directly
            prim = stage.GetPrimAtPath(settings_path)
            if not prim.IsValid():
                # Create the prim using direct USD API
                prim = stage.DefinePrim(settings_path)
                print(f"[MTConnect] Created prim at {settings_path}")
            
            if not prim or not prim.IsValid():
                print(f"[MTConnect] ERROR: Could not create or get prim at {settings_path}")
                return
            
            # Create or get the attribute
            attr_name = "mtconnect:agentUrl"
            if not prim.HasAttribute(attr_name):
                attr = prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.String, custom=True)
                print(f"[MTConnect] Created attribute {attr_name}")
            else:
                attr = prim.GetAttribute(attr_name)
            
            # Set the value
            attr.Set(agent_address)
            print(f"[MTConnect] Set attribute value to: {agent_address}")
            
            # Verify it was saved
            saved_value = attr.Get()
            if saved_value != agent_address:
                print(f"[MTConnect] WARNING: Verification failed. Set: {agent_address}, Got: {saved_value}")
                
        except Exception as e:
            print(f"[MTConnect] ERROR saving agent URL to USD: {e}")
            import traceback
            traceback.print_exc()

    # -------------------------------------------------------------------------
    # Public API for external scripts and UI
    # -------------------------------------------------------------------------
    
    def reload_settings_from_usd(self):
        """
        Reload MTConnect settings from the current USD stage.
        Call this after opening a new stage to load any saved agent settings.
        """
        self._load_settings_from_usd()
    
    def connect(self, agent_address: str = "") -> bool:
        """
        Connect to an MTConnect agent.
        
        Args:
            agent_address: The base URL of the MTConnect agent (e.g., "http://demo.mtconnect.org:5000")
                          If empty, will attempt to use the saved agent URL from USD scene settings.
            
        Returns:
            True if connection successful, False otherwise
        """
        # If no agent address provided, try to use saved URL from USD
        if not agent_address:
            if self._last_agent_url:
                print(f"[MTConnect] Using saved agent URL from scene: {self._last_agent_url}")
                agent_address = self._last_agent_url
            else:
                print("[MTConnect] ERROR: No agent address provided and no saved URL found in scene")
                return False
        
        result = self.mtconnect_client.connect(agent_address)
        if result:
            self._last_agent_url = agent_address
            self._save_agent_url_to_usd(agent_address)
        return result
    
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
    def last_agent_url(self) -> str:
        """The last agent URL used (loaded from USD or most recent connection)."""
        return self._last_agent_url
    
    @property
    def data_cache(self) -> dict:
        """The current data cache from the MTConnect stream."""
        return self.mtconnect_client.data_cache

    def on_shutdown(self):
        global _extension_instance
        _extension_instance = None
        
        remove_menu_items(self._menu_items, EXTENSION_TITLE)

        action_registry = omni.kit.actions.core.get_action_registry()
        action_registry.deregister_action(self.ext_id, f"CreateUIExtension:{EXTENSION_TITLE}")

        if self._window:
            self._window = None
        self.ui_builder.cleanup()
        
        # Cleanup client
        if self.mtconnect_client:
            self.mtconnect_client.stop_streaming()
            self.mtconnect_client = None
            
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
        self._window.visible = not self._window.visible
