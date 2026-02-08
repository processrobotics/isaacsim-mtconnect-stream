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

# Add the impl directory to the path to access global_variables
impl_path = os.path.join(os.path.dirname(__file__), "..", "..", "impl")
if impl_path not in sys.path:
    sys.path.insert(0, impl_path)

from global_variables import get_mtconnect_client


class OgnIsaacsimMtconnectStream2PyInternalState:
    """Convenience class for maintaining per-node state information"""

    def __init__(self):
        """Instantiate the per-node state information"""
        self.status = False
        self.last_client = None


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
            # Get the MTConnect client from the global registry
            client = get_mtconnect_client()
            
            if client is None:
                # No client available yet - return empty arrays
                db.outputs.values = []
                db.outputs.timestamps = []
                return True
            
            # Store reference for debugging
            state.last_client = client
            
            # Read input dataItemIds
            data_item_ids = db.inputs.dataItemIds
            
            if not data_item_ids or len(data_item_ids) == 0:
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
                    # Extract value - try to convert to numeric
                    value = observation.get("value")
                    timestamp = observation.get("timestamp", "")
                    
                    # Convert value to float if possible
                    numeric_value = 0.0
                    if value is not None:
                        try:
                            # Handle different value types
                            if isinstance(value, (int, float)):
                                numeric_value = float(value)
                            elif isinstance(value, str):
                                # Try to convert string to float
                                # Handle common string values
                                if value.upper() == "AVAILABLE":
                                    numeric_value = 1.0
                                elif value.upper() == "UNAVAILABLE":
                                    numeric_value = 0.0
                                else:
                                    try:
                                        numeric_value = float(value)
                                    except ValueError:
                                        # Non-numeric string, use 0.0
                                        numeric_value = 0.0
                        except (ValueError, TypeError):
                            numeric_value = 0.0
                    
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
            import traceback
            db.log_error(f"Traceback: {traceback.format_exc()}")
            # Return empty arrays on error
            db.outputs.values = []
            db.outputs.timestamps = []
            return False
            
        return True
