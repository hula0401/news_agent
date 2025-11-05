#!/bin/bash
# Run integration and E2E tests with proper environment setup

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}  Integration & E2E Test Runner${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Check environment variables
echo -e "${YELLOW}Checking environment...${NC}"
if [ -z "$ZHIPUAI_API_KEY" ]; then
    echo -e "${RED}❌ ZHIPUAI_API_KEY not set${NC}"
    echo "Export it with: export ZHIPUAI_API_KEY=your_key"
    exit 1
fi

if [ -z "$SUPABASE_URL" ]; then
    echo -e "${YELLOW}⚠️  SUPABASE_URL not set (using mock)${NC}"
fi

echo -e "${GREEN}✅ Environment OK${NC}"
echo ""

# Parse test type
TEST_TYPE="${1:-integration}"

case "$TEST_TYPE" in
    integration)
        echo -e "${GREEN}Running Integration Tests...${NC}"
        echo -e "${YELLOW}Testing agent with various real queries${NC}"
        echo ""
        pytest integration/test_agent_queries.py -v -s --tb=short
        ;;

    e2e)
        echo -e "${GREEN}Running E2E Tests...${NC}"
        echo -e "${YELLOW}Testing full pipeline with memory and watchlist${NC}"
        echo ""
        pytest e2e/test_full_pipeline.py -v -s --tb=short
        ;;

    all)
        echo -e "${GREEN}Running All Integration & E2E Tests...${NC}"
        echo ""
        echo -e "${BLUE}=== Integration Tests ===${NC}"
        pytest integration/ -v -s --tb=short
        echo ""
        echo -e "${BLUE}=== E2E Tests ===${NC}"
        pytest e2e/ -v -s --tb=short
        ;;

    quick)
        echo -e "${GREEN}Running Quick Test Suite (no slow tests)...${NC}"
        pytest integration/ e2e/ -m "not slow" -v --tb=short
        ;;

    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo ""
        echo "Usage: ./run_integration_tests.sh [type]"
        echo ""
        echo "Test types:"
        echo "  integration  - Integration tests with real APIs (default)"
        echo "  e2e          - End-to-end pipeline tests"
        echo "  all          - Run both integration and E2E"
        echo "  quick        - Run fast tests only"
        echo ""
        echo "Examples:"
        echo "  ./run_integration_tests.sh integration"
        echo "  ./run_integration_tests.sh e2e"
        echo "  ./run_integration_tests.sh all"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Tests complete!${NC}"
