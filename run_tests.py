#!/usr/bin/env python3
"""Test runner for Google Drive & Photos Sync Application."""

import sys
import unittest
from pathlib import Path


def discover_and_run_tests():
    """Discover and run all tests in the tests directory."""
    # Get the project root directory
    project_root = Path(__file__).parent
    tests_dir = project_root / 'tests'
    
    if not tests_dir.exists():
        print(f"Tests directory not found: {tests_dir}")
        return False
    
    # Discover tests
    loader = unittest.TestLoader()
    start_dir = str(tests_dir)
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Run tests
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        descriptions=True,
        failfast=False
    )
    
    print("Running Google Drive & Photos Sync Application Tests")
    print("=" * 60)
    
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Error:')[-1].strip()}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed.")
    
    return success


def run_specific_test(test_name: str):
    """Run a specific test module or test case."""
    project_root = Path(__file__).parent
    tests_dir = project_root / 'tests'
    
    # Add tests directory to Python path
    sys.path.insert(0, str(tests_dir))
    sys.path.insert(0, str(project_root))
    
    try:
        # Try to load the specific test
        loader = unittest.TestLoader()
        
        if '.' in test_name:
            # Specific test method (e.g., test_auth_manager.TestAuthManager.test_init)
            suite = loader.loadTestsFromName(test_name)
        else:
            # Test module (e.g., test_auth_manager)
            if not test_name.startswith('test_'):
                test_name = f'test_{test_name}'
            suite = loader.loadTestsFromName(test_name)
        
        runner = unittest.TextTestRunner(
            verbosity=2,
            stream=sys.stdout,
            descriptions=True
        )
        
        print(f"Running specific test: {test_name}")
        print("=" * 60)
        
        result = runner.run(suite)
        
        success = len(result.failures) == 0 and len(result.errors) == 0
        return success
        
    except Exception as e:
        print(f"Error running test '{test_name}': {e}")
        return False


def main():
    """Main entry point for test runner."""
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        success = run_specific_test(test_name)
    else:
        # Run all tests
        success = discover_and_run_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()