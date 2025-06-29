#!/usr/bin/env python3
import subprocess
import json
import sys
import os
from pathlib import Path
from colorama import init, Fore, Style
import time
import argparse

init(autoreset=True)


class TestRunner:
    def __init__(self, binary_path, tests_file, timeout=5):
        self.binary_path = Path(binary_path)
        self.tests_file = Path(tests_file)
        self.timeout = timeout
        self.results = {
            'passed': 0,
            'failed': 0,
            'total': 0,
            'failures': []
        }

        if not self.binary_path.exists():
            raise FileNotFoundError(f"Binary not found: {self.binary_path}")
        if not self.tests_file.exists():
            raise FileNotFoundError(f"Tests file not found: {self.tests_file}")

    def load_tests(self):
        with open(self.tests_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def run_single_test(self, test_case):
        test_name = test_case.get('name', 'Unnamed test')
        input_data = test_case.get('input', '')
        expected_output = test_case.get('expected', '').strip()

        try:
            process = subprocess.Popen(
                [self.binary_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(
                input=input_data,
                timeout=self.timeout
            )

            actual_output = stdout.strip()

            if actual_output == expected_output:
                return True, actual_output, None
            else:
                return False, actual_output, "Output mismatch"

        except subprocess.TimeoutExpired:
            process.kill()
            return False, None, f"Timeout ({self.timeout}s)"
        except Exception as e:
            return False, None, f"Error: {str(e)}"

    def run_all_tests(self):
        tests = self.load_tests()

        print(f"\n{Fore.CYAN}Running {len(tests['test_cases'])} tests...{Style.RESET_ALL}\n")

        for i, test_case in enumerate(tests['test_cases'], 1):
            test_name = test_case.get('name', f'Test {i}')
            print(f"[{i}/{len(tests['test_cases'])}] {test_name}: ", end='', flush=True)

            start_time = time.time()
            passed, actual, error = self.run_single_test(test_case)
            elapsed = time.time() - start_time

            self.results['total'] += 1

            if passed:
                self.results['passed'] += 1
                print(f"{Fore.GREEN}PASSED{Style.RESET_ALL} ({elapsed:.3f}s)")
            else:
                self.results['failed'] += 1
                print(f"{Fore.RED}FAILED{Style.RESET_ALL} ({elapsed:.3f}s)")

                failure_info = {
                    'test': test_name,
                    'input': test_case.get('input', ''),
                    'expected': test_case.get('expected', ''),
                    'actual': actual,
                    'error': error
                }
                self.results['failures'].append(failure_info)

                if hasattr(self, 'verbose') and self.verbose:
                    self.print_failure_details(failure_info)

    def print_failure_details(self, failure):
        print(f"\n  {Fore.YELLOW}Details for '{failure['test']}':{Style.RESET_ALL}")
        print(f"  Input: {repr(failure['input'])}")
        print(f"  Expected: {repr(failure['expected'])}")
        if failure['actual'] is not None:
            print(f"  Actual: {repr(failure['actual'])}")
        if failure['error']:
            print(f"  Error: {failure['error']}")
        print()

    def print_summary(self):
        print(f"\n{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}")
        print(f"Total tests: {self.results['total']}")
        print(f"{Fore.GREEN}Passed: {self.results['passed']}{Style.RESET_ALL}")
        print(f"{Fore.RED}Failed: {self.results['failed']}{Style.RESET_ALL}")

        if self.results['failed'] > 0:
            print(f"\n{Fore.RED}Failed tests:{Style.RESET_ALL}")
            for failure in self.results['failures']:
                print(f"\n  • {failure['test']}")
                print(f"    Input: {repr(failure['input'])}")
                print(f"    Expected: {repr(failure['expected'])}")
                if failure['actual'] is not None:
                    print(f"    Actual: {repr(failure['actual'])}")
                if failure['error']:
                    print(f"    Error: {failure['error']}")

        print(f"\n{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}")

        return 0 if self.results['failed'] == 0 else 1


def main():
    parser = argparse.ArgumentParser(description='Test runner for compiled programs')
    parser.add_argument('binary', help='Path to the compiled binary')
    parser.add_argument('tests', help='Path to the tests JSON file')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show detailed output for failed tests immediately')
    parser.add_argument('-t', '--timeout', type=float, default=5.0,
                        help='Timeout for each test in seconds (default: 5.0)')

    args = parser.parse_args()

    try:
        runner = TestRunner(args.binary, args.tests, args.timeout)
        runner.verbose = args.verbose
        runner.run_all_tests()
        exit_code = runner.print_summary()
        sys.exit(exit_code)
    except Exception as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
