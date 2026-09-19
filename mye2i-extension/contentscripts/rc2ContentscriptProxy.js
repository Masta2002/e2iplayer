if (typeof browser !== 'undefined') { chrome = browser; }

function e2ilog(...args) {
    console.log("[MyE2i-DEBUG]", ...args);
    // Test-Build-Ergaenzung (2026-09-15): jede Log-Zeile zusaetzlich an den
    // noch offenen lokalen mye2iserver-Tab (e2it.html) weiterleiten, der
    // sie per XHR an mye2iserver.py schickt -> landet dort per stdout ->
    // printDBG() direkt im echten Box-Debug-Log (iptv.dbg), ohne dass man
    // die Browser-DevTools auf DIESEM (sich selbst schliessenden) Tab
    // offen halten muss.
    try {
        var msg = args.map(function (a) {
            return (typeof a === 'string') ? a : JSON.stringify(a);
        }).join(' ');
        chrome.runtime.sendMessage({action: "DEBUG_LOG", msg: msg});
    } catch (e) {}
}

function _E2iSendMsgToPage(from, payload, cb) {
    const id = Math.random().toString(36).slice(2);
    if (cb !== undefined)
    {
        function onResp(e) {
            if (e.source !== window)
                return;
            const m = e.data;
            if (!m || m.__MYE2I !== true || m.to !== 'TO_' + from  + '_RESPONSE' || m.id !== id)
                return;
            window.removeEventListener('message', onResp);
            cb && cb(m.response);
        }

        window.addEventListener('message', onResp);
    }

    window.postMessage({
        __MYE2I: true,
        to: 'TO_PAGE',
        from: 'FROM_' + from,
        id,
        payload
    }, '*');
}



function E2iSendMsgToPage(payload, cb) {
    _E2iSendMsgToPage("PROXY", payload, cb);
}

function E2iSendMsgToBackground(payload, cb) {
    chrome.runtime.sendMessage(payload, cb);
}


chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    e2ilog('MESSAGE IN PROXY chrome.runtime.onMessage.addListener(): ' + JSON.stringify(msg));

    if (msg.to === 'TO_PAGE' && msg.from === 'FROM_BACKGROUND' ) {
        _E2iSendMsgToPage('BACKGROUND', msg.payload, sendResponse)
    }

    if (msg.to === 'TO_PROXY' && msg.from === 'FROM_BACKGROUND' ) {
        E2iHandleMessage(msg.payload, sendResponse);
    }

    return true;
});


function E2iHandleMessage(msg, cb)
{
    e2ilog('MESSAGE IN PROXY E2iHandleMessage(): ' + JSON.stringify(msg));

    if (msg.action == 'CAPTCHA_RESPONSE')
    {
        let token = msg.response;
        let e2i_job = window.e2i_job;
  
        var response = {
            action: "SEND_RESPONSE",
            response: {
                token: token,
                callbackUrl: e2i_job.callbackUrl,
                captchaId: e2i_job.captchaId
            }
        };
            
        E2iSendMsgToBackground(response, (resp) => {
            E2iSendMsgToBackground({'action':'CLOSE_ME'}, (resp2) => {
                cb('OK');
            });
        });
    }
    if (msg.action == 'HTTP_STATUS')
    {
        HandleStatusCode(msg);
        cb('OK');
    }
}

function E2iSetupEventListener() {
    window.addEventListener('message', (e) => {
        if (e.source !== window)
            return;
        const msg = e.data;
        if (!msg || msg.__MYE2I !== true)
            return;

        if (msg.to === 'TO_BACKGROUND' && msg.from === 'FROM_PAGE' ) {

            chrome.runtime.sendMessage(msg.payload, (resp) => {
                window.postMessage({
                    __MYE2I: true,
                    from: 'FROM_BACKGROUND',
                    to: 'TO_PAGE_RESPONSE',
                    id: msg.id,
                    response: resp
                }, '*');
            });
        }

        if (msg.to === 'TO_PROXY' && msg.from === 'FROM_PAGE' ) {
            E2iHandleMessage(msg.payload, (resp) => {
                window.postMessage({
                    __MYE2I: true,
                    from: 'FROM_PROXY',
                    to: 'TO_PAGE_RESPONSE',
                    id: msg.id,
                    response: resp
                }, '*');
            });
        }

    });
}

