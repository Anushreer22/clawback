"""
Unit tests for deterministic SLA tools.
Test each tool in isolation before wiring in the AI.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.calculator import calculate_uptime
from tools.clauses import get_clause
from tools.status import get_status_history, check_notice_period
from tools.comms import file_claim


def test_calculate_uptime():
    """Test uptime calculation with demo scenario."""
    print("Testing calculate_uptime...")

    # Demo scenario: 78 minutes down, 35 excluded, 44640 minutes in month
    result = calculate_uptime(78, 35, 44640)

    # Effective downtime = 78 - 35 = 43 minutes
    # Uptime = (44640 - 43) / 44640 * 100 = 99.9036%
    assert result["effective_downtime_minutes"] == 43
    assert abs(result["uptime_percentage"] - 99.9036) < 0.01
    assert result["credit_eligible"] == False  # Above 99.9% threshold
    assert result["credit_tier"] == "none"

    # Test scenario with valid credit
    result2 = calculate_uptime(100, 0, 44640)
    assert result2["credit_eligible"] == True
    assert result2["credit_tier"] == "tier1"

    print("[OK] calculate_uptime tests passed")


def test_get_clause():
    """Test clause retrieval."""
    print("Testing get_clause...")

    # Test valid clause
    result = get_clause("VendorA", "maintenance_exclusion")
    assert result["found"] == True
    assert "72 hours" in result["clause_text"]

    # Test uptime clause
    result2 = get_clause("VendorA", "uptime")
    assert result2["found"] == True
    assert "99.9%" in result2["clause_text"]

    # Test invalid vendor
    result3 = get_clause("VendorX", "uptime")
    assert result3["found"] == False

    # Test invalid topic
    result4 = get_clause("VendorA", "nonexistent")
    assert result4["found"] == False

    print("[OK] get_clause tests passed")


def test_get_status_history():
    """Test status history retrieval."""
    print("Testing get_status_history...")

    result = get_status_history("VendorA", "2026-10-01T00:00:00Z", "2026-10-31T23:59:59Z")
    assert result["vendor"] == "VendorA"
    assert result["count"] >= 0

    # Check that notices have required fields
    if result["count"] > 0:
        notice = result["notices"][0]
        assert "notice_posted" in notice
        assert "maintenance_window_start" in notice

    print("[OK] get_status_history tests passed")


def test_check_notice_period():
    """Test notice period validation."""
    print("Testing check_notice_period...")

    # Demo scenario: notice posted 20 hours before, required 72 hours
    result = check_notice_period(
        "2026-10-04T18:30:00Z",
        "2026-10-05T14:45:00Z",
        72
    )
    assert result["valid"] == False
    assert result["actual_hours"] == 20.25  # 20 hours 15 minutes
    assert result["required_hours"] == 72
    assert result["difference_hours"] < 0

    # Test valid notice (80 hours before)
    result2 = check_notice_period(
        "2026-10-01T08:45:00Z",
        "2026-10-05T14:45:00Z",
        72
    )
    assert result2["valid"] == True
    assert result2["actual_hours"] >= 72

    print("[OK] check_notice_period tests passed")


def test_file_claim():
    """Test claim filing (simulation mode)."""
    print("Testing file_claim...")

    result = file_claim("VendorA", "We request a credit for the outage on 2026-10-05")
    assert result["vendor"] == "VendorA"
    assert result["status"] in ["rejected", "approved", "submitted", "error"]
    assert "claim_id" in result
    assert "mode" in result

    print("[OK] file_claim tests passed")


if __name__ == "__main__":
    print("Running unit tests for SLA tools...\n")
    test_calculate_uptime()
    test_get_clause()
    test_get_status_history()
    test_check_notice_period()
    test_file_claim()
    print("\n[SUCCESS] All tests passed!")
