"""JSON-RPC 2.0 message model.

Sage speaks JSON-RPC 2.0 over newline-delimited JSON (the transport
convention used by the Model Context Protocol on stdio). This module is a
tiny, dependency-free implementation of the parts of the spec a server
needs: parsing inbound messages, detecting notifications, and building
well-formed requests / responses / errors.
"""

import json

from .errors import (
    PARSE_ERROR,
    INVALID_REQUEST,
    McpError,
)


def parse_message(raw: str) -> dict:
    """Parse a raw JSON-RPC message string into a dict.

    Raises :class:`McpError` with the appropriate code when the payload is
    not a valid JSON-RPC 2.0 object.
    """
    text = (raw or "").strip()
    if not text:
        raise McpError(PARSE_ERROR, "empty message")
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise McpError(PARSE_ERROR, "parse error: %s" % exc)
    if not isinstance(obj, dict):
        raise McpError(INVALID_REQUEST, "request must be a JSON object")
    if obj.get("jsonrpc") != "2.0":
        raise McpError(INVALID_REQUEST, "missing or invalid jsonrpc version")
    return obj


def is_notification(message: dict) -> bool:
    """A notification carries a ``method`` but no ``id``."""
    return "id" not in message


def make_response(msg_id, result) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def make_error(msg_id, code: int, message: str, data=None) -> dict:
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": msg_id, "error": err}


def make_request(msg_id, method: str, params=None) -> dict:
    msg = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def make_notification(method: str, params=None) -> dict:
    msg = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def serialize(message: dict) -> str:
    return json.dumps(message, ensure_ascii=False)
