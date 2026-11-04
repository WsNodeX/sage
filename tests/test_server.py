import json
import threading
import unittest

from sage.protocol import make_notification, make_request, parse_message
from sage.server import MCPServer, SUPPORTED_VERSIONS
from sage.transport import InMemoryTransport


def build_server() -> MCPServer:
    srv = MCPServer("test", "0.1.0")

    @srv.tool(description="add")
    def add(a: int, b: int) -> int:
        """Add.

        :param a: x
        :param b: y
        """
        return a + b

    @srv.tool(description="boom")
    def boom(x: int) -> int:
        raise ValueError("kaboom")

    @srv.resource(uri="mem://doc", description="d")
    def doc() -> str:
        return "body"

    @srv.prompt(description="g")
    def greet(name: str) -> str:
        return "hi %s" % name

    return srv


class TestHandleSingle(unittest.TestCase):
    def setUp(self):
        self.srv = build_server()

    def _call(self, raw):
        return json.loads(self.srv.handle(raw))

    def test_initialize_shape(self):
        resp = self._call(json.dumps(make_request(1, "initialize", {
            "protocolVersion": SUPPORTED_VERSIONS[-1],
            "capabilities": {},
            "clientInfo": {"name": "c", "version": "1"},
        })))
        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["protocolVersion"], SUPPORTED_VERSIONS[-1])
        self.assertIn("tools", resp["result"]["capabilities"])
        self.assertEqual(resp["result"]["serverInfo"]["name"], "test")

    def test_initialize_negotiates_unknown_version(self):
        resp = self._call(json.dumps(make_request(2, "initialize",
                                                 {"protocolVersion": "1999-01-01"})))
        self.assertEqual(resp["result"]["protocolVersion"], SUPPORTED_VERSIONS[-1])

    def test_ping(self):
        resp = self._call(json.dumps(make_request(3, "ping")))
        self.assertEqual(resp["result"], {})

    def test_tools_list(self):
        resp = self._call(json.dumps(make_request(4, "tools/list")))
        names = {t["name"] for t in resp["result"]["tools"]}
        self.assertIn("add", names)
        self.assertIn("boom", names)

    def test_tools_call_success(self):
        resp = self._call(json.dumps(make_request(5, "tools/call",
                                                 {"name": "add", "arguments": {"a": 4, "b": 5}})))
        self.assertFalse(resp["result"]["isError"])
        self.assertEqual(resp["result"]["content"][0]["text"], "9")

    def test_tools_call_missing_arg(self):
        resp = self._call(json.dumps(make_request(6, "tools/call",
                                                 {"name": "add", "arguments": {"a": 1}})))
        self.assertEqual(resp["error"]["code"], -32602)

    def test_tools_call_unknown(self):
        resp = self._call(json.dumps(make_request(7, "tools/call",
                                                 {"name": "nope", "arguments": {}})))
        self.assertEqual(resp["error"]["code"], -32602)

    def test_tools_call_returns_error_result(self):
        resp = self._call(json.dumps(make_request(8, "tools/call",
                                                 {"name": "boom", "arguments": {"x": 1}})))
        self.assertTrue(resp["result"]["isError"])
        self.assertIn("kaboom", resp["result"]["content"][0]["text"])

    def test_resources_list_and_read(self):
        lst = self._call(json.dumps(make_request(9, "resources/list")))
        self.assertEqual(lst["result"]["resources"][0]["uri"], "mem://doc")
        rd = self._call(json.dumps(make_request(10, "resources/read",
                                               {"uri": "mem://doc"})))
        self.assertEqual(rd["result"]["contents"][0]["text"], "body")

    def test_prompts_list_and_get(self):
        lst = self._call(json.dumps(make_request(11, "prompts/list")))
        self.assertEqual(lst["result"]["prompts"][0]["name"], "greet")
        got = self._call(json.dumps(make_request(12, "prompts/get",
                                                {"name": "greet", "arguments": {"name": "Jo"}})))
        self.assertIn("Jo", got["result"]["messages"][0]["content"]["text"])

    def test_unknown_method(self):
        resp = self._call(json.dumps(make_request(13, "bogus/method")))
        self.assertEqual(resp["error"]["code"], -32601)

    def test_notification_returns_none(self):
        self.assertIsNone(self.srv.handle(
            json.dumps(make_notification("notifications/initialized"))))


class TestIntegrationLoop(unittest.TestCase):
    def test_full_conversation_over_transport(self):
        srv = build_server()
        transport = InMemoryTransport()

        def serve():
            srv.run(transport)

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()

        transport.send(json.dumps(make_request(1, "initialize", {
            "protocolVersion": SUPPORTED_VERSIONS[-1],
            "capabilities": {}, "clientInfo": {},
        })))
        init = json.loads(transport.recv())
        self.assertEqual(init["result"]["serverInfo"]["name"], "test")

        # A notification must NOT produce a response.
        transport.send(json.dumps(make_notification("notifications/initialized")))
        with self.assertRaises(TimeoutError):
            transport.recv(timeout=1.0)

        transport.send(json.dumps(make_request(2, "tools/call",
                                               {"name": "add", "arguments": {"a": 2, "b": 40}})))
        call = json.loads(transport.recv())
        self.assertEqual(call["result"]["content"][0]["text"], "42")

        transport.send(json.dumps(make_request(3, "tools/list")))
        lst = json.loads(transport.recv())
        self.assertGreaterEqual(len(lst["result"]["tools"]), 2)

        transport.close()
        thread.join(timeout=5.0)
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
