import os
from isaacsim import SimulationApp

this_dir = os.path.dirname(os.path.abspath(__file__))
usd_path = os.path.join(this_dir, "mtc_cube_demo.usd")

# Create the simulation app without opening a file yet
simulation_app = SimulationApp({"headless": False})

from isaacsim.core.utils.extensions import enable_extension
import omni.usd
import omni.timeline
import carb

exts = [
    "omni.graph.action",
    "omni.graph.core",
    "omni.graph.ui",
    "omni.graph.action_ui",
    "isaacsim.mtconnect.stream"
]

# Enable extensions needed for action graphs and MTConnect
for ext in exts:
    if not enable_extension(ext):
        carb.log_error(f"Failed to enable extension: {ext}")
    else:
        carb.log_info(f"Enabled extension: {ext}")

# Now explicitly open the USD file
carb.log_info(f"[MTConnect Demo] Opening USD file: {usd_path}")
omni.usd.get_context().open_stage(usd_path)

# Wait for the stage to be fully loaded
carb.log_info("[MTConnect Demo] Waiting for stage to load...")
stage = None
max_wait_cycles = 100  # Wait up to ~10 seconds
for i in range(max_wait_cycles):
    simulation_app.update()
    stage = omni.usd.get_context().get_stage()
    if stage:
        # Check if the stage has prims (indication it's loaded)
        root_prim = stage.GetPseudoRoot()
        if root_prim and len(list(root_prim.GetChildren())) > 0:
            carb.log_info(f"[MTConnect Demo] Stage loaded after {i+1} update cycles")
            break
    if i == max_wait_cycles - 1:
        carb.log_warn("[MTConnect Demo] Warning: Stage may not be fully loaded")



# Now import from the extension
from isaacsim.mtconnect.stream.impl.extension import get_extension_instance
extension_instance = get_extension_instance()

# Reload settings from the opened USD stage
extension_instance.reload_settings_from_usd()

# Connect to MTConnect agent
# If the scene has saved MTConnect settings, it will use those
# Otherwise, you can provide an agent URL: extension_instance.connect("http://demo.mtconnect.org:5000")
carb.log_info("[MTConnect Demo] Connecting to agent...")
if extension_instance.connect():
    carb.log_info("[MTConnect Demo] Connected successfully!")
    
    carb.log_info("[MTConnect Demo] Starting streaming...")
    if extension_instance.start_streaming():
        carb.log_info("[MTConnect Demo] Streaming started!")
    else:
        carb.log_error("[MTConnect Demo] Failed to start streaming")
else:
    carb.log_error("[MTConnect Demo] Failed to connect to agent")
    carb.log_info("[MTConnect Demo] To connect manually, use: extension_instance.connect('http://demo.mtconnect.org:5000')")

# Start the simulation timeline
timeline = omni.timeline.get_timeline_interface()
carb.log_info("[MTConnect Demo] Starting simulation timeline...")
timeline.play()

# Run simulation loop
# Give a few more updates for good measure
for _ in range(5):
    simulation_app.update()
carb.log_info("[MTConnect Demo] Running simulation. Press Ctrl+C or close the window to exit.")
while simulation_app.is_running():
    simulation_app.update()

# Cleanup
if extension_instance:
    extension_instance.stop_streaming()
    extension_instance.disconnect()
    
simulation_app.close()