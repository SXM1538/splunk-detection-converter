#!/usr/bin/env python3
"""Streaming command: | rest ... | convertdetection profile=contentctl_5_6_0"""
import base64
import copy
import json
import os
import sys

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(APP_ROOT, "lib"))

from splunklib.searchcommands import Configuration, StreamingCommand, Option, dispatch
from tde_converter.core import convert, identity, boolean, options_checked
from tde_converter.service import validate_selection


@Configuration(distributed=False)
class ConvertDetectionCommand(StreamingCommand):
    profile = Option(default="contentctl_5_6_0")
    base_profile = Option(default="contentctl_5_6_0")
    fields = Option(default=None)
    omit_empty = Option(default="true")
    author = Option(default=None)
    options_b64 = Option(default=None)
    mode = Option(default="convert")
    request_b64 = Option(default=None)

    def selected_request(self):
        if not self.request_b64 or len(self.request_b64) > 512 * 1024:
            raise ValueError("Selection request is missing or exceeds 512 KiB")
        request = json.loads(base64.b64decode(self.request_b64, validate=True).decode("utf-8"))
        if not isinstance(request, dict):
            raise ValueError("Selection request must be an object")
        selections = request.get("selections")
        if not isinstance(selections, list) or not 1 <= len(selections) <= 25:
            raise ValueError("Select between 1 and 25 detections per batch")
        options = request.get("options", {})
        options_checked(options)
        selected = {}
        for item in selections:
            validate_selection(item)
            source = identity(item)
            if item.get("key") != source["key"] or source["key"] in selected:
                raise ValueError("Invalid or duplicate selected identity")
            selected[source["key"]] = item
        return selected, options

    def stream(self, records):
        if self.mode not in ("convert", "catalogue", "selected"):
            raise ValueError("Unknown converter mode")
        if self.mode == "selected":
            selected, selected_options = self.selected_request()
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
            if self.mode != "convert":
                self._catalogue_count = getattr(self, "_catalogue_count", 0) + 1
                if self._catalogue_count > 100000:
                    raise ValueError("Saved-search catalogue exceeds 100,000 records")
                source = identity(record)
                if self.mode == "catalogue":
                    row = dict(source, description=str(record.get("description", ""))[:1000],
                        detection=any(boolean(record.get(key, False)) for key in
                            ("action.correlationsearch.enabled", "action.risk", "action.notable")),
                        disabled=boolean(record.get("disabled", False)), actions=str(record.get("actions", "")))
                    yield {"result_json": json.dumps(row, ensure_ascii=True)}
                    continue
                item = selected.get(source["key"])
                if item is None:
                    continue
                options = copy.deepcopy(selected_options)
                options["overrides"] = dict(options.get("overrides", {}), **item.get("overrides", {}))
            result = convert(record, options)
            yield {"source_key": result.get("source", {}).get("key", ""), "title": result.get("source", {}).get("title", ""),
                   "app": result.get("source", {}).get("app", ""), "owner": result.get("source", {}).get("owner", ""),
                   "filename": result["filename"], "yaml": result["yaml"], "status": result["status"], "profile": result["profile"],
                   "issues": json.dumps(result["issues"]), "result_json": json.dumps(result, ensure_ascii=True)}


if __name__ == "__main__":
    dispatch(ConvertDetectionCommand, sys.argv, sys.stdin, sys.stdout, __name__)
