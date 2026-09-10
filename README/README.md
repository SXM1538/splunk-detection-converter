# TDE Detection Converter 1.0.1

A Splunk app for turning UI-created saved searches into YAML. Includes a searchable picker, single-file preview, batch conversion, direct YAML/ZIP/JSON downloads, versioned output profiles and custom field selection.

## Install

1. In Splunk Web, open **Apps → Manage Apps → Install app from file**.
2. Upload `splunk_detection_converter-1.0.1.tar.gz` and complete the platform-required restart. Hard-refresh the dashboard afterwards.
3. Open **TDE Detection Converter → Detection YAML Converter**.
4. Select detections, choose a format, supply missing metadata, then select **Convert selected**.
5. Review the results. Download a single YAML or a ZIP containing all exportable results.

The package includes its Python SDK, pure-Python YAML dependency and browser ZIP library. No pip/npm installation, outbound internet access, service account, scheduled searches or changes to saved searches are needed at runtime. Install on the search head. Search-head-cluster and Splunk Cloud deployments must use their normal app installation process.

Designed for Splunk Enterprise 9.x/10.x running Python 3.9 or newer with Classic Simple XML dashboards. Live Splunk installation and hosted Cloud/Splunkbase vetting have **not** been run here. A local Cloud-tag AppInspect check is documented in `docs/APPINSPECT.md`. See `docs/VALIDATION.md` for the precise test coverage and release gates.

## Updating the renamed work app

Replace the `splunk_detection_converter/` source folder cleanly, keeping your existing work `.gitlab-ci.yml`. Do not merge the old handler back into the new folder. `default/restmap.conf` and `default/web.conf` are intentionally comment-only to replace the old default endpoint registrations. Any converter-specific `local/` overrides must also be removed; see `docs/SECURITY_REVIEW.md`.

No Node.js installation is required. The app uses Splunk's Python and browser JavaScript. No custom REST endpoint, system token, outbound service or scheduled/background job is added. Search jobs use the current user and the command is app-scoped.

## Output formats

| Profile | Target | Behaviour |
| --- | --- | --- |
| `contentctl_5_5_1` | Classic contentctl v5.5.1 | Nested tags, `date`, RBA and inline `deployment.scheduling` |
| `contentctl_5_6_0` | Classic contentctl v5.6.0 | Same mapped structural contract, separately identified version |
| `contentctl_ng` | ESCU schema at `a02c60b2c7f132dda85c7e65b898317d1e9b97a9` | Top-level classification, two dates, `finding`, `intermediate_findings`, `custom_schedule`; experimental target |
| `custom` | Your selected fields | Start from a preset, choose field groups and add nested source mappings or literal values |

Profiles are bundled, not fetched at runtime. A preset locks required fields and retains action-bearing fields when the source action is enabled. Custom YAML allows free field selection and makes no contentctl compatibility claim. A preset is a conversion target, not a guarantee that the generated YAML will build in every repository.

