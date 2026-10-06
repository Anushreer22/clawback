"""
Deterministic calculator tools for SLA calculations.
No AI should ever do arithmetic - use these functions instead.
"""
from typing import Dict, Any


def calculate_uptime(incident_minutes: int, excluded_minutes: int, month_minutes: int) -> Dict[str, Any]:
    """
    Calculate uptime percentage and determine credit tier.

    Args:
        incident_minutes: Total downtime in minutes
        excluded_minutes: Minutes excluded from downtime (e.g., valid maintenance)
        month_minutes: Total minutes in the month (default 44640 for 31-day month)

    Returns:
        Dict with:
            - uptime_percentage: Actual uptime after exclusions
            - downtime_percentage: Actual downtime percentage
            - credit_eligible: Boolean indicating if credit is due
            - credit_tier: String describing the credit tier
    """
    # Calculate effective downtime after exclusions
    effective_downtime = max(0, incident_minutes - excluded_minutes)

    # Calculate uptime percentage
    uptime_percentage = ((month_minutes - effective_downtime) / month_minutes) * 100
    downtime_percentage = (effective_downtime / month_minutes) * 100

    # SLA threshold is 99.9%
    sla_threshold = 99.9
    credit_eligible = uptime_percentage < sla_threshold

    # Determine credit tier based on how far below SLA
    if not credit_eligible:
        credit_tier = "none"
    elif uptime_percentage >= 99.5:
        credit_tier = "tier1"  # Small breach
    elif uptime_percentage >= 99.0:
        credit_tier = "tier2"  # Medium breach
    else:
        credit_tier = "tier3"  # Severe breach

    return {
        "uptime_percentage": round(uptime_percentage, 4),
        "downtime_percentage": round(downtime_percentage, 4),
        "effective_downtime_minutes": effective_downtime,
        "credit_eligible": credit_eligible,
        "credit_tier": credit_tier,
        "sla_threshold": sla_threshold
    }
