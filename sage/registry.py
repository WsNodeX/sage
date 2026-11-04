"""Tool / resource / prompt definitions and the decorators that build them.

A server owns three registries. Each entry is a thin wrapper around a plain
Python callable plus whatever metadata the protocol needs. The decorators
return the wrapper so they can be used both inline (``@srv.tool()``) and as
standalone factories that you later hand to ``server.add_tool(...)``.
"""

import inspect

from .schema import build_input_schema


def _first_line(func) -> str:
    doc = inspect.getdoc(func)
    if not doc:
        return func.__name__
    return doc.strip().splitlines()[0]


class Tool:
    """A callable exposed to clients through ``tools/call``."""

    def __init__(self, name, description, func, input_schema=None):
        self.name = name
        self.description = description
        self.func = func
        self.input_schema = input_schema or build_input_schema(func)

    def invoke(self, arguments: dict):
        return self.func(**arguments)

    def describe(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class Resource:
    """A read-only piece of content addressable by URI."""

    def __init__(self, uri, name, description, read_func, mime_type="text/plain"):
        self.uri = uri
        self.name = name
        self.description = description
        self.read_func = read_func
        self.mime_type = mime_type

    def read(self) -> str:
        return self.read_func()

    def describe(self) -> dict:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


class Prompt:
    """A templated conversation starter rendered on ``prompts/get``."""

    def __init__(self, name, description, render_func, arguments=None):
        self.name = name
        self.description = description
        self.render_func = render_func
        self.arguments = arguments if arguments is not None else self._infer()

    def _infer(self) -> list:
        schema = build_input_schema(self.render_func)
        result = []
        for prop_name, prop in schema.get("properties", {}).items():
            entry = {"name": prop_name}
            if "description" in prop:
                entry["description"] = prop["description"]
            if prop_name not in schema.get("required", []):
                entry["required"] = False
            else:
                entry["required"] = True
            result.append(entry)
        return result

    def render(self, arguments: dict) -> list:
        text = self.render_func(**arguments)
        if isinstance(text, list):
            return text
        return [{"role": "user", "content": {"type": "text", "text": str(text)}}]

    def describe(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments,
        }


# --------------------------------------------------------------------------
# Standalone decorators (return a wrapper; register it manually later).
# --------------------------------------------------------------------------

def tool(name=None, description=None):
    def deco(func):
        return Tool(name or func.__name__, description or _first_line(func), func)
    return deco


def resource(uri, name=None, description=None, mime_type="text/plain"):
    def deco(func):
        return Resource(
            uri,
            name or func.__name__,
            description or _first_line(func),
            func,
            mime_type,
        )
    return deco


def prompt(name=None, description=None):
    def deco(func):
        return Prompt(name or func.__name__, description or _first_line(func), func)
    return deco
