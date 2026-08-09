# -*- coding: utf-8 -*-
"""
Dedicated setup screen for AI Live Subtitles.
"""
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.config import config, getConfigListEntry, ConfigPassword
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

# ensure config keys exist
try:
    from Plugins.Extensions.IPTVPlayer.tools.ailivesubtitles.config import *
except Exception:
    pass


class AILiveSubtitlesSetup(ConfigListScreen, Screen):
    skin = """
    <screen name="AILiveSubtitlesSetup" position="center,center" size="920,560" title="AI Live Subtitles">
        <widget name="config" position="15,15" size="890,460" scrollbarMode="showOnDemand" />
        <widget source="key_red" render="Label" position="15,500" size="200,40" font="Regular;22" halign="center" valign="center" backgroundColor="#9f1313" />
        <widget source="key_green" render="Label" position="230,500" size="200,40" font="Regular;22" halign="center" valign="center" backgroundColor="#1f771f" />
        <widget source="key_yellow" render="Label" position="445,500" size="220,40" font="Regular;22" halign="center" valign="center" backgroundColor="#a08500" />
        <widget name="footnote" position="680,500" size="220,40" font="Regular;18" halign="center" valign="center" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.skinName = ["AILiveSubtitlesSetup", "Setup"]
        self.setTitle(_("AI Live Subtitles Setup"))

        self["key_red"] = StaticText(_("Cancel"))
        self["key_green"] = StaticText(_("Save"))
        self["key_yellow"] = StaticText(_("Default"))
        self["footnote"] = Label(_("Yellow = defaults"))

        self.list = []
        ConfigListScreen.__init__(self, self.list, session=session, on_change=self._changed)
        self._build()

        self["actions"] = ActionMap(
            ["SetupActions", "ColorActions"],
            {
                "cancel": self.keyCancel,
                "red": self.keyCancel,
                "green": self.keySave,
                "ok": self.keySave,
                "yellow": self.keyDefaults,
            },
            -2,
        )

    def _build(self):
        self.list = []
        c = config.plugins.iptvplayer.ailivesubs
        self.list.append(getConfigListEntry(_("----- General -----"),))
        self.list.append(getConfigListEntry(_("Enable AI Live Subtitles"), c.enabled))
        self.list.append(getConfigListEntry(_("AI Provider"), c.provider))
        self.list.append(getConfigListEntry(_("Groq API Key"), c.api_key_groq))
        try:
            self.list.append(getConfigListEntry(_("Gemini API Key"), c.api_key_gemini))
        except Exception:
            pass
        self.list.append(getConfigListEntry(_("Target language"), c.target_lang))
        self.list.append(getConfigListEntry(_("Audio chunk duration"), c.chunk))

        self.list.append(getConfigListEntry(_("----- Appearance -----"),))
        self.list.append(getConfigListEntry(_("Subtitle position"), c.position))
        self.list.append(getConfigListEntry(_("Subtitle font"), c.font_name))
        self.list.append(getConfigListEntry(_("Subtitle font size"), c.font_size))
        self.list.append(getConfigListEntry(_("Subtitle font color"), c.font_color))
        self.list.append(getConfigListEntry(_("Subtitle border / strip enabled"), c.border_enabled))
        self.list.append(getConfigListEntry(_("Subtitle border color"), c.border_color))

        self["config"].list = self.list
        self["config"].l.setList(self.list)

    def _changed(self):
        pass

    def keyDefaults(self):
        try:
            c = config.plugins.iptvplayer.ailivesubs
            c.enabled.value = False
            c.provider.value = "groq"
            c.target_lang.value = "ar"
            c.chunk.value = "3"
            c.position.value = "bottom"
            c.font_name.value = "Regular"
            c.font_size.value = 36
            c.font_color.value = "#FFFFFF"
            c.border_enabled.value = True
            c.border_color.value = "#000000"
            self._build()
            self.session.open(MessageBox, _("Defaults restored (not saved yet).\nPress Green to save."), MessageBox.TYPE_INFO, timeout=3)
        except Exception as e:
            self.session.open(MessageBox, str(e), MessageBox.TYPE_ERROR, timeout=4)

    def keySave(self):
        try:
            for x in self["config"].list:
                if len(x) > 1:
                    x[1].save()
            # persist
            try:
                from Components.config import configfile
                configfile.save()
            except Exception:
                pass
            self.close(True)
        except Exception as e:
            self.session.open(MessageBox, _("Save failed: %s") % str(e), MessageBox.TYPE_ERROR, timeout=4)

    def keyCancel(self):
        for x in self["config"].list:
            try:
                if len(x) > 1:
                    x[1].cancel()
            except Exception:
                pass
        self.close(False)
