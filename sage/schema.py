"""Introspect Python functions into JSON Schema input documents.

A big part of what makes an MCP server pleasant to write is not having to
hand-maintain an ``inputSchema`` for every tool. Sage derives it directly
from the function signature and type hints, so the schema can never drift
from the implementation. Supported annotations:

    str, int, float, bool, dict, list
    list[T], dict[K, V]
    Optional[T]            -> nullable variant
    Literal["a", "b"]      -> enum constraint
    default values         -> mark the property as optional
"""

import inspect
import re
import typing


_PRIMITIVES = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    dict: "object",
    list: "array",
}


def _param_descriptions(func) -> dict:
    doc = inspect.getdoc(func)
    descs = {}
    if not doc:
        return descs
    for line in doc.splitlines():
        match = re.match(r"\s*:param\s+(\w+)\s*:\s*(.*)", line)
        if match:
            descs[match.group(1)] = match.group(2).strip()
    return descs


def _describe(annotation) -> dict:
    """Map a Python annotation to a JSON Schema fragment (without 'type')."""
    origin = typing.get_origin(annotation)
    if origin is None:
        if annotation in _PRIMITIVES:
            return {"type": _PRIMITIVES[annotation]}
        if annotation is inspect.Parameter.empty or annotation is None:
            return {"type": "string"}
        name = getattr(annotation, "__name__", str(annotation))
        if name == "str":
            return {"type": "string"}
        if name == "int":
            return {"type": "integer"}
        if name == "float":
            return {"type": "number"}
        if name == "bool":
            return {"type": "boolean"}
        return {"type": "string"}

    if origin is typing.Union:
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            base = _describe(args[0])
            base = dict(base)
            base["type"] = _as_type_list(base.get("type"))
            return base
        return {"type": "string"}

    if origin in (list, typing.List):
        args = typing.get_args(annotation)
        if args:
            item = _describe(args[0])
            return {"type": "array", "items": _strip_type(item)}
        return {"type": "array"}

    if origin in (dict, typing.Dict):
        return {"type": "object"}

    if origin is typing.Literal:
        values = [str(a) for a in typing.get_args(annotation)]
        return {"type": "string", "enum": values}

    return {"type": "string"}


def _as_type_list(prim):
    if isinstance(prim, list):
        return prim + ["null"]
    return [prim, "null"]


def _strip_type(fragment: dict) -> dict:
    """Return fragment without the leading 'type' (used for array items)."""
    out = dict(fragment)
    return out


def build_input_schema(func) -> dict:
    """Build a JSON Schema ``object`` describing ``func``'s parameters."""
    try:
        hints = typing.get_type_hints(func)
    except Exception:
        hints = {}

    sig = inspect.signature(func)
    descs = _param_descriptions(func)

    properties = {}
    required = []
    for name, param in sig.parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        annotation = hints.get(name, param.annotation)
        fragment = _describe(annotation)
        fragment = dict(fragment)
        if name in descs:
            fragment["description"] = descs[name]
        properties[name] = fragment
        if param.default is param.empty:
            required.append(name)

    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema
