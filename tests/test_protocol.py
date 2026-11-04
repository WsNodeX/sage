import json
import unittest

from sage.errors import INVALID_REQUEST, PARSE_ERROR, McpError
from sage.protocol import (
    is_notification,
    make_error,
    make_notification,
    make_request,
    make_response,
    parse_message,
    serialize,
)


class TestParse(unittest.TestCase):
    def test_valid_request(self):
        msg = parse_message('{"jsonrpc":"2.0","id":1,"method":"ping"}')
        self.assertEqual(msg["method"], "ping")
        self.assertEqual(msg["id"], 1)

    def test_empty_string_is_parse_error(self):
        with self.assertRaises(McpError) as ctx:
            parse_message("")
        self.assertEqual(ctx.exception.code, PARSE_ERROR)

    def test_malformed_json_is_parse_error(self):
        with self.assertRaises(McpError) as ctx:
            parse_message("{not json")
        self.assertEqual(ctx.exception.code, PARSE_ERROR)

    def test_non_object_is_invalid_request(self):
        with self.assertRaises(McpError) as ctx:
            parse_message("[1,2,3]")
        self.assertEqual(ctx.exception.code, INVALID_REQUEST)

    def test_missing_version_is_invalid_request(self):
        with self.assertRaises(McpError) as ctx:
            parse_message('{"id":1,"method":"ping"}')
        self.assertEqual(ctx.exception.code, INVALID_REQUEST)

    def test_wrong_version_is_invalid_request(self):
        with self.assertRaises(McpError) as ctx:
            parse_message('{"jsonrpc":"1.0","id":1,"method":"ping"}')
        self.assertEqual(ctx.exception.code, INVALID_REQUEST)


class TestNotification(unittest.TestCase):
    def test_notification_has_no_id(self):
        self.assertTrue(is_notification({"jsonrpc": "2.0", "method": "x"}))

    def test_request_has_id(self):
        self.assertFalse(is_notification({"jsonrpc": "2.0", "id": 2, "method": "x"}))


class TestBuilders(unittest.TestCase):
    def test_make_response_round_trip(self):
        out = json.loads(serialize(make_response(7, {"ok": True})))
        self.assertEqual(out["id"], 7)
        self.assertEqual(out["result"], {"ok": True})
        self.assertEqual(out["jsonrpc"], "2.0")

    def test_make_error_with_data(self):
        out = json.loads(serialize(make_error(3, -32000, "boom", {"x": 1})))
        self.assertEqual(out["error"]["code"], -32000)
        self.assertEqual(out["error"]["data"], {"x": 1})

    def test_make_request_omits_params_when_none(self):
        out = json.loads(serialize(make_request("a", "b")))
        self.assertNotIn("params", out)

    def test_make_request_includes_params(self):
        out = json.loads(serialize(make_request("a", "b", {"c": 1})))
        self.assertEqual(out["params"], {"c": 1})

    def test_make_notification_omits_id(self):
        out = json.loads(serialize(make_notification("n", {"k": 1})))
        self.assertNotIn("id", out)


if __name__ == "__main__":
    unittest.main()
