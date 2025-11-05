#!/bin/bash
# Quick test runner script for LangGraph agent tests

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}  LangGraph Agent Test Runner${NC}"
echo -e "${BLUE}===========================================${NC}"
echo ""

# Parse arguments
TEST_TYPE="${1:-unit}"
VERBOSE="${2:-}"

case "$TEST_TYPE" in
  unit)
    echo -e "${GREEN}Running unit tests (fast)...${NC}"
    pytest unit/ -v $VERBOSE
    ;;

  integration)
    echo -e "${GREEN}Running integration tests...${NC}"
    echo -e "${RED}Warning: Requires API keys${NC}"
    pytest integration/ -v $VERBOSE
    ;;

  e2e)
    echo -e "${GREEN}Running E2E tests...${NC}"
    echo -e "${RED}Warning: Requires full environment${NC}"
    pytest e2e/ -v $VERBOSE
    ;;

  all)
    echo -e "${GREEN}Running all tests...${NC}"
    pytest -v $VERBOSE
    ;;

  coverage)
    echo -e "${GREEN}Running tests with coverage...${NC}"
    pytest unit/ --cov=backend/app/llm_agent --cov-report=html --cov-report=term
    echo ""
    echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
    ;;

  fast)
    echo -e "${GREEN}Running fast tests only...${NC}"
    pytest -m "unit and not slow" -v
    ;;

  ci)
    echo -e "${GREEN}Running CI-safe tests...${NC}"
    pytest unit/ -m "not skip_ci" -v --tb=short
    ;;

  *)
    echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
    echo ""
    echo "Usage: ./run_tests.sh [type] [options]"
    echo ""
    echo "Test types:"
    echo "  unit         - Run unit tests (fast, default)"
    echo "  integration  - Run integration tests (requires APIs)"
    echo "  e2e          - Run end-to-end tests (full pipeline)"
    echo "  all          - Run all tests"
    echo "  coverage     - Run with coverage report"
    echo "  fast         - Run only fast tests"
    echo "  ci           - Run CI-safe tests"
    echo ""
    echo "Options:"
    echo "  -s           - Show print statements"
    echo "  --pdb        - Drop into debugger on failure"
    echo ""
    echo "Examples:"
    echo "  ./run_tests.sh unit"
    echo "  ./run_tests.sh integration -s"
    echo "  ./run_tests.sh coverage"
    echo "  ./run_tests.sh ci"
    exit 1
    ;;
esac

echo ""
echo -e "${GREEN}✅ Tests complete!${NC}"
