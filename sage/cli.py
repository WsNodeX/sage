"""Command-line entry point for running a Sage server over stdio."""

import sys

from .examples.demo_server import create_server
from .transport import StdioTransport


def main(argv=None) -> int:
    """Launch the demo server over stdio.

    ``python -m sage`` starts the bundled demo server. The process then
    speaks JSON-RPC 2.0 on stdin/stdout and can be driven by any MCP client.
    """
    server = create_server()
    server.run(StdioTransport())
    return 0


if __name__ == "__main__":
    sys.exit(main())
