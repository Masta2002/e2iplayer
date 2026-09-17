'use strict';

if (typeof browser !== 'undefined') { chrome = browser; }

function e2ilog(txt) {
    console.log("[MyE2i-DEBUG e2it]", txt);
}

// Test-Build-Ergaenzung (2026-09-15): meldet die eigene Version sofort
// an mye2iserver.py, damit dessen neuer Versions-Check greift und bei zu
// alter Erweiterung direkt einen Hinweis auf dem Box-Bildschirm zeigt.
(function reportExtensionVersion() {
    try {
        var v = chrome.runtime.getManifest().version;
        var u = window.location;
        var xhr = new XMLHttpRequest();
        xhr.open("GET", u.protocol + "//" + u.host + "/version?v=" + encodeURIComponent(v));
        xhr.send();
    } catch (e) {}
})();

chrome.runtime.onMessage.addListener(
    function (request, sender, sendResponse) {
        try {
            if (request.action === "DEBUG_LOG") {
                // Test-Build-Ergaenzung (2026-09-15): Debug-Zeile aus dem
                // Challenge-Tab (per background.js weitergeleitet) an
                // mye2iserver.py schicken, damit sie ueber printDBG() im
                // echten Box-Debug-Log (iptv.dbg) landet.
                var dbgXhr = new XMLHttpRequest();
                var dbgUrl = window.location;
                dbgXhr.open("GET", dbgUrl.protocol + "//" + dbgUrl.host + "/debug?msg=" + encodeURIComponent('' + request.msg));
                dbgXhr.responseType = "text";
                dbgXhr.onload = function () { sendResponse('OK'); };
                dbgXhr.onerror = function () { sendResponse('ERR'); };
                dbgXhr.send();
                return;
            }

            if (request.action === "SEND_RESPONSE" && request.data && request.data.token && request.data.captchaId) {
                var xhr = new XMLHttpRequest();
                var getUrl = window.location;
                var responseUrl = getUrl.protocol + "//" + getUrl.host + "/response?" + "c=" + request.data.captchaId + "&token=" + request.data.token;
                xhr.open("GET", responseUrl);
                xhr.responseType = "text";

                xhr.onload = function () {
                    e2ilog(Date.now() + " | response send OK");
                    tryCloseTabIfElementExists();
                    
                    //showError('' + "DUPA");
                    sendResponse('OK');
                };

                xhr.onerror = function () {
                    console.log(Date.now() + " | response send FAILED");
                    showError('' + xhr.status);
                    sendResponse('ERR');
                };

                xhr.send();

            }
        } catch (e) {
            showError('' + e);
        }
    }
);

function showError(sts) {
    var elem = document.querySelector("[id^='mye2i_1']");
    if (elem) {
        elem.style.display = "block";
        elem.innerHTML = "<strong>Error occurs: " + sts + "</strong>"
    }
}

function tryCloseTabIfElementExists() {
    if (document.querySelector("#e2i-close-on-success")) {
        chrome.runtime.sendMessage({'action':'CLOSE_ME'});
    }
}

function compareVersions(v1, v2) {
  const a1 = v1.split('.').map(Number);
  const a2 = v2.split('.').map(Number);
  for (let i = 0; i < Math.max(a1.length, a2.length); i++) {
    const n1 = a1[i] || 0;
    const n2 = a2[i] || 0;
    if (n1 > n2) return 1;
    if (n1 < n2) return -1;
  }
  return 0;
}


function e2i_checkBanner(event) {
    var elem = document.querySelector("[id^='mye2i_1']");
    if (elem) {
        var currentVersion = chrome.runtime.getManifest().version;
        var expectedVersion = elem.id.replace("mye2i_", ""); 
        
        if (compareVersions(currentVersion, expectedVersion) >= 0) {
            elem.style.display = "none";
        }
    }
}

document.addEventListener('readystatechange', e2i_checkBanner);

// Test-Build-Ergaenzung (2026-09-15): zeigt immer die aktuell installierte
// Erweiterungs-Version oben rechts an, damit man beim Testen sofort sieht,
// ob der Browser wirklich die neue (gepatchte) Version geladen hat, statt
// noch die alte 1.17 im Hintergrund zu benutzen.
function e2i_showExtensionVersion() {
    try {
        if (!document.body) return;
        if (document.getElementById('mye2i-version-badge')) return;
        var badge = document.createElement('div');
        badge.id = 'mye2i-version-badge';
        badge.style.cssText = 'position:fixed;top:8px;right:8px;background:#222;color:#fff;padding:6px 12px;border-radius:8px;font-family:sans-serif;font-size:14px;z-index:2147483647;box-shadow:0 2px 6px rgba(0,0,0,0.4);';
        badge.textContent = 'MyE2i Extension v' + chrome.runtime.getManifest().version;
        document.body.appendChild(badge);
    } catch (e) {}
}

document.addEventListener('readystatechange', function () {
    if (document.readyState !== 'loading') {
        e2i_showExtensionVersion();
    }
});

