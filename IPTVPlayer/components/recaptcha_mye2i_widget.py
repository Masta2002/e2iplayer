# -*- coding: utf-8 -*-
#

###################################################
# LOCAL import
###################################################
from Plugins.Extensions.IPTVPlayer.tools.iptvtools import printDBG, printExc, rm, GetTmpDir, GetPyScriptCmd, getDebugMode, get_ip, is_port_in_use, eConnectCallback
from Plugins.Extensions.IPTVPlayer.components.iptvplayerinit import TranslateTXT as _
from Plugins.Extensions.IPTVPlayer.components.captchascriptwidget import CaptchaScriptWidgetBase
from Plugins.Extensions.IPTVPlayer.libs.web_qr import make_qr_png
###################################################

###################################################
# FOREIGN import
###################################################
from enigma import eConsoleAppContainer
from Components.Pixmap import Pixmap
from Tools.LoadPixmap import LoadPixmap

from Plugins.Extensions.IPTVPlayer.p2p3.manipulateStrings import ensure_str, ensure_binary

try:
    import json
except Exception:
    import simplejson as json
import re
import base64
###################################################

# HD-reference width the QR pixmap strip adds next to the shared console box,
# and the square QR pixmap's own size within that strip - kept equal to the
# console's own height (see `_prepareSkin`'s HEIGHT - 142) so it lines up
# with the console box instead of reaching down into the footer below it.
_QR_STRIP_WIDTH = 220
_QR_SIZE = 178


class UnCaptchaReCaptchaMyE2iWidget(CaptchaScriptWidgetBase):
    # the chrome/skin building, eConsoleAppContainer wiring, and
    # stdout/stderr scaffolding are shared with the near-identical
    # `UnCaptchaReCaptchaMyJDWidget` via `CaptchaScriptWidgetBase`. Only
    # the genuinely MyE2i-specific bits remain here:
    # `ip_address`/`port` bookkeeping, the exact `mye2iserver` command,
    # the regex-based JSON-substring extraction its script's log output
    # actually needs (unlike MyJD's plain `byteify(json.loads())`), and a
    # QR code of the local URL the script prints, so it can be scanned with
    # a phone instead of typed in by hand.
    ACTION_CONTEXTS = ["ColorActions", "OkCancelActions"]

    def __init__(self, session, title, sitekey, referer, captchaType):
        # scale="1" is required here - without it Enigma2 draws the loaded
        # pixmap at its native size (see make_qr_png()'s own `scale` factor,
        # much bigger than this box) instead of fitting it into the widget.
        qrWidget = '<widget name="qrcode" position="%d,68" size="%d,%d" zPosition="2" scale="1" alphatest="blend" transparent="1" />' % (500 + (_QR_STRIP_WIDTH - _QR_SIZE) // 2, _QR_SIZE, _QR_SIZE)
        self.skin = CaptchaScriptWidgetBase._prepareSkin(self, extraWidth=_QR_STRIP_WIDTH, extraBody=qrWidget)
        CaptchaScriptWidgetBase.__init__(self, session, title, sitekey, referer, captchaType)
        self["qrcode"] = Pixmap()
        self["qrcode"].hide()  # shown once startExecution() has an image to put in it
        self.ip_address = get_ip()
        self.port = 9001
        self._qrPath = GetTmpDir("mye2i_web_access_qr.png")
        self.onClose.append(self._removeQrFile)

    def _scriptFinishedMsg(self):
        return _('MyE2i script finished.')

    def _scriptFailedMsg(self, code):
        return _("MyE2i script execution failed.\nError code: %s\n") % (code)

    def _parseJsonLine(self, line):
        matches = re.findall("{.*}", line)
        if not matches:
            return None
        return json.loads(matches[0])

    def _removeQrFile(self):
        rm(self._qrPath)

    def _scriptStderrAvail(self, data):
        hadResult = bool(self.result)
        CaptchaScriptWidgetBase._scriptStderrAvail(self, data)
        if not hadResult and self.result:
            # captcha just got solved - the QR code (and the file behind it)
            # served its purpose, drop both instead of leaving them lying around.
            self["qrcode"].hide()
            self._removeQrFile()

    def startExecution(self):
        captcha = {'siteKey': self.sitekey, 'sameOrigin': True, 'siteUrl': self.referer, 'contextUrl': '/'.join(self.referer.split('/')[:3]), 'boundToDomain': True, 'stoken': None, 'captchaType': self.captchaType}
        try:
            captcha = ensure_str(base64.b64encode(ensure_binary(json.dumps(captcha))))
        except Exception:
            printExc()

        if getDebugMode() == '':
            debug = 0
        else:
            debug = 1

        while is_port_in_use(self.ip_address, self.port):
            self.port += 1

        cmd = GetPyScriptCmd('mye2iserver') + ' "%s" "%s" "%s"' % (captcha, self.ip_address, self.port)

        try:
            # scale=10 -> a 370x370 native PNG, comfortably above the qrcode
            # widget's box even at WQHD (_QR_SIZE=178 HD-reference * 2.0 =
            # 356px there) so Enigma2's scale="1" only ever downscales it,
            # never blows it up past its native resolution.
            make_qr_png("http://%s:%s" % (self.ip_address, self.port), self._qrPath, scale=10, border=4)  # NOSONAR - LAN-only mye2iserver.py has no TLS support
            self["qrcode"].instance.setPixmap(LoadPixmap(self._qrPath))
            self["qrcode"].show()
        except Exception:
            printExc()

        self["console"].setText(_('Please Open site:\nhttp://{0}:{1}\nin a web browser with the MyE2i extension installed').format(self.ip_address, self.port))

        self.workconsole['console'] = eConsoleAppContainer()
        self.workconsole['close_conn'] = eConnectCallback(self.workconsole['console'].appClosed, self._scriptClosed)
        self.workconsole['stderr_conn'] = eConnectCallback(self.workconsole['console'].stderrAvail, self._scriptStderrAvail)
        self.workconsole['stdout_conn'] = eConnectCallback(self.workconsole['console'].stdoutAvail, self._scriptStdoutAvail)
        self.workconsole["console"].execute(cmd)
        printDBG(">>> EXEC CMD [%s]" % cmd)
