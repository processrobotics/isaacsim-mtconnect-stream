# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Optional

EXTENSION_TITLE = "MTConnect Stream"
EXTENSION_DESCRIPTION = "Stream MTConnect data from an MTConnect Agent"
DEFAULT_AGENT_ADDRESS = "http://localhost:5000"

# Global registry for MTConnect client access from OmniGraph nodes
_mtconnect_client_instance: Optional["MTConnectClient"] = None


def set_mtconnect_client(client: "MTConnectClient") -> None:
    """Register the MTConnect client instance for global access."""
    global _mtconnect_client_instance
    _mtconnect_client_instance = client


def get_mtconnect_client() -> Optional["MTConnectClient"]:
    """Get the registered MTConnect client instance."""
    return _mtconnect_client_instance


def clear_mtconnect_client() -> None:
    """Clear the MTConnect client instance."""
    global _mtconnect_client_instance
    _mtconnect_client_instance = None
