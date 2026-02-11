"""
OmniGraph core Python API:
  https://docs.omniverse.nvidia.com/kit/docs/omni.graph/latest/Overview.html

OmniGraph attribute data types:
  https://docs.omniverse.nvidia.com/kit/docs/omni.graph.docs/latest/dev/ogn/attribute_types.html

Collection of OmniGraph code examples in Python:
  https://docs.omniverse.nvidia.com/kit/docs/omni.graph.docs/latest/dev/ogn/ogn_code_samples_python.html

Collection of OmniGraph tutorials:
  https://docs.omniverse.nvidia.com/kit/docs/omni.graph.tutorials/latest/Overview.html
"""

import sys
import os
import traceback
from typing import Any
import carb

# Try to import get_extension_instance from the impl module
_get_extension_instance = None

def _try_import_extension():
    """Try importing the extension module."""
    global _get_extension_instance
    if _get_extension_instance is not None:
        return True
    
    try:
        # Try direct package import first
        from isaacsim.mtconnect.stream2.impl.extension import get_extension_instance
        _get_extension_instance = get_extension_instance
        carb.log_warn("MTConnect OmniGraph Node: Successfully imported get_extension_instance via package path")
        return True
    except ImportError as e:
        carb.log_warn(f"MTConnect OmniGraph Node: Package import failed: {e}")
        
    # Fallback: Add impl path to sys.path
    # Path from nodes: ../python -> ../ogn -> ../stream2 -> /impl
    impl_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "impl"))
    if impl_path not in sys.path:
        sys.path.insert(0, impl_path)
        carb.log_warn(f"MTConnect OmniGraph Node: Added impl path to sys.path: {impl_path}")
    
    try:
        from extension import get_extension_instance as gei
        _get_extension_instance = gei
        carb.log_warn("MTConnect OmniGraph Node: Successfully imported get_extension_instance via sys.path")
        return True
    except ImportError as e:
        carb.log_error(f"MTConnect OmniGraph Node: Failed to import extension: {e}")
        return False


def get_extension_instance():
    """Get the extension instance, trying import if needed."""
    if _get_extension_instance is None:
        _try_import_extension()
    if _get_extension_instance is not None:
        return _get_extension_instance()
    return None


def convert_to_numeric(value: Any) -> float:
    """
    Convert an MTConnect value to a numeric float.
    
    Args:
        value: The value to convert (can be int, float, str, or None)
        
    Returns:
        float: The converted numeric value
        
    Conversion rules:
    - Numeric values: Used directly
    - "AVAILABLE": 1.0
    - "UNAVAILABLE": 0.0
    - Other strings: Attempt numeric conversion, default to 0.0
    - None: 0.0
    """
    if value is None:
        return 0.0
    
    # Handle numeric types directly
    if isinstance(value, (int, float)):
        return float(value)
    
    # Handle string types
    if isinstance(value, str):
        # Handle common MTConnect status values
        value_upper = value.upper()
        if value_upper == "AVAILABLE":
            return 1.0
        elif value_upper == "UNAVAILABLE":
            return 0.0
        
        # Try to convert to float
        try:
            return float(value)
        except ValueError:
            # Non-numeric string, return 0.0
            return 0.0
    
    # Unknown type, return default
    return 0.0


class OgnIsaacsimMtconnectStream2PyInternalState:
    """Convenience class for maintaining per-node state information"""

    def __init__(self):
        """Instantiate the per-node state information"""
        self.status = False
        self.last_extension = None


class OgnIsaacsimMtconnectStream2Py:
    """The Ogn node class"""

    @staticmethod
    def internal_state():
        """Returns an object that contains per-node state information"""
        return OgnIsaacsimMtconnectStream2PyInternalState()

    @staticmethod
    def compute(db) -> bool:
        """Compute the output based on inputs and internal state"""
        state = db.per_instance_state

        try:
            # Get the extension instance
            extension = get_extension_instance()
            
            if extension is None:
                # No extension available yet - return empty arrays
                carb.log_warn("MTConnect OmniGraph Node: Extension instance not available")
                db.outputs.values = []
                db.outputs.timestamps = []
                db.outputs.intValues = []
                db.outputs.floatValues = []
                db.outputs.doubleValues = []
                db.outputs.stringValues = []
                return True
            
            # Store reference for debugging
            state.last_extension = extension
            
            # Access the MTConnect client through the extension
            client = extension.mtconnect_client
            
            # Read input dataItemIds
            data_item_ids = db.inputs.dataItemIds
            # carb.log_warn(f"MTConnect OmniGraph Node: Querying {len(data_item_ids)} data items: {data_item_ids}")
            
            if not data_item_ids:
                # No input data items - return empty arrays
                carb.log_error("MTConnect OmniGraph Node: No input data items specified")
                db.outputs.values = []
                db.outputs.timestamps = []
                db.outputs.intValues = []
                db.outputs.floatValues = []
                db.outputs.doubleValues = []
                db.outputs.stringValues = []
                return True
            
            # Query the MTConnect client for each dataItemId
            values = []
            timestamps = []
            int_values = []
            float_values = []
            double_values = []
            string_values = []
            
            for data_item_id in data_item_ids:
                observation = client.get_observation(str(data_item_id))
                
                if observation:
                    # Extract value and timestamp
                    value = observation.get("value")
                    timestamp = observation.get("timestamp", "")
                    
                    # Convert value to numeric format for backward compatibility
                    numeric_value = convert_to_numeric(value)
                    
                    # Convert to different primitive types
                    # Int conversion
                    try:
                        int_val = int(numeric_value)
                    except (ValueError, TypeError):
                        int_val = 0
                    
                    # Float conversion
                    try:
                        float_val = float(numeric_value)
                    except (ValueError, TypeError):
                        float_val = 0.0
                    
                    # Double conversion (same as float in Python)
                    try:
                        double_val = float(numeric_value)
                    except (ValueError, TypeError):
                        double_val = 0.0
                    
                    # String conversion
                    str_val = str(value) if value is not None else ""
                    
                    carb.log_info(f"MTConnect OmniGraph Node: {data_item_id} = {numeric_value} (raw: {value}) @ {timestamp}")
                    values.append(numeric_value)
                    timestamps.append(timestamp)
                    int_values.append(int_val)
                    float_values.append(float_val)
                    double_values.append(double_val)
                    string_values.append(str_val)
                else:
                    # DataItem not found - append default values
                    carb.log_warn(f"MTConnect OmniGraph Node: DataItem '{data_item_id}' not found - using defaults")
                    values.append(0.0)
                    timestamps.append("")
                    int_values.append(0)
                    float_values.append(0.0)
                    double_values.append(0.0)
                    string_values.append("")
            
            # Write output values
            db.outputs.values = values
            db.outputs.timestamps = timestamps
            db.outputs.intValues = int_values
            db.outputs.floatValues = float_values
            db.outputs.doubleValues = double_values
            db.outputs.stringValues = string_values
            carb.log_verbose(f"MTConnect OmniGraph Node: Output {len(values)} values: {values}")
            
            state.status = True
            
        except Exception as e:
            carb.log_error(f"MTConnect OmniGraph Node: Computation error: {e}")
            carb.log_error(f"MTConnect OmniGraph Node: Traceback: {traceback.format_exc()}")
            db.log_error(f"Computation error: {e}")
            db.log_error(f"Traceback: {traceback.format_exc()}")
            # Return empty arrays on error
            db.outputs.values = []
            db.outputs.timestamps = []
            db.outputs.intValues = []
            db.outputs.floatValues = []
            db.outputs.doubleValues = []
            db.outputs.stringValues = []
            return False
            
        return True
