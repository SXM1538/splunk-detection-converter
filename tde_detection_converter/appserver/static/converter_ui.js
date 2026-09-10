(function (root, factory) {
    if (typeof define === "function" && define.amd) { define([], factory); }
    else { root.TDEUI = factory(); }
}(typeof self !== "undefined" ? self : this, function () {
    "use strict";
    function mount(root, request, Core, JSZip) {
        // Only this fixed template uses HTML. Every source/result string is assigned through textContent/value.
        root.innerHTML = '<div class="tde-app">' +
          '<header class="tde-heading"><div><span class="tde-eyebrow">DETECTION AS CODE</span><h1>From saved search to YAML.</h1><p>Choose your detections. Set your format. Take your content with you.</p></div><span id="tde-version" class="tde-version">v1.0.0</span></header>' +
          '<div id="tde-message" class="tde-message" role="status" aria-live="polite">Loading profiles and saved searches…</div>' +
          '<div class="tde-workspace"><section class="tde-card tde-picker"><div class="tde-section-title"><h2><span>1</span> Choose detections</h2><button id="tde-refresh" type="button">Refresh</button></div>' +
          '<div class="tde-filter"><label for="tde-filter">Filter by title, app or owner</label><input id="tde-filter" type="search" placeholder="Search saved searches…"/><label class="tde-check"><input id="tde-detections-only" type="checkbox" checked/> Detection actions only</label></div>' +
          '<div class="tde-selection"><strong id="tde-selected">0 selected</strong><div><button id="tde-select-page" type="button">Select page</button><button id="tde-select-all" type="button">Select all matching</button><button id="tde-clear" type="button">Clear</button></div></div>' +
          '<div class="tde-table-wrap"><table><thead><tr><th scope="col"><span class="tde-sr-only">Select</span></th><th scope="col">Saved search</th><th scope="col">App / owner</th></tr></thead><tbody id="tde-rows"></tbody></table></div>' +
          '<div class="tde-pagination"><span id="tde-page-label"></span><div><button id="tde-prev" type="button">Previous</button><button id="tde-next" type="button">Next</button></div></div></section>' +
          '<section class="tde-card tde-settings"><div class="tde-section-title"><h2><span>2</span> Choose your output</h2></div><div id="tde-config">' +
          '<label for="tde-profile">YAML format</label><select id="tde-profile"></select><p id="tde-profile-note" class="tde-hint"></p>' +
          '<div id="tde-base-wrap" hidden><label for="tde-base">Start custom fields from</label><select id="tde-base"></select></div>' +
          '<details open><summary>Metadata defaults <span>Used when absent in the source</span></summary><div class="tde-form-grid">' +
          '<div><label for="tde-author">Author</label><input id="tde-author" data-default="author" placeholder="Name or team"/></div>' +
          '<div><label for="tde-story">Analytic stories</label><input id="tde-story" data-default="analytic_story" placeholder="Comma-separated story names"/></div>' +
          '<div><label for="tde-asset">Asset type</label><select id="tde-asset" data-default="asset_type"></select></div>' +
          '<div><label for="tde-domain">Security domain</label><select id="tde-domain" data-default="security_domain"></select></div>' +
          '<div><label for="tde-data">Data sources</label><input id="tde-data" data-default="data_source" placeholder="Comma-separated data sources"/></div>' +
          '<div><label for="tde-status">Content status</label><select id="tde-status" data-default="status"><option value="experimental">Experimental</option><option value="production">Production</option><option value="deprecated">Deprecated</option></select></div>' +
          '<div id="tde-category-wrap"><label for="tde-category">Category (ng)</label><select id="tde-category" data-default="category"></select></div>' +
          '</div><label for="tde-implementation">How to implement</label><textarea id="tde-implementation" data-default="how_to_implement" rows="2" placeholder="Data, add-ons and setup needed"></textarea>' +
          '<label for="tde-false-positives">Known false positives</label><textarea id="tde-false-positives" data-default="known_false_positives" rows="2" placeholder="Expected benign activity and tuning guidance"></textarea></details>' +
          '<details><summary>Included fields</summary><p class="tde-hint">Required and active action fields stay included in fixed profiles. Custom YAML lets you choose freely.</p><div id="tde-fields" class="tde-fields"></div><label class="tde-check"><input id="tde-omit-empty" type="checkbox" checked/> Omit empty optional fields</label></details>' +
          '<details><summary>Field overrides and mappings</summary><label for="tde-overrides">Output overrides for all selected detections</label><textarea id="tde-overrides" class="tde-json" rows="5" spellcheck="false" placeholder="Use output paths such as tags.manual_test">{}</textarea>' +
          '<p class="tde-hint">JSON object. Use output paths such as tags.analytic_story, finding.entity or tests. Values here replace source values.</p>' +
          '<div id="tde-rules-wrap" hidden><label for="tde-rules">Custom field mappings</label><textarea id="tde-rules" class="tde-json" rows="5" spellcheck="false">[]</textarea><p class="tde-hint">Example: [{"path":"cron_schedule","source":"cron_schedule"}]. Use source or value, plus an optional transform: boolean, integer, list, json or next_steps.</p></div></details>' +
          '</div><div class="tde-profile-tools"><button id="tde-save-options" type="button">Save settings</button><button id="tde-load-options" type="button">Load settings</button><input id="tde-options-file" type="file" accept=".json" hidden/></div></section></div>' +
          '<section class="tde-run"><div><strong id="tde-run-label">Ready when you are.</strong><p>Each selected detection gets a result. Your saved searches are read only.</p></div><div><button id="tde-cancel" type="button" hidden>Cancel remaining</button><button id="tde-convert" class="tde-primary" type="button" disabled>Convert selected</button></div></section>' +
          '<section id="tde-output" class="tde-card tde-output" hidden><div class="tde-section-title"><h2><span>3</span> Review &amp; download</h2><div class="tde-downloads"><label class="tde-check"><input id="tde-include-drafts" type="checkbox"/> Include review drafts</label><button id="tde-json-export" type="button">JSON</button><button id="tde-zip" class="tde-primary" type="button">Download ZIP</button></div></div>' +
          '<p id="tde-result-summary"></p><div class="tde-results-layout"><div><label for="tde-result-filter">Results</label><select id="tde-result-filter"><option value="all">All results</option><option value="needs_review">Needs review</option><option value="ready">Checks passed</option><option value="error">Failed</option></select><div id="tde-result-list" class="tde-result-list"></div></div>' +
          '<div class="tde-preview"><div class="tde-preview-heading"><strong id="tde-preview-name"></strong><button id="tde-yaml" type="button" disabled>Download YAML</button></div><div id="tde-issues"></div><pre id="tde-yaml-text" tabindex="0"></pre>' +
          '<details><summary>Override this detection</summary><label for="tde-row-overrides">Output field overrides</label><textarea id="tde-row-overrides" class="tde-json" rows="5" spellcheck="false">{}</textarea><button id="tde-apply-row" type="button">Apply &amp; reconvert selection</button></details></div></div></section></div>';

        function el(id) { return root.querySelector("#tde-" + id); }
        var rows = [], selected = new Map(), overrides = new Map(), page = 0, pageSize = 20, config, busy = false, cancel = false;
        var results = [], selectedResult = null, resultOptions = {}, catalogueReady = false;
        function message(value, error) { el("message").textContent = value; el("message").classList.toggle("tde-error", Boolean(error)); }
        function option(parent, value, label) { var opt = document.createElement("option"); opt.value = value; opt.textContent = label; parent.appendChild(opt); }
        function fillSelect(id, values) { el(id).replaceChildren(); option(el(id), "", "Choose if needed…"); values.forEach(function (v) { option(el(id), v, v); }); }
        function invalidate() { results = []; selectedResult = null; el("output").hidden = true; el("run-label").textContent = "Settings changed. Convert to refresh the output."; }
        function matching() {
            var term = el("filter").value.toLocaleLowerCase();
            return rows.filter(function (r) { return (!el("detections-only").checked || r.detection) && [r.title, r.app, r.owner].join(" ").toLocaleLowerCase().includes(term); });
        }
        function renderRows() {
            var matches = matching(), maxPage = Math.max(0, Math.ceil(matches.length / pageSize) - 1); page = Math.min(page, maxPage);
            el("rows").replaceChildren();
            matches.slice(page * pageSize, (page + 1) * pageSize).forEach(function (r) {
                var tr = document.createElement("tr"), pick = document.createElement("td"), name = document.createElement("td"), context = document.createElement("td");
                var checkbox = document.createElement("input"); checkbox.type = "checkbox"; checkbox.checked = selected.has(r.key); checkbox.disabled = busy;
                checkbox.setAttribute("aria-label", "Select " + r.title + " in " + r.app + " owned by " + r.owner); checkbox.dataset.key = r.key;
                checkbox.addEventListener("change", function () { if (checkbox.checked) { selected.set(r.key, r); } else { selected.delete(r.key); } invalidate(); renderRows(); });
                pick.appendChild(checkbox); var title = document.createElement("strong"); title.textContent = r.title; name.appendChild(title);
                var state = document.createElement("small"); state.textContent = r.disabled ? "Disabled" : "Enabled"; name.appendChild(state);
                context.textContent = r.app; var owner = document.createElement("small"); owner.textContent = r.owner; context.appendChild(owner);
                tr.append(pick, name, context); tr.classList.toggle("tde-picked", selected.has(r.key)); el("rows").appendChild(tr);
            });
            if (!matches.length) { var tr = document.createElement("tr"), td = document.createElement("td"); td.colSpan = 3; td.textContent = "No matching saved searches. Try clearing the filter or showing all saved searches."; tr.appendChild(td); el("rows").appendChild(tr); }
            el("selected").textContent = selected.size + " selected";
            el("page-label").textContent = matches.length + " matching · " + rows.length + " loaded · Page " + (page + 1) + " of " + (maxPage + 1);
            el("prev").disabled = page === 0; el("next").disabled = page >= maxPage;
            el("convert").disabled = busy || !catalogueReady || !selected.size;
            ["select-page", "select-all", "clear", "refresh"].forEach(function (id) { el(id).disabled = busy || !catalogueReady; });
        }
        function renderFields(previous) {
            var custom = el("profile").value === "custom", base = custom ? el("base").value : el("profile").value, spec = config.profiles[base];
            el("base-wrap").hidden = !custom; el("rules-wrap").hidden = !custom; el("category-wrap").hidden = spec.family !== "ng";
            el("profile-note").textContent = custom ? "Start from a preset, select fields and add mappings. Custom output has no contentctl compatibility claim." : (spec.note || "Pinned to " + spec.target + ". Local checks run before export; validate the result in your content repository.");
            el("fields").replaceChildren();
            spec.fields.concat(custom ? config.extra_fields : []).forEach(function (field) {
                var label = document.createElement("label"), check = document.createElement("input"), caption = document.createElement("span"); label.className = "tde-check";
                check.type = "checkbox"; check.value = field;
                check.disabled = !custom && spec.required.includes(field);
                check.checked = check.disabled || (previous ? previous.includes(field) : spec.fields.includes(field));
                caption.textContent = field + (check.disabled ? " *" : ""); label.append(check, caption); el("fields").appendChild(label);
            });
        }
        function readJSON(id, kind) {
            var v;
            try { v = JSON.parse(el(id).value); } catch (e) { throw new Error(id + " contains invalid JSON"); }
            if ((kind === "array" && !Array.isArray(v)) || (kind === "object" && (!v || typeof v !== "object" || Array.isArray(v)))) { throw new Error(id + " must be a JSON " + kind); }
            return v;
        }
        function readOptions() {
            var defaults = {};
            root.querySelectorAll("[data-default]").forEach(function (input) {
                var value = input.value.trim(), key = input.dataset.default;
                if (value) { defaults[key] = ["analytic_story", "data_source"].includes(key) ? value.split(",").map(function (s) { return s.trim(); }).filter(Boolean) : value; }
            });
            return {profile: el("profile").value, base_profile: el("base").value, fields: Array.from(el("fields").querySelectorAll("input:checked")).map(function (x) { return x.value; }),
                omit_empty: el("omit-empty").checked, defaults: defaults, overrides: readJSON("overrides", "object"), custom_fields: el("profile").value === "custom" ? readJSON("rules", "array") : []};
        }
        function download(name, content, type) {
            var blob = content instanceof Blob ? content : new Blob([content], {type: type || "text/plain;charset=utf-8"});
            var url = URL.createObjectURL(blob), a = document.createElement("a"); a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
            window.setTimeout(function () { URL.revokeObjectURL(url); }, 10000);
        }
        function setBusy(value) {
            busy = value;
            el("config").querySelectorAll("input,textarea,select").forEach(function (x) { x.disabled = value; });
            if (!value && config) { var existing = Array.from(el("fields").querySelectorAll("input:checked")).map(function (x) { return x.value; }); renderFields(existing); }
            ["save-options", "load-options", "apply-row"].forEach(function (id) { el(id).disabled = value; });
            el("cancel").hidden = !value; renderRows();
        }
        function showResult(result) {
            selectedResult = result; el("preview-name").textContent = result.source.title || "Unavailable source";
            el("yaml-text").textContent = result.yaml || "No YAML generated. See the errors above.";
            el("issues").replaceChildren();
            (result.issues || []).forEach(function (issue) {
                var p = document.createElement("p"); p.className = issue.severity === "error" ? "tde-issue-error" : "tde-issue-note";
                p.textContent = (issue.field ? issue.field + ": " : "") + issue.message; el("issues").appendChild(p);
            });
            el("yaml").disabled = !result.yaml || (result.status !== "ready" && !el("include-drafts").checked);
            el("row-overrides").value = JSON.stringify(overrides.get(result.source.key) || {}, null, 2);
            el("result-list").querySelectorAll("button").forEach(function (b) { b.classList.toggle("tde-active-result", b.dataset.key === result.source.key); });
        }
        function renderResults() {
            el("output").hidden = false;
            var counts = {ready: 0, needs_review: 0, error: 0}; results.forEach(function (r) { counts[r.status]++; });
            el("result-summary").textContent = results.length + " selected · " + counts.ready + " passed local checks · " + counts.needs_review + " need review · " + counts.error + " failed or cancelled";
            el("result-list").replaceChildren();
            var visible = results.filter(function (r) { return el("result-filter").value === "all" || r.status === el("result-filter").value; });
            visible.forEach(function (r) {
                var b = document.createElement("button"), name = document.createElement("strong"), detail = document.createElement("small"), badge = document.createElement("span");
                b.type = "button"; b.dataset.key = r.source.key; name.textContent = r.source.title || "Unavailable source"; detail.textContent = r.source.app + " / " + r.source.owner;
                badge.className = "tde-badge tde-" + r.status; badge.textContent = {ready: "Checks passed", needs_review: "Needs review", error: "Failed"}[r.status]; b.append(name, detail, badge);
                b.addEventListener("click", function () { showResult(r); }); el("result-list").appendChild(b);
            });
            if (visible.length) { showResult(visible.find(function (r) { return selectedResult && r.source.key === selectedResult.source.key; }) || visible[0]); }
            else { selectedResult = null; el("preview-name").textContent = "No matching results"; el("issues").replaceChildren(); el("yaml-text").textContent = ""; el("yaml").disabled = true; }
        }
        async function run() {
            var options;
            try { options = readOptions(); } catch (e) { message(e.message, true); return; }
            if (!selected.size || busy) { return; }
            var inputs = Array.from(selected.values()).map(function (s) { return Object.assign({}, s, {overrides: overrides.get(s.key) || {}}); });
            cancel = false; setBusy(true); el("output").hidden = true;
            message("Converting " + inputs.length + " detections…");
            try {
                results = await Core.convertBatches(inputs, options, request, function (done, total) { message("Converted " + done + " of " + total + "."); }, function () { return cancel; }, config.batch_size);
                resultOptions = JSON.parse(JSON.stringify(options));
                // Do not keep a second copy of full SPL in the JSON options.
                resultOptions.per_detection_overrides = inputs.filter(function (s) { return Object.keys(s.overrides).length; }).map(function (s) { return {key: s.key, overrides: s.overrides}; });
                el("run-label").textContent = "Every selection accounted for."; renderResults(); message("Conversion complete. Review the results below.");
            } catch (e) { message(e.message, true); }
            finally { setBusy(false); }
        }
        async function loadCatalogue() {
            if (busy) { return; }
            if (!config) { message("Profiles could not be loaded. Reload the page after checking the app installation.", true); return; }
            catalogueReady = false; setBusy(true); var loaded = [], seen = new Set(), offset = 0, total = null;
            try {
                do {
                    var data = await request({action: "list", offset: offset});
                    if (!Array.isArray(data.entries) || !Number.isInteger(data.total) || data.total < 0 || data.offset !== offset) { throw new Error("Invalid saved-search catalogue response"); }
                    if (total !== null && total !== data.total) { throw new Error("Saved searches changed while loading. Refresh to load a consistent list."); }
                    total = data.total;
                    data.entries.forEach(function (r) { if (seen.has(r.key)) { throw new Error("Repeated saved-search identity while paging. Refresh the list."); } seen.add(r.key); loaded.push(r); });
                    offset += data.entries.length;
                    if (!data.entries.length && offset < total) { throw new Error("Saved-search list stopped before all entries were received"); }
                    if (total > 100000) { throw new Error("Catalogue exceeds 100,000 saved searches"); }
                    message("Loading saved searches: " + offset + " of " + total + "…");
                } while (offset < total);
                if (offset !== total) { throw new Error("Catalogue totals do not reconcile"); }
                rows = loaded; catalogueReady = true;
                // Retain selected identities that disappeared, so conversion reports the missing source.
                invalidate(); message(rows.length + " saved searches loaded. Selections stay selected across filters and pages.");
            } catch (e) { message(e.message, true); }
            finally { setBusy(false); el("refresh").disabled = false; }
        }

        el("filter").addEventListener("input", function () { page = 0; renderRows(); });
        el("detections-only").addEventListener("change", function () { page = 0; renderRows(); });
        el("prev").addEventListener("click", function () { page--; renderRows(); });
        el("next").addEventListener("click", function () { page++; renderRows(); });
        el("select-page").addEventListener("click", function () { matching().slice(page * pageSize, (page + 1) * pageSize).forEach(function (r) { selected.set(r.key, r); }); invalidate(); renderRows(); });
        el("select-all").addEventListener("click", function () { matching().forEach(function (r) { selected.set(r.key, r); }); invalidate(); renderRows(); });
        el("clear").addEventListener("click", function () { selected.clear(); invalidate(); renderRows(); });
        el("refresh").addEventListener("click", loadCatalogue);
        el("config").addEventListener("input", invalidate);
        el("config").addEventListener("change", function (e) { if (["tde-profile", "tde-base"].includes(e.target.id)) { renderFields(); } invalidate(); });
        el("convert").addEventListener("click", run);
        el("cancel").addEventListener("click", function () { cancel = true; message("Finishing the current batch, then cancelling the remaining selections."); });
        el("result-filter").addEventListener("change", renderResults);
        el("include-drafts").addEventListener("change", function () { if (selectedResult) { showResult(selectedResult); } });
        el("yaml").addEventListener("click", function () { if (selectedResult && selectedResult.yaml) { download(selectedResult.filename, selectedResult.yaml, "application/yaml;charset=utf-8"); } });
        el("json-export").addEventListener("click", function () { download("detection-converter-results.json", JSON.stringify({format_version: 1, options: resultOptions, results: results}, null, 2), "application/json"); });
        el("zip").addEventListener("click", async function () {
            el("zip").disabled = true;
            try {
                var archive = Core.buildArchive(results, resultOptions, el("include-drafts").checked), zip = new JSZip();
                archive.files.forEach(function (f) { zip.file(f.path, f.content); });
                var blob = await zip.generateAsync({type: "blob", compression: "DEFLATE", compressionOptions: {level: 6}});
                download("detections-" + new Date().toISOString().slice(0, 10) + ".zip", blob);
                message("Downloaded " + archive.manifest.counts.exported + " YAML files and a manifest covering all " + results.length + " selections.");
            } catch (e) { message(e.message, true); }
            finally { el("zip").disabled = false; }
        });
        el("apply-row").addEventListener("click", function () {
            if (!selectedResult) { return; }
            try { overrides.set(selectedResult.source.key, readJSON("row-overrides", "object")); run(); } catch (e) { message(e.message, true); }
        });
        el("save-options").addEventListener("click", function () { try { download("detection-converter-settings.json", JSON.stringify(readOptions(), null, 2), "application/json"); } catch (e) { message(e.message, true); } });
        el("load-options").addEventListener("click", function () { el("options-file").click(); });
        el("options-file").addEventListener("change", async function () {
            var file = el("options-file").files[0]; if (!file) { return; }
            try {
                if (file.size > 512 * 1024) { throw new Error("Settings file exceeds 512 KiB"); }
                var data = JSON.parse(await file.text());
                if (!config.profiles[data.profile] || !config.profiles[data.base_profile || "contentctl_5_6_0"] || data.base_profile === "custom") { throw new Error("Unrecognised settings profile"); }
                el("profile").value = data.profile; el("base").value = data.base_profile || "contentctl_5_6_0"; renderFields(data.fields);
                root.querySelectorAll("[data-default]").forEach(function (input) { var value = (data.defaults || {})[input.dataset.default]; input.value = Array.isArray(value) ? value.join(", ") : value || ""; });
                el("overrides").value = JSON.stringify(data.overrides || {}, null, 2); el("rules").value = JSON.stringify(data.custom_fields || [], null, 2);
                el("omit-empty").checked = data.omit_empty !== false; readOptions(); invalidate(); message("Settings loaded.");
            } catch (e) { message("Could not load settings: " + e.message, true); }
            finally { el("options-file").value = ""; }
        });
        request({action: "profiles"}).then(function (data) {
            config = data;
            Object.keys(config.profiles).forEach(function (id) { option(el("profile"), id, config.profiles[id].label); if (id !== "custom") { option(el("base"), id, config.profiles[id].label); } });
            el("profile").value = "contentctl_5_6_0"; el("base").value = "contentctl_5_6_0";
            fillSelect("asset", config.asset_types); fillSelect("domain", config.security_domains); fillSelect("category", config.categories);
            el("version").textContent = "v" + config.version; renderFields(); return loadCatalogue();
        }).catch(function (e) { message(e.message, true); });
        return {getSelection: function () { return Array.from(selected.keys()); }, getResults: function () { return results; }};
    }
    return {mount: mount};
}));
