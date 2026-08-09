# -*- coding: utf-8 -*-
"""
AISubtitlesUI
- Subtitle border enabled = Yes  → dark strip (aiSubBg) behind text
- Subtitle border enabled = No   → text only, NO strip at all
"""
from Components.config import config
from enigma import gFont, ePoint, eSize, getDesktop, gRGB
from skin import parseColor

class AISubtitlesUI(object):
    def __init__(self, player):
        self.player = player
        self.active = True
        self._layout = {}
        self._apply_style()

    def _cfg(self, name, default):
        try:
            return getattr(config.plugins.iptvplayer.ailivesubs, name).value
        except Exception:
            return default

    def _border_on(self):
        """True only when user explicitly enabled the strip/border."""
        try:
            v = config.plugins.iptvplayer.ailivesubs.border_enabled.value
        except Exception:
            v = False
        # ConfigYesNo returns bool; be defensive for string leftovers
        if v is True or v == 1 or v == "1" or str(v).lower() in ("true", "yes", "on"):
            return True
        return False

    def _nuke(self, name):
        try:
            w = self.player[name]
        except Exception:
            return
        try:
            w.setText("")
        except Exception:
            pass
        try:
            w.instance.setBackgroundColor(parseColor("#00000000"))
        except Exception:
            pass
        try:
            w.instance.setBorderWidth(0)
        except Exception:
            pass
        try:
            w.instance.setShadowOffset(ePoint(0, 0))
            w.instance.setShadowColor(gRGB())
        except Exception:
            pass
        try:
            w.move(ePoint(-2000, -2000))
            w.instance.move(ePoint(-2000, -2000))
            w.resize(eSize(1, 1))
            w.instance.resize(eSize(1, 1))
        except Exception:
            pass
        try:
            w.hide()
        except Exception:
            pass

    def _place(self, name, x, y, w, h):
        self._layout[name] = (x, y, w, h)
        try:
            widget = self.player[name]
            widget.move(ePoint(x, y))
            widget.instance.move(ePoint(x, y))
            widget.resize(eSize(w, h))
            widget.instance.resize(eSize(w, h))
        except Exception:
            pass

    def _hide_strip(self):
        """Always remove background strip completely."""
        self._nuke("aiSubBg")
        # also clear any bg on the text label itself
        try:
            su = self.player["aiSubtitles"]
            su.instance.setBackgroundColor(parseColor("#00000000"))
            su.instance.setBorderWidth(0)
            su.instance.setShadowOffset(ePoint(0, 0))
            su.instance.setShadowColor(gRGB())
        except Exception:
            pass

    def _apply_style(self):
        font_name = self._cfg("font_name", "Regular")
        try:
            font_size = int(self._cfg("font_size", 36))
        except Exception:
            font_size = 36
        font_color = self._cfg("font_color", "#FFFFFF")
        pos = self._cfg("position", "bottom")

        if isinstance(font_name, str) and font_name.endswith(";Bold"):
            face = "Regular"
        elif isinstance(font_name, str) and ";" in font_name:
            face = font_name.split(";")[0]
        else:
            face = font_name or "Regular"

        dw = getDesktop(0).size().width()
        dh = getDesktop(0).size().height()
        box_h = max(110, int(font_size * 3.0))
        if pos == "top":
            status_y, sub_y = 16, 48
        else:
            status_y = dh - box_h - 48
            sub_y = dh - box_h - 12

        try:
            st = self.player["aiStatus"]
            st.instance.setFont(gFont("Regular", 20))
            st.instance.setForegroundColor(parseColor("#FFFF00"))
            try:
                st.instance.setBackgroundColor(parseColor("#00000000"))
            except Exception:
                pass
            self._place("aiStatus", 20, status_y, dw - 40, 28)
            st.hide()

            su = self.player["aiSubtitles"]
            su.instance.setFont(gFont(face, font_size))
            su.instance.setForegroundColor(parseColor(font_color))
            try:
                su.instance.setBackgroundColor(parseColor("#00000000"))
            except Exception:
                pass
            try:
                su.instance.setBorderWidth(0)
            except Exception:
                pass
            self._place("aiSubtitles", 20, sub_y, dw - 40, box_h)
            su.hide()

            # Prepare strip geometry but keep it hidden until border=Yes + text
            try:
                bg = self.player["aiSubBg"]
                try:
                    bg.instance.setFont(gFont("Regular", 1))
                except Exception:
                    pass
                self._place("aiSubBg", 0, sub_y, dw, box_h)
            except Exception:
                pass
            self._hide_strip()
        except Exception:
            pass

    def setStatus(self, text):
        if not self.active:
            return
        try:
            w = self.player["aiStatus"]
            t = str(text) if text else ""
            if t:
                g = self._layout.get("aiStatus")
                if g:
                    self._place("aiStatus", *g)
                w.setText(t)
                w.show()
            else:
                w.setText("")
                w.hide()
        except Exception:
            pass

    def setSubtitle(self, text):
        if not self.active:
            return
        try:
            su = self.player["aiSubtitles"]
            t = str(text) if text else ""
            if not t:
                self._nuke("aiSubtitles")
                self._hide_strip()
                return

            g = self._layout.get("aiSubtitles")
            if g:
                self._place("aiSubtitles", *g)
            su.setText(t)
            try:
                su.instance.setBackgroundColor(parseColor("#00000000"))
            except Exception:
                pass
            try:
                su.instance.setBorderWidth(0)
            except Exception:
                pass
            try:
                su.instance.setShadowOffset(ePoint(0, 0))
                su.instance.setShadowColor(gRGB())
            except Exception:
                pass
            su.show()

            # Strip ONLY if setting is Yes
            if self._border_on():
                try:
                    bg = self.player["aiSubBg"]
                    gb = self._layout.get("aiSubBg")
                    if gb:
                        self._place("aiSubBg", *gb)
                    try:
                        bg.instance.setBackgroundColor(parseColor("#B0000000"))
                    except Exception:
                        try:
                            bg.instance.setBackgroundColor(parseColor("#000000"))
                        except Exception:
                            pass
                    bg.setText(" ")
                    bg.show()
                except Exception:
                    pass
                # optional outline on text
                try:
                    bc = self._cfg("border_color", "#000000")
                    su.instance.setBorderColor(parseColor(bc))
                    su.instance.setBorderWidth(2)
                    su.instance.setShadowColor(parseColor(bc))
                    su.instance.setShadowOffset(ePoint(2, 2))
                except Exception:
                    pass
            else:
                # Setting = No → must not leave any strip
                self._hide_strip()
        except Exception:
            pass

    def clear(self):
        self.active = False
        self._hide_strip()
        for name in ("aiStatus", "aiSubtitles", "aiSubBg"):
            self._nuke(name)

    def reactivate(self):
        self.active = True
        self._apply_style()
        # Respect current setting immediately
        if not self._border_on():
            self._hide_strip()

class AISubtitlesOverlay(AISubtitlesUI):
    def __init__(self, session_or_player):
        AISubtitlesUI.__init__(self, session_or_player)
