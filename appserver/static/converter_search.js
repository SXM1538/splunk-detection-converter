/* Splunk's existing search-job API only. No custom REST endpoint or raw SPL input. */
(function (root, factory) {
    if (typeof define === 'function' && define.amd) { define([], factory); }
    else if (typeof module === 'object' && module.exports) { module.exports = factory(); }
    else { root.TDESearch = factory(); }
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';
    var REST = '| rest /servicesNS/-/-/saved/searches splunk_server=local count=0';
    function truth(value) { return value === true || value === 1 || value === '1'; }
    function warnings(messages) {
        return (messages || []).filter(function (message) {
            return /^(WARN|WARNING|ERROR|FATAL)$/i.test(message.type || message.severity || '');
        }).map(function (message) { return message.text || message.message || 'Splunk reported incomplete results'; });
    }
    function encode(payload) {
        // Only the base64 alphabet enters SPL. Names, SPL and overrides remain data.
        var bytes = new TextEncoder().encode(JSON.stringify(payload)), text = '';
        bytes.forEach(function (value) { text += String.fromCharCode(value); });
        var encoded = btoa(text);
        if (encoded.length > 512 * 1024) { throw new Error('Conversion options exceed 512 KiB. Reduce the overrides.'); }
        return encoded;
    }
    function create(service, profiles, Core) {
        var catalogue = null, active = new Set(), disposed = false;
        function runSearch(query, limit) {
            return new Promise(function (resolve, reject) {
                if (disposed) { reject(new Error('The converter page was closed')); return; }
                var job = null, settled = false, pollTimer = null, rows = [];
                var timeout = setTimeout(function () { finish(new Error('Converter search timed out; partial results were discarded.')); }, 120000);
                function cancelJob() { if (job) { try { job.cancel(function () {}); } catch (ignored) {} } }
                function finish(error, value) {
                    if (settled) { return; } settled = true;
                    clearTimeout(timeout); clearTimeout(pollTimer); active.delete(abort); cancelJob();
                    if (error) { reject(error); } else { resolve(value); }
                }
                function abort() { finish(new Error('Converter search cancelled')); }
                function failure(error) {
                    var status = Number(error && (error.status || error.statusCode));
                    return new Error('Splunk search failed' + (status ? ' (HTTP ' + status + ')' : '') + '. Check your search permissions and that convertdetection is installed in this app.');
                }
                function readResults(total) {
                    job.results({output_mode: 'json', count: 500, offset: rows.length}, function (error, data) {
                        if (settled) { return; }
                        if (error) { finish(failure(error)); return; }
                        try {
                            if (typeof data === 'string') { data = JSON.parse(data); }
                            if (!data || truth(data.preview) || !Array.isArray(data.results)) { throw new Error('Splunk returned invalid or preview results'); }
                            var notes = warnings(data.messages);
                            if (notes.length) { throw new Error(notes.join('; ')); }
                            if (!data.results.length && rows.length < total) { throw new Error('Splunk result paging ended early'); }
                            data.results.forEach(function (row) { rows.push(JSON.parse(row.result_json)); });
                            if (rows.length > total || rows.length > limit) { throw new Error('Splunk result counts do not reconcile'); }
                            if (rows.length < total) { readResults(total); } else { finish(null, rows); }
                        } catch (e) { finish(e); }
                    });
                }
                function poll() {
                    job.fetch(function (error) {
                        if (settled) { return; }
                        if (error) { finish(failure(error)); return; }
                        try {
                            var properties = job.properties(), notes = warnings(properties.messages);
                            if (truth(properties.isFailed) || truth(properties.isFinalized) || truth(properties.isZombie)) {
                                throw new Error('Splunk did not complete the converter search; partial results were discarded.');
                            }
                            if (notes.length) { throw new Error(notes.join('; ')); }
                            if (truth(properties.isDone)) {
                                var total = Number(properties.resultCount);
                                if (!Number.isInteger(total) || total < 0 || total > limit) { throw new Error('Converter search exceeded the result limit or returned invalid counts'); }
                                if (!total) { finish(null, []); } else { readResults(total); }
                            } else { pollTimer = setTimeout(poll, 500); }
                        } catch (e) { finish(e); }
                    });
                }
                active.add(abort);
                try {
                    service.search(query, {exec_mode: 'normal', status_buckets: 0, auto_cancel: 60,
                        max_time: 90, max_count: 100001, enable_lookups: false}, function (error, created) {
                        job = created;
                        if (settled) { cancelJob(); return; }
                        if (error) { finish(failure(error)); return; }
                        poll();
                    });
                } catch (e) { finish(failure(e)); }
            });
        }
        async function request(payload) {
            if (disposed) { throw new Error('The converter page was closed'); }
            if (payload.action === 'profiles') { return JSON.parse(JSON.stringify(profiles)); }
            if (payload.action === 'list') {
                var offset = payload.offset || 0;
                if (!Number.isInteger(offset) || offset < 0 || offset > 100000) { throw new Error('Invalid catalogue offset'); }
                if (offset === 0) {
                    catalogue = null;
                    catalogue = await runSearch(REST + ' | convertdetection mode=catalogue | fields result_json', 100000);
                }
                if (!catalogue) { throw new Error('Refresh the saved-search list'); }
                return {entries: catalogue.slice(offset, offset + 200), total: catalogue.length, offset: offset, page_size: 200};
            }
            if (payload.action === 'convert') {
                if (!Array.isArray(payload.selections) || !payload.selections.length || payload.selections.length > 25) { throw new Error('Select between 1 and 25 detections per batch'); }
                var encoded = encode({selections: payload.selections, options: payload.options || {}});
                var results = await runSearch(REST + ' | convertdetection mode=selected request_b64="' + encoded + '" | fields result_json', 25);
                // Missing/deleted/inaccessible sources remain explicit failures in the manifest.
                return {results: Core.reconcile(payload.selections, results), requested: payload.selections.length, processed: payload.selections.length};
            }
            throw new Error('Unknown converter action');
        }
        return {request: request, dispose: function () { disposed = true; active.forEach(function (abort) { abort(); }); catalogue = null; }};
    }
    return {create: create};
}));
