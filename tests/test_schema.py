import unittest
from typing import Dict, List, Literal, Optional

from sage.schema import build_input_schema


def sample(a: int, b: str) -> None:
    """Sample.

    :param a: first
    :param b: second
    """
    pass


def with_defaults(name: str, count: int = 1) -> None:
    pass


def with_optional(value: Optional[int] = None) -> None:
    pass


def with_list(items: List[str]) -> None:
    pass


def with_dict(config: Dict[str, int]) -> None:
    pass


def with_literal(mode: Literal["fast", "slow"]) -> None:
    pass


class TestSchema(unittest.TestCase):
    def test_basic_types_and_required(self):
        schema = build_input_schema(sample)
        self.assertEqual(schema["type"], "object")
        self.assertIn("a", schema["properties"])
        self.assertIn("b", schema["properties"])
        self.assertEqual(schema["properties"]["a"]["type"], "integer")
        self.assertEqual(schema["properties"]["b"]["type"], "string")
        self.assertEqual(set(schema["required"]), {"a", "b"})

    def test_descriptions_pulled_from_docstring(self):
        schema = build_input_schema(sample)
        self.assertEqual(schema["properties"]["a"]["description"], "first")
        self.assertEqual(schema["properties"]["b"]["description"], "second")

    def test_default_marks_optional(self):
        schema = build_input_schema(with_defaults)
        self.assertIn("name", schema["required"])
        self.assertNotIn("count", schema["required"])

    def test_optional_is_nullable(self):
        schema = build_input_schema(with_optional)
        self.assertNotIn("value", schema.get("required", []))
        tipe = schema["properties"]["value"]["type"]
        self.assertIn("null", tipe)

    def test_list_annotation(self):
        schema = build_input_schema(with_list)
        prop = schema["properties"]["items"]
        self.assertEqual(prop["type"], "array")
        self.assertEqual(prop["items"]["type"], "string")

    def test_dict_annotation(self):
        schema = build_input_schema(with_dict)
        self.assertEqual(schema["properties"]["config"]["type"], "object")

    def test_literal_is_enum(self):
        schema = build_input_schema(with_literal)
        prop = schema["properties"]["mode"]
        self.assertEqual(prop["enum"], ["fast", "slow"])


if __name__ == "__main__":
    unittest.main()