function loadSolverTemplate(callback, error, templateUrl) {
    var xhr = new XMLHttpRequest();
    xhr.onload = function () {
        e2ilog(Date.now() + " | solver template loaded");
        if (callback !== undefined && typeof callback === "function") {
            callback(this.response);
        }
    };
    xhr.onerror = function () {
        e2ilog(Date.now() + " | failed to load solver template");
        if (error !== undefined && typeof error === "function") {
            error(this.response);
        }
    };
    xhr.open("GET", templateUrl === undefined ? chrome.runtime.getURL("./res/browser_solver_template.html") : templateUrl);
    xhr.responseType = "text";
    xhr.send();
}

function insertJSCode(jscode) {
    E2iSendMsgToPage({action: 'INSERT_JS_CODE', 'jscode':jscode}, (resp) => {
        e2ilog("INSERT_IS_CODE response: " + resp);
    });
}

function insertJSSrc(jssrc) {
    E2iSendMsgToPage({action: 'INSERT_JS_SRC', 'jssrc':jssrc}, (resp) => {
        e2ilog("INSERT_JS_SRC response: " + resp);
    });
}


var insertRc2ScriptIntoDOM = function (job) {
    e2ilog(Date.now() + " | inserting rc2 script into DOM for job " + JSON.stringify(job));
    var captchaContainer = document.getElementById("captchaContainer");
    var captchaClass = "g-recaptcha";
    if (job.siteKeyType === "h1") {
        captchaClass = "h-captcha";
    } else if (job.siteKeyType === "cf_re") {
        captchaClass = "cf-turnstile";
    }

    captchaContainer.innerHTML = "<div id=\"recaptcha_container\"><form action=\"\" method=\"post\"> <div class=\"placeholder\"> <div id=\"recaptcha_widget\"> \
            <form action=\"?\" method=\"POST\"> \
            <div class=\"" + captchaClass + "\" data-callback=\"onResponse\"></div> \
            </form></div>";

    captchaContainer.querySelector("." + captchaClass).setAttribute("data-sitekey", job.siteKey);
    if (job.siteKeyType === "INVISIBLE") {
        captchaContainer.querySelector("." + captchaClass).setAttribute("data-size", "invisible");
        captchaContainer.innerHTML += "<button class='invisible-captcha-button' id='submit' onclick='grecaptcha.execute();'>" + chrome.i18n.getMessage("button_i_am_no_robot")
            + "</button>";
    }
    
    insertJSCode(`
        const ids = ['captcha-response', 'g-recaptcha-response', 'h-captcha-response'];

        for (const id of ids) {
          const el = document.getElementById(id);
          if (!el) continue;

          const descriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
          if (!descriptor || !descriptor.set) continue;
            Object.defineProperty(el, 'value', {
              set(v) {
                if (v && v.trim() !== "") {
                    E2iSendMsgToProxy({ action: "CAPTCHA_RESPONSE", response:v }, (resp) => {
                        e2ilog("CAPTCHA_RESPONSE: " + resp);
                    });
                }
                descriptor.set.call(this, v);
              },
              get() {
                return descriptor.get.call(this);
              }
            });
        }
    `);



    var callbackUrl = "" + job.callbackUrl + "";
    if (job.siteKeyType === "INVISIBLE" && callbackUrl.includes("://") && callbackUrl.endsWith('/')) {
        insertJSCode('var onResponse = function (response) {\n' +
            '            document.getElementById(\'captcha-response\').value = response;\n' +
            '        }');

        insertJSCode('function onloadCallback() {\n' +
            'grecaptcha.ready(function(){ grecaptcha.execute(); });' +
        '};');

        insertJSSrc("https://www.google.com/recaptcha/api.js?onload=onloadCallback");

    } else if (job.siteKeyAction !== undefined && job.siteKeyAction !== "undefined") {
        captchaContainer.querySelector("." + captchaClass).setAttribute("data-size", "invisible");
        captchaContainer.innerHTML += "<button class='invisible-captcha-button'>" + chrome.i18n.getMessage("button_please_wait")
            + "</button>";


        insertJSCode('var onResponse = function (response) {\n' +
            '            document.getElementById(\'captcha-response\').value = response;\n' +
            '        }');

        insertJSCode('function onloadCallback() {\n' +
            'grecaptcha.ready(function() {\n' +
            '     grecaptcha.execute("' + job.siteKey + '", {action: "' + job.siteKeyAction + '"}).then(onResponse);\n' +
            '})\n;' +
        '};');

        insertJSSrc("https://www.google.com/recaptcha/api.js?onload=onloadCallback&render=" + job.siteKey);

    }
    else
    {
        insertJSCode(`var onResponse = function (response) {
                        document.getElementById('captcha-response').value = response;
                    }`);


        if (job.siteKeyType === "cf_re") {
            insertJSSrc("https://challenges.cloudflare.com/turnstile/v0/api.js?compat=recaptcha");
        }
        else if (job.siteKeyType === "h1") {
            insertJSSrc("https://hcaptcha.com/1/api.js");
        } else {
            insertJSSrc("https://www.google.com/recaptcha/api.js");
        }

    }
};

