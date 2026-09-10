require([
    'splunkjs/mvc', '../app/splunk_detection_converter/converter_ui',
    '../app/splunk_detection_converter/converter_core', '../app/splunk_detection_converter/vendor/jszip.browser.min',
    '../app/splunk_detection_converter/converter_search', '../app/splunk_detection_converter/converter_profiles',
    'splunkjs/mvc/simplexml/ready!'
], function (mvc, UI, Core, JSZip, Search, Profiles) {
    'use strict';
    // Splunk supplies the logged-in session and CSRF handling. No admin token or credentials.
    var adapter = Search.create(mvc.createService({app: 'splunk_detection_converter'}), Profiles, Core);
    window.addEventListener('pagehide', adapter.dispose);
    UI.mount(document.getElementById('tde-converter'), adapter.request, Core, JSZip);
}, function (error) {
    var root = document.getElementById('tde-converter');
    if (root) {
        root.textContent = 'Detection Converter 1.0.1 could not load its scripts. Hard-refresh after deploying the complete app. Failed module: ' + ((error && error.requireModules) || ['unknown']).join(', ');
    }
});
