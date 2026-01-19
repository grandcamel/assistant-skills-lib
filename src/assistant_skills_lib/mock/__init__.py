"""
Mock Client Module for Assistant Skills

Provides base classes for creating mock clients used in testing.
Service-specific libraries (JIRA, Confluence, Splunk) extend these
base classes with domain-specific functionality.

Example usage:
    from assistant_skills_lib.mock import BaseMockClient, create_mock_mode_checker

    # Create a service-specific mock mode checker
    is_mock_mode = create_mock_mode_checker("MYSERVICE_MOCK_MODE")

    # Create a custom mock client
    class MockMyServiceClient(BaseMockClient):
        def __init__(self, **kwargs):
            super().__init__(base_url="https://mock.myservice.com", **kwargs)

        def get_resource(self, resource_id: str) -> dict:
            return self._get_response(f"/resources/{resource_id}")
"""

from .base import (
    BaseMockClient,
    create_mock_mode_checker,
)

__all__ = [
    "BaseMockClient",
    "create_mock_mode_checker",
]
