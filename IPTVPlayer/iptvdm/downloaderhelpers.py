# -*- coding: utf-8 -*-
# IPTV download manager API
# # added: 07.08.2026 - Shared helpers for Downloader: Py2/Py3 safe text & path handling, shell quoting, and the sidecar, (.txt description + .jpg poster). - Kamikaze24
###################################################
# LOCAL import
###################################################
from Plugins.Extensions.IPTVPlayer.tools.iptvtools import printDBG, printExc, eConnectCallback, GetNice, E2PrioFix
###################################################
# FOREIGN import
###################################################
from Tools.BoundFunction import boundFunction
from enigma import eConsoleAppContainer
import os
###################################################

try:
    text_type = unicode
    binary_type = str
    string_types = (basestring,)
except NameError:
    text_type = str
    binary_type = bytes
    string_types = (str, bytes)


def ensureText(data, encoding='utf-8'):
    if data is None:
        return u''

    if isinstance(data, text_type):
        return data

    if isinstance(data, binary_type):
        try:
            return data.decode(encoding)
        except Exception:
            try:
                return data.decode(encoding, 'replace')
            except Exception:
                try:
                    return data.decode('latin-1', 'replace')
                except Exception:
                    return u''

    try:
        return text_type(data)
    except Exception:
        try:
            return text_type(str(data))
        except Exception:
            return u''


def fsPath(path):
    path = ensureText(path)
    try:
        if text_type is not str:
            return path.encode('utf-8')
    except Exception:
        pass
    return path


def shellQuote(value):
    value = ensureText(value)
    value = value.replace('\\', '\\\\')
    value = value.replace('"', '\\"')
    value = value.replace('`', '\\`')
    value = value.replace('$', '\\$')
    return value


def writeUtf8TextFile(path, data):
    try:
        txt = ensureText(data)
        f = open(fsPath(path), 'wb')
        try:
            f.write(txt.encode('utf-8'))
        finally:
            f.close()
        return True
    except Exception:
        printExc()
        return False


class SidecarMixin(object):
    """
    Shared .txt / .jpg sidecar handling plus the generic "finish download"
    flow, used identically by WgetDownloader, HLSDownloader and
    MergeDownloader.

    The including class must also inherit from BaseDownloader (for
    self.filePath, self.onFinish()) and must implement self._cleanUp()
    itself, since temp-file cleanup differs per downloader.

    Usage in each downloader's __init__:
        self._initSidecarState()

    Usage in each downloader's _terminate():
        self._terminateSidecar()
    """

    def _initSidecarState(self):
        self.sidecarConsole = None
        self.sidecarConsole_appClosed_conn = None
        self.sidecarConsole_stderrAvail_conn = None
        self.sidecarEnabled = False
        self.sidecarTxt = ''
        self.sidecarImg = ''
        self.waitingForSidecar = False

    def _clearSidecarData(self):
        self.sidecarEnabled = False
        self.sidecarTxt = ''
        self.sidecarImg = ''
        self.waitingForSidecar = False

    def _prepareSidecarData(self, meta):
        self._clearSidecarData()
        try:
            if meta.get('e2i_sidecar_enabled', False):
                self.sidecarEnabled = True
                self.sidecarTxt = meta.get('e2i_sidecar_txt', '')
                self.sidecarImg = meta.get('e2i_sidecar_img', '')
                printDBG("%s sidecar enabled" % self.__class__.__name__)
        except Exception:
            printExc()

    def _writeTxtSidecar(self, filePath):
        try:
            if not self.sidecarTxt:
                printDBG("%s sidecar TXT skipped: empty content" % self.__class__.__name__)
                return

            basePath = ensureText(filePath).rsplit('.', 1)[0]
            txtPath = basePath + '.txt'

            if os.path.isfile(fsPath(txtPath)):
                printDBG("%s sidecar TXT already exists [%s]" % (self.__class__.__name__, txtPath))
                return

            if writeUtf8TextFile(txtPath, self.sidecarTxt):
                printDBG("%s sidecar TXT saved [%s]" % (self.__class__.__name__, txtPath))
            else:
                printDBG("%s sidecar TXT save failed [%s]" % (self.__class__.__name__, txtPath))
        except Exception:
            printExc("%s sidecar TXT save failed" % self.__class__.__name__)

    def _imgSidecarDataAvail(self, data):
        return

    def _imgSidecarFinished(self, jpgPath, code):
        printDBG("%s._imgSidecarFinished code[%r]" % (self.__class__.__name__, code))

        try:
            # break circular references
            self.sidecarConsole_appClosed_conn = None
            self.sidecarConsole_stderrAvail_conn = None
            self.sidecarConsole = None
            self.waitingForSidecar = False

            if os.path.isfile(fsPath(jpgPath)):
                printDBG("%s sidecar JPG saved [%s]" % (self.__class__.__name__, jpgPath))
            else:
                printDBG("%s sidecar JPG failed [%s]" % (self.__class__.__name__, jpgPath))
        except Exception:
            printExc()

        self._finishDownloadFlow()

    def _startImgSidecarDownload(self, filePath):
        try:
            if not self.sidecarImg:
                printDBG("%s sidecar JPG skipped: empty URL" % self.__class__.__name__)
                self._finishDownloadFlow()
                return

            basePath = ensureText(filePath).rsplit('.', 1)[0]
            jpgPath = basePath + '.jpg'

            if os.path.isfile(fsPath(jpgPath)):
                printDBG("%s sidecar JPG already exists [%s]" % (self.__class__.__name__, jpgPath))
                self._finishDownloadFlow()
                return

            cmd = 'wget --header "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36" --no-check-certificate "%s" -O "%s" > /dev/null 2>&1' % (shellQuote(self.sidecarImg), shellQuote(jpgPath))
            printDBG("%s sidecar JPG cmd[%s]" % (self.__class__.__name__, cmd))

            self.waitingForSidecar = True
            self.sidecarConsole = eConsoleAppContainer()
            self.sidecarConsole_appClosed_conn = eConnectCallback(self.sidecarConsole.appClosed, boundFunction(self._imgSidecarFinished, jpgPath))
            self.sidecarConsole_stderrAvail_conn = eConnectCallback(self.sidecarConsole.stderrAvail, self._imgSidecarDataAvail)
            if hasattr(self.sidecarConsole, "setNice"):
                self.sidecarConsole.setNice(GetNice() + 2)
                self.sidecarConsole.execute(cmd)
            else:
                self.sidecarConsole.execute(E2PrioFix(cmd))
        except Exception:
            printExc("%s sidecar JPG start failed" % self.__class__.__name__)
            self._finishDownloadFlow()

    def _terminateSidecar(self):
        # Call from each downloader's _terminate() to kill an in-flight
        # sidecar JPG download and avoid leaving a zombie process behind.
        if self.sidecarConsole is not None:
            try:
                if hasattr(self.sidecarConsole, "sendCtrlC"):
                    self.sidecarConsole.sendCtrlC()
                elif hasattr(self.sidecarConsole, "kill"):
                    self.sidecarConsole.kill()
            except Exception:
                printExc()
            self.sidecarConsole = None
            self.sidecarConsole_appClosed_conn = None
            self.sidecarConsole_stderrAvail_conn = None

    def _finishDownloadFlow(self):
        # Generic finish-flow used by all three downloaders. Relies on
        # self._cleanUp() being implemented by the downloader subclass
        # (temp-file cleanup differs per downloader).
        try:
            self.onFinish()
        except Exception:
            printExc()
        self._cleanUp()
