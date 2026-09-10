# Security review: Detection Converter 1.0.1

## Decision

The custom REST backend added in 1.0.0 was unnecessary for this app. It has been removed. Version 1.0.1 uses Splunk's existing authenticated search-job API and a fixed `| rest /servicesNS/-/-/saved/searches splunk_server=local count=0 | convertdetection ...` pipeline. This restores the original read-and-convert model while retaining profiles, field selection and direct downloads.

Node.js is not an installation or runtime requirement. JavaScript runs in the user's browser. Node was used only on the development machine to test that code. No Node runtime, npm packages, development server or background service is included in the installable tarball.

This is a source/configuration review with automated tests and a local AppInspect run. It is not a penetration test, dependency vulnerability certification, Splunk Cloud approval or a live deployment test. The deployed GitLab tree and CI configuration were not supplied; this package uses the recovered 1.0.0 source plus the documented rename to `splunk_detection_converter`.

## Findings and actions

| Component or concern | Finding | Action in 1.0.1 |
| --- | --- | --- |
| Custom REST handler | Added a persistent Python request handler and another authenticated endpoint to review. It used the caller's token, not system/admin authentication, and only read saved searches. It was avoidable. | Removed `bin/tde_converter_rest.py` and all REST/Web registration stanzas. The two configuration files are comment-only so upgrades overwrite old default registrations. |
| REST 404 | 1.0.0 used `web.conf` `[endpoint:...]`/`match`, which registers a CherryPy controller, instead of `[expose:...]`/`pattern` for a splunkd endpoint. | Eliminated that entire custom endpoint path. The UI now uses built-in search jobs. |
| JSZip / Node `stream` | The browser bundle probed Node's optional stream module. Under RequireJS that reached the host loader. This was a packaging error, not evidence of a Node service running in Splunk. | Browser-only adaptation of JSZip 3.10.1 removes the external Node-stream probe. Tested with actual RequireJS and no Node globals in the application realm. |
| Command visibility | 1.0.0 exported `convertdetection` system-wide. This was not needed for the dashboard. | Command is app-scoped. It can still be used from this app's search context. |
| Privileges | No supplied app code grants capabilities or roles, changes authentication, bypasses CSRF or uses a service/admin token. | Retained normal Splunk session handling. Configuration write access is limited to the existing `admin` and `sc_admin` roles; no role is created or granted. |
| SPL injection | Building an OR clause from unescaped detection names would be risky. | The dispatched SPL is fixed. Selections/options are JSON encoded as standard base64; only the base64 alphabet is inserted into a quoted command argument. Python matches exact app/owner/title identities. Titles, overrides and saved SPL are never evaluated as code. |
| Execution of detections | Converting a saved search does not require executing its SPL. | The command reads metadata and serialises text. No `map`, saved-search dispatch, `eval()`/`exec()` or shell execution is used by the converter. Tests include pipe/backtick/quote/Unicode names and SPL containing `outputlookup`; they remain data. |
| Source changes | No converter path writes or deletes a saved search, changes a schedule, enables alerts, writes lookups or changes Splunk configuration. | All source operations remain reads. Splunk itself creates ordinary search-job artefacts and audit records. |
| External connections | No app-owned code sends detections to an external service, uses a CDN or downloads schemas at runtime. Bundled SDK networking methods exist but are not invoked by the conversion command. | Browser calls remain within Splunk's built-in session/API. Downloads use local Blob URLs. No telemetry is added by this app. |
| Browser injection | A fixed HTML template is used. Saved-search names, descriptions, YAML, issues and preview text use `textContent`/`value`. | Retained text-only rendering; DOM tests cover hostile source strings. Custom output paths reject prototype-related names. |
| YAML and paths | The converter emits YAML and re-reads it with `yaml.safe_load`; schema references are restricted to the bundled document. ZIP filenames are sanitised and collisions are rejected. | Retained these protections. No arbitrary server file path is accepted by the dashboard/command. |
| Resource usage | New profiles/validation and browser ZIP creation consume CPU/memory. A full catalogue is reread for each conversion batch; this is metadata enumeration, not an indexed-event search. | At most 25 selected detections per sequential batch, 100,000 catalogue records, 512 KiB encoded options, a 90-second server search limit and 120-second browser timeout. Jobs are cancelled/cleaned up afterwards and on page exit. Finalised, failed, preview, warning-bearing or incompletely paged results are rejected. Large deployments still need a load test. |
| Sensitive output | YAML and manifests intentionally contain detection SPL/configuration. Overrides appear in ordinary Splunk search-job text as base64, which is not encryption. | No browser local storage is used. Users control downloads; treat downloads and job/audit records as detection source. Do not put credentials in overrides. |
| Prior CI changes | Only screenshots describing the rename and pipeline were supplied. | The new app ID/folder match the screenshots. The work GitLab pipeline has not been inspected, changed or recreated. |

