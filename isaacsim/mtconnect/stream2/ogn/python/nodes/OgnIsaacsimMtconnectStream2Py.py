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

# Note: OmniGraph nodes may run in a context where the extension package path
# is not automatically available. We add the impl path to allow import.
impl_path = os.path.join(os.path.dirname(__file__), "..", "..", "impl")
if impl_path not in sys.path:
    sys.path.insert(0, impl_path)

from extension import get_extension_instance


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
        state = db.internal_state

        try:
            # Get the extension instance
            extension = get_extension_instance()
            
            if extension is None:
                # No extension available yet - return empty arrays
                db.outputs.values = []
                db.outputs.timestamps = []
                return True
            
            # Store reference for debugging
            state.last_extension = extension
            
            # Access the MTConnect client through the extension
            client = extension.mtconnect_client
            
            # Read input dataItemIds
            data_item_ids = db.inputs.dataItemIds
            
            if not data_item_ids:
                # No input data items - return empty arrays
                db.outputs.values = []
                db.outputs.timestamps = []
                return True
            
            # Query the MTConnect client for each dataItemId
            values = []
            timestamps = []
            
            for data_item_id in data_item_ids:
                observation = client.get_observation(str(data_item_id))
                
                if observation:
                    # Extract value and timestamp
                    value = observation.get("value")
                    timestamp = observation.get("timestamp", "")
                    
                    # Convert value to numeric format
                    numeric_value = convert_to_numeric(value)
                    
                    values.append(numeric_value)
                    timestamps.append(timestamp)
                else:
                    # DataItem not found - append default values
                    values.append(0.0)
                    timestamps.append("")
            
            # Write output values
            db.outputs.values = values
            db.outputs.timestamps = timestamps
            
            state.status = True
            
        except Exception as e:
            db.log_error(f"Computation error: {e}")
            db.log_error(f"Traceback: {traceback.format_exc()}")
            # Return empty arrays on error
            db.outputs.values = []
            db.outputs.timestamps = []
            return False
            
        return True
