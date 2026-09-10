# Local AppInspect result

Splunk AppInspect **4.3.1**, run with `--mode precert --included-tags cloud --skip-trusted-libraries-update` on the 1.0.1 installable package.

| Result | Count |
| --- | ---: |
| Current failures | 0 |
| Errors | 0 |
| Future failures | 1 |
| Warnings | 3 |
| Skipped | 1 |
| Not applicable | 132 |
| Success | 109 |

This is **not** a clean, unconditional pass and is **not** hosted Splunk Cloud approval.

Remaining items:

- **Future failure:** `check_commands_conf_python_required` requests `python.required = 3.13`. It is not forced in this repair because the target Splunk/Python version was not supplied. The command retains `python.version = python3`.
- **Warning:** `check_python_sdk_version` requests SDK 3.0.0+. The bundled 2.1.0 is retained; SDK 3.0.0 requires Python 3.13. A runtime-specific update needs verification against the target platform.
- **Warning:** `check_for_splunk_js` detects the normal SplunkJS framework; the check's own message says it has no impact on the app.
- **Warning:** `check_for_python_script_existence` is a legacy Python 2/3 migration notice. This app is explicitly Python 3.
- **Skipped:** manifest package-ID cross-check because no `app.manifest` is provided. The app folder, `[package] id`, `[id] name` and version agree and are checked during the build.

Fixed during this review: removed the preconfigured `is_configured = 1` flag, supplied `[id]` metadata and allowed the existing `sc_admin` role to administer app knowledge objects alongside `admin`. No capabilities or role assignments were added.

`appinspect-cloud.json` in this source package contains the full final report. Trusted-library list updates were disabled for this offline run. It does not replace live installation/role testing, hosted vetting or a current dependency-vulnerability scan.
