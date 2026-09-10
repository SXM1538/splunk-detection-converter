# Validation and release status: 1.0.1

The app has been repaired and locally tested. No live Splunk or hosted Splunk Cloud approval is claimed.

## Automated checks

- **51 Python tests pass**: existing conversion/schema/batch/splitter checks plus the actual bundled Splunk SDK SCP2 protocol, catalogue mode, selected mode across chunks, per-source overrides, absent sources and rejected forged/oversized requests.
- **RequireJS integration passes**: production entry point, generated profiles, search adapter, shared browser code and browser-only JSZip loaded using RequireJS 2.3.7 without Node globals or a `stream` shim. No loader errors. A 503-file DEFLATE ZIP is generated as a browser Blob and reopened.
- **Search transport regressions pass**: fixed query construction, base64 Unicode round-trip, injection-shaped titles staying out of SPL, 503-result paging, cached UI pagination, missing-result accounting, HTTP errors, failed/finalised/zombie jobs, preview rejection, search warnings, early result termination, cleanup and page exit.
- **DOM integration passes**: production picker and search adapter with a simulated Splunk job API backed by the actual Python command and SCP2 protocol. 503 sources produce 502 YAMLs and one deliberately malformed-source failure. Filtering, selection persistence, same-title identity, hostile text, custom fields, single download, stale-output invalidation, review drafts, per-source overrides and settings export pass.
- **Shared browser core passes**: 503-source batching, ZIP round-trip, reconciliation, cancellation, transport failures, collision detection and unsafe-path rejection.
- **Package checks pass**: Python 3.9 grammar, XML/config parsing, ID/folder/version agreement, required files, no custom endpoint stanzas or REST handler, safe archive paths and bundled licences.

The browser test dependencies are development-only and excluded from the installable app. The installed app needs no Node.js or npm packages.

## AppInspect

See `APPINSPECT.md` and `appinspect-cloud.json` for the final local Cloud-tag results and remaining warnings. A local inspection is not the hosted vetting/approval service.

## Not verified here

- Live Splunk installation, built-in search SDK behaviour in the actual Splunk Web shell, actual user roles/ACLs, endpoint removal after the existing deployment, and search-head-cluster operation.
- Rendered browser checks: the Chromium download timed out. DOM and RequireJS checks do not substitute for a rendered browser or live Splunk.
- Full contentctl 5.5.1/5.6.0 or ng builds inside representative repositories.
- Full current dependency-vulnerability database scan or independent penetration test.
- Python 3.13 / SDK 3.x target migration. This repair retains the tested SDK 2.1.0 and does not force an unknown target runtime upgrade.

## Reproduce

```bash
python -m unittest discover -s tests -v
node tests/test_browser_core.cjs
TDE_REQUIREJS=/path/to/requirejs/require.js node tests/test_amd_bootstrap.cjs
TDE_HAPPY_DOM=/path/to/happy-dom/lib/index.js node tests/test_ui_dom.mjs
python tools/build.py
```

The development dependencies used were `requirejs@2.3.7` and `happy-dom@20.0.11`. `tools/fixture_api.py` is a development-only stdio bridge to synthetic records and the real command. It is not a web endpoint or installed service.

`tests/browser_smoke.cjs` and `tools/dev_server.py` remain available for rendered UI testing where Chromium is available. That dev server uses synthetic fixtures and is excluded from the app.
