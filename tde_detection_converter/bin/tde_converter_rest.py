"""Authenticated Splunk REST adapter. All reads use the requesting user's token."""
import json
import os
import sys
from urllib.parse import quote, parse_qs

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(APP_ROOT, "lib"))

import splunk.rest
from splunk.persistconn.application import PersistentServerConnectionApplication
from tde_converter.service import ConverterService


class SplunkRepository:
    def __init__(self, session_key):
        self.session_key = session_key

    def _get(self, path, args=None):
        parameters = dict(args or {}, output_mode="json")
        response, body = splunk.rest.simpleRequest(path, sessionKey=self.session_key, getargs=parameters,
                                                   method="GET", raiseAllErrors=True)
        if int(response.status) >= 400:
            raise RuntimeError("Saved search read failed")
        return json.loads(body)

    def list(self, offset, count):
        return self._get("/servicesNS/-/-/saved/searches", {"count": count, "offset": offset, "sort_key": "name", "sort_dir": "asc"})

    def get(self, app, owner, title):
        path = "/servicesNS/" + quote(owner, safe="") + "/" + quote(app, safe="") + "/saved/searches/" + quote(title, safe="")
        response = self._get(path)
        if len(response.get("entry", [])) != 1:
            raise RuntimeError("Saved search not found uniquely")
        return response["entry"][0]


class DetectionConverterHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line=None, command_arg=None):
        pass

    def handle(self, request):
        try:
            if isinstance(request, (str, bytes)):
                request = json.loads(request)
            if request.get("method", "").upper() != "POST":
                return {"status": 405, "payload": json.dumps({"error": "Use POST"})}
            # Never use system_authtoken or a service/admin account as a fallback.
            session = request.get("session", {}).get("authtoken")
            if not session:
                return {"status": 401, "payload": json.dumps({"error": "Sign in to Splunk"})}
            form = dict(request.get("form", []))
            raw = form.get("payload", request.get("payload", ""))
            if not isinstance(raw, str) or len(raw.encode("utf-8")) > 512 * 1024:
                raise ValueError("Request is missing or exceeds 512 KiB")
            if raw.startswith("payload="):
                # Some Splunk builds provide the raw form body with passPayload.
                values = parse_qs(raw, keep_blank_values=True)
                if len(values.get("payload", [])) != 1:
                    raise ValueError("Expected one payload form field")
                raw = values["payload"][0]
            payload = json.loads(raw)
            data = ConverterService(SplunkRepository(session)).handle(payload)
            return {"status": 200, "payload": json.dumps(data, ensure_ascii=True, allow_nan=False)}
        except (ValueError, TypeError, KeyError) as error:
            return {"status": 400, "payload": json.dumps({"error": str(error)})}
        except Exception:
            return {"status": 500, "payload": json.dumps({"error": "Converter request failed. Check app installation and saved-search access."})}
