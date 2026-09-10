#!/usr/bin/env python3
"""Streaming command: | rest ... | convertdetection profile=contentctl_5_6_0"""
import base64
import json
import os
import sys

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(APP_ROOT, "lib"))

from splunklib.searchcommands import Configuration, StreamingCommand, Option, dispatch
from tde_converter.core import convert


@Configuration(distributed=False)
class ConvertDetectionCommand(StreamingCommand):
    profile = Option(default="contentctl_5_6_0")
    base_profile = Option(default="contentctl_5_6_0")
    fields = Option(default=None)
    omit_empty = Option(default="true")
    author = Option(default=None)
    options_b64 = Option(default=None)

    def stream(self, records):
        try:
            if self.options_b64:
                if len(self.options_b64) > 512 * 1024:
                    raise ValueError("Options exceed 512 KiB")
                options = json.loads(base64.b64decode(self.options_b64, validate=True).decode("utf-8"))
            else:
                options = {"profile": self.profile, "base_profile": self.base_profile, "omit_empty": self.omit_empty}
                if self.fields is not None:
                    options["fields"] = [x.strip() for x in self.fields.split(",") if x.strip()]
                if self.author is not None:
                    options["defaults"] = {"author": self.author}
        except Exception:
            options = {"profile": "INVALID_OPTIONS"}
        for record in records:
            result = convert(record, options)
            yield {"source_key": result.get("source", {}).get("key", ""), "title": result.get("source", {}).get("title", ""),
                   "app": result.get("source", {}).get("app", ""), "owner": result.get("source", {}).get("owner", ""),
                   "filename": result["filename"], "yaml": result["yaml"], "status": result["status"], "profile": result["profile"],
                   "issues": json.dumps(result["issues"]), "result_json": json.dumps(result, ensure_ascii=True)}


if __name__ == "__main__":
    dispatch(ConvertDetectionCommand, sys.argv, sys.stdin, sys.stdout, __name__)
