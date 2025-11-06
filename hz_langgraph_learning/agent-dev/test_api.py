#!/usr/bin/env python3
"""
Quick test script to verify API structure and imports.
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all required imports work."""
    try:
        logger.info("Testing imports...")

        # Test FastAPI imports
        from fastapi import FastAPI, HTTPException
        logger.info("✓ FastAPI imports successful")

        # Test Pydantic imports
        from pydantic import BaseModel, Field
        logger.info("✓ Pydantic imports successful")

        # Test agent_core imports
        from agent_core.graph import run_market_agent
        from agent_core.state import ChatMessage, MarketState
        logger.info("✓ agent_core imports successful")

        # Test API module
        import api
        logger.info("✓ api module imports successful")

        # Verify app instance
        assert hasattr(api, 'app'), "FastAPI app instance not found"
        logger.info("✓ FastAPI app instance exists")

        # Check routes
        routes = [route.path for route in api.app.routes]
        logger.info(f"✓ Available routes: {routes}")

        expected_routes = ["/", "/health", "/chat", "/api/info"]
        for route in expected_routes:
            assert route in routes, f"Route {route} not found"
        logger.info("✓ All expected routes exist")

        logger.info("\n✅ All tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Import test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
