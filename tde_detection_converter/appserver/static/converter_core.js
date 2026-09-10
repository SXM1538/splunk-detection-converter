/* Shared browser logic. No DOM, Splunk, global selection state, or network side effects. */
(function (root, factory) {
    if (typeof define === "function" && define.amd) { define([], factory); }
    else if (typeof module === "object" && module.exports) { module.exports = factory(); }
    else { root.TDECore = factory(); }
}(typeof self !== "undefined" ? self : this, function () {
    "use strict";
    function failure(source, message, code) {
        return {source: source, status: "error", filename: "", yaml: "", issues: [
            {severity: "error", code: code || "transport_error", field: "", message: message}
        ]};
    }
    function reconcile(selected, rows) {
        if (!Array.isArray(rows)) { return selected.map(function (s) { return failure(s, "No results returned"); }); }
        var expected = new Set(selected.map(function (s) { return s.key; })), byKey = new Map(), duplicate = new Set(), unexpected = false;
        rows.forEach(function (r) {
            var key = r && r.source && r.source.key;
            if (!expected.has(key)) { unexpected = true; return; }
            if (byKey.has(key)) { duplicate.add(key); }
            byKey.set(key, r);
        });
        return selected.map(function (s) {
            if (unexpected) { return failure(s, "Server returned an unexpected identity; this batch was rejected", "identity_mismatch"); }
            if (duplicate.has(s.key)) { return failure(s, "Server returned duplicate results for this identity", "duplicate_result"); }
            var r = byKey.get(s.key);
            if (!r) { return failure(s, "No conversion result was returned", "missing_result"); }
            if (!["ready", "needs_review", "error"].includes(r.status) || (r.status !== "error" && (!r.yaml || !r.filename))) {
                return failure(s, "Incomplete conversion response", "invalid_result");
            }
            return r;
        });
    }
    function finalise(results) {
        var ids = new Map(), files = new Map();
        results.forEach(function (r) {
            [[ids, r.document && r.document.id, "duplicate_detection_id", "Two selected sources have the same detection UUID"],
             [files, r.filename && r.filename.toLowerCase(), "filename_collision", "Two selected sources have the same output filename"]].forEach(function (entry) {
                var map = entry[0], key = entry[1];
                if (!key) { return; }
                if (map.has(key)) {
                    [map.get(key), r].forEach(function (item) {
                        if (item.status !== "error") { item.status = "needs_review"; }
                        item.issues = item.issues || [];
                        if (!item.issues.some(function (x) { return x.code === entry[2]; })) {
                            item.issues.push({severity: "error", code: entry[2], field: "id", message: entry[3]});
                            if (item.yaml) { item.yaml = "# REVIEW: " + entry[3] + "\n" + item.yaml; }
                            if (item.validation) { item.validation.profile_checks = false; }
                        }
                    });
                } else { map.set(key, r); }
            });
        });
        return results;
    }
    async function convertBatches(selected, options, request, progress, cancelled, batchSize) {
        var results = [], size = batchSize || 25;
        // Snapshot choices once. Later UI edits cannot alter an in-flight batch.
        var frozen = JSON.parse(JSON.stringify(options));
        for (var offset = 0; offset < selected.length; offset += size) {
            var batch = selected.slice(offset, offset + size);
            if (cancelled && cancelled()) {
                results = results.concat(selected.slice(offset).map(function (s) { return failure(s, "Cancelled before processing", "cancelled"); }));
                break;
            }
            try {
                var response = await request({action: "convert", selections: batch, options: frozen});
                if (response.requested !== batch.length || response.processed !== batch.length) { throw new Error("Batch counts do not match the request"); }
                results = results.concat(reconcile(batch, response.results));
            } catch (error) {
                results = results.concat(batch.map(function (s) { return failure(s, error.message || "Batch request failed"); }));
            }
            if (progress) { progress(results.length, selected.length); }
        }
        return finalise(results);
    }
    function buildArchive(results, options, includeDrafts) {
        var files = new Map(), entries = [], counts = {selected: results.length, processed: 0, ready: 0, needs_review: 0, failed: 0, cancelled: 0, exported: 0};
        results.forEach(function (r) {
            var cancelled = (r.issues || []).some(function (i) { return i.code === "cancelled"; });
            if (cancelled) { counts.cancelled++; } else { counts.processed++; }
            if (r.status === "ready") { counts.ready++; }
            else if (r.status === "needs_review") { counts.needs_review++; }
            else { counts.failed++; }
            var entry = JSON.parse(JSON.stringify(r));
            delete entry.yaml; delete entry.document;
            entry.archive_path = null;
            if (r.yaml && (r.status === "ready" || (includeDrafts && r.status === "needs_review"))) {
                if (!/^[A-Za-z0-9_-]+\.yml$/.test(r.filename)) { throw new Error("Unsafe output filename"); }
                var path = (r.status === "ready" ? "detections/" : "drafts/") + r.filename;
                if (files.has(path.toLowerCase())) { throw new Error("Duplicate archive path: " + path); }
                files.set(path.toLowerCase(), {path: path, content: r.yaml});
                entry.archive_path = path;
                counts.exported++;
            }
            entries.push(entry);
        });
        var manifest = {format_version: 1, converter_version: "1.0.0", created_at: new Date().toISOString(), options: options,
            include_drafts: Boolean(includeDrafts), counts: counts, entries: entries};
        files.set("manifest.json", {path: "manifest.json", content: JSON.stringify(manifest, null, 2) + "\n"});
        files.set("readme.txt", {path: "README.txt", content: "TDE Detection Converter\n\n" +
            "detections/: YAML passed the converter's local checks. Run your repository validation before deployment.\n" +
            "drafts/: included only when explicitly selected; review the errors in manifest.json.\n" +
            "manifest.json accounts for every selected source, including failed and cancelled conversions.\n" +
            "Source settings in the manifest may contain internal configuration.\n"});
        return {files: Array.from(files.values()), manifest: manifest};
    }
    return {reconcile: reconcile, finalise: finalise, convertBatches: convertBatches, buildArchive: buildArchive};
}));
