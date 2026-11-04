"""A self-contained demo server showcasing tools, a resource and a prompt.

Run it with ``python -m sage`` and connect any MCP client, or import
``create_server`` and drive it in-process (see the test-suite).
"""

import datetime
import platform

from ..registry import prompt, resource, tool
from ..server import MCPServer


def create_server() -> MCPServer:
    server = MCPServer("sage-demo", "1.0.0")

    @server.tool(description="Add two integers and return the sum.")
    def add(a: int, b: int) -> int:
        """Add two integers together.

        :param a: the first operand
        :param b: the second operand
        """
        return a + b

    @server.tool(description="Perform a basic arithmetic operation on two numbers.")
    def calculate(a: int, b: int, op: str = "add") -> str:
        """Apply +, -, * or / to two integers.

        :param a: left operand
        :param b: right operand
        :param op: one of add, sub, mul, div
        """
        if op == "add":
            result = a + b
        elif op == "sub":
            result = a - b
        elif op == "mul":
            result = a * b
        elif op == "div":
            if b == 0:
                return "error: division by zero"
            result = a / b
        else:
            return "error: unknown operator '%s'" % op
        return "%d %s %d = %s" % (a, op, b, result)

    @server.tool(description="Echo the supplied text straight back to the caller.")
    def echo(text: str) -> str:
        """Return the input text unchanged.

        :param text: the message to echo
        """
        return text

    @server.tool(description="Return the current time in UTC as an ISO-8601 string.")
    def current_time() -> str:
        """Report the current UTC timestamp."""
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    @server.tool(description="Report basic information about the host system.")
    def system_info() -> str:
        """Summarise OS, hostname and the running Python version."""
        return "system=%s node=%s python=%s" % (
            platform.system(),
            platform.node(),
            platform.python_version(),
        )

    @server.resource(
        uri="sage://docs/intro",
        description="A short markdown introduction to the demo server.",
        mime_type="text/markdown",
    )
    def intro_doc() -> str:
        """The introductory document served at sage://docs/intro."""
        return (
            "# Sage Demo Server\n\n"
            "This server demonstrates three MCP primitives:\n\n"
            "- **tools** -- `add`, `calculate`, `echo`, `current_time`, `system_info`\n"
            "- **resources** -- the document you are reading at `sage://docs/intro`\n"
            "- **prompts** -- a `greeting` prompt builder\n"
        )

    @server.prompt(description="Build a friendly greeting for a named person.")
    def greeting(name: str) -> str:
        """Create a warm opening line addressing the given name.

        :param name: the person to greet
        """
        return "Please greet %s warmly and ask how you can be of help today." % name

    return server
