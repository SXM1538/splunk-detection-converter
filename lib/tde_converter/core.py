"""Extract, map, validate and serialise exactly one saved search per call."""
import copy
import hashlib
import json
import math
import re
import uuid
from datetime import date

import yaml

from . import __version__
from .profiles import (PROFILES, PRODUCTS, COMMON_FIELDS, CLASSIC_FIELDS, NG_FIELDS,
                       EXTRA_FIELDS, CLASSIC_REQUIRED, NG_SCHEMA, NG_CHECK_SCHEMA, SCHEMA_DIR, family)
from .schema_check import check

MISSING = object()
NAMESPACE = uuid.UUID("4d457b65-12de-4d65-a779-a30b9a2cbe0f")
MAX_TEXT = 2 * 1024 * 1024


def text(value):
    return "" if value is None else str(value)


def boolean(value):
    if value in (True, False) and isinstance(value, bool):
        return value
    raw = text(value).strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off", ""):
        return False
    raise ValueError("Invalid boolean value: " + raw[:80])


def array(value):
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return copy.deepcopy(value)
    if isinstance(value, str):
        if value.lstrip().startswith("["):
            return parsed(value, list, "list field")
        return [x.strip() for x in value.split(",") if x.strip()]
    raise ValueError("Expected a list or comma-separated string")


def parsed(value, expected, field):
    if value is None or value == "":
        return expected()
    try:
        obj = json.loads(value) if isinstance(value, str) else copy.deepcopy(value)
    except (ValueError, TypeError):
        raise ValueError(field + ": malformed JSON")
    if not isinstance(obj, expected):
        raise ValueError(field + ": expected " + expected.__name__)
    return obj


def get_path(obj, path, default=MISSING):
    for part in path.split("."):
        if not isinstance(obj, dict) or part not in obj:
            return default
        obj = obj[part]
    return obj


def set_path(obj, path, value):
    parts = path.split(".")
    if not path or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", p) or p in ("__proto__", "constructor", "prototype") for p in parts):
        raise ValueError("Invalid output field path: " + path)
    current = obj
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        if not isinstance(current[part], dict):
            raise ValueError("Conflicting output field path: " + path)
        current = current[part]
    current[parts[-1]] = copy.deepcopy(value)


def apply_overrides(document, overrides):
    if not isinstance(overrides, dict):
        raise ValueError("Overrides must be a JSON object of output field paths and values")
    for path, value in overrides.items():
        set_path(document, path, value)


def normalise_record(record):
    if not isinstance(record, dict):
        raise ValueError("Saved search must be an object")
    content = record.get("content")
    if isinstance(content, dict):
        result = copy.deepcopy(content)
        result["title"] = record.get("name", record.get("title", result.get("title", "")))
        acl = record.get("acl", content.get("eai:acl", {}))
        result["eai:acl.app"] = acl.get("app", "")
        result["eai:acl.owner"] = acl.get("owner", "")
        for key in ("updated", "published"):
            if key in record:
                result[key] = record[key]
        return result
    return copy.deepcopy(record)


def identity(record):
    acl = record.get("eai:acl", {})
    if not isinstance(acl, dict):
        acl = {}
    source = {"app": text(record.get("eai:acl.app", acl.get("app", record.get("app", "")))),
              "owner": text(record.get("eai:acl.owner", acl.get("owner", record.get("owner", "")))),
              "title": text(record.get("title", record.get("name", "")))}
    key = json.dumps([source["app"], source["owner"], source["title"]], ensure_ascii=True, separators=(",", ":"))
    source["key"] = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return source


def filename(source):
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", source["title"]).strip("_-")[:72] or "detection"
    return slug + "__" + source["key"][:20] + ".yml"


def note(issues, code, field, message, severity="warning"):
    issues.append({"code": code, "field": field, "message": message, "severity": severity})


def unwrap_next_steps(value):
    if not isinstance(value, str):
        return value.get("data", value) if isinstance(value, dict) else value
    try:
        obj = json.loads(value)
        return obj["data"] if isinstance(obj, dict) and isinstance(obj.get("data"), str) else value
    except ValueError:
        return value


