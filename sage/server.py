"""The MCP server: lifecycle, capability negotiation and request dispatch."""

import json

from .errors import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    McpError,
)
from .protocol import (
    is_notification,
    make_error,
    make_response,
    parse_message,
    serialize,
)
from .registry import Prompt, Resource, Tool
from .transport import Transport

# Protocol versions this server understands, oldest -> newest.
SUPPORTED_VERSIONS = ["2024-11-05", "2025-03-26"]


class MCPServer:
    """A dependency-free Model Context Protocol server.

    Register tools, resources and prompts, then either call :meth:`handle`
    for a single message (useful for tests and embedded use) or :meth:`run`
    to serve a :class:`~sage.transport.Transport` until it closes.
    """

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.tools = {}
        self.resources = {}
        self.prompts = {}
        self._initialized = False
        self.protocol_version = SUPPORTED_VERSIONS[-1]
        self.client_info = {}
        self.client_capabilities = {}

    # -- registration -----------------------------------------------------
    def add_tool(self, tool: Tool) -> Tool:
        self.tools[tool.name] = tool
        return tool

    def add_resource(self, resource: Resource) -> Resource:
        self.resources[resource.uri] = resource
        return resource

    def add_prompt(self, prompt: Prompt) -> Prompt:
        self.prompts[prompt.name] = prompt
        return prompt

    def tool(self, name=None, description=None):
        def deco(func):
            return self.add_tool(Tool(name or func.__name__,
                                     description or _first_line(func), func))
        return deco

    def resource(self, uri, name=None, description=None, mime_type="text/plain"):
        def deco(func):
            return self.add_resource(Resource(uri, name or func.__name__,
                                             description or _first_line(func),
                                             func, mime_type))
        return deco

    def prompt(self, name=None, description=None):
        def deco(func):
            return self.add_prompt(Prompt(name or func.__name__,
                                         description or _first_line(func), func))
        return deco

    # -- single-message handling -----------------------------------------
    def handle(self, raw: str):
        """Process one raw JSON-RPC message and return the response string.

        Returns ``None`` for notifications (which require no reply).
        """
        try:
            message = parse_message(raw)
        except McpError as exc:
            return serialize(exc.to_dict(None))

        if is_notification(message):
            self._handle_notification(message.get("method"), message.get("params") or {})
            return None

        msg_id = message.get("id")
        method = message.get("method")
        params = message.get("params") or {}
        if not isinstance(params, dict):
            params = {}

        try:
            result = self._dispatch(method, params)
        except McpError as exc:
            return serialize(make_error(msg_id, exc.code, exc.message, exc.data))
        except Exception as exc:  # defensive: never leak a traceback
            return serialize(make_error(msg_id, INTERNAL_ERROR,
                                        "internal error: %s" % exc))
        return serialize(make_response(msg_id, result))

    # -- dispatch table ---------------------------------------------------
    def _dispatch(self, method, params):
        if method == "initialize":
            return self._do_initialize(params)
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [t.describe() for t in self.tools.values()]}
        if method == "tools/call":
            return self._do_tool_call(params)
        if method == "resources/list":
            return {"resources": [r.describe() for r in self.resources.values()]}
        if method == "resources/read":
            return self._do_resource_read(params)
        if method == "prompts/list":
            return {"prompts": [p.describe() for p in self.prompts.values()]}
        if method == "prompts/get":
            return self._do_prompt_get(params)
        raise McpError(METHOD_NOT_FOUND, "method not found: %s" % method)

    # -- handlers ---------------------------------------------------------
    def _handle_notification(self, method, params):
        if method == "notifications/initialized":
            self._initialized = True

    def _negotiate_version(self, client_version) -> str:
        if client_version in SUPPORTED_VERSIONS:
            return client_version
        # Client asked for something we don't recognise: offer our newest.
        return SUPPORTED_VERSIONS[-1]

    def _do_initialize(self, params):
        requested = params.get("protocolVersion")
        self.protocol_version = self._negotiate_version(requested)
        self.client_capabilities = params.get("capabilities", {}) or {}
        self.client_info = params.get("clientInfo", {}) or {}
        return {
            "protocolVersion": self.protocol_version,
            "capabilities": self._capabilities(),
            "serverInfo": {"name": self.name, "version": self.version},
        }

    def _capabilities(self) -> dict:
        caps = {}
        if self.tools:
            caps["tools"] = {"listChanged": False}
        if self.resources:
            caps["resources"] = {"listChanged": False}
        if self.prompts:
            caps["prompts"] = {"listChanged": False}
        return caps

    def _do_tool_call(self, params):
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            arguments = {}
        tool = self.tools.get(name)
        if tool is None:
            raise McpError(INVALID_PARAMS, "unknown tool: %s" % name)
        required = tool.input_schema.get("required", [])
        missing = [r for r in required if r not in arguments]
        if missing:
            raise McpError(INVALID_PARAMS,
                           "missing required arguments: %s" % ", ".join(missing))
        try:
            output = tool.invoke(arguments)
        except Exception as exc:
            # Per the MCP spec, tool failures are *results*, not protocol errors.
            return {"content": [{"type": "text",
                                 "text": "error: %s" % exc}],
                    "isError": True}
        if isinstance(output, (list, dict)):
            content = output
        else:
            content = [{"type": "text", "text": str(output)}]
        return {"content": content, "isError": False}

    def _do_resource_read(self, params):
        uri = params.get("uri")
        resource = self.resources.get(uri)
        if resource is None:
            raise McpError(INVALID_PARAMS, "unknown resource: %s" % uri)
        return {"contents": [{"uri": uri,
                              "mimeType": resource.mime_type,
                              "text": resource.read()}]}

    def _do_prompt_get(self, params):
        name = params.get("name")
        arguments = params.get("arguments") or {}
        prompt = self.prompts.get(name)
        if prompt is None:
            raise McpError(INVALID_PARAMS, "unknown prompt: %s" % name)
        return {"messages": prompt.render(arguments)}

    # -- serving loop -----------------------------------------------------
    def run(self, transport: Transport) -> None:
        """Read, handle and reply to messages until the transport closes."""
        try:
            while True:
                try:
                    raw = transport.read_message()
                except EOFError:
                    break
                if not raw.strip():
                    continue
                response = self.handle(raw)
                if response is not None:
                    transport.write_message(response)
        finally:
            transport.close()


def _first_line(func) -> str:
    doc = getattr(func, "__doc__", None)
    if not doc:
        return func.__name__
    return doc.strip().splitlines()[0]
