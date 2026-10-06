"""
Test script for Clawback agent without API key (mock mode).
This tests the tool integration without calling ASI:One.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tools import calculate_uptime, get_clause, get_status_history, check_notice_period


def test_demo_scenario():
    """Test the demo scenario manually to verify tools work correctly."""
    print("Testing demo scenario...\n")

    # Step 1: Get the maintenance exclusion clause
    print("Step 1: Get maintenance exclusion clause")
    clause = get_clause("VendorA", "maintenance_exclusion")
    print(f"Clause: {clause['clause_text']}\n")

    # Step 2: Calculate uptime with maintenance excluded
    print("Step 2: Calculate uptime (assuming maintenance is valid)")
    uptime = calculate_uptime(78, 35, 44640)
    print(f"Uptime with 35min excluded: {uptime['uptime_percentage']}%")
    print(f"Credit eligible: {uptime['credit_eligible']}\n")

    # Step 3: Check the notice period
    print("Step 3: Check notice period")
    notice = check_notice_period(
        "2026-10-04T18:30:00Z",
        "2026-10-05T14:45:00Z",
        72
    )
    print(f"Notice valid: {notice['valid']}")
    print(f"Actual notice: {notice['actual_hours']} hours")
    print(f"Required: {notice['required_hours']} hours")
    print(f"Difference: {notice['difference_hours']} hours\n")

    # Step 4: Recalculate uptime with INVALID maintenance (notice too short)
    print("Step 4: Recalculate uptime (maintenance exclusion INVALID)")
    uptime2 = calculate_uptime(78, 0, 44640)  # Exclude 0 minutes since notice was invalid
    print(f"Uptime with 0min excluded: {uptime2['uptime_percentage']}%")
    print(f"Credit eligible: {uptime2['credit_eligible']}")
    print(f"Credit tier: {uptime2['credit_tier']}\n")

    # Step 5: Get uptime clause
    print("Step 5: Get uptime clause")
    uptime_clause = get_clause("VendorA", "uptime")
    print(f"Clause: {uptime_clause['clause_text']}\n")

    print("="*50)
    print("CONCLUSION:")
    print("="*50)
    print("The maintenance exclusion is INVALID because notice was only")
    print(f"{notice['actual_hours']} hours instead of required {notice['required_hours']} hours.")
    print(f"Actual uptime: {uptime2['uptime_percentage']}% (below 99.9% SLA)")
    print(f"Credit eligible: YES ({uptime2['credit_tier']})")
    print("\nRecommended action: File claim citing invalid notice period.")


if __name__ == "__main__":
    test_demo_scenario()
