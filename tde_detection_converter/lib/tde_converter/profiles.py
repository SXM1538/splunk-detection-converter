"""Explicit, bundled targets. Upstream changes never change an installed profile."""
import copy
import json
from pathlib import Path

NG_COMMIT = "a02c60b2c7f132dda85c7e65b898317d1e9b97a9"
SCHEMA_DIR = Path(__file__).parent / "schemas"
NG_SCHEMA = json.loads((SCHEMA_DIR / "ng-a02c60b2.json").read_text(encoding="utf-8"))
NG_CHECK_SCHEMA = copy.deepcopy(NG_SCHEMA)
# These enums are generated from the upstream repository contents, not universal
# allowed names. A customer's own repository supplies its own objects.
for _name in ("StoryEnum", "BaselineEnum", "ScheduleEnum", "AllContentEnum"):
    NG_CHECK_SCHEMA["$defs"][_name] = {"type": "string", "minLength": 1}
NG_CHECK_SCHEMA["$defs"]["AtomicGuidEnum"] = {"type": "string", "format": "uuid"}
PRODUCTS = ["Splunk Enterprise", "Splunk Enterprise Security", "Splunk Cloud"]
PROFILES = {
    "contentctl_5_5_1": {"label": "Classic contentctl 5.5.1", "family": "classic", "target": "splunk/contentctl v5.5.1"},
    "contentctl_5_6_0": {"label": "Classic contentctl 5.6.0", "family": "classic", "target": "splunk/contentctl v5.6.0"},
    "contentctl_ng": {"label": "ESCU / contentctl-ng (experimental)", "family": "ng", "target": "security_content@" + NG_COMMIT,
                      "note": "Pinned ESCU schema snapshot. Splunk does not position contentctl-ng as a supported customer replacement."},
    "custom": {"label": "Custom YAML", "family": "custom", "target": "User-selected fields; no contentctl compatibility claim"},
}

COMMON_FIELDS = ["name", "id", "version", "author", "status", "type", "description", "search", "data_source",
                 "how_to_implement", "known_false_positives", "references", "tests", "drilldown_searches"]
CLASSIC_FIELDS = COMMON_FIELDS + ["date", "enabled_by_default", "rba", "deployment.scheduling", "deployment.alert_action",
    "tags.analytic_story", "tags.asset_type", "tags.product", "tags.security_domain", "tags.mitre_attack_id",
    "tags.throttling", "tags.manual_test", "tags.cve", "tags.group"]
NG_FIELDS = COMMON_FIELDS + ["creation_date", "modification_date", "analytic_story", "asset_type", "product", "security_domain",
    "mitre_attack_id", "category", "finding", "intermediate_findings", "threat_objects", "custom_schedule", "cve", "threat_group"]
EXTRA_FIELDS = ["cron_schedule", "earliest_time", "latest_time", "schedule_window", "index_earliest", "index_latest",
    "allow_skew", "realtime_schedule", "enableSched", "disabled", "next_steps", "rule_title", "rule_description",
    "rule_severity", "drilldown_dashboards", "email", "to", "subject", "message", "sendresults", "sendcsv", "source_identity"]
CLASSIC_REQUIRED = ["name", "id", "version", "date", "author", "status", "type", "description", "search",
    "enabled_by_default",
    "how_to_implement", "known_false_positives", "tags.analytic_story", "tags.asset_type", "tags.product", "tags.security_domain",
    "deployment.scheduling", "deployment.alert_action"]


def family(profile):
    if profile not in PROFILES or profile == "custom":
        raise ValueError("Choose a recognised base profile")
    return PROFILES[profile]["family"]


def catalogue():
    result = copy.deepcopy(PROFILES)
    for name, item in result.items():
        if item["family"] == "classic":
            item.update(fields=CLASSIC_FIELDS, required=CLASSIC_REQUIRED)
        elif item["family"] == "ng":
            item.update(fields=NG_FIELDS, required=NG_SCHEMA["required"] + ["custom_schedule", "tests"])
    classic_schema = json.loads((SCHEMA_DIR / "classic.json").read_text(encoding="utf-8"))
    assets = sorted(set(NG_SCHEMA["$defs"]["AssetType"]["enum"]) | set(classic_schema["properties"]["tags"]["properties"]["asset_type"]["enum"]))
    return {"profiles": result, "extra_fields": EXTRA_FIELDS, "products": PRODUCTS,
            "asset_types": assets,
            "security_domains": NG_SCHEMA["$defs"]["SecurityDomain"]["enum"],
            "categories": NG_SCHEMA["$defs"]["DetectionCategory"]["enum"]}