## Runtime dependencies

| Dependency | Why present | Runtime location |
| --- | --- | --- |
| Splunk Python SDK 2.1.0 | Implements Splunk's chunked custom-command protocol. | Splunk's existing Python process on the search head. |
| PyYAML 6.0.3, pure Python | Serialises output and checks the YAML round-trip. | Same Python process. |
| JSZip 3.10.1, documented browser adaptation | Creates a multi-file ZIP download. | User's browser only. |
| Pinned schemas | Offline output checks. | Bundled data files, no network retrieval. |

No extra operating-system service or runtime needs installing. These dependencies still belong in a company's software inventory and dependency review.

## AppInspect and compatibility

See `APPINSPECT.md` and `appinspect-cloud.json` in the source package for the exact local results. This is a local Cloud-tag check, not the hosted Cloud approval service; trusted-library updates were disabled for the offline run.

AppInspect recommends Python SDK 3.0.0+ and flags a future Python 3.13 requirement. The official 3.0.0 SDK requires Python 3.13. Forcing that dependency without knowing the deployed Splunk/Python version could break this repair, so this package retains the tested SDK 2.1.0 and `python.version = python3`. The warnings are explicitly retained, not hidden or suppressed. A Python-3.13-specific release needs the target version and matching runtime testing before claiming that compatibility.

## Evidence and remaining checks

Automated checks cover the actual bundled command protocol, metadata-only catalogue, exact selections across chunks, overrides, malformed-source isolation, injection-shaped text, RequireJS startup, browser Blob ZIP creation, search pagination, partial-result rejection, job cleanup, UI selection persistence and export accounting. The DOM integration test exercises the new search adapter with a simulated Splunk job API backed by the real Python command, not the removed REST backend.

No live Splunk instance is available here. Verify installation, role/ACL behaviour, search dispatch, downloads and clean endpoint removal on the target search head. The rendered-browser test could not run because Chromium could not be downloaded. No full current vulnerability-database scan of every bundled dependency was completed.

## Upgrade precautions

Replace the app source folder cleanly in the deployment repository rather than overlaying old files. Preserve your existing `.gitlab-ci.yml` outside that folder. Deploy as an update to `splunk_detection_converter`, complete the platform's required restart and hard-refresh the dashboard.

The comment-only `default/restmap.conf` and `default/web.conf` deliberately overwrite old default registrations. If you created `local/restmap.conf` or `local/web.conf` overrides, remove only the obsolete converter endpoint stanzas there: local settings take precedence over defaults. Check that the removed handler is no longer registered. Do not alter unrelated app endpoints.

## Primary references

- [Splunk web.conf: endpoint versus expose](https://help.splunk.com/en/splunk-enterprise/administer/admin-manual/9.4/configuration-file-reference/9.4.3-configuration-file-reference/web.conf)
- [Splunk search jobs and completion/finalisation fields](https://help.splunk.com/en/splunk-enterprise/rest-api-reference/9.4/search-endpoints/search-endpoint-descriptions)
- [Splunk SDK 3.0.0 runtime requirement](https://pypi.org/project/splunk-sdk/3.0.0/)