def entity(item, kind="risk"):
    if not isinstance(item, dict):
        raise ValueError("Each " + kind + " object must be an object")
    field = item.get("field", item.get("risk_object_field", ""))
    obj_type = item.get("type", item.get("risk_object_type", ""))
    score = item.get("score", item.get("risk_score"))
    # Never round, clamp, reinterpret a type, or manufacture a risk score.
    if isinstance(score, str) and re.fullmatch(r"[0-9]+", score):
        score = int(score)
    if isinstance(score, bool) or not isinstance(score, int):
        raise ValueError(kind + " object " + text(field) + ": score must be an integer")
    return {"field": field, "type": obj_type, "score": score}


def extract(record, defaults, issues, today):
    source = identity(record)
    if not source["title"].strip():
        raise ValueError("Saved search has no title")
    search = record.get("search")
    if not isinstance(search, str) or not search.strip():
        raise ValueError("Saved search has empty or non-text SPL")
    if len(search.encode("utf-8")) > MAX_TEXT:
        raise ValueError("Saved search SPL exceeds the 2 MiB per-detection limit")
    if not source["app"] or not source["owner"]:
        note(issues, "identity_incomplete", "source_identity", "App or owner is missing. Supply both to guarantee cross-app identity.", "error")
    annotations = parsed(record.get("action.correlationsearch.annotations"), dict, "annotations")
    metadata = parsed(record.get("action.correlationsearch.metadata"), dict, "correlation metadata")
    def fallback(key, candidates=(), default=""):
        for candidate in candidates:
            if candidate is not None and candidate != "" and candidate != []:
                return copy.deepcopy(candidate)
        return copy.deepcopy(defaults.get(key, default))
    def metadata_value(key, default=""):
        return fallback(key, (record.get("action.escu." + key), metadata.get(key), annotations.get(key)), default)
    identifier = next((x for x in (record.get("detection_id"), record.get("action.escu.id"), metadata.get("id"), annotations.get("id"), record.get("action.correlationsearch.id")) if x), None)
    if identifier:
        try:
            identifier = str(uuid.UUID(text(identifier)))
        except ValueError:
            note(issues, "invalid_source_id", "id", "Existing source ID is not a UUID; it is preserved for review.", "error")
    else:
        identifier = str(uuid.uuid5(NAMESPACE, source["key"]))
    notable = boolean(record.get("action.notable", False))
    risk = boolean(record.get("action.risk", False))
    raw_risk = parsed(record.get("action.risk.param._risk"), list, "risk objects") if risk else []
    risks, threats = [], []
    risk_message = text(record.get("action.risk.param._risk_message", ""))
    for item in raw_risk:
        if not isinstance(item, dict):
            raise ValueError("Risk object array contains a non-object")
        if "threat_object_field" in item:
            threats.append({"field": item.get("threat_object_field"), "type": item.get("threat_object_type", "")})
            continue
        field = text(item.get("risk_object_field", item.get("field"))).strip()
        if field.lower() in ("", "n/a", "na", "none", "null"):
            note(issues, "placeholder_risk_object", "rba", "A blank or placeholder risk object was excluded; inspect the source risk configuration.", "error")
            continue
        obj = entity(item)
        obj["message"] = item.get("risk_message", item.get("message", risk_message))
        risks.append(obj)
    if risk and not risks and not threats:
        note(issues, "empty_risk_action", "rba", "The risk action is enabled but has no usable entities.", "error")
    finding_entities = parsed(record.get("action.notable.param._entities"), list, "finding entities") if notable else []
    finding_entities = [entity(x, "finding") for x in finding_entities]
    det_type = "TTP" if notable and risk else "Correlation" if notable else "Anomaly" if risk else "Hunting"
    raw_version = metadata_value("version", 1)
    try:
        version = int(raw_version)
        if isinstance(raw_version, bool) or str(version) != str(raw_version):
            raise ValueError()
    except (ValueError, TypeError):
        version = raw_version
    original_date = metadata_value("date")
    created = metadata_value("creation_date") or original_date or text(record.get("published"))[:10] or today
    modified = metadata_value("modification_date") or original_date or text(record.get("updated"))[:10] or today
    if created == today and not original_date and not metadata.get("creation_date") and not record.get("published"):
        note(issues, "date_fallback", "date", "No creation date was available; the conversion date was used.")
    mitre = fallback("mitre_attack_id", (annotations.get("mitre_attack"), annotations.get("mitre_attack_id")), [])
    schedule = {"cron_schedule": text(record.get("cron_schedule", "")), "earliest_time": text(record.get("dispatch.earliest_time", "")),
                "latest_time": text(record.get("dispatch.latest_time", "")), "schedule_window": text(record.get("schedule_window", ""))}
    desc = text(record.get("description", ""))
    model = {"name": source["title"], "id": identifier, "version": version, "date": modified,
             "creation_date": created, "modification_date": modified, "author": metadata_value("author"),
             "status": metadata_value("status", "experimental"), "type": fallback("type", (), det_type),
             "description": desc, "search": search, "enabled_by_default": not boolean(record.get("disabled", True)),
             "how_to_implement": metadata_value("how_to_implement"), "known_false_positives": metadata_value("known_false_positives"),
             "data_source": array(metadata_value("data_source", [])), "analytic_story": array(metadata_value("analytic_story", [])),
             "asset_type": metadata_value("asset_type"), "security_domain": fallback("security_domain", (record.get("action.notable.param.security_domain"), annotations.get("security_domain"))),
             "product": array(metadata_value("product", PRODUCTS)), "mitre_attack_id": array(mitre),
             "category": metadata_value("category"), "references": array(metadata_value("references", [])),
             "tests": copy.deepcopy(defaults.get("tests", [])), "schedule": schedule, "risk_enabled": risk, "notable_enabled": notable,
             "risks": risks, "threats": threats, "risk_message": risk_message, "finding_entities": finding_entities,
             "rule_title": text(record.get("action.notable.param.rule_title")) or source["title"],
             "rule_description": text(record.get("action.notable.param.rule_description")) or desc,
             "rule_severity": text(record.get("action.notable.param.severity", "")),
             "nes_fields": array(record.get("action.notable.param.nes_fields", [])),
             "next_steps": unwrap_next_steps(record.get("action.notable.param.next_steps", "")),
             "drilldown_searches": parsed(record.get("action.notable.param.drilldown_searches"), list, "drilldown searches") if notable else [],
             "drilldown_dashboards": parsed(record.get("action.notable.param.drilldown_dashboards"), list, "drilldown dashboards") if notable else [],
             "throttling": None, "source_identity": source,
             "cve": array(metadata_value("cve", [])), "threat_group": array(metadata_value("threat_group", []))}
    if boolean(record.get("alert.suppress", False)):
        model["throttling"] = {"period": text(record.get("alert.suppress.period", "")), "fields": array(record.get("alert.suppress.fields", ""))}
    extra_map = {"index_earliest": "dispatch.index_earliest", "index_latest": "dispatch.index_latest", "allow_skew": "allow_skew",
                 "realtime_schedule": "realtime_schedule", "enableSched": "is_scheduled" if "is_scheduled" in record else "enableSched",
                 "disabled": "disabled", "email": "action.email", "to": "action.email.to", "subject": "action.email.subject.alert",
                 "message": "action.email.message.alert", "sendresults": "action.email.sendresults", "sendcsv": "action.email.sendcsv"}
    bool_keys = {"realtime_schedule", "enableSched", "disabled", "email", "sendresults", "sendcsv"}
    for key, field in extra_map.items():
        if field in record:
            model[key] = boolean(record[field]) if key in bool_keys else copy.deepcopy(record[field])
    model.update(schedule)
    return model


