"""
Status history and notice period validation tools.
"""
import json
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime, timedelta


def get_status_history(vendor: str, window_start: str, window_end: str) -> Dict[str, Any]:
    """
    Retrieve maintenance notice timestamps for a vendor within a time window.

    Args:
        vendor: Vendor name (e.g., "VendorA")
        window_start: ISO 8601 timestamp for window start
        window_end: ISO 8601 timestamp for window end

    Returns:
        Dict with:
            - vendor: Vendor name
            - notices: List of maintenance notices with timestamps
            - count: Number of notices found
    """
    incidents_file = Path(__file__).parent.parent / "data" / "incidents.json"

    if not incidents_file.exists():
        return {
            "vendor": vendor,
            "notices": [],
            "count": 0,
            "error": "Incidents file not found"
        }

    with open(incidents_file, 'r') as f:
        incidents_data = json.load(f)

    # Filter incidents for the vendor
    vendor_incidents = [inc for inc in incidents_data.get("incidents", []) if inc.get("vendor") == vendor]

    # Extract maintenance notices
    notices = []
    for inc in vendor_incidents:
        if "maintenance_notice_posted" in inc:
            notice_time = inc["maintenance_notice_posted"]
            notices.append({
                "incident_id": inc.get("id"),
                "notice_posted": notice_time,
                "maintenance_window_start": inc.get("maintenance_window_start"),
                "maintenance_window_end": inc.get("maintenance_window_end")
            })

    return {
        "vendor": vendor,
        "window_start": window_start,
        "window_end": window_end,
        "notices": notices,
        "count": len(notices)
    }


def check_notice_period(notice_time: str, window_start: str, required_hours: int) -> Dict[str, Any]:
    """
    Validate if a maintenance notice was posted with sufficient lead time.

    Args:
        notice_time: ISO 8601 timestamp when notice was posted
        window_start: ISO 8601 timestamp when maintenance window starts
        required_hours: Required notice period in hours

    Returns:
        Dict with:
            - valid: Boolean indicating if notice period is valid
            - actual_hours: Actual hours of notice provided
            - required_hours: Required hours
            - difference_hours: Difference (positive if valid, negative if invalid)
    """
    try:
        notice_dt = datetime.fromisoformat(notice_time.replace('Z', '+00:00'))
        window_dt = datetime.fromisoformat(window_start.replace('Z', '+00:00'))
    except ValueError as e:
        return {
            "valid": False,
            "error": f"Invalid timestamp format: {e}"
        }

    # Calculate actual notice period in hours
    actual_hours = (window_dt - notice_dt).total_seconds() / 3600
    difference_hours = actual_hours - required_hours
    valid = actual_hours >= required_hours

    return {
        "valid": valid,
        "actual_hours": round(actual_hours, 2),
        "required_hours": required_hours,
        "difference_hours": round(difference_hours, 2),
        "notice_time": notice_time,
        "window_start": window_start
    }
