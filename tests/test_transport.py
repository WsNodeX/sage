import io
import unittest

from sage.transport import InMemoryTransport, StdioTransport


class TestInMemory(unittest.TestCase):
    def test_client_send_is_read_by_server(self):
        # Client side uses send() -> inbox; server side reads via read_message().
        t = InMemoryTransport()
        t.send("hello")
        self.assertEqual(t.read_message(), "hello")

    def test_server_write_is_received_by_client(self):
        # Server side uses write_message() -> outbox; client side reads via recv().
        t = InMemoryTransport()
        t.write_message("world")
        self.assertEqual(t.recv(timeout=1.0), "world")

    def test_full_round_trip(self):
        t = InMemoryTransport()
        t.send("from-client")
        self.assertEqual(t.read_message(), "from-client")
        t.write_message("from-server")
        self.assertEqual(t.recv(timeout=1.0), "from-server")

    def test_recv_timeout(self):
        t = InMemoryTransport()
        with self.assertRaises(TimeoutError):
            t.recv(timeout=0.2)

    def test_close_unblocks_reader(self):
        t = InMemoryTransport()
        with self.assertRaises(EOFError):
            t.close()
            t.read_message()


class TestStdio(unittest.TestCase):
    def test_write_message_appends_newline(self):
        out = io.StringIO()
        tr = StdioTransport(outstream=out)
        tr.write_message("{}")
        self.assertEqual(out.getvalue(), "{}\n")

    def test_read_message_strips_newline(self):
        inp = io.StringIO('{"a":1}\n')
        tr = StdioTransport(instream=inp)
        self.assertEqual(tr.read_message(), '{"a":1}')

    def test_read_message_eof(self):
        inp = io.StringIO("")
        tr = StdioTransport(instream=inp)
        with self.assertRaises(EOFError):
            tr.read_message()


if __name__ == "__main__":
    unittest.main()
