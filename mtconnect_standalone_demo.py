# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Standalone Isaac Sim script that monitors MTConnect device position data.
- Creates a cube in the scene
- Reads X/Y/Z positions from demo.mtconnect.org/OKUMA
- Updates cube position based on MTConnect data

To use:
1. Start the MTConnect extension in Isaac Sim
2. Configure it to connect to demo.mtconnect.org
3. Start streaming data
4. Run this script in Isaac Sim's Python environment
"""
from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": False})

import carb
import numpy as np
from omni.kit.app import get_app
from pxr import Gf
from isaacsim.core.api import World
from isaacsim.core.utils.extensions import enable_extension
from isaacsim.core.api.objects import VisualCuboid

# Enable your extension by its extension ID
enable_extension("isaacsim.mtconnect.stream")

# Now import from the extension
from isaacsim.mtconnect.stream.impl.extension import get_extension_instance


class MTConnectDeviceMonitor:
    """Monitor MTConnect device position and update cube position."""
    
    DATAITEM_POSITION = "Lp1LPathPos"
    CUBE_PATH = "/World/DeviceMonitorCube"
    AGENT_ADDRESS = "demo.mtconnect.org/OKUMA"
    POSITION_SCALE = 0.001  # Scale MTConnect values (mm) to Isaac Sim (m)
    LERP_SPEED = 0.1  # Interpolation speed (0.0 to 1.0, higher = faster)
    
    def __init__(self):
        self.app = get_app()
        self.extension = None
        self.cube = None
        self.cube_obj = None
        self.last_position = None
        self.current_position = None
        self.target_position = None
        
    def setup_mtconnect_client(self):
        """Get the MTConnect client from the extension."""
        try:
            self.extension = get_extension_instance()
            if not self.extension:
                carb.log_error("Error: MTConnect extension not loaded")
                return False
            carb.log_info("MTConnect extension accessed successfully")
            return True
        except Exception as e:
            carb.log_error(f"Error accessing MTConnect extension: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_cube(self):
        """Create a cube in the scene."""
        
        # Create a cube
        self.cube_obj = VisualCuboid(
            prim_path=self.CUBE_PATH,
            position=(0, 0, 0.5),
            scale=np.array([0.1, 0.1, 0.1]),
            color=np.array([1.0, 0.0, 0.0])  # Red color
        )
        self.cube = self.cube_obj.prim
        
        if self.cube:
            carb.log_info(f"Cube created at {self.CUBE_PATH}")
        
        return self.cube is not None
    
    def set_cube_position(self, x: float, y: float, z: float):
        """Set the cube's position."""
        if not self.cube_obj:
            return
        
        position = np.array([x, y, z])
        self.cube_obj.set_world_pose(position=position)
    
    def update_cube_from_mtconnect(self):
        """Update cube position based on MTConnect device position data."""
        if not self.extension:
            return False
        
        # Get the observation (returns a dict)
        obs = self.extension.mtconnect_client.get_observation(self.DATAITEM_POSITION)
        
        if not obs:
            return False
        
        try:
            # Get position value (list of [X, Y, Z])
            position_list = obs.get("value", [])
            if not position_list or len(position_list) != 3:
                carb.log_error(f"Expected 3 position values, got {len(position_list) if position_list else 0}")
                return False
            
            # Extract position values and scale them
            x = float(position_list[0]) * self.POSITION_SCALE
            y = float(position_list[1]) * self.POSITION_SCALE
            z = (float(position_list[2]) * self.POSITION_SCALE) + 0.5  # Add offset to Z for better visibility above ground
            
            current_position = (x, y, z)
            
            # Update target if position has changed
            if current_position != self.last_position:
                self.target_position = np.array([x, y, z], dtype=float)
                self.last_position = current_position
                return True
        except (ValueError, TypeError, IndexError) as e:
            carb.log_error(f"Error parsing position values: {e}")
            return False
        
        return False
    
    def physics_callback(self, *args):
        """Physics callback for world.add_physics_callback."""
        # Update target from MTConnect
        self.update_cube_from_mtconnect()
        
        # Smoothly interpolate to target position
        if self.target_position is not None and self.cube_obj:
            # Initialize current position if needed
            if self.current_position is None:
                current_pose = self.cube_obj.get_world_pose()
                self.current_position = current_pose[0]
            
            # Lerp towards target
            self.current_position = self.current_position + (self.target_position - self.current_position) * self.LERP_SPEED
            
            # Apply interpolated position
            self.set_cube_position(self.current_position[0], self.current_position[1], self.current_position[2])


def main():
    """Entry point for the standalone script."""
    carb.log_info("=" * 60)
    carb.log_info("MTConnect Device Monitor")
    carb.log_info("=" * 60)
    
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
        carb.log_error("Failed to create cube")
        return False
    
    # Register physics callback
    world.add_physics_callback("mtconnect_monitor", monitor.physics_callback)
    monitor.extension.connect(monitor.AGENT_ADDRESS)
    monitor.extension.start_streaming()
    carb.log_info(f"Monitoring position data item '{monitor.DATAITEM_POSITION}' at {monitor.AGENT_ADDRESS}")
    world.reset()
    # Main simulation loop
    try:
        while True:
            world.step(render=True)
    except KeyboardInterrupt:
        carb.log_info("\nApplication stopped by user")
    finally:
        monitor.extension.stop_streaming()
        simulation_app.close()


if __name__ == "__main__":
    main()
