# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Standalone Isaac Sim script that monitors MTConnect device availability.
- Creates a cube in the scene
- Colors it GREEN when mxi_m001 is AVAILABLE
- Colors it RED when mxi_m001 is UNAVAILABLE

To use:
1. Start the MTConnect extension in Isaac Sim
2. Configure it to connect to your MTConnect agent
3. Start streaming data
4. Run this script in Isaac Sim's Python environment
"""
from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": False})

import sys
import os
from omni.kit.app import get_app
from pxr import Gf
from isaacsim.core.api import World
from isaacsim.core.utils.extensions import enable_extension
from isaacsim.core.api.objects import VisualCuboid, DynamicCuboid


class MTConnectDeviceMonitor:
    """Monitor MTConnect device availability and update cube color."""
    
    DATAITEM_ID = "mxi_m001_avail"
    CUBE_PATH = "/World/DeviceMonitorCube"
    GREEN = Gf.Vec3f(0.0, 1.0, 0.0)
    RED = Gf.Vec3f(1.0, 0.0, 0.0)
    
    def __init__(self):
        self.app = get_app()
        self.mtconnect_client = None
        self.cube = None
        self.cube_obj = None
        self.last_state = None
        
    def setup_mtconnect_client(self):
        """Get the MTConnect client from the extension."""
        try:
            
            
            # Add workspace path to sys.path
            workspace_path = os.path.join(
                os.path.dirname(__file__),
                "workspace",
                "isaacsim.mtconnect.extension"
            )
            if workspace_path not in sys.path:
                sys.path.insert(0, workspace_path)
            
            # Import the extension module directly
            import isaacsim_mtconnect_stream_python.extension as ext_module
            
            # Get the Extension instance
            ext = ext_module.Extension()
            
            # Initialize the extension by calling on_startup
            ext.on_startup("isaacsim.mtconnect.stream_python")
            
            self.mtconnect_client = ext.ui_builder.mtconnect_client
            print(f"MTConnect client obtained. Streaming: {self.mtconnect_client.is_streaming}")
            return True
        except Exception as e:
            print(f"Error accessing MTConnect extension: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_cube(self):
        """Create a cube in the scene."""
        
        # Create a cube
        self.cube_obj = DynamicCuboid(
            prim_path=self.CUBE_PATH,
            position=(0, 0, 0.5),
            size=0.5
        )
        self.cube = self.cube_obj.prim
        
        if self.cube:
            print(f"Cube created at {self.CUBE_PATH}")
        
        return self.cube is not None
    
    def set_cube_color(self, color: Gf.Vec3f):
        """Set the cube's display color."""
        if not self.cube_obj:
            return
        
        visual_material = self.cube_obj.get_applied_visual_material()
        if visual_material:
            import numpy as np
            color_array = np.array([color[0], color[1], color[2]])
            visual_material.set_color(color_array)
            print(f"Cube color set to {color}")
    
    def update_cube_from_mtconnect(self):
        """Update cube color based on MTConnect device availability."""
        if not self.mtconnect_client:
            return False
        
        # Get the observation for mxi_m001_avail
        obs = self.mtconnect_client.get_observation(self.DATAITEM_ID)
        
        if not obs:
            return False
        
        current_state = obs.get("value", "UNKNOWN")
        
        if current_state != self.last_state:
            print(f"Device availability changed: {current_state}")
        
            if current_state == "AVAILABLE":
                self.set_cube_color(self.GREEN)
                self.last_state = "AVAILABLE"
            elif current_state == "UNAVAILABLE":
                self.set_cube_color(self.RED)
                self.last_state = "UNAVAILABLE"
            else:
                print(f"Unknown state: {current_state}")
                return False
            
            return True
    
    def physics_callback(self, *args):
        """Physics callback for world.add_physics_callback."""
        self.update_cube_from_mtconnect()


def main():
    """Entry point for the standalone script."""
    print("=" * 60)
    print("MTConnect Device Monitor")
    print("=" * 60)
    
    # Create world
    world = World(stage_units_in_meters=1.0)
    world.scene.add_default_ground_plane()
    
    # Create monitor
    monitor = MTConnectDeviceMonitor()

    """Setup and register physics callback."""
    # Setup MTConnect client
    if not monitor.setup_mtconnect_client():
        return False
    
    # Create cube
    if not monitor.create_cube():
        print("Failed to create cube")
        return False
    
    # Register physics callback
    world.add_physics_callback("mtconnect_monitor", monitor.physics_callback)
    monitor.mtconnect_client.connect('192.168.0.247:5000')
    monitor.mtconnect_client.start_streaming()
    print(f"Monitoring {monitor.DATAITEM_ID}")
    world.reset()
    # Main simulation loop
    try:
        while True:
            world.step(render=True)
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
    finally:
        monitor.mtconnect_client.stop_streaming()
        simulation_app.close()


if __name__ == "__main__":
    main()