def map_profile(model, base):
    out = {key: copy.deepcopy(model[key]) for key in COMMON_FIELDS}
    if family(base) == "classic":
        out.update(date=model["date"], enabled_by_default=model["enabled_by_default"])
        out["tags"] = {k: copy.deepcopy(model[k]) for k in ("analytic_story", "asset_type", "product", "security_domain", "mitre_attack_id", "cve")}
        if model["throttling"] is not None:
            out["tags"]["throttling"] = model["throttling"]
        if model["threat_group"]:
            out["tags"]["group"] = model["threat_group"]
        out["deployment"] = {"scheduling": model["schedule"], "alert_action": {"rba": {"enabled": model["risk_enabled"]}}}
        if model["notable_enabled"]:
            out["deployment"]["alert_action"]["notable"] = {"rule_title": model["rule_title"], "rule_description": model["rule_description"],
                "nes_fields": model["nes_fields"]}
        if model["risk_enabled"]:
            out["rba"] = {"message": model["risk_message"], "risk_objects": [{k: v for k, v in r.items() if k != "message"} for r in model["risks"]],
                          "threat_objects": model["threats"]}
    else:
        out.update({key: copy.deepcopy(model[key]) for key in ("creation_date", "modification_date", "analytic_story", "asset_type", "product",
            "security_domain", "mitre_attack_id", "category", "cve", "threat_group")})
        out["custom_schedule"] = model["schedule"]
        if model["notable_enabled"]:
            out["finding"] = {"title": model["rule_title"]}
            if len(model["finding_entities"]) == 1:
                out["finding"]["entity"] = model["finding_entities"][0]
        if model["risk_enabled"]:
            out["intermediate_findings"] = {"entities": copy.deepcopy(model["risks"])}
        out["threat_objects"] = model["threats"]
    return out


