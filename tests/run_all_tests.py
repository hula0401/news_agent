#!/usr/bin/env python3
"""
Unified Test Runner for All Tests

Runs:
- src/ streaming tests
- backend/ streaming tests
- VAD and interruption tests
- Integration tests

Usage:
    python tests/run_all_tests.py [options]

Options:
    --src-only          Run only src/ tests
    --backend-only      Run only backend/ tests
    --vad-only          Run only VAD tests
    --streaming-only    Run only streaming tests
    --quick             Run quick subset
    --verbose, -v       Verbose output
    --html              Generate HTML report
"""

import sys
import os
import argparse
from pathlib import Path
import subprocess

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class Colors:
    """ANSI color codes."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")


def print_section(text):
    """Print formatted section."""
    print(f"\n{Colors.OKBLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'-'*len(text)}{Colors.ENDC}")


def run_pytest(test_path, extra_args=None):
    """Run pytest on specified path."""
    args = ["pytest", str(test_path), "-v"]

    if extra_args:
        args.extend(extra_args)

    print(f"{Colors.OKCYAN}Running: {' '.join(args)}{Colors.ENDC}\n")

    result = subprocess.run(args, cwd=project_root)
    return result.returncode == 0


def run_src_streaming_tests(args):
    """Run src/ streaming tests."""
    print_section("Running src/ Streaming Tests")

    test_file = project_root / "tests" / "src" / "test_streaming.py"

    if not test_file.exists():
        print(f"{Colors.FAIL}✗ Test file not found: {test_file}{Colors.ENDC}")
        return False

    extra_args = []
    if args.verbose:
        extra_args.append("-s")
    if args.html:
        extra_args.extend(["--html=reports/src_streaming_tests.html", "--self-contained-html"])

    return run_pytest(test_file, extra_args)


def run_backend_streaming_tests(args):
    """Run backend/ streaming tests."""
    print_section("Running backend/ Streaming Tests")

    test_file = project_root / "tests" / "backend" / "local" / "core" / "test_streaming_llm_tts.py"

    if not test_file.exists():
        print(f"{Colors.FAIL}✗ Test file not found: {test_file}{Colors.ENDC}")
        return False

    extra_args = []
    if args.verbose:
        extra_args.append("-s")
    if args.html:
        extra_args.extend(["--html=reports/backend_streaming_tests.html", "--self-contained-html"])

    return run_pytest(test_file, extra_args)


def run_vad_tests(args):
    """Run VAD and interruption tests."""
    print_section("Running VAD and Interruption Tests")

    # Use existing VAD test runner
    vad_runner = project_root / "tests" / "run_vad_tests.py"

    if not vad_runner.exists():
        print(f"{Colors.FAIL}✗ VAD test runner not found: {vad_runner}{Colors.ENDC}")
        return False

    cmd = ["python", str(vad_runner)]

    if args.verbose:
        cmd.append("--verbose")
    if args.html:
        cmd.append("--html")

    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode == 0


def run_quick_tests(args):
    """Run quick subset of all tests."""
    print_section("Running Quick Test Subset")

    test_cases = [
        # src/ quick tests
        "tests/src/test_streaming.py::TestLLMStreaming::test_get_response_stream_yields_chunks",
        "tests/src/test_streaming.py::TestTTSStreaming::test_stream_tts_audio_yields_chunks",

        # backend/ quick tests
        "tests/backend/local/core/test_streaming_llm_tts.py::TestStreamingLLMResponse::test_agent_stream_voice_response",
        "tests/backend/local/core/test_streaming_llm_tts.py::TestConcurrentTTS::test_tts_streaming_chunks",

        # VAD quick tests
        "tests/backend/local/core/test_vad_validation.py::TestVADValidation::test_audio_samples_exist",
    ]

    extra_args = []
    if args.verbose:
        extra_args.append("-s")

    all_passed = True
    for test_case in test_cases:
        test_path = project_root / test_case.split("::")[0]
        if test_path.exists():
            if not run_pytest(test_case, extra_args):
                all_passed = False

    return all_passed


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description="Unified Test Runner for All Tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python tests/run_all_tests.py

  # Run only src/ tests
  python tests/run_all_tests.py --src-only

  # Run only streaming tests (src + backend)
  python tests/run_all_tests.py --streaming-only

  # Run quick tests with verbose output
  python tests/run_all_tests.py --quick -v

  # Generate HTML report
  python tests/run_all_tests.py --html
        """
    )

    parser.add_argument("--src-only", action="store_true", help="Run only src/ tests")
    parser.add_argument("--backend-only", action="store_true", help="Run only backend/ tests")
    parser.add_argument("--vad-only", action="store_true", help="Run only VAD tests")
    parser.add_argument("--streaming-only", action="store_true", help="Run only streaming tests (src + backend)")
    parser.add_argument("--quick", action="store_true", help="Run quick subset of tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")

    args = parser.parse_args()

    print_header("Unified Test Suite - All Tests")

    # Create reports directory if needed
    if args.html:
        reports_dir = project_root / "reports"
        reports_dir.mkdir(exist_ok=True)
        print(f"{Colors.OKCYAN}Reports will be saved to: {reports_dir}{Colors.ENDC}\n")

    results = {}

    # Run tests based on arguments
    if args.quick:
        results["quick"] = run_quick_tests(args)
    elif args.src_only:
        results["src_streaming"] = run_src_streaming_tests(args)
    elif args.backend_only:
        results["backend_streaming"] = run_backend_streaming_tests(args)
    elif args.vad_only:
        results["vad"] = run_vad_tests(args)
    elif args.streaming_only:
        results["src_streaming"] = run_src_streaming_tests(args)
        results["backend_streaming"] = run_backend_streaming_tests(args)
    else:
        # Run all tests
        results["src_streaming"] = run_src_streaming_tests(args)
        results["backend_streaming"] = run_backend_streaming_tests(args)
        results["vad"] = run_vad_tests(args)

    # Print summary
    print_header("Test Summary")

    all_passed = True
    for test_name, passed in results.items():
        status = f"{Colors.OKGREEN}✓ PASSED{Colors.ENDC}" if passed else f"{Colors.FAIL}✗ FAILED{Colors.ENDC}"
        print(f"{test_name.upper():30s}: {status}")
        if not passed:
            all_passed = False

    print()

    if all_passed:
        print(f"{Colors.OKGREEN}{Colors.BOLD}All tests passed! 🎉{Colors.ENDC}")
        return 0
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}Some tests failed{Colors.ENDC}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
