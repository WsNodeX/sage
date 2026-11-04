"""Error codes and exceptions used across the Sage protocol layer.

These mirror the JSON-RPC 2.0 standard error space plus a server-error
window (-32000 .. -32099) reserved for implementation specific faults.
"""

# JSON-RPC 2.0 standard codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Implementation defined server errors
SERVER_ERROR = -32000


class McpError(Exception):
    """An error that maps directly onto a JSON-RPC error object."""

    def __init__(self, code: int, message: str, data=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self, msg_id=None) -> dict:
        err = {"code": self.code, "message": self.message}
        if self.data is not None:
            err["data"] = self.data
        return {"jsonrpc": "2.0", "id": msg_id, "error": err}