def prune_empty(value, required, path=""):
    if not isinstance(value, dict):
        return value
    out = {}
    for key, child in value.items():
        child_path = (path + "." + key).lstrip(".")
        child = prune_empty(child, required, child_path)
        protected = any(p == child_path or p.startswith(child_path + ".") for p in required)
        if protected or child not in (None, "", [], {}):
            out[key] = child
    return out


def dependencies(search):
    clean = re.sub(r"```.*?```", " ", search, flags=re.S)
    macros = sorted(set(re.findall(r"`([^`\s(]+)(?:\([^`]*\))?`", clean)))
    clean = re.sub(r"`[^`]*`", " ", clean)
    # Match command positions, excluding quoted eval strings and fenced comments.
    tokens = re.finditer(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|(?:^|[|\[])\s*(?:inputlookup|lookup)\s+(?:(?:[\w.]+)=(?:"[^"\n]*"|[^\s|]+)\s+)*("[^"\n]+"|[\w.-]+)', clean, flags=re.I | re.M)
    lookups = sorted(set(m.group(1).strip('"') for m in tokens if m.group(1)))
    return {"macros": macros, "lookups": lookups}


def source_audit(record):
    # Restrict the audit to conversion-relevant settings; never collect session keys.
    keys = ("cron_schedule", "schedule_window", "allow_skew", "realtime_schedule", "is_scheduled", "enableSched", "disabled", "actions")
    prefixes = ("dispatch.", "alert.", "action.notable.", "action.risk.", "action.email.")
    return {k: copy.deepcopy(v) for k, v in record.items() if k in keys or k in ("action.risk", "action.notable", "action.email") or k.startswith(prefixes)}


def fidelity(model, record, document, base, issues):
    """Identify settings that the chosen target cannot faithfully express."""
    fam = family(base)
    unsupported = []
    for key in ("index_earliest", "index_latest", "next_steps", "drilldown_dashboards"):
        if model.get(key) not in (None, "", [], {}):
            unsupported.append(key)
    if model.get("allow_skew") not in (None, "", "0", "0%", 0):
        unsupported.append("allow_skew")
    if model.get("email"):
        unsupported.append("email")
    if model.get("realtime_schedule") is False:
        unsupported.append("realtime_schedule=false")
    if model.get("enableSched") is False:
        unsupported.append("enableSched=false")
    if fam == "ng" and model.get("throttling"):
        unsupported.append("throttling")
    if fam == "ng" and "disabled" in model:
        unsupported.append("disabled/enabled state")
    if fam == "ng" and model["notable_enabled"]:
        if len(model["finding_entities"]) != 1 and get_path(document, "finding.entity", None) is None:
            note(issues, "finding_entity_required", "finding.entity", "The ng target needs exactly one finding entity. Supply it explicitly in overrides; risk entities are not substituted.", "error")
        if model["rule_description"]:
            unsupported.append("rule_description")
    if fam == "classic" and model["finding_entities"]:
        unsupported.append("finding entities")
    if fam == "classic" and any(r["message"] != model["risk_message"] for r in model["risks"]):
        unsupported.append("per-entity risk messages")
    if model["notable_enabled"] and model["rule_severity"]:
        # Classic computes severity from maximum risk; NG's schema has no severity field.
        risks = model["risks"]
        computed = "high"
        if risks:
            score = max(r["score"] for r in risks)
            computed = "informational" if score <= 20 else "low" if score <= 40 else "medium" if score <= 60 else "high" if score <= 80 else "critical"
        if fam == "ng" or model["rule_severity"].lower() != computed:
            unsupported.append("rule_severity")
    for action in array(record.get("actions")):
        if action not in ("risk", "notable", "email") and boolean(record.get("action." + action, True)):
            unsupported.append("action." + action)
    if unsupported:
        note(issues, "unmapped_settings", "source_settings", "Target cannot preserve: " + ", ".join(unsupported) + ". Original values are recorded in the manifest; use Custom YAML for these fields.", "error")


def validate(document, base, issues):
    fam = family(base)
    if fam == "ng":
        schema = NG_CHECK_SCHEMA
    else:
        schema = json.loads((SCHEMA_DIR / "classic.json").read_text(encoding="utf-8"))
    for field, message in check(document, schema):
        note(issues, "schema", field, message, "error")
    for field in ("name", "author", "description", "search", "how_to_implement", "known_false_positives"):
        value = get_path(document, field, "")
        if not isinstance(value, str) or not value.strip():
            note(issues, "missing_input", field, "Supply " + field.replace("_", " "), "error")
    status, det_type = document.get("status"), document.get("type")
    schedule_path = "deployment.scheduling" if fam == "classic" else "custom_schedule"
    schedule = get_path(document, schedule_path, {})
    if isinstance(schedule, dict):
        cron = schedule.get("cron_schedule", "")
        if isinstance(cron, str) and len(cron.split()) != 5:
            note(issues, "schedule_incomplete", schedule_path + ".cron_schedule", "Expected a five-field cron schedule. Full cron semantics require the target CLI.", "error")
        for field in ("earliest_time", "latest_time", "schedule_window"):
            if not text(schedule.get(field)).strip():
                note(issues, "schedule_incomplete", schedule_path + "." + field, "Supply the source schedule value or an explicit override.", "error")
    story_path = "tags.analytic_story" if fam == "classic" else "analytic_story"
    if get_path(document, story_path, []):
        note(issues, "repository_reference", story_path, "Referenced stories must exist in your target repository; existence was not checked.")
    if fam == "classic":
        if status == "production" and det_type != "Correlation" and not document.get("tests") and not get_path(document, "tags.manual_test", None):
            note(issues, "tests_required", "tests", "Production detections require test data or an explicit manual-test explanation.", "error")
        rba = document.get("rba")
        enabled = get_path(document, "deployment.alert_action.rba.enabled", False)
        if bool(rba) != bool(enabled):
            note(issues, "rba_action_mismatch", "deployment.alert_action.rba", "RBA content and deployment action enablement disagree.", "error")
        if isinstance(rba, dict) and status == "production":
            search = text(document.get("search")).lower()
            fields = [x.get("field", "") for x in rba.get("risk_objects", []) + rba.get("threat_objects", []) if isinstance(x, dict)]
            fields += re.findall(r"\$([^\s.$]+)\$", text(rba.get("message")))
            for field in set(fields):
                if field and field.lower() not in search:
                    note(issues, "rba_field", "rba", "Classic validation expects field '" + field + "' in the search.", "error")
    else:
        if not document.get("tests"):
            note(issues, "tests_required", "tests", "The ng target requires a unit or experimental test entry.", "error")
        if bool(document.get("schedule")) == bool(document.get("custom_schedule")):
            note(issues, "schedule_choice", "custom_schedule", "Supply exactly one schedule or custom_schedule.", "error")
        finding = bool(document.get("finding"))
        intermediate = bool(document.get("intermediate_findings"))
        if (det_type in ("TTP", "Correlation")) != finding or (det_type == "Anomaly" and not intermediate) or (det_type in ("Correlation", "Hunting") and intermediate) or (det_type == "Hunting" and document.get("threat_objects")):
            note(issues, "type_actions", "type", "Finding/risk actions do not match the selected detection type.", "error")
        token_strings = [("finding.title", get_path(document, "finding.title", None))]
        entities = get_path(document, "intermediate_findings.entities", [])
        if isinstance(entities, list):
            token_strings += [("intermediate_findings.entities[" + str(i) + "].message", x.get("message")) for i, x in enumerate(entities) if isinstance(x, dict)]
        for field, value in token_strings:
            if isinstance(value, str) and (value.count("$") % 2 or not re.search(r"\$[^$\s]+\$", value)):
                note(issues, "es_token", field, "The ng target requires balanced $field$ tokens and at least one token.", "error")
        spl = document.get("search")
        if isinstance(spl, str) and spl != spl.strip():
            note(issues, "spl_whitespace", "search", "The ng validator rejects leading/trailing SPL whitespace. Source SPL was preserved.", "error")


class LiteralDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def represent_string(dumper, value):
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|" if "\n" in value and "\r" not in value else None)


LiteralDumper.add_representer(str, represent_string)


def dump_yaml(document):
    # The JSON check excludes arbitrary Python objects and non-finite numbers.
    json.dumps(document, allow_nan=False)
    rendered = yaml.dump(document, Dumper=LiteralDumper, allow_unicode=True, sort_keys=False, width=110)
    if yaml.safe_load(rendered) != document:
        raise ValueError("YAML round-trip did not preserve the mapped document")
    return rendered


def options_checked(options):
    if not isinstance(options, dict):
        raise ValueError("Options must be an object")
    if set(options) - {"profile", "base_profile", "fields", "omit_empty", "defaults", "overrides", "custom_fields"}:
        raise ValueError("Unknown converter option")
    profile = options.get("profile", "contentctl_5_6_0")
    if profile not in PROFILES:
        raise ValueError("Unknown output profile")
    base = options.get("base_profile", "contentctl_5_6_0") if profile == "custom" else profile
    family(base)
    for name in ("defaults", "overrides"):
        if not isinstance(options.get(name, {}), dict):
            raise ValueError(name + " must be an object")
    fields = options.get("fields")
    if fields is not None and (not isinstance(fields, list) or any(not isinstance(f, str) for f in fields)):
        raise ValueError("fields must be a list of field paths")
    rules = options.get("custom_fields", [])
    if not isinstance(rules, list) or len(rules) > 100:
        raise ValueError("custom_fields must be a list of at most 100 rules")
    if rules and profile != "custom":
        raise ValueError("Extra field mappings require the Custom YAML profile")
    return profile, base


def convert(record, options=None, today=None):
    """Never let one row, including validation/serialisation, abort a batch."""
    result = {"source": {}, "filename": "", "profile": text((options or {}).get("profile", "contentctl_5_6_0")) if isinstance(options or {}, dict) else "",
              "status": "error", "yaml": "", "issues": [], "dependencies": {"macros": [], "lookups": []}, "source_settings": {},
              "validation": {"yaml_round_trip": False, "profile_checks": False, "repository_build": "not_run"}, "converter_version": __version__}
    try:
        options = copy.deepcopy(options or {})
        profile, base = options_checked(options)
        result.update(profile=profile, target=PROFILES[base]["target"] if profile != "custom" else PROFILES["custom"]["target"], base_profile=base)
        record = normalise_record(record)
        result["source"] = identity(record)
        result["filename"] = filename(result["source"])
        result["source_settings"] = source_audit(record)
        issues = result["issues"]
        model = extract(record, options.get("defaults", {}), issues, today or date.today().isoformat())
        document = map_profile(model, base)
        custom = profile == "custom"
        required = set() if custom else set(CLASSIC_REQUIRED if family(base) == "classic" else NG_SCHEMA["required"] + ["custom_schedule", "tests"])
        fields = options.get("fields")
        available = set(CLASSIC_FIELDS if family(base) == "classic" else NG_FIELDS)
        if custom:
            available.update(EXTRA_FIELDS)
            document.update({k: copy.deepcopy(model[k]) for k in EXTRA_FIELDS if k in model})
        if fields is not None:
            unknown = set(fields) - available
            if unknown:
                raise ValueError("Unknown selected fields: " + ", ".join(sorted(unknown)))
            selected = set(fields) | required
            # Action-bearing fields are conditional requirements in fixed profiles.
            if not custom:
                selected |= {"rba"} if family(base) == "classic" and model["risk_enabled"] else set()
                if family(base) == "ng":
                    selected |= {"finding", "intermediate_findings", "threat_objects"}
                if model["throttling"] and family(base) == "classic":
                    selected.add("tags.throttling")
            filtered = {}
            for field in (CLASSIC_FIELDS if family(base) == "classic" else NG_FIELDS) + EXTRA_FIELDS:
                if field in selected:
                    value = get_path(document, field)
                    if value is not MISSING:
                        set_path(filtered, field, value)
            omitted = [f for f in available - selected if get_path(document, f, None) not in (None, "", [], {})]
            if omitted:
                note(issues, "fields_omitted", "fields", "Excluded by field selection: " + ", ".join(sorted(omitted)))
            document = filtered
        for rule in options.get("custom_fields", []):
            if not isinstance(rule, dict) or not isinstance(rule.get("path"), str) or (("source" in rule) == ("value" in rule)):
                raise ValueError("Each custom rule needs path and exactly one of source or value")
            if set(rule) - {"path", "source", "value", "transform"}:
                raise ValueError("Unknown custom mapping property")
            if "source" in rule:
                if rule["source"] not in record:
                    note(issues, "mapping_source_missing", rule["path"], "Source field is missing: " + text(rule["source"]), "error")
                    continue
                value = copy.deepcopy(record[rule["source"]])
            else:
                value = copy.deepcopy(rule["value"])
            transform = rule.get("transform", "identity")
            if transform == "boolean": value = boolean(value)
            elif transform == "list": value = array(value)
            elif transform == "json": value = json.loads(value) if isinstance(value, str) else value
            elif transform == "integer":
                if not re.fullmatch(r"-?\d+", text(value)): raise ValueError("Integer mapping would lose information")
                value = int(value)
            elif transform == "next_steps": value = unwrap_next_steps(value)
            elif transform != "identity": raise ValueError("Unknown mapping transform")
            set_path(document, rule["path"], value)
        apply_overrides(document, options.get("overrides", {}))
        if boolean(options.get("omit_empty", True)):
            # Protect schema-required children and valid empty collections inside action groups.
            nested = {"rba.message", "rba.risk_objects", "rba.threat_objects", "intermediate_findings.entities", "finding.entity",
                      "deployment.scheduling.cron_schedule", "deployment.scheduling.earliest_time", "deployment.scheduling.latest_time",
                      "deployment.scheduling.schedule_window", "deployment.alert_action.notable.nes_fields",
                      "deployment.alert_action.notable.rule_title", "deployment.alert_action.notable.rule_description",
                      "custom_schedule.cron_schedule", "custom_schedule.earliest_time",
                      "custom_schedule.latest_time", "custom_schedule.schedule_window"} if not custom else set()
            document = prune_empty(document, required | nested)
        if not custom:
            validate(document, base, issues)
            fidelity(model, record, document, base, issues)
        else:
            note(issues, "custom_profile", "profile", "Custom field selection: only YAML integrity and source extraction are checked.")
        result["dependencies"] = dependencies(text(document.get("search", model["search"])))
        for kind, values in result["dependencies"].items():
            if values:
                note(issues, "repository_dependency", "search", "Check repository " + kind + ": " + ", ".join(values))
        note(issues, "repository_not_checked", "profile", "A contentctl repository build, referenced content and live Splunk behaviour have not been validated by this conversion.")
        body = dump_yaml(document)
        result["validation"]["yaml_round_trip"] = True
        errors = [x for x in issues if x["severity"] == "error"]
        result["status"] = "needs_review" if errors else "ready"
        result["validation"]["profile_checks"] = not errors if not custom else "not_applicable"
        header = "# TDE Detection Converter " + __version__ + " | " + profile + " | " + result["status"] + "\n"
        header += "# Repository build: not run. See the export manifest for checks and source settings.\n"
        for item in errors:
            header += "# REVIEW " + item["field"].replace("\n", " ") + ": " + item["message"].replace("\n", " ").replace("\r", " ") + "\n"
        result["yaml"] = header + body
        result["document"] = document
    except Exception as error:
        # No source SPL or request payload in exceptions/logs. Structured row stays in the manifest.
        result["status"] = "error"
        result["yaml"] = ""
        note(result["issues"], "conversion_error", "", type(error).__name__ + ": " + str(error), "error")
    return result
