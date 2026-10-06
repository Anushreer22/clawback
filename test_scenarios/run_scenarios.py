"""
Test scenario runner - executes all scenarios and measures performance.
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools import calculate_uptime, get_clause, check_notice_period


def load_scenarios(scenarios_dir: Path) -> List[Dict[str, Any]]:
    """Load all scenario JSON files (excluding results.json)."""
    scenarios = []
    for file in scenarios_dir.glob("*.json"):
        if file.name == "results.json":
            continue
        with open(file, 'r') as f:
            scenarios.append(json.load(f))
    return sorted(scenarios, key=lambda x: x['scenario_id'])


def evaluate_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate a single scenario and compare with expected results.

    Returns:
        Dict with evaluation results including correctness flag
    """
    incident = scenario['incident']
    expected = scenario['expected']

    # Calculate uptime
    uptime_result = calculate_uptime(
        incident['duration_minutes'],
        incident.get('maintenance_overlap_minutes', 0),
        incident['month_minutes']
    )

    # Check maintenance notice if applicable
    notice_valid = None
    has_maintenance = incident.get('maintenance_overlap_minutes', 0) > 0

    if has_maintenance:
        if 'maintenance_notice_posted' in incident and incident['maintenance_notice_posted']:
            notice_result = check_notice_period(
                incident['maintenance_notice_posted'],
                incident.get('maintenance_window_start', incident['timestamp']),
                72  # Required hours from SLA
            )
            notice_valid = notice_result['valid']

            # If notice is invalid, recalculate uptime without exclusion
            if not notice_valid:
                uptime_result = calculate_uptime(
                    incident['duration_minutes'],
                    0,  # No exclusion
                    incident['month_minutes']
                )
        else:
            # No notice posted - exclusion is invalid
            notice_valid = False
            uptime_result = calculate_uptime(
                incident['duration_minutes'],
                0,  # No exclusion
                incident['month_minutes']
            )

    # Compare with expected
    credit_eligible_match = uptime_result['credit_eligible'] == expected['credit_eligible']
    credit_tier_match = uptime_result['credit_tier'] == expected['credit_tier']

    correct = credit_eligible_match and credit_tier_match

    return {
        'scenario_id': scenario['scenario_id'],
        'name': scenario['name'],
        'correct': correct,
        'credit_eligible_match': credit_eligible_match,
        'credit_tier_match': credit_tier_match,
        'actual': {
            'credit_eligible': uptime_result['credit_eligible'],
            'credit_tier': uptime_result['credit_tier'],
            'uptime_percentage': uptime_result['uptime_percentage']
        },
        'expected': expected,
        'notice_valid': notice_valid
    }


def run_all_scenarios():
    """Run all scenarios and generate performance report."""
    scenarios_dir = Path(__file__).parent
    scenarios = load_scenarios(scenarios_dir)

    print("="*60)
    print("TEST SCENARIO RUNNER")
    print("="*60)
    print(f"Found {len(scenarios)} scenarios\n")

    results = []
    correct_count = 0

    for scenario in scenarios:
        print(f"Running {scenario['scenario_id']}: {scenario['name']}")
        result = evaluate_scenario(scenario)
        results.append(result)

        if result['correct']:
            correct_count += 1
            print(f"  [PASS] Credit eligible: {result['actual']['credit_eligible']}, Tier: {result['actual']['credit_tier']}")
        else:
            print(f"  [FAIL] Expected: eligible={result['expected']['credit_eligible']}, tier={result['expected']['credit_tier']}")
            print(f"         Actual: eligible={result['actual']['credit_eligible']}, tier={result['actual']['credit_tier']}")
        print()

    # Generate report
    print("="*60)
    print("PERFORMANCE REPORT")
    print("="*60)
    print(f"Total scenarios: {len(scenarios)}")
    print(f"Correct decisions: {correct_count}")
    print(f"Incorrect decisions: {len(scenarios) - correct_count}")
    print(f"Accuracy: {(correct_count / len(scenarios) * 100):.1f}%")
    print()

    # False claims (claims when no credit is due)
    false_claims = sum(1 for r in results if r['actual']['credit_eligible'] and not r['expected']['credit_eligible'])
    print(f"False claims: {false_claims} (target: 0)")
    print()

    # Detailed results
    print("="*60)
    print("DETAILED RESULTS")
    print("="*60)
    for result in results:
        status = "[PASS]" if result['correct'] else "[FAIL]"
        print(f"{status} {result['scenario_id']}: {result['name']}")
        print(f"       Uptime: {result['actual']['uptime_percentage']:.4f}%")
        print(f"       Credit eligible: {result['actual']['credit_eligible']} (expected: {result['expected']['credit_eligible']})")
        print(f"       Credit tier: {result['actual']['credit_tier']} (expected: {result['expected']['credit_tier']})")
        if result['notice_valid'] is not None:
            print(f"       Notice valid: {result['notice_valid']}")
        print()

    # Save results to file
    results_file = scenarios_dir / "results.json"
    with open(results_file, 'w') as f:
        json.dump({
            'summary': {
                'total': len(scenarios),
                'correct': correct_count,
                'incorrect': len(scenarios) - correct_count,
                'accuracy': correct_count / len(scenarios),
                'false_claims': false_claims
            },
            'results': results
        }, f, indent=2)

    print(f"Results saved to {results_file}")


if __name__ == "__main__":
    run_all_scenarios()
