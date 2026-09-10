# 1.0.1 repair

- Applied the documented app rename to `splunk_detection_converter` consistently across the app folder, metadata, browser module paths, tools and tests.
- Removed the persistent custom REST handler. The UI uses Splunk's existing authenticated search-job API and a fixed `| rest ... | convertdetection ...` pipeline.
- Left `default/restmap.conf` and `default/web.conf` comment-only to replace obsolete default registrations on upgrade.
- Added catalogue/selected modes to the existing command. Selection data is exact-identity matched in Python, not assembled into SPL predicates. Detection SPL is never executed.
- Added a search-job adapter with paged final results, sequential batches, partial-result rejection, bounded runtime and cleanup.
- Restricted command visibility to this app. Updated Cloud administrator metadata and app identifiers.
- Adapted JSZip 3.10.1 to disable its external Node stream probe. The app requires no Node runtime.
- Added actual RequireJS startup/ZIP tests and extended the real command-protocol and DOM tests to cover the replacement search workflow.
- Added the security review and AppInspect report, including unresolved Python 3.13 / SDK 3.x compatibility flags.

The work `.gitlab-ci.yml` was not available and is not included. Preserve that file and replace the app folder cleanly. This source package is not a reconstruction of any other unprovided work edits.
