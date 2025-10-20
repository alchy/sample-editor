#!/usr/bin/env python
"""
run_tests.py - Helper script to run all tests

Usage:
    python tests/run_tests.py              # Run all tests
    python tests/run_tests.py velocity     # Run specific test
"""
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

TESTS = {
    'velocity': 'test_velocity_assignment.py',
    'metadata': 'test_sample_metadata.py',
    'load': 'test_load_files.py',
    'batch': 'test_batch_analyzer.py',
    'session': 'test_session_manager_cache.py',
    'error': 'test_error_handling.py',
    'full': 'test_full_flow.py',
}


def run_test(test_file):
    """Run a single test file."""
    test_path = Path(__file__).parent / test_file
    if not test_path.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    print(f"\n{'='*60}")
    print(f"Running: {test_file}")
    print(f"{'='*60}\n")

    result = subprocess.run(
        [sys.executable, str(test_path)],
        cwd=str(project_root)
    )

    return result.returncode == 0


def main():
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        if test_name in TESTS:
            success = run_test(TESTS[test_name])
            sys.exit(0 if success else 1)
        else:
            print(f"Unknown test: {test_name}")
            print(f"Available tests: {', '.join(TESTS.keys())}")
            sys.exit(1)
    else:
        # Run all tests
        print("Running all tests...")
        results = {}
        for name, test_file in TESTS.items():
            results[name] = run_test(test_file)

        # Summary
        print(f"\n{'='*60}")
        print("Test Summary:")
        print(f"{'='*60}")
        for name, success in results.items():
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"{status}: {name}")

        all_passed = all(results.values())
        sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
