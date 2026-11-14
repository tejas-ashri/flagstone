"""Python SDK for Flagstone feature flags.

    from flagstone_sdk import FlagClient

    client = FlagClient(sdk_key="...", base_url="https://flags.example.com")
    if client.is_enabled("new-dashboard", {"id": "user-123"}):
        ...
"""

from importlib.metadata import PackageNotFoundError, version

from .client import FlagClient

try:
    __version__ = version("flagstone-sdk")
except PackageNotFoundError:  # running from a source checkout that isn't installed
    __version__ = "0.0.0"

__all__ = ["FlagClient", "__version__"]
