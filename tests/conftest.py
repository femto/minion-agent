"""
Shared pytest fixtures for the minion-manus project tests.

This module contains shared fixtures that can be used across multiple test files.

To run all tests:
    pytest

To run specific test files:
    pytest tests/test_minion_provider_adapter.py

To run specific test functions:
    pytest tests/test_minion_provider_adapter.py::test_create_adapter_from_model_name

To run tests with specific markers:
    pytest -m "asyncio"

To generate test coverage report:
    pytest --cov=minion_agent
"""

import os
import sys
import pytest
from unittest import mock

# Add parent directory to path to import from minion_agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Shared fixtures for mocking
@pytest.fixture
def mock_minion():
    """Fixture to mock the minion module."""
    return mock.MagicMock()


@pytest.fixture
def mock_config():
    """Fixture to mock the minion.config module."""
    config_mock = mock.MagicMock()
    config_mock.models = {"gpt-4o": {"some": "config"}}
    return config_mock


@pytest.fixture
def mock_providers():
    """Fixture to mock the minion.providers module."""
    return mock.MagicMock()


@pytest.fixture
def mock_basic_provider():
    """Fixture to mock a basic provider instance."""
    provider_mock = mock.MagicMock()
    provider_mock.generate_sync.return_value = "Mock response"
    # The adapter's async path awaits provider.generate()
    provider_mock.generate = mock.AsyncMock(return_value="Async mock response")
    provider_mock.agenerate = mock.AsyncMock(return_value={
        "choices": [{"message": {"content": "Async mock response"}}]
    })
    provider_mock.chat_completion.return_value = {
        "choices": [{"message": {"content": "Mock response"}}]
    }
    return provider_mock


@pytest.fixture
def mock_tool_calling_provider():
    """Fixture to mock a provider with tool calling capability."""
    provider_mock = mock.MagicMock()
    tool_call_response = "I'll help with that"
    provider_mock.generate_sync.return_value = tool_call_response
    provider_mock.chat_completion.return_value = {
        "choices": [{
            "message": {
                "content": "I'll help with that",
                "tool_calls": [
                    {
                        "type": "function",
                        "function": {
                            "name": "date_tool",
                            "arguments": "{}"
                        }
                    }
                ]
            }
        }]
    }
    return provider_mock


@pytest.fixture
def mock_smolagents():
    """Fixture to mock the smolagents module."""
    return mock.MagicMock()


@pytest.fixture
def mock_tool_decorator():
    """Fixture to mock the tool decorator."""
    def tool_decorator(func):
        func._is_tool = True
        return func
    return tool_decorator


@pytest.fixture
def patch_basic_modules(mock_minion, mock_config, mock_providers, mock_basic_provider, monkeypatch):
    """Fixture to patch modules for basic tests."""
    # Set up patches
    modules = {
        'minion': mock_minion,
        'minion.config': mock_config,
        'minion.providers': mock_providers,
    }
    for name, mock_obj in modules.items():
        monkeypatch.setitem(sys.modules, name, mock_obj)
    
    # Configure mock provider
    mock_providers.create_llm_provider.return_value = mock_basic_provider 