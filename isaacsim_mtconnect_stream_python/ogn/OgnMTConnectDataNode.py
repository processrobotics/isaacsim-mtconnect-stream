# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import omni.graph.core as og
import omni.graph.core.types as ogtypes


class MTConnectDataNode(og.Node):
    """Omnigraph node that outputs MTConnect data values for given dataItem IDs."""

    @staticmethod
    def compute(db) -> bool:
        """Compute the node's outputs from inputs."""
        # Get the list of dataItem IDs from input
        data_item_ids = db.inputs.dataItemIds

        # Get the MTConnect client from global variables
        from .isaacsim_mtconnect_stream_python.global_variables import mtconnect_client
        if mtconnect_client is None:
            # If no client, output empty lists
            db.outputs.values = []
            db.outputs.timestamps = []
            return True

        # Get the cache
        cache = mtconnect_client.data_cache

        # Collect values and timestamps for the requested IDs
        values = []
        timestamps = []

        for data_item_id in data_item_ids:
            if data_item_id in cache:
                item = cache[data_item_id]
                value = item.get("value")
                timestamp = item.get("timestamp")

                # Try to convert value to float if possible, else use 0.0
                try:
                    if value is not None:
                        value = float(value)
                    else:
                        value = 0.0
                except (ValueError, TypeError):
                    value = 0.0

                values.append(value)
                timestamps.append(timestamp or "")
            else:
                values.append(0.0)
                timestamps.append("")

        # Set outputs
        db.outputs.values = values
        db.outputs.timestamps = timestamps

        return True

        return True