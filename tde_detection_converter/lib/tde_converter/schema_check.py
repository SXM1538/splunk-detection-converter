"""Offline evaluator for the vocabulary used by the bundled schemas.

This is deliberately not a general JSON Schema implementation. Unknown assertion
keywords fail closed. References can only point inside the bundled document.
Repository references are checked separately from structural validation.
"""
import json
import re
import uuid
from datetime import date
from urllib.parse import urlparse

ANNOTATIONS = {"description", "title", "default", "discriminator", "$schema", "$id", "$defs", "definitions", "examples"}
ASSERTIONS = {"$ref", "type", "enum", "const", "properties", "required", "additionalProperties", "items", "minItems",
              "maxItems", "uniqueItems", "minLength", "maxLength", "minimum", "maximum", "exclusiveMinimum",
              "exclusiveMaximum", "pattern", "format", "anyOf", "oneOf", "allOf"}


def check(value, schema, root=None, path=""):
    root = schema if root is None else root
    errors = []
    here = path or "$"
    if isinstance(schema, bool):
        return [] if schema else [(here, "Value is not permitted")]
    unknown = set(schema) - ANNOTATIONS - ASSERTIONS
    if unknown:
        return [(here, "Unsupported schema assertion: " + ", ".join(sorted(unknown)))]
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            return [(here, "External schema references are disabled")]
        target = root
        for segment in ref[2:].split("/"):
            target = target[segment.replace("~1", "/").replace("~0", "~")]
        errors += check(value, target, root, path)
    for op in ("anyOf", "oneOf", "allOf"):
        if op in schema:
            variants = [check(value, s, root, path) for s in schema[op]]
            passes = sum(not e for e in variants)
            valid = passes > 0 if op == "anyOf" else passes == 1 if op == "oneOf" else passes == len(variants)
            if not valid:
                errors += min(variants, key=len) or [(here, "Expected exactly one matching schema")]
    kinds = {"object": isinstance(value, dict), "array": isinstance(value, list), "string": isinstance(value, str),
             "boolean": isinstance(value, bool), "integer": isinstance(value, int) and not isinstance(value, bool),
             "number": isinstance(value, (int, float)) and not isinstance(value, bool), "null": value is None}
    if "type" in schema:
        expected = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(kinds.get(t, False) for t in expected):
            return errors + [(here, "Expected " + " or ".join(expected))]
    if "enum" in schema and not any(type(value) is type(x) and value == x for x in schema["enum"]):
        sample = schema["enum"]
        errors.append((here, "Value is outside the pinned target's allowed values" + (": " + ", ".join(map(str, sample)) if len(sample) < 10 else "")))
    if "const" in schema and value != schema["const"]:
        errors.append((here, "Expected " + str(schema["const"])))
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(((path + "." + key).lstrip("."), "Required field is missing"))
        props = schema.get("properties", {})
        for key, child in value.items():
            child_path = (path + "." + key).lstrip(".")
            if key in props:
                errors += check(child, props[key], root, child_path)
            elif schema.get("additionalProperties") is False:
                errors.append((child_path, "Field is not supported by this target"))
            elif isinstance(schema.get("additionalProperties"), dict):
                errors += check(child, schema["additionalProperties"], root, child_path)
    if isinstance(value, list):
        for op, bad in (("minItems", len(value) < schema.get("minItems", 0)), ("maxItems", len(value) > schema.get("maxItems", float("inf")))):
            if bad:
                errors.append((here, "Expected " + ("at least " if op == "minItems" else "at most ") + str(schema[op]) + " entries"))
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in value}) != len(value):
            errors.append((here, "Entries must be unique"))
        if "items" in schema:
            for index, item in enumerate(value):
                errors += check(item, schema["items"], root, here + "[" + str(index) + "]")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append((here, "Value is too short"))
        if len(value) > schema.get("maxLength", float("inf")):
            errors.append((here, "Value is too long for the target"))
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append((here, "Value does not match the target's format"))
        try:
            fmt = schema.get("format")
            if fmt == "uuid":
                uuid.UUID(value)
            elif fmt == "date":
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError()
            elif fmt == "uri":
                if not urlparse(value).scheme:
                    raise ValueError()
        except (ValueError, AttributeError):
            errors.append((here, "Invalid " + str(schema.get("format"))))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        for op, bad in (("minimum", value < schema.get("minimum", -float("inf"))), ("maximum", value > schema.get("maximum", float("inf"))),
                        ("exclusiveMinimum", value <= schema.get("exclusiveMinimum", -float("inf"))), ("exclusiveMaximum", value >= schema.get("exclusiveMaximum", float("inf")))):
            if bad:
                errors.append((here, op + " is " + str(schema[op])))
    return errors
