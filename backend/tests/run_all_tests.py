import unittest
import sys
import os
import time

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from tests.test_api_endpoints import TestApiEndpoints
from tests.test_ml_and_physics import TestMLAndPhysics
from tests.test_aggregation_hierarchy import TestAggregationHierarchy
from tests.test_security_audit import TestSecurityAndAudit

def run_master_suite():
    print("=" * 80)
    print("  AI-POWERED RENEWABLE GENERATION FORECASTING PLATFORM")
    print("  PHASE 19: COMPREHENSIVE END-TO-END VALIDATION & TEST SUITE")
    print("=" * 80)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all modules
    suite.addTests(loader.loadTestsFromTestCase(TestApiEndpoints))
    suite.addTests(loader.loadTestsFromTestCase(TestMLAndPhysics))
    suite.addTests(loader.loadTestsFromTestCase(TestAggregationHierarchy))
    suite.addTests(loader.loadTestsFromTestCase(TestSecurityAndAudit))

    total_tests = suite.countTestCases()
    print(f"\n[INFO] Discovered {total_tests} comprehensive automated test cases across 4 domain suites:")
    print("  - Suite 1: End-to-End API Integration & Contract Verification (12 domain tests)")
    print("  - Suite 2: Machine Learning Invariants & Physical Boundary Adherence (5 domain tests)")
    print("  - Suite 3: Hierarchical Mathematical Aggregation Fidelity (3 theorem tests)")
    print("  - Suite 4: Enterprise Security, BCrypt, JWT, RBAC & Audit Logging (4 security tests)")
    print("\nExecuting test pipeline...\n" + "-" * 80)

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    duration = time.time() - start_time

    print("-" * 80)
    print("\n" + "=" * 80)
    print("  EXECUTIVE VALIDATION REPORT")
    print("=" * 80)
    print(f"  Total Test Cases Run:   {result.testsRun}")
    print(f"  Passed:                 {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  Failures:               {len(result.failures)}")
    print(f"  Errors:                 {len(result.errors)}")
    print(f"  Total Execution Time:   {duration:.2f} seconds")
    print(f"  Success Rate:           {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100:.1f}%")
    print("=" * 80)

    if result.wasSuccessful():
        print("\n[VERIFICATION CERTIFICATE] ALL PLATFORM LAYERS PASS 100% QUALITY VALIDATION!")
        return 0
    else:
        print("\n[VERIFICATION FAILED] One or more tests failed.")
        return 1

if __name__ == "__main__":
    exit_code = run_master_suite()
    sys.exit(exit_code)