var insertHosterName = function (hosterName) {
    if (hosterName != null && hosterName != "" && hosterName != "undefined") {
        log.push(Date.now() + " | inserting hostername into DOM for job " + JSON.stringify(hosterName));
        var hosterNameContainer = document.getElementsByClassName("hosterName");
        for (var i = 0; i < hosterNameContainer.length; i++) {
            hosterNameContainer[i].textContent = hosterName.replace(/^(https?):\/\//, "");
        }
    } else {
        var shouldHideContainer = document.getElementsByClassName("hideIfNoHoster");
        for (var i = 0; i < shouldHideContainer.length; i++) {
            shouldHideContainer[i].style.visibility = "hidden";
        }
    }
};

function E2iClearDocument() {
    document.open();
    document.write("");
    document.close();

    // Remember that above clear all window context we need add listeners again
    E2iSetupEventListener();
}

var Params = function (url) {
    this.params = url.split("?")[1].split("&");
};

Params.prototype.get = function (name) {
    var ret;
    this.params.forEach(function (param) {
        if (param.indexOf(name + "=") !== -1) {
            var split = param.split("=");
            ret = split[1];
            return false;
        }
    });
    return ret;
};

var ParamsExt = function (url) {
    // FIX (2026-09-15): a Cloudflare "Managed Challenge" can complete via a
    // full page navigation to the plain target URL, which drops the
    // "#e2itXX_sep_..." fragment entirely - "".split("_sep_")[1] is then
    // undefined and the original code crashed here
    // ("Cannot read properties of undefined (reading 'split')") before any
    // of the callers' own fallback logic (e.g. the domain-from-hostname
    // fallback right below this constructor's call sites) ever got a
    // chance to run. Degrade to an empty param set instead of throwing -
    // every caller already tolerates missing individual params.
    try {
        this.params = (url || "").split("_sep_")[1].split("&");
    } catch (e) {
        this.params = [];
    }
};

ParamsExt.prototype.get = function (name) {
    var ret;
    this.params.forEach(function (param) {
        if (param.indexOf(name + "=") !== -1) {
            var split = param.split("=");
            ret = split[1];
            return false;
        }
    });
    return ret;
};


if (document.location.hash.startsWith("#e2itco")) {
    //E2iSetupEventListener();
    main_e2itco();

} else if (document.location.hash.startsWith("#e2itcf")) {
    //E2iSetupEventListener();
    main_e2itcf();

} else if (document.location.hash.startsWith("#e2itdbg")) {
    // Debug snapshot: only tell the background script to watch this tab -
    // it injects the probe (contentscripts/dbgProbe.js) after every finished
    // page load, so a Cloudflare redirect that drops this fragment does not
    // end the probe.
    E2iSendMsgToBackground({action: 'DBG_REGISTER', origin: document.location.origin}, function () {});

} else if (document.location.hash.startsWith("#e2i")) {
    E2iClearDocument();

    E2iSendMsgToBackground({action:'runMainScript'} , (resp) => {
        loadSolverTemplate(main_e2i);
    });
}


function main_e2i(template){
    document.body.innerHTML = template;

    var params = new Params(document.location.hash);
    var siteKey = decodeURIComponent(params.get("k"));
    var siteKeyType = decodeURIComponent(params.get("st"));
    var siteKeyAction = decodeURIComponent(params.get("a"));
    callbackUrl = decodeURIComponent(params.get("u"));
    var captchaId = decodeURIComponent(params.get("c"));
    var hoster = decodeURIComponent(params.get("h"));

    e2ilog(Date.now() + " | [params] sitekey: " + siteKey + " callbackUrl: " + callbackUrl + " captchaId: " + captchaId + " hoster: " + hoster);
    window.e2i_job = {
        siteKey: siteKey,
        siteKeyType: siteKeyType,
        siteKeyAction: siteKeyAction,
        callbackUrl: callbackUrl,
        captchaId: captchaId,
        hoster: hoster
    };
    insertRc2ScriptIntoDOM(window.e2i_job);
    insertHosterName(window.e2i_job.hoster);
}

function e2i_checkCookiesPre(resParams) {
    if (resParams.cookies.length === 0 || Array.isArray(window.e2i_all_cookies)) {
        if (resParams.cookies.length === 0) {
            e2ilog("MyE2i cookies is an empty array.");
        }
        else
        {
            function isEqual(a, b) {
              return JSON.stringify(a) === JSON.stringify(b);
            }

            /*
            window.e2i_all_cookies.push(
              ...resParams.cookies.filter(c =>
                !window.e2i_all_cookies.some(e => isEqual(e, c))
              )
            );
            */
            function isEqual(a, b) {
              return JSON.stringify(a) === JSON.stringify(b);
            }

            const allowed = new Set(window.e2i_cookie_names);

            window.e2i_all_cookies.push(
              ...resParams.cookies
                .filter(c => allowed.has(c.name))
                .filter(c =>
                  !window.e2i_all_cookies.some(e => isEqual(e, c))
                )
            );
        }

        
        let idx = resParams.idx;
        let cookieParams = {idx: idx+1, partition_key: {}, with_partition_key: false};
        if (window.e2i_cookie_names.length == 1) {
            cookieParams.name = window.e2i_cookie_names[0];
        }

        if (idx === 0 || idx === 2) {
            cookieParams.type = 'domain';

            let params = new ParamsExt(document.location.hash);
            let domain = decodeURIComponent(params.get("domain"));
            if (domain === undefined || domain + '' == 'undefined' || domain === null || domain === '') {
                let url = new URL(document.location.href);
                domain = url.hostname;
                let parts = domain.split('.');
                let baseDomain = parts.length > 2 ? parts.slice(-2).join('.') : domain;
                domain = '.' + baseDomain;
            }

            cookieParams.domain = domain;
            if (idx === 0) {
                cookieParams.with_partition_key = true;
            }

        } else if (idx === 1 || idx === 3) {
            cookieParams.type = 'url';
            cookieParams.url = document.location.href;

            if (idx === 1) {
                cookieParams.with_partition_key = true;
            }
        } else {
            let resCookies = [];
            if (Array.isArray(window.e2i_all_cookies)) {
                resCookies = window.e2i_all_cookies;
            } else {
                resCookies = resParams.cookies;
            }
            
            e2ilog("MyE2i cookies found2:", resCookies);
            e2i_checkCookies(resCookies);
            return;
        }

        e2ilog("MyE2i sending GET_COOKIE query:", JSON.stringify(cookieParams));
        chrome.runtime.sendMessage({
            action: "GET_COOKIE",
            data: cookieParams
        }, e2i_checkCookiesPre);

    } else {
        e2ilog("MyE2i cookies found:", resParams.cookies);
        e2i_checkCookies(resParams.cookies);
    }
}

function e2i_checkCookies(cookie) {
    let url = new URL(document.location.href);
    let domain = '.' + url.hostname;
    let result = {user_agent:navigator.userAgent,
                  cookie:cookie,
                  url:document.location.href,
                  domain:domain}
    e2ilog("MyE2i FINAL result being sent:", JSON.stringify(result));
    let params = new ParamsExt(document.location.hash);
    window.e2i_job = {callbackUrl: decodeURIComponent(params.get("u")),
                      captchaId: decodeURIComponent(params.get("c"))};
    let token = window.btoa(JSON.stringify(result));

    var response = {
        action: "SEND_RESPONSE",
        response: {
            token: token,
            callbackUrl: e2i_job.callbackUrl,
            captchaId: e2i_job.captchaId
        }
    };

    E2iSendMsgToBackground(response, (resp) => {
        E2iSendMsgToBackground({'action':'CLOSE_ME'}, (resp2) => {
            cb('OK');
        });
    });
}
    
function main_e2itcf(){
    window.e2i_cookie_names = ['cf_clearance'];

    // FIX (2026-09-15): the previous implementation decided "challenge is
    // done" on the very first readystatechange event where #challenge-form
    // happened to be absent, using a one-shot "_kanikulye2ikaramba" flag
    // that (a) could fire true before Cloudflare had even inserted its
    // challenge-form/link/script markers into the DOM yet (race on fast
    // "Managed Challenge" pages -> false "done" with an empty/invalid
    // cf_clearance cookie sent back immediately), and (b) relied entirely
    // on readystatechange firing again later, which it does NOT do for an
    // in-place DOM removal of the challenge widget without a full page
    // navigation. Rewritten to only ever conclude "done" once
    // document.readyState is "complete" (real content, not a half-parsed
    // shell), to check ALL <link>/<script> tags (not just index 0) plus a
    // document.title fallback ("Just a moment...") as extra markers, and
    // to also watch for in-place DOM mutations via MutationObserver so a
    // challenge widget removed without a full reload is still detected.
    var e2i_cfDone = false;

    function e2i_looksLikeChallengePage() {
        try {
            if (document.getElementById("challenge-form")) return true;
        } catch (e) {}
        try {
            var links = document.getElementsByTagName("link");
            for (var i = 0; i < links.length; i++) {
                var href = links[i].getAttribute("href");
                if (href && href.includes('/challenges')) return true;
            }
        } catch (e) {}
        try {
            var scripts = document.getElementsByTagName('script');
            for (var j = 0; j < scripts.length; j++) {
                if (scripts[j].text && scripts[j].text.includes("window._cf_chl_opt")) return true;
            }
        } catch (e) {}
        try {
            if (document.title && document.title.indexOf("Just a moment") !== -1) return true;
        } catch (e) {}
        return false;
    }

    function e2i_reportChallengeDoneIfReady() {
        if (e2i_cfDone) return;
        if (document.readyState !== "complete") return;
        if (!document.body) return;
        if (e2i_looksLikeChallengePage()) return;

        e2i_cfDone = true;
        try { document.removeEventListener('readystatechange', e2i_reportChallengeDoneIfReady); } catch (e) {}
        try { e2i_cfObserver.disconnect(); } catch (e) {}

        document.open();
        document.write("");
        document.close();

        e2i_checkCookiesPre({cookies:[], idx:0});
    }

    document.addEventListener('readystatechange', e2i_reportChallengeDoneIfReady);

    var e2i_cfObserver = new MutationObserver(function () {
        e2i_reportChallengeDoneIfReady();
    });
    try {
        e2i_cfObserver.observe(document.documentElement || document, {childList: true, subtree: true});
    } catch (e) {}

    // covers the case where this script runs after the document already
    // finished loading (readystatechange for "complete" already fired)
    e2i_reportChallengeDoneIfReady();
}

function HandleStatusCode(data)
{
    if (data.url.includes("#e2itco") && data.status == 200)
    {
        if (!window.e2i_challenge_id || document.getElementById(window.e2i_challenge_id) == null)
        {
            document.open();
            document.write("");
            document.close();
            e2i_checkCookiesPre({cookies:[], idx:0});
        }
    }
}

function main_e2itco()
{
    let params = new ParamsExt(document.location.hash);
    let cn = decodeURIComponent(params.get("cn"));
    let ceid = params.get("ceid");
    if (ceid)
    {
        window.e2i_challenge_id = decodeURIComponent(ceid);
    }

    window.e2i_all_cookies = []; //;
    window.e2i_cookie_names = JSON.parse(window.atob(cn));
    
    
    
    function e2i_checkChallengeForm(event) {
        if (document.readyState == "complete")
        {
            E2iSendMsgToBackground({
                action: 'PROXY_READY'
            }, (resp2) => {
                //
            });
        }
    }
    document.addEventListener('readystatechange', e2i_checkChallengeForm);
}