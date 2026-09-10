"""Small application API with injectable, read-only saved-search access."""
import copy
import json

from . import __version__
from .core import convert, identity, normalise_record, options_checked, boolean
from .profiles import catalogue

PAGE_SIZE = 200
BATCH_SIZE = 25


def validate_selection(item):
    if not isinstance(item, dict):
        raise ValueError("Selection must be an object")
    for part in ("app", "owner", "title"):
        value = item.get(part)
        if not isinstance(value, str) or not value or len(value) > 2048 or any(ord(c) < 32 for c in value):
            raise ValueError("Invalid selection " + part)
        if part in ("app", "owner") and (value in ("-", ".", "..") or "/" in value or "\\" in value):
            raise ValueError("Selection needs an exact " + part)
    if "overrides" in item and not isinstance(item["overrides"], dict):
        raise ValueError("Per-detection overrides must be an object")


class ConverterService:
    def __init__(self, repository):
        self.repository = repository

    def handle(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Request must be a JSON object")
        action = payload.get("action")
        if action == "profiles":
            return dict(catalogue(), version=__version__, batch_size=BATCH_SIZE)
        if action == "list":
            offset = payload.get("offset", 0)
            if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= 100000:
                raise ValueError("Invalid catalogue offset")
            response = self.repository.list(offset, PAGE_SIZE)
            entries = response.get("entry", [])
            total = int(response.get("paging", {}).get("total", len(entries)))
            rows = []
            for entry in entries:
                record = normalise_record(entry)
                source = identity(record)
                rows.append(dict(source, description=str(record.get("description", ""))[:1000],
                    detection=boolean(record.get("action.correlationsearch.enabled", False)) or boolean(record.get("action.risk", False)) or boolean(record.get("action.notable", False)),
                    disabled=boolean(record.get("disabled", False)), actions=str(record.get("actions", ""))))
            return {"entries": rows, "total": total, "offset": offset, "page_size": PAGE_SIZE}
        if action == "convert":
            selections = payload.get("selections")
            if not isinstance(selections, list) or len(selections) > BATCH_SIZE:
                raise ValueError("A conversion request supports at most 25 selections")
            options = payload.get("options", {})
            options_checked(options)
            # Preserve order and return one outcome even if a source has vanished or lost its ACL.
            results = []
            for item in selections:
                source = {}
                try:
                    validate_selection(item)
                    source = identity({"title": item["title"], "app": item["app"], "owner": item["owner"]})
                    entry = self.repository.get(item["app"], item["owner"], item["title"])
                    record = normalise_record(entry)
                    if identity(record)["key"] != source["key"]:
                        raise ValueError("Returned saved-search identity does not match the selection")
                    effective = copy.deepcopy(options)
                    effective["overrides"] = dict(options.get("overrides", {}), **item.get("overrides", {}))
                    converted = convert(record, effective)
                    results.append(converted)
                except Exception as error:
                    # Splunk exception bodies can contain details of requests; do not return them.
                    message = str(error) if isinstance(error, ValueError) else "Saved search could not be read. It may have been deleted or access may have changed."
                    results.append({"source": source, "filename": "", "profile": options.get("profile", "contentctl_5_6_0"), "status": "error", "yaml": "",
                        "issues": [{"severity": "error", "code": "source_unavailable", "field": "source", "message": message}]})
            return {"results": results, "requested": len(selections), "processed": len(results)}
        raise ValueError("Unknown API action")
