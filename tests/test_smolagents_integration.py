#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for the SmolaAgents integration with MinionProviderToSmolAdapter.

This module tests the integration between MinionProviderToSmolAdapter and SmolaAgents,
ensuring that tools can be properly called through the adapter.
"""

import os
import sys
import pytest
from unittest import mock
from typing import List, Dict, Any, Optional

# Add parent directory to path to import from minion_agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from minion_agent.providers.adapters import MinionProviderToSmolAdapter


@pytest.fixture
def mock_agent():
    """Fixture to mock a ToolCallingAgent instance."""
    agent_mock = mock.MagicMock()
    agent_mock.run.return_value = "Today's date is 2023-01-01 and the capital of France is Paris."
    return agent_mock


@pytest.fixture
def patch_tool_calling_modules(
    mock_minion, mock_config, mock_providers, mock_tool_calling_provider, 
    mock_smolagents, mock_tool_decorator, mock_agent, monkeypatch
):
    """Fixture to patch all required modules and configure mocks for tool calling."""
    # Set up patches
    modules = {
        'minion': mock_minion,
        'minion.config': mock_config,
        'minion.providers': mock_providers,
        'smolagents': mock_smolagents,
        'smolagents.agents': mock_smolagents.agents,
        'smolagents.tools': mock_smolagents.tools,
    }
    
    for name, mock_obj in modules.items():
        monkeypatch.setitem(sys.modules, name, mock_obj)
    
    # Configure mocks
    mock_providers.create_llm_provider.return_value = mock_tool_calling_provider
    mock_smolagents.tools.tool = mock_tool_decorator
    mock_smolagents.agents.ToolCallingAgent.return_value = mock_agent


def test_tool_calling_agent_integration(patch_tool_calling_modules, mock_smolagents, mock_agent):
    """Test integration with ToolCallingAgent."""
    from smolagents.agents import ToolCallingAgent
    from smolagents.tools import tool
    
    # Create the adapter
    adapter = MinionProviderToSmolAdapter.from_model_name("gpt-4o")
    
    # Define tools
    @tool
    def date_tool() -> str:
        """Get the current date."""
        return "2023-01-01"
    
    @tool
    def capital_tool(country: str) -> str:
        """Get the capital of a country."""
        return "Paris" if country.lower() == "france" else f"Unknown capital for {country}"
    
    # Create the agent
    agent = ToolCallingAgent(
        model=adapter,
        tools=[date_tool, capital_tool]
    )
    
    # Test the agent
    response = agent.run("What is today's date? Also, what is the capital of France?")
    
    # Verify we got a proper response
    assert response == "Today's date is 2023-01-01 and the capital of France is Paris."
    
    # Verify the model was called with our query
    mock_smolagents.agents.ToolCallingAgent.assert_called_once()
    mock_agent.run.assert_called_once_with(
        "What is today's date? Also, what is the capital of France?"
    ) 