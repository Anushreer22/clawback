"""
Clauses tool for retrieving SLA contract clauses.
"""
import json
from typing import Dict, Any, Optional
from pathlib import Path


def get_clause(vendor: str, topic: str) -> Dict[str, Any]:
    """
    Retrieve the exact clause text for a vendor and topic.

    Args:
        vendor: Vendor name (e.g., "VendorA")
        topic: Clause topic (e.g., "maintenance_exclusion", "uptime", "claim_window")

    Returns:
        Dict with:
            - vendor: Vendor name
            - topic: Topic requested
            - clause_text: The exact clause text
            - found: Boolean indicating if clause was found
    """
    # Map vendor to its SLA file
    sla_file = Path(__file__).parent.parent / "data" / f"sla_{vendor.lower()}.json"

    if not sla_file.exists():
        return {
            "vendor": vendor,
            "topic": topic,
            "clause_text": None,
            "found": False,
            "error": f"SLA file not found for vendor: {vendor}"
        }

    with open(sla_file, 'r') as f:
        sla_data = json.load(f)

    # Check if topic exists in clauses
    if topic in sla_data.get("clauses", {}):
        clause_text = sla_data["clauses"][topic]
        return {
            "vendor": vendor,
            "topic": topic,
            "clause_text": clause_text,
            "found": True
        }

    # Also check nested structures
    if topic in sla_data:
        if isinstance(sla_data[topic], dict):
            clause_text = sla_data[topic].get("description", json.dumps(sla_data[topic]))
        else:
            clause_text = str(sla_data[topic])
        return {
            "vendor": vendor,
            "topic": topic,
            "clause_text": clause_text,
            "found": True
        }

    return {
        "vendor": vendor,
        "topic": topic,
        "clause_text": None,
        "found": False,
        "error": f"Topic '{topic}' not found in SLA for vendor: {vendor}"
    }
