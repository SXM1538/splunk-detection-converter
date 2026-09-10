# Profile provenance and dependency inventory

Profiles are fixed at app version 1.0.0. The app performs no runtime schema downloads.

## Classic profiles

The classic structural contract was derived from the released detection, tags, RBA, deployment, scheduling, notable and test models. The mapped detection/RBA/tags contracts in 5.5.1 and 5.6.0 are equivalent for the fields this converter emits; the versions remain separate profile identifiers.

- [contentctl v5.5.1 detection model](https://github.com/splunk/contentctl/blob/v5.5.1/contentctl/objects/abstract_security_content_objects/detection_abstract.py)
- [contentctl v5.6.0 detection model](https://github.com/splunk/contentctl/blob/v5.6.0/contentctl/objects/abstract_security_content_objects/detection_abstract.py)
- [Classic RBA model and 1–100 score bounds](https://github.com/splunk/contentctl/blob/v5.6.0/contentctl/objects/rba.py)
- [Classic inline deployments](https://github.com/splunk/contentctl/blob/v5.6.0/contentctl/objects/deployment.py)
- [Classic notable fields](https://github.com/splunk/contentctl/blob/v5.6.0/contentctl/objects/deployment_notable.py)
- [Classic tags](https://github.com/splunk/contentctl/blob/v5.6.0/contentctl/objects/detection_tags.py)

`classic.json` is the converter's structural contract, not an official JSON Schema release. It includes a stricter non-empty metadata gate and requires explicit inline deployment and enabled state to preserve the source. It uses the released 67-character detection-name limit. It is deliberately limited to supported fields; arbitrary runtime/computed Pydantic attributes are not export options.

Local validation cannot evaluate the complete contentctl repository context. Repository object resolution, app configuration, enrichments, template behaviour, full SPL parsing, runtime tests, filename conventions, generated macros/drilldowns and CLI-specific validators remain target-repository work. Preserving the original name does not prevent a downstream contentctl build from adding its own name decoration.

## Experimental ng profile

The app bundles the original [EventBasedDetection schema at commit a02c60b2c7f132dda85c7e65b898317d1e9b97a9](https://github.com/splunk/security_content/blob/a02c60b2c7f132dda85c7e65b898317d1e9b97a9/schemas/EventBasedDetection.schema.json). The evaluator supports the exact assertion vocabulary used by this snapshot and rejects unknown assertion keywords and external references.

Story, baseline, schedule and replacement-content enums in the published snapshot contain objects from Splunk's repository. They are treated as non-empty references for local validation, so a customer's own story name is not incorrectly rejected. Atomic test references are UUID-checked. Existence of these objects is deferred to the target repository. The original bundled schema remains unchanged; `profiles.py` describes this explicit validation adaptation.

The ng profile additionally checks selected constraints described in the schema but not encoded as JSON Schema assertions, including detection/action combinations, test presence, balanced ES field tokens and leading/trailing SPL whitespace. It is not a replacement for the ng CLI or a claim of supported customer tooling. [Splunk maintainer guidance](https://github.com/splunk/security_content/issues/4068#issuecomment-4604532740).

The source ZIP includes `upstream-sha256.json`, recording hashes of the inspected upstream source files.

## Bundled runtime dependencies

| Component | Version | Licence | Packaging |
| --- | --- | --- | --- |
| Splunk SDK for Python | 2.1.0 | Apache-2.0 | `lib/splunklib`; fetched from the official release tag |
| PyYAML | 6.0.3 | MIT | Pure-Python `lib/yaml`; optional compiled extension excluded |
| JSZip | 3.10.1 | MIT or GPLv3; used under MIT | `appserver/static/vendor/jszip.min.js` |
| Splunk security_content schema | Pinned commit above | Apache-2.0 | Original schema JSON |

Licence texts are included under the app's `README/` directory. New code and app icons are MIT-licensed. No external browser scripts, fonts, tracking or content delivery networks are used by the installed app.

## Splunk integration references

- [Script-based custom REST endpoints](https://dev.splunk.com/enterprise/docs/developapps/customrestendpoints/customrestscript/)
- [restmap.conf session and payload settings](https://help.splunk.com/en/splunk-enterprise/administer/admin-manual/10.4/configuration-file-reference/10.4.0-configuration-file-reference/restmap.conf)
- [commands.conf](https://help.splunk.com/en?resourceId=Splunk_Admin_commandsconf)
- [Splunk Python search-command SDK](https://splunk-python-sdk.readthedocs.io/en/latest/searchcommands.html)

The REST adapter explicitly requests the caller session and disables system authentication. The command uses SCP2's non-distributed streaming configuration, which the SDK encodes as `type=stateful` in its getinfo response.