Splunk does not position contentctl-ng as a supported customer replacement for classic contentctl. [Maintainer clarification](https://github.com/splunk/security_content/issues/4068#issuecomment-4604532740).

## What gets preserved

- The detection title and SPL remain unchanged, including comments, Unicode, line endings and trailing spaces. No naming-prefix removal, filter macro, description stamp or comment-fence workaround.
- Selection identity is app + owner + title. The same title in two namespaces remains two separate detections.
- Existing UUID metadata is retained when present. Otherwise, a deterministic UUID derives from the source identity. Filenames use a separate safe slug and identity hash.
- Disabled risk/notable actions do not export their stale action settings as active actions.
- Real risk scores, including zero, and threat-object types are retained. If the target rejects them, the file becomes a review draft. Scores are never clamped or rounded.
- Source scheduling and supported deployment fields are mapped. Unsupported settings are reported and recorded in the manifest.
- Analyst next steps can be unwrapped from their JSON shell in Custom YAML.

The converter does not discover or export the contents of macros, lookups, stories or test datasets. It reports detected SPL dependencies for repository follow-up. Dependency scanning is a best-effort lexical check, not a complete SPL parser.

## Metadata, fields and overrides

**Metadata defaults** fill values missing from the saved search. No invented author, analytic story or asset type is inserted. Status defaults to `experimental` when the source has no status metadata. This is a conversion default, not evidence that the detection has been tested. Date metadata is reused where available; missing dates use the conversion date with a warning.

**Output overrides** replace values after mapping. They accept a JSON object of dotted output paths. Use the per-detection editor for exceptions within a batch:

```json
{
  "author": "My Detection Team",
  "tags.analytic_story": ["My Existing Story"],
  "tags.manual_test": "Explain the actual manual test procedure here."
}
```

For ng, a finding entity must come from the notable action's `_entities` configuration or an explicit override. The converter never substitutes an arbitrary risk entity:

```json
{
  "finding.entity": {"field": "user", "type": "user", "score": 40}
}
```

**Custom field mappings** use an output path and exactly one of `source` or `value`. Source names are literal saved-search REST keys. Supported transforms: `identity`, `boolean`, `integer`, `list`, `json`, `next_steps`.

```json
[
  {"path": "cron_schedule", "source": "cron_schedule"},
  {"path": "scheduling.allow_skew", "source": "allow_skew"},
  {"path": "next_steps", "source": "action.notable.param.next_steps", "transform": "next_steps"},
  {"path": "team", "value": "Detection Engineering"}
]
```

Checkboxes select mapped fields or complete dependent groups such as `rba` and `deployment.scheduling`. To reshape a group at a finer level, deselect the group in Custom YAML and add the exact output paths as mappings or overrides. Empty optional values can be omitted; meaningful `false` and `0` survive. Save/load settings as JSON for reuse. Detection selections and SPL are not stored in browser local storage.

## Results and downloads

| Status | Meaning | Export |
| --- | --- | --- |
| `ready` / Checks passed | YAML round-trip and implemented local checks passed | `detections/` |
| `needs_review` | YAML exists, but metadata, target constraints or unmapped settings need attention | `drafts/`, only with **Include review drafts** |
| `error` | Source read, extraction or serialisation failed | Manifest entry, no YAML |

`ready` does not mean a contentctl repository build or live test passed. Custom results only have extraction and YAML-integrity checks.

The ZIP contains `manifest.json`, `README.txt` and one file per exportable detection. The manifest accounts for every selected source, including failed, missing, cancelled and non-exported drafts, and records the submitted options, issues, dependencies and relevant original settings. Downloads may contain internal SPL and configuration, so handle them as detection source code.

Selections survive filters and pagination. **Select all matching** selects the complete loaded match set, not just the current page. Refresh detects incomplete/repeated catalogue pages. Conversion uses sequential batches of 25 identities via Splunk search jobs. The fixed REST pipeline rereads saved-search metadata for each batch; it does not execute detection SPL. Selections and overrides enter the command as base64 JSON, never as a title-based SPL clause. A failed batch does not stop later batches. Cancel finishes the current request and records the remaining selections as cancelled. Downloads always use the last completed option snapshot; changing conversion inputs invalidates the old results.

Existing UUID collisions across selected sources are flagged; the converter does not silently rewrite those IDs. Duplicate archive paths are rejected rather than overwritten.

## Search command

From the converter app's search context:

```spl
| rest /servicesNS/-/-/saved/searches splunk_server=local count=0
| search title="My detection" 'eai:acl.app'="my_app" 'eai:acl.owner'="nobody"
| convertdetection profile=contentctl_5_6_0 author="My Detection Team"
| table title app owner status filename yaml issues result_json
```

For Custom YAML:

```spl
| rest /servicesNS/-/-/saved/searches splunk_server=local count=0
| search 'eai:acl.app'="my_app"
| convertdetection profile=custom fields="name,id,search,rba,cron_schedule,next_steps"
```

Advanced options can be passed as UTF-8 JSON encoded in standard base64 through `options_b64`. This avoids ambiguous SPL quoting. The dashboard submits fixed search jobs with base64 JSON options; base64 is not encryption, and those options may appear in Splunk job/audit records. There is no custom REST endpoint.

## Offline tools

The source ZIP includes these optional tools. Python 3.9+ is sufficient; the conversion tool uses the dependencies bundled in the app directory.

```bash
python tools/convert_json.py saved-searches.json converted.json --options my-settings.json
python tools/split_export.py converted.json exported-files --include-drafts
```

The splitter accepts app JSON, Splunk results JSON and Splunk JSONL envelopes containing `result_json`. It rejects preview exports, unsafe paths, duplicate filenames and existing destination files. Exit code 2 means there are drafts or failures; exit code 1 means the operation failed. The old unverified `--tree` behaviour is replaced by explicit `detections/` and `drafts/` directories.

## Development

```bash
python -m unittest discover -s tests -v
node tests/test_browser_core.cjs
python tools/dev_server.py
# In another terminal, with Playwright and Chromium installed:
node tests/browser_smoke.cjs
python tools/build.py
```

The development server binds to localhost and uses synthetic fixtures only. It is excluded from the installable Splunk app. It exercises the production UI and conversion engine but does not emulate Splunk authentication or the entire Splunk Web shell.

`bin/convert_detection.py` implements the search-command boundary. `converter_search.js` uses Splunk's existing authenticated search-job API. The custom REST handler has been removed. `lib/tde_converter/core.py` holds the conversion boundary; `profiles.py` and `schemas/` define targets; `service.py` contains shared validation and offline fixture helpers. `converter_profiles.js` is generated from the Python profile catalogue at build time. The browser's shared batch/archive logic is independently testable in `converter_core.js`.

This release reconstructs the converter from the supplied source excerpts and implements the missing picker/export path. Parity dashboards are outside this converter package; their original files were not available.

## Sources and licences

Schema provenance and dependency licences are documented in `docs/PROVENANCE.md` and the app's `README/` directory. New app code is MIT-licensed. The bundled Splunk SDK and security-content schema retain Apache-2.0 licences; PyYAML and JSZip retain their upstream licences.
