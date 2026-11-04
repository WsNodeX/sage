import json
import unittest

from sage.examples.demo_server import create_server


class TestDemoServer(unittest.TestCase):
    def setUp(self):
        self.srv = create_server()

    def _handle(self, method, params=None):
        msg = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                          "params": params or {}})
        return json.loads(self.srv.handle(msg))

    def test_has_expected_tools(self):
        resp = self._handle("tools/list")
        names = {t["name"] for t in resp["result"]["tools"]}
        self.assertEqual(names, {"add", "calculate", "echo",
                                 "current_time", "system_info"})

    def test_add(self):
        resp = self._handle("tools/call", {"name": "add",
                                          "arguments": {"a": 7, "b": 5}})
        self.assertEqual(resp["result"]["content"][0]["text"], "12")

    def test_calculate_division_by_zero_is_handled(self):
        resp = self._handle("tools/call", {"name": "calculate",
                                          "arguments": {"a": 1, "b": 0, "op": "div"}})
        # The tool reports the failure in-band rather than raising.
        self.assertFalse(resp["result"]["isError"])
        self.assertIn("division by zero", resp["result"]["content"][0]["text"])

    def test_echo(self):
        resp = self._handle("tools/call", {"name": "echo",
                                          "arguments": {"text": "hi"}})
        self.assertEqual(resp["result"]["content"][0]["text"], "hi")

    def test_current_time_iso(self):
        resp = self._handle("tools/call", {"name": "current_time", "arguments": {}})
        self.assertIn("T", resp["result"]["content"][0]["text"])

    def test_resource_read(self):
        resp = self._handle("resources/read", {"uri": "sage://docs/intro"})
        self.assertIn("Sage Demo", resp["result"]["contents"][0]["text"])

    def test_prompt_render(self):
        resp = self._handle("prompts/get", {"name": "greeting",
                                           "arguments": {"name": "Ada"}})
        self.assertIn("Ada", resp["result"]["messages"][0]["content"]["text"])

    def test_schema_has_descriptions(self):
        resp = self._handle("tools/list")
        add = next(t for t in resp["result"]["tools"] if t["name"] == "add")
        self.assertIn("a", add["inputSchema"]["properties"])


if __name__ == "__main__":
    unittest.main()
