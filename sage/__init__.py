"""Sage -- a zero-dependency framework for building MCP servers in Python.

Sage lets you expose Python functions as Model Context Protocol tools,
resources and prompts with no third-party dependencies. Build a server,
register your callables, and serve it over stdio so any MCP client can
drive it.
"""

from .errors import McpError
from .protocol import (
    make_error,
    make_notification,
    make_request,
    make_response,
    parse_message,
)
from .registry import Prompt, Resource, Tool, prompt, resource, tool
from .server import MCPServer, SUPPORTED_VERSIONS
from .transport import InMemoryTransport, StdioTransport, Transport

__version__ = "1.0.0"

__all__ = [
    "MCPServer",
    "Tool",
    "Resource",
    "Prompt",
    "tool",
    "resource",
    "prompt",
    "Transport",
    "StdioTransport",
    "InMemoryTransport",
    "McpError",
    "parse_message",
    "make_request",
    "make_response",
    "make_error",
    "make_notification",
    "SUPPORTED_VERSIONS",
    "__version__",
]
