"""Transports for moving JSON-RPC messages in and out of a server.

A :class:`Transport` is intentionally minimal: read one message, write one
message. Sage ships two implementations:

* :class:`StdioTransport` -- the production path. Reads newline-delimited
  JSON from ``stdin`` and writes it to ``stdout`` so the process can be
  driven by any MCP client (Claude Desktop, IDE extensions, custom agents).
* :class:`InMemoryTransport` -- a loopback pair used by the test-suite and
  by anyone who wants to exercise a server without spawning a subprocess.
"""

import abc
import queue
import sys


class Transport(abc.ABC):
    """Bidirectional message channel."""

    @abc.abstractmethod
    def read_message(self) -> str:
        """Return the next inbound message as a raw string."""
        raise NotImplementedError

    @abc.abstractmethod
    def write_message(self, text: str) -> None:
        """Emit an outbound message."""
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover - default no-op
        pass


class StdioTransport(Transport):
    """Read from ``stdin`` / write to ``stdout`` (newline-delimited JSON)."""

    def __init__(self, instream=None, outstream=None):
        self._in = instream if instream is not None else sys.stdin
        self._out = outstream if outstream is not None else sys.stdout
        self._closed = False

    def read_message(self) -> str:
        line = self._in.readline()
        if line == "":  # EOF
            raise EOFError("stdio transport closed")
        return line.rstrip("\n").rstrip("\r")

    def write_message(self, text: str) -> None:
        self._out.write(text + "\n")
        self._out.flush()

    def close(self) -> None:
        self._closed = True


class InMemoryTransport(Transport):
    """A synchronous loopback transport for tests and in-process use.

    The *server side* (what :class:`~sage.server.MCPServer` talks to) reads
    from and writes to the internal queues via :meth:`read_message` /
    :meth:`write_message`. The *client side* drives the same queues with
    :meth:`send` and :meth:`recv`.
    """

    def __init__(self):
        self._inbox = queue.Queue()   # client -> server
        self._outbox = queue.Queue()  # server -> client
        self._closed = False
        self._sentinel = object()

    # -- server side --
    def read_message(self) -> str:
        item = self._inbox.get()
        if item is self._sentinel:
            raise EOFError("transport closed")
        return item

    def write_message(self, text: str) -> None:
        self._outbox.put(text)

    # -- client side --
    def send(self, text: str) -> None:
        self._inbox.put(text)

    def recv(self, timeout: float = 5.0):
        try:
            return self._outbox.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError("no response received within %ss" % timeout)

    def pending(self) -> bool:
        return not self._outbox.empty()

    def close(self) -> None:
        self._closed = True
        self._inbox.put(self._sentinel)
