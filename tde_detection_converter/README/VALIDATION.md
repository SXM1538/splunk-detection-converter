# Validation and release status

This is an implemented, packaged application. Its local checks are not a Splunkbase certification or a claim of production deployment testing.

## Automated checks

- Python unittest suite: **49 passing tests**, covering extraction, YAML round-trip, both classic targets, ng schema mapping, Custom YAML, required/optional field behaviour, malformed-record isolation, zero scores, unchanged names/SPL, duplicate namespace identities and filenames, metadata overrides, dependencies, source-access failures and splitter safeguards.
- Real bundled Splunk SDK subprocess: SCP2 getinfo plus 500 input records across five chunks, including a malformed record; all 500 outputs accounted for. Empty input returns no phantom detection. This runs the actual command and SDK, not a stub of the command.
- REST adapter tests: caller-token forwarding, rejection without caller authentication, method restrictions and correct escaping of saved-search paths. Splunk's REST functions are simulated in these tests; the permission enforcement of a real deployment is not claimed as tested.
- JavaScript core: 503-source batching and ZIP round-trip, response reconciliation, missing/duplicate/unexpected identities, cancellation, transport failures, duplicate existing IDs and unsafe archive paths.
- DOM integration: production UI code with a local synthetic API, catalogue paging, persistent selections, same-title searches, source text escaping, custom fields, single and batch downloads, stale-output invalidation, review-draft gating and per-detection overrides. This is DOM emulation, not rendered-browser testing. The shipped JSZip runs in Node with a Blob adapter for the emulated DOM.
- Package checks: Python 3.9 grammar, XML and configuration parsing, required app files, safe archive member paths and bundled dependencies/licences.

The DOM test fixture has 503 selected sources: 502 convertible detections and one malformed source. The archive is independently reopened and checked for a 503-entry manifest and 502 parseable YAML files. Tests use synthetic data only.

## Not run here

- Rendered browser smoke: the browser service could not open the local test endpoint; the standalone Chromium download was unavailable. The reusable `tests/browser_smoke.cjs` test is included for an environment with Chromium.
- Live Splunk Enterprise/Splunk Cloud installation, Classic dashboard loading, SDK/CSRF behaviour inside Splunk Web, actual role/ACL enforcement and search-head-cluster deployment.
- Full contentctl 5.5.1/5.6.0 or ng CLI validation/build inside representative complete customer repositories.
- Splunkbase AppInspect or Splunk Cloud app vetting.

## Before publishing on Splunkbase

1. Install the tarball on a non-production Splunk search head and load the dashboard with a normal user role.
2. Confirm the user sees exactly the saved searches they can read. Check a search owned by another user, a private search and a search shared at app scope.
3. Convert one real search with each intended profile. Inspect schedules, active actions and dependencies in the output and manifest, then validate/build in the matching repository.
4. Select across pages and filters; include same-title searches in two apps and a missing/changed source. Download a batch larger than 500 records and reconcile the manifest and actual files.
5. Confirm XML/AMD loading, POST/CSRF handling, browser downloads and cache behaviour on each claimed Splunk release.
6. Run Splunkbase AppInspect and address its findings. Use Splunk Cloud's separate vetting/install process before advertising Cloud compatibility.

## Reproduce

```bash
python -m unittest discover -s tests -v
node tests/test_browser_core.cjs
python tools/dev_server.py --port 8766
```

For the DOM integration check, install the development-only dependency `happy-dom@20.0.11`, then run `node tests/test_ui_dom.mjs`. It uses a JSONL stdio bridge to the real Python service with synthetic records and needs no server or network. The dependency is not bundled into the Splunk app. `TDE_HAPPY_DOM` can point to an existing `happy-dom/lib/index.js` installation.

For rendered-browser testing, install Playwright and its Chromium browser, run the fixture server on port 8765 and execute `node tests/browser_smoke.cjs`.

The build script creates the installable tarball, full source ZIP and SHA-256 checksums in `dist/`. Tests and the local fixture server are excluded from the installable app.
