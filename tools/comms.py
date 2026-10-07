"""
Communication tool for filing claims with vendor agents.
Supports both simulation mode and live uAgents Chat Protocol.
"""
from typing import Dict, Any, Optional
import os
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.communication import get_communicator

try:
    from uagents import Agent, Context
    from agents.vendor_agent import ClaimMessage, ClaimResponse, get_vendor_agent
    UAGENTS_AVAILABLE = True
except ImportError:
    UAGENTS_AVAILABLE = False


def file_claim_simulation(vendor: str, claim_message: str, claim_id: str = None) -> Dict[str, Any]:
    """
    Simulation mode - returns deterministic vendor responses.

    Args:
        vendor: Vendor name (e.g., "VendorA")
        claim_message: The claim message to send
        claim_id: Optional claim ID for tracking

    Returns:
        Dict with vendor response
    """
    communicator = get_communicator()
    return communicator._simulate_claim(vendor, claim_message, claim_id)


async def file_claim_live(vendor: str, claim_message: str, claim_id: str = None) -> Dict[str, Any]:
    """
    Live mode - sends message to vendor agent via uAgents Chat Protocol.

    Args:
        vendor: Vendor name (e.g., "VendorA")
        claim_message: The claim message to send
        claim_id: Optional claim ID for tracking

    Returns:
        Dict with vendor response
    """
    communicator = get_communicator()
    return await communicator.send_claim_async(vendor, claim_message, claim_id)


def file_claim(vendor: str, claim_message: str, claim_id: str = None) -> Dict[str, Any]:
    """
    File a claim with a vendor agent.

    Automatically selects simulation or live mode based on DEMO_MODE environment variable.

    Args:
        vendor: Vendor name (e.g., "VendorA")
        claim_message: The claim message to send
        claim_id: Optional claim ID for tracking

    Returns:
        Dict with vendor response
    """
    communicator = get_communicator()
    return communicator.send_claim(vendor, claim_message, claim_id)

