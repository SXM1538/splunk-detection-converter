require([
    "jquery", "splunkjs/mvc", "../app/tde_detection_converter/converter_ui",
    "../app/tde_detection_converter/converter_core", "../app/tde_detection_converter/vendor/jszip.min",
    "splunkjs/mvc/simplexml/ready!"
], function ($, mvc, UI, Core, JSZip) {
    "use strict";
    var service = mvc.createService({owner: "nobody", app: "tde_detection_converter"});
    function request(payload) {
        return new Promise(function (resolve, reject) {
            var timeout = window.setTimeout(function () { reject(new Error("Splunk request timed out after 90 seconds. The affected selections will be recorded as failures.")); }, 90000);
            // SDK SplunkWebHttp supplies session/CSRF handling and proxy-prefix support.
            service.post("/services/tde_detection_converter", {payload: JSON.stringify(payload), output_mode: "json"}, function (error, response) {
                window.clearTimeout(timeout);
                if (error) { reject(new Error("Splunk request failed. Check your session, app installation and permissions.")); return; }
                try {
                    var data = response.data;
                    if (typeof data === "string") { data = JSON.parse(data); }
                    if (data && data.error) { throw new Error(data.error); }
                    resolve(data);
                } catch (e) { reject(e); }
            });
        });
    }
    UI.mount(document.getElementById("tde-converter"), request, Core, JSZip);
});
