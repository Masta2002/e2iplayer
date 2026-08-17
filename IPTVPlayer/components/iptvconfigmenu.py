# -*- coding: utf-8 -*-
#
#  Konfigurator dla iptv 2013
#  autorzy: j00zek, samsamsam
#

###################################################
# LOCAL import
###################################################

from Plugins.Extensions.IPTVPlayer.tools.iptvtools import printDBG, printExc, GetSkinsList, GetHostsList, GetEnabledHostsList, \
                                                          IsExecutable, CFakeMoviePlayerOption, GetCookieDir, GetJSCacheDir, \
                                                          GetSubtitlesDir, GetMovieMetaDataDir, RemoveDirContents, RemoveAllDirsIconsFromPath, \
                                                          GetSearchHistoryDir, GetFavouritesDir, GetMoviePlayerPerHostDir, GetHostOrderDir
from Plugins.Extensions.IPTVPlayer.components.configbase import ConfigBaseWidget, ConfigIPTVFileSelection, COLORS_DEFINITONS
from Plugins.Extensions.IPTVPlayer.components.confighost import ConfigHostsMenu
from Plugins.Extensions.IPTVPlayer.components.iptvdirbrowser import IPTVDirectorySelectorWidget
from Plugins.Extensions.IPTVPlayer.components.configextmovieplayer import ConfigExtMoviePlayer
from Plugins.Extensions.IPTVPlayer.__init__ import _, GRIDSUPPORT
from .iptvpin import IPTVPinWidget
###################################################

###################################################
# FOREIGN import
###################################################
from Screens.MessageBox import MessageBox

from Components.config import config, ConfigSubsection, ConfigSelection, ConfigDirectory, ConfigYesNo, ConfigOnOff, ConfigInteger, \
                              ConfigText, ConfigSelectionNumber, getConfigListEntry, configfile
from Tools.BoundFunction import boundFunction
###################################################


###################################################
# Config options for HOST
###################################################
config.plugins.iptvplayer = ConfigSubsection()

config.plugins.iptvplayer.plarformfpuabi = ConfigSelection(default="", choices=[("", ""), ("hard_float", _("Hardware floating point")), ("soft_float", _("Software floating point"))])
config.plugins.iptvplayer.exteplayer3path = ConfigText(default="", fixed_size=False)
config.plugins.iptvplayer.set_curr_title = ConfigYesNo(default=False)
config.plugins.iptvplayer.curr_title_file = ConfigText(default="", fixed_size=False)

config.plugins.iptvplayer.showcover = ConfigYesNo(default=True)
# RemoveOldDirsIcons() (iptvtools.py) only deletes when deltaInDays >= 0,
# so a negative value is naturally "never" - no changes needed there
config.plugins.iptvplayer.deleteIcons = ConfigSelection(default="3", choices=[("0", _("after closing")), ("1", _("after day")), ("3", _("after three days")), ("7", _("after a week")), ("-1", _("never"))])
# config.plugins.iptvplayer.allowedcoverformats = ConfigSelection(default="jpeg,png", choices=[("jpeg,png,gif", _("jpeg,png,gif")), ("jpeg,png", _("jpeg,png")), ("jpeg", _("jpeg")), ("all", _("all"))])
config.plugins.iptvplayer.showinextensions = ConfigYesNo(default=True)
# "T" (tree list) is intentionally not offered here - never implemented,
# would silently behave like "G" if selected
config.plugins.iptvplayer.hostsListType = ConfigSelection(default="G", choices=[("G", _("Graphic services selector")), ("S", _("List view")), ("P", _("Simple list"))])
config.plugins.iptvplayer.showinMainMenu = ConfigYesNo(default=False)
# config.plugins.iptvplayer.ListaGraficzna = ConfigYesNo(default=True)
config.plugins.iptvplayer.group_hosts = ConfigYesNo(default=True)
# NaszaSciezka (Polish for "our path") is kept, hidden from the UI, only
# so its already-persisted value can seed DownloadsDir's default below -
# renaming a config attribute changes its settings-file key, so without
# this a user's customized path would silently reset to the built-in
# default after the rename. Same for SciezkaCache/NaszaTMP further down.
config.plugins.iptvplayer.NaszaSciezka = ConfigDirectory(default="/hdd/movie/")  # , fixed_size = False)
config.plugins.iptvplayer.DownloadsDir = ConfigDirectory(default=config.plugins.iptvplayer.NaszaSciezka.value)  # , fixed_size = False)
config.plugins.iptvplayer.bufferingPath = ConfigDirectory(default=config.plugins.iptvplayer.DownloadsDir.value)  # , fixed_size = False)
config.plugins.iptvplayer.buforowanie = ConfigYesNo(default=False)
config.plugins.iptvplayer.buforowanie_m3u8 = ConfigYesNo(default=True)
config.plugins.iptvplayer.buforowanie_rtmp = ConfigYesNo(default=False)
config.plugins.iptvplayer.requestedBuffSize = ConfigInteger(2, (1, 120))
config.plugins.iptvplayer.requestedAudioBuffSize = ConfigInteger(256, (1, 10240))

config.plugins.iptvplayer.IPTVDMRunAtStart = ConfigYesNo(default=False)
config.plugins.iptvplayer.IPTVDMShowAfterAdd = ConfigYesNo(default=True)
config.plugins.iptvplayer.IPTVDMMaxDownloadItem = ConfigSelection(default="1", choices=[("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5"), ("10", "10"), ("20", "20"), ("30", "30"), ("40", "40"), ("50", "50")])

config.plugins.iptvplayer.sortuj = ConfigYesNo(default=True)
config.plugins.iptvplayer.remove_diabled_hosts = ConfigYesNo(default=False)
config.plugins.iptvplayer.IPTVWebIterface = ConfigYesNo(default=False)
config.plugins.iptvplayer.plugin_autostart = ConfigYesNo(default=False)
config.plugins.iptvplayer.plugin_autostart_method = ConfigSelection(default="wizard", choices=[("wizard", "wizard"), ("infobar", "infobar")])

config.plugins.iptvplayer.osk_type = ConfigSelection(default="", choices=[("", _("Auto")), ("system", _("System")), ("own", _("Own model"))])
config.plugins.iptvplayer.osk_layout = ConfigText(default="", fixed_size=False)
config.plugins.iptvplayer.osk_allow_suggestions = ConfigYesNo(default=True)
config.plugins.iptvplayer.osk_allow_search_history = ConfigYesNo(default=True)
config.plugins.iptvplayer.osk_remember_last_search = ConfigYesNo(default=True)
config.plugins.iptvplayer.osk_default_suggestions = ConfigSelection(default="", choices=[("", _("Auto")), ("none", _("None")), ("google", "google.com"), ("bing", "bing.com"), ("duckduckgo", "duckduckgo.com"), ("filmweb", "filmweb.pl"), ("imdb", "imdb.com")])
config.plugins.iptvplayer.osk_allow_host_suggestions = ConfigYesNo(default=True)
config.plugins.iptvplayer.osk_background_color = ConfigSelection(default="", choices=[('', _('Default')), ('transparent', _('Transparent')), ('#000000', _('Black')), ('#80000000', _('Darkgray')), ('#cc000000', _('Lightgray'))])
# the tightest element (the HD/SD input line: 26pt base in a fixed 36px-tall
# row) is already close to its limit, so the positive end is kept modest to
# avoid clipping instead of matching NewVirtualKeyBoard's wider 0-30 range
config.plugins.iptvplayer.osk_font_size_offset = ConfigSelectionNumber(min=-6, max=6, stepwidth=1, default=0, wraparound=False)
config.plugins.iptvplayer.osk_searchfield_align = ConfigSelection(default="left", choices=[("left", _("Left")), ("right", _("Right"))])
config.plugins.iptvplayer.osk_show_flags = ConfigYesNo(default=True)


def GetMoviePlayerName(player):
    map = {"auto": _("auto"), "mini": _("internal"), "standard": _("standard"), 'exteplayer': _("external eplayer3"), 'extgstplayer': _("external gstplayer")}
    return map.get(player, _('unknown'))


def ConfigPlayer(player):
    return (player, GetMoviePlayerName(player))


config.plugins.iptvplayer.defaultMoviePlayer0 = ConfigSelection(default="auto", choices=[ConfigPlayer("auto"), ConfigPlayer("mini"), ConfigPlayer("standard"), ConfigPlayer('extgstplayer'), ConfigPlayer('exteplayer')])
config.plugins.iptvplayer.alternativeMoviePlayer0 = ConfigSelection(default="auto", choices=[ConfigPlayer("auto"), ConfigPlayer("mini"), ConfigPlayer("standard"), ConfigPlayer('extgstplayer'), ConfigPlayer('exteplayer')])
config.plugins.iptvplayer.defaultMoviePlayer = ConfigSelection(default="auto", choices=[ConfigPlayer("auto"), ConfigPlayer("mini"), ConfigPlayer("standard"), ConfigPlayer('extgstplayer'), ConfigPlayer('exteplayer')])
config.plugins.iptvplayer.alternativeMoviePlayer = ConfigSelection(default="auto", choices=[ConfigPlayer("auto"), ConfigPlayer("mini"), ConfigPlayer("standard"), ConfigPlayer('extgstplayer'), ConfigPlayer('exteplayer')])
# "standard" keeps the blue-key "Select movie player" picker showing just
# the 4 configured default/alternative slots (+ Auto), like before
# GetAvailableMoviePlayers() started listing every player directly -
# "extended" opts into that full list instead
config.plugins.iptvplayer.moviePlayerPickerMode = ConfigSelection(default="standard", choices=[("standard", _("Standard")), ("extended", _("Extended"))])

config.plugins.iptvplayer.SciezkaCache = ConfigDirectory(default="/hdd/IPTVCache/")  # , fixed_size = False)
config.plugins.iptvplayer.CacheDir = ConfigDirectory(default=config.plugins.iptvplayer.SciezkaCache.value)  # , fixed_size = False)
config.plugins.iptvplayer.NaszaTMP = ConfigDirectory(default="/tmp/")  # , fixed_size = False)
config.plugins.iptvplayer.TmpDir = ConfigDirectory(default=config.plugins.iptvplayer.NaszaTMP.value)  # , fixed_size = False)
# holds real user data (favourites/watched status, search history, movie
# player preferences, host order/groups) as opposed to CacheDir's
# disposable, freely-regenerable cache data - kept separate so "Delete
# all cache files now" can never touch it, and so it can live somewhere
# that survives a cache wipe/reflash of external storage
config.plugins.iptvplayer.ConfigDir = ConfigDirectory(default="/etc/enigma2/IPTVPlayer/")  # , fixed_size = False)
# hides all the per-category cleanup entries below by default - most
# users never need to touch these, only the three folder paths above
config.plugins.iptvplayer.storageExpertMode = ConfigYesNo(default=False)

# per-category auto-cleanup for the CacheDir subfolders that otherwise
# grow forever (unlike icons, which already had their own deleteIcons
# cleanup above). 0 = never delete. The "fakeXxxDelete" entries are
# non-editable action triggers (same pattern as fakePin/fakeHostsList
# below) wired up in ConfigMenu.keyOK() to a confirm dialog + immediate
# manual delete
config.plugins.iptvplayer.cookiesCacheDeleteAfterDays = ConfigSelectionNumber(min=0, max=365, stepwidth=1, default=0, wraparound=False)
config.plugins.iptvplayer.fakeCookiesCacheDelete = ConfigSelection(default="fake", choices=[("fake", _("Delete now"))])
config.plugins.iptvplayer.jsCacheDeleteAfterDays = ConfigSelectionNumber(min=0, max=365, stepwidth=1, default=0, wraparound=False)
config.plugins.iptvplayer.fakeJSCacheDelete = ConfigSelection(default="fake", choices=[("fake", _("Delete now"))])
config.plugins.iptvplayer.subtitlesCacheDeleteAfterDays = ConfigSelectionNumber(min=0, max=365, stepwidth=1, default=0, wraparound=False)
config.plugins.iptvplayer.fakeSubtitlesCacheDelete = ConfigSelection(default="fake", choices=[("fake", _("Delete now"))])
config.plugins.iptvplayer.movieMetaDataCacheDeleteAfterDays = ConfigSelectionNumber(min=0, max=365, stepwidth=1, default=0, wraparound=False)
config.plugins.iptvplayer.fakeMovieMetaDataCacheDelete = ConfigSelection(default="fake", choices=[("fake", _("Delete now"))])
# per-host remembered movie player/buffering choice (CMoviePlayerPerHost) -
# always current, no real notion of "stale" - manual reset only, no
# auto-cleanup-after-days option
config.plugins.iptvplayer.fakeMoviePlayerCacheDelete = ConfigSelection(default="fake", choices=[("fake", _("Delete now"))])
# host group definitions + per-group/overall host order (migrated here
# from /etc/enigma2/, see GetMigratedHostOrderFile()) - reflects current
# live sorting state, not aging cache, so manual reset only
config.plugins.iptvplayer.fakeHostOrderCacheDelete = ConfigSelection(default="fake", choices=[("fake", _("Delete now"))])
# deleteIcons itself (moved here from Skin configuration) already had its
# own auto-cleanup (RemoveOldDirsIcons, driven from IconMenager.__del__) -
# only the immediate "delete now" trigger is new
config.plugins.iptvplayer.fakeIconsCacheDelete = ConfigSelection(default="fake", choices=[("fake", _("Delete now"))])
config.plugins.iptvplayer.fakeSearchHistoryDelete = ConfigSelection(default="fake", choices=[("fake", _("Delete now"))])
# Favourites/watched status is real user data, not disposable cache like
# the others above - no auto-cleanup-after-days option, deliberately
# manual-only with a stronger confirmation text
config.plugins.iptvplayer.fakeFavouritesCacheDelete = ConfigSelection(default="fake", choices=[("fake", _("Delete now"))])
# wipes the entire CacheDir (cookies, JS cache, subtitles, movie
# metadata, thumbnails - everything disposable/regenerable)
config.plugins.iptvplayer.fakeAllCacheDelete = ConfigSelection(default="fake", choices=[("fake", _("Delete now"))])
# wipes the entire ConfigDir (favourites/watched, search history, movie
# player preferences, host order/groups - everything that's real user data)
config.plugins.iptvplayer.fakeAllConfigDelete = ConfigSelection(default="fake", choices=[("fake", _("Delete now"))])

config.plugins.iptvplayer.ZablokujWMV = ConfigYesNo(default=True)

config.plugins.iptvplayer.vkcom_login = ConfigText(default="", fixed_size=False)
config.plugins.iptvplayer.vkcom_password = ConfigText(default="", fixed_size=False)

config.plugins.iptvplayer.fichiercom_login = ConfigText(default="", fixed_size=False)
config.plugins.iptvplayer.fichiercom_password = ConfigText(default="", fixed_size=False)

config.plugins.iptvplayer.iptvplayer_login = ConfigText(default="", fixed_size=False)
config.plugins.iptvplayer.iptvplayer_password = ConfigText(default="", fixed_size=False)

config.plugins.iptvplayer.useSubtitlesParserExtension = ConfigYesNo(default=True)
config.plugins.iptvplayer.subsourceapi = ConfigText(default="", fixed_size=False)
config.plugins.iptvplayer.subdlapi = ConfigText(default="", fixed_size=False)
config.plugins.iptvplayer.opensuborg_login = ConfigText(default="", fixed_size=False)
config.plugins.iptvplayer.opensuborg_password = ConfigText(default="", fixed_size=False)
config.plugins.iptvplayer.napisy24pl_login = ConfigText(default="", fixed_size=False)
config.plugins.iptvplayer.napisy24pl_password = ConfigText(default="", fixed_size=False)

config.plugins.iptvplayer.debugprint = ConfigSelection(default="", choices=[("", _("No")), ("console", _("Yes, to console")),
                                                                            ("debugfile", _("Yes, to file /hdd/iptv.dbg")),
                                                                            ("/tmp/iptv.dbg", _("Yes, to file /tmp/iptv.dbg")),
                                                                            ("/home/root/logs/iptv.dbg", _("Yes, to file /home/root/logs/iptv.dbg")),
                                                                            ])

# icons
config.plugins.iptvplayer.IconsSize = ConfigSelection(default="100", choices=[("100", "100x100"), ("120", "120x120"), ("135", "135x135")])
config.plugins.iptvplayer.numOfRow = ConfigSelection(default="0", choices=[("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("0", "auto")])
config.plugins.iptvplayer.numOfCol = ConfigSelection(default="0", choices=[("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5"), ("6", "6"), ("7", "7"), ("8", "8"), ("0", "auto")])

config.plugins.iptvplayer.skinforceinternal = ConfigYesNo(default=False)
config.plugins.iptvplayer.skin = ConfigSelection(default="", choices=GetSkinsList())
config.plugins.iptvplayer.use_colors = ConfigYesNo(default=True)

# Pin code
config.plugins.iptvplayer.fakePin = ConfigSelection(default="fake", choices=[("fake", "****")])
config.plugins.iptvplayer.pin = ConfigText(default="0000", fixed_size=False)
config.plugins.iptvplayer.disable_live = ConfigYesNo(default=False)
config.plugins.iptvplayer.configProtectedByPin = ConfigYesNo(default=False)
config.plugins.iptvplayer.pluginProtectedByPin = ConfigYesNo(default=False)

config.plugins.iptvplayer.httpssslcertvalidation = ConfigYesNo(default=False)

# PROXY
config.plugins.iptvplayer.proxyurl = ConfigText(default="http://user:pass@ip:port", fixed_size=False)
config.plugins.iptvplayer.german_proxyurl = ConfigText(default="http://user:pass@ip:port", fixed_size=False)
config.plugins.iptvplayer.russian_proxyurl = ConfigText(default="http://user:pass@ip:port", fixed_size=False)
config.plugins.iptvplayer.ukrainian_proxyurl = ConfigText(default="http://user:pass@ip:port", fixed_size=False)
config.plugins.iptvplayer.alternative_proxy1 = ConfigText(default="http://user:pass@ip:port", fixed_size=False)
config.plugins.iptvplayer.alternative_proxy2 = ConfigText(default="http://user:pass@ip:port", fixed_size=False)

# config.plugins.iptvplayer.captcha_bypass_order = ConfigSelection(default="", choices=[("", _("Internal, then external")), ("free", _("Only free")), ("free_pay", _("External free, then paid")), ("pay", _("External paid"))])
# config.plugins.iptvplayer.captcha_bypass_free = ConfigSelection(default="", choices=[("", _("None")), ("myjd", "MyJDownloader")])
# config.plugins.iptvplayer.captcha_bypass_pay = ConfigSelection(default="", choices=[("", _("None")), ("2captcha.com", "2captcha.com"), ("9kw.eu", "9kw.eu")])
config.plugins.iptvplayer.captcha_bypass = ConfigSelection(default="", choices=[("", _("Auto")), ("mye2i", "MyE2i"), ("2captcha.com", "2captcha.com"), ("9kw.eu", "9kw.eu")])

config.plugins.iptvplayer.api_key_9kweu = ConfigText(default="", fixed_size=False)
config.plugins.iptvplayer.api_key_2captcha = ConfigText(default="", fixed_size=False)

config.plugins.iptvplayer.myjd_login = ConfigText(default="", fixed_size=False)
config.plugins.iptvplayer.myjd_password = ConfigText(default="", fixed_size=False)
config.plugins.iptvplayer.myjd_jdname = ConfigText(default="", fixed_size=False)

config.plugins.iptvplayer.api_key_youtube = ConfigText(default="", fixed_size=False)

# Hosts lists
config.plugins.iptvplayer.fakeHostsList = ConfigSelection(default="fake", choices=[("fake", "  ")])


# External movie player settings
config.plugins.iptvplayer.fakExtMoviePlayerList = ConfigSelection(default="fake", choices=[("fake", "  ")])

# hidden options
# config.plugins.iptvplayer.hiddenAllVersionInUpdate = ConfigYesNo(default=False)
config.plugins.iptvplayer.hidden_ext_player_def_aspect_ratio = ConfigSelection(default="-1", choices=[("-1", _("default")), ("0", _("4:3 Letterbox")), ("1", _("4:3 PanScan")), ("2", _("16:9")), ("3", _("16:9 always")), ("4", _("16:10 Letterbox")), ("5", _("16:10 PanScan")), ("6", _("16:9 Letterbox"))])

config.plugins.iptvplayer.search_history_size = ConfigInteger(50, (0, 1000000))
config.plugins.iptvplayer.autoplay_start_delay = ConfigInteger(3, (0, 9))

config.plugins.iptvplayer.favourites_use_watched_flag = ConfigYesNo(default=True)
config.plugins.iptvplayer.watched_item_color = ConfigSelection(default="#808080", choices=COLORS_DEFINITONS)
config.plugins.iptvplayer.started_item_color = ConfigSelection(default="#FFFF00", choices=COLORS_DEFINITONS)
config.plugins.iptvplayer.sidecar_enabled = ConfigYesNo(default=True)


def IsSidecarEnabled():
    # single central place hosts ask whether to create sidecar .txt/.jpg files,
    # instead of each host keeping its own copy of this config option
    return config.plugins.iptvplayer.sidecar_enabled.value


config.plugins.iptvplayer.usepycurl = ConfigYesNo(default=False)

config.plugins.iptvplayer.prefer_hlsdl_for_pls_with_alt_media = ConfigYesNo(default=True)

###################################################

config.plugins.iptvplayer.extplayer_summary = ConfigSelection(default="yes", choices=[('auto', _('Auto')), ('yes', _('Yes')), ('no', _('No'))])
config.plugins.iptvplayer.use_clear_iframe = ConfigYesNo(default=False)
config.plugins.iptvplayer.show_iframe = ConfigYesNo(default=True)
config.plugins.iptvplayer.iframe_file = ConfigIPTVFileSelection(fileMatch=r"^.*\.mvi$", default="/usr/share/enigma2/radio.mvi")
config.plugins.iptvplayer.clear_iframe_file = ConfigIPTVFileSelection(fileMatch=r"^.*\.mvi$", default="/usr/share/enigma2/black.mvi")

config.plugins.iptvplayer.remember_last_position = ConfigYesNo(default=False)
config.plugins.iptvplayer.remember_last_position_time = ConfigInteger(0, (0, 99))
config.plugins.iptvplayer.fakeExtePlayer3 = ConfigSelection(default="fake", choices=[("fake", " ")])
config.plugins.iptvplayer.rambuffer_sizemb_network_proto = ConfigInteger(0, (0, 999))
config.plugins.iptvplayer.rambuffer_sizemb_files = ConfigInteger(0, (0, 999))
config.plugins.iptvplayer.aac_software_decode = ConfigYesNo(default=False)
config.plugins.iptvplayer.ac3_software_decode = ConfigYesNo(default=False)
config.plugins.iptvplayer.eac3_software_decode = ConfigYesNo(default=False)
config.plugins.iptvplayer.dts_software_decode = ConfigYesNo(default=False)
config.plugins.iptvplayer.wma_software_decode = ConfigYesNo(default=True)
config.plugins.iptvplayer.mp3_software_decode = ConfigYesNo(default=False)
config.plugins.iptvplayer.stereo_software_decode = ConfigYesNo(default=False)
config.plugins.iptvplayer.software_decode_as = ConfigSelection(default="pcm", choices=[("pcm", "PCM"), ("lpcm", "LPCM")])
config.plugins.iptvplayer.aac_mix = ConfigSelection(default=None, choices=[(None, _("from E2 settings"))])
config.plugins.iptvplayer.ac3_mix = ConfigSelection(default=None, choices=[(None, _("from E2 settings"))])

config.plugins.iptvplayer.extplayer_infobar_timeout = ConfigSelection(default="5", choices=[
    ("1", "1 " + _("second")), ("2", "2 " + _("seconds")), ("3", "3 " + _("seconds")),
    ("4", "4 " + _("seconds")), ("5", "5 " + _("seconds")), ("6", "6 " + _("seconds")), ("7", "7 " + _("seconds")),
    ("8", "8 " + _("seconds")), ("9", "9 " + _("seconds")), ("10", "10 " + _("seconds"))
])
config.plugins.iptvplayer.extplayer_aspect = ConfigSelection(default=None, choices=[(None, _("from E2 settings"))])
config.plugins.iptvplayer.extplayer_policy = ConfigSelection(default=None, choices=[(None, _("from E2 settings"))])
config.plugins.iptvplayer.extplayer_policy2 = ConfigSelection(default=None, choices=[(None, _("from E2 settings"))])

config.plugins.iptvplayer.extplayer_subtitle_auto_enable = ConfigYesNo(default=True)
config.plugins.iptvplayer.extplayer_subtitle_font = ConfigSelection(default="Regular", choices=[("Regular", "Regular")])
config.plugins.iptvplayer.extplayer_subtitle_font_size = ConfigInteger(40, (20, 90))
config.plugins.iptvplayer.extplayer_subtitle_font_color = ConfigSelection(default="#FFFFFF", choices=COLORS_DEFINITONS)
config.plugins.iptvplayer.extplayer_subtitle_wrapping_enabled = ConfigYesNo(default=False)
config.plugins.iptvplayer.extplayer_subtitle_line_height = ConfigInteger(40, (20, 999))
config.plugins.iptvplayer.extplayer_subtitle_line_spacing = ConfigInteger(4, (0, 99))
config.plugins.iptvplayer.extplayer_subtitle_background = ConfigSelection(default="#000000", choices=[('transparent', _('Transparent')), ('#000000', _('Black')), ('#80000000', _('Darkgray')), ('#cc000000', _('Lightgray'))])

config.plugins.iptvplayer.extplayer_subtitle_border_color = ConfigSelection(default="#000000", choices=COLORS_DEFINITONS)
config.plugins.iptvplayer.extplayer_subtitle_shadow_color = ConfigSelection(default="#000000", choices=COLORS_DEFINITONS)

config.plugins.iptvplayer.extplayer_subtitle_border_enabled = ConfigYesNo(default=True)
config.plugins.iptvplayer.extplayer_subtitle_shadow_enabled = ConfigYesNo(default=False)

config.plugins.iptvplayer.extplayer_subtitle_border_width = ConfigInteger(3, (1, 6))
config.plugins.iptvplayer.extplayer_subtitle_shadow_xoffset = ConfigInteger(3, (-6, 6))
config.plugins.iptvplayer.extplayer_subtitle_shadow_yoffset = ConfigInteger(3, (-6, 6))
config.plugins.iptvplayer.extplayer_subtitle_pos = ConfigInteger(50, (0, 400))
config.plugins.iptvplayer.extplayer_subtitle_box_valign = ConfigSelection(default="bottom", choices=[("bottom", _("bottom")), ("center", _("center")), ("top", _("top"))])
config.plugins.iptvplayer.extplayer_subtitle_box_height = ConfigInteger(240, (50, 400))

config.plugins.iptvplayer.extplayer_infobanner_clockformat = ConfigSelection(default="", choices=[("", _("None")), ("24", _("24 hour format")), ("12", _("12 hour format"))])

config.plugins.iptvplayer.GSTplayer_no_IFD = ConfigYesNo(default=False)
config.plugins.iptvplayer.extplayer_skin = ConfigSelection(default="default", choices=[("default", _("default")), ("black", _("black")), ("red", _("red")), ("blue", _("blue")), ("green", _("green")), ("black-white", _("black&white")), ("cobalt", _("cobalt")), ("jersey", _("jersey")), ("navy", _("navy")), ("line", _("line"))])


########################################################
# Generate list of hosts options for Enabling/Disabling
########################################################

class ConfigIPTVHostOnOff(ConfigOnOff):
    def __init__(self, default=False):
        ConfigOnOff.__init__(self, default=default)


gListOfHostsNames = GetHostsList()
for hostName in gListOfHostsNames:
    try:
        # as default all hosts are enabled
        enabledByDefault = hostName not in ['ipla']
        setattr(config.plugins.iptvplayer, 'host' + hostName, ConfigIPTVHostOnOff(default=enabledByDefault))
    except Exception:
        printExc(hostName)


def GetListOfHostsNames():
    global gListOfHostsNames
    return gListOfHostsNames


###################################################


def GetOskOwnModelConfigList(indent=True):
    # the "Own model" keyboard's own options - shared by ConfigMenu's
    # "Grundkonfiguration" section (indented, nested under "Virtual Keyboard
    # type") and E2iVKQuickSettings (the keyboard's own MENU -> Settings
    # screen, shown standalone since that screen only exists while the "own"
    # model is already active) so both stay in sync
    #
    # The indent is purely presentational, so it's applied to the already-
    # translated result instead of being baked into the msgid - that used to
    # be the case (msgid "    Show suggestions") and every .po's msgstr had
    # the same 4 spaces baked in too, so this only works untranslated for
    # E2iVKQuickSettings (indent=False) before now. Migrated all 12 locales'
    # existing translations onto the unindented msgid instead of leaving
    # them stuck on a dead, presentation-specific key.
    prefix = '    ' if indent else ''
    list = []
    list.append(getConfigListEntry(prefix + _("Background color"), config.plugins.iptvplayer.osk_background_color))
    list.append(getConfigListEntry(prefix + _("Show suggestions"), config.plugins.iptvplayer.osk_allow_suggestions))
    list.append(getConfigListEntry(prefix + _("Default suggestions provider"), config.plugins.iptvplayer.osk_default_suggestions))
    list.append(getConfigListEntry(prefix + _("Allow host to override suggestions provider"), config.plugins.iptvplayer.osk_allow_host_suggestions))
    list.append(getConfigListEntry(prefix + _("Show search history"), config.plugins.iptvplayer.osk_allow_search_history))
    list.append(getConfigListEntry(prefix + _("Show flags"), config.plugins.iptvplayer.osk_show_flags))
    list.append(getConfigListEntry(prefix + _("Font size offset"), config.plugins.iptvplayer.osk_font_size_offset))
    list.append(getConfigListEntry(prefix + _("Text field alignment"), config.plugins.iptvplayer.osk_searchfield_align))
    return list


def GetOskConfigList():
    list = []
    list.append(getConfigListEntry(_("Virtual Keyboard type"), config.plugins.iptvplayer.osk_type))
    list.append(getConfigListEntry(_("Remember last search entry"), config.plugins.iptvplayer.osk_remember_last_search))
    if config.plugins.iptvplayer.osk_type.value == 'own':
        list.extend(GetOskOwnModelConfigList(indent=True))
    return list


class E2iVKQuickSettings(ConfigBaseWidget):
    def __init__(self, session):
        self.list = []
        ConfigBaseWidget.__init__(self, session)

    def layoutFinished(self):
        ConfigBaseWidget.layoutFinished(self)
        self.setTitle(_("E2iPlayer - keyboard settings"))

    def runSetup(self):
        self.list = GetOskOwnModelConfigList(indent=False)
        ConfigBaseWidget.runSetup(self)

    def getSubOptionsList(self):
        return []

    def keyDefaults(self):
        # ConfigBaseWidget's own keyDefaults() is a no-op stub; ConfigMenu
        # overrides it for the full settings list, this does the same but
        # scoped to just the keyboard options shown here.
        def keyDefaultsConfirm(result):
            if result:
                for item in self.list:
                    if len(item) > 1:
                        configItem = item[1]
                        if not isinstance(configItem, ConfigText):
                            configItem.value = configItem.default
                self.close()
        message = _("Are you sure you want to reset all settings to their default values?")
        self.session.openWithCallback(keyDefaultsConfirm, MessageBox, text=message, type=MessageBox.TYPE_YESNO)


class ConfigMenu(ConfigBaseWidget):

    def __init__(self, session):
        printDBG("ConfigMenu.__init__ -------------------------------")
        self.list = []
        ConfigBaseWidget.__init__(self, session)
        # remember old
        self.showcoverOld = config.plugins.iptvplayer.showcover.value
        self.CacheDirOld = config.plugins.iptvplayer.CacheDir.value
        self.remove_diabled_hostsOld = config.plugins.iptvplayer.remove_diabled_hosts.value
        self.enabledHostsListOld = GetEnabledHostsList()
        self.runtimeOptionsValues = self.getRuntimeOptionsValues()

    def __del__(self):
        printDBG("ConfigMenu.__del__ -------------------------------")

    def __onClose(self):
        printDBG("ConfigMenu.__onClose -----------------------------")
        ConfigBaseWidget.__onClose(self)

    def layoutFinished(self):
        ConfigBaseWidget.layoutFinished(self)
        self.setTitle(_("E2iPlayer - settings"))

    @staticmethod
    def fillConfigList(list,):
        list.append(getConfigListEntry(_("----- BASIC CONFIGURATION -----"),))
        list.extend(GetOskConfigList())
        list.append(getConfigListEntry(_("Initialize web interface"), config.plugins.iptvplayer.IPTVWebIterface))
        list.append(getConfigListEntry(_("Show IPTVPlayer in extension list"), config.plugins.iptvplayer.showinextensions))
        list.append(getConfigListEntry(_("Show IPTVPlayer in main menu"), config.plugins.iptvplayer.showinMainMenu))
        list.append(getConfigListEntry(_("E2iPlayer auto start at Enigma2 start"), config.plugins.iptvplayer.plugin_autostart))
        if config.plugins.iptvplayer.plugin_autostart.value:
            list.append(getConfigListEntry(_("Auto start method"), config.plugins.iptvplayer.plugin_autostart_method))
        list.append(getConfigListEntry(_("Disable live at plugin start"), config.plugins.iptvplayer.disable_live))
        list.append(getConfigListEntry(_("Use the PyCurl for HTTP(S) requests"), config.plugins.iptvplayer.usepycurl))
        list.append(getConfigListEntry(_("https - validate SSL certificates"), config.plugins.iptvplayer.httpssslcertvalidation))
        list.append(getConfigListEntry(_("----- SERVICE CONFIGURATION -----"),))
        list.append(getConfigListEntry(_("Services configuration"), config.plugins.iptvplayer.fakeHostsList))
        list.append(getConfigListEntry(_("Remove disabled services"), config.plugins.iptvplayer.remove_diabled_hosts))
        list.append(getConfigListEntry(_("Allow watched flag to be set"), config.plugins.iptvplayer.favourites_use_watched_flag))
        if config.plugins.iptvplayer.favourites_use_watched_flag.value:
            list.append(getConfigListEntry("    " + _("The color of the viewed item"), config.plugins.iptvplayer.watched_item_color))
            list.append(getConfigListEntry("    " + _("The color of the started item"), config.plugins.iptvplayer.started_item_color))
        list.append(getConfigListEntry(_("Create sidecar files (.txt/.jpg)"), config.plugins.iptvplayer.sidecar_enabled))
        list.append(getConfigListEntry(_("----- SECURITY CONFIGURATION -----"),))
        list.append(getConfigListEntry(_("Pin protection for plugin"), config.plugins.iptvplayer.pluginProtectedByPin))
        list.append(getConfigListEntry(_("Pin protection for configuration"), config.plugins.iptvplayer.configProtectedByPin))
        if config.plugins.iptvplayer.pluginProtectedByPin.value or config.plugins.iptvplayer.configProtectedByPin.value:
            list.append(getConfigListEntry(_("Set pin code"), config.plugins.iptvplayer.fakePin))

        list.append(getConfigListEntry(_("----- SKIN CONFIGURATION -----"),))
        list.append(getConfigListEntry(_("Skin"), config.plugins.iptvplayer.skin))
        list.append(getConfigListEntry(_("Force internal Skin"), config.plugins.iptvplayer.skinforceinternal))
        list.append(getConfigListEntry(_("Use colors"), config.plugins.iptvplayer.use_colors))
        list.append(getConfigListEntry(_("Info bar clock format"), config.plugins.iptvplayer.extplayer_infobanner_clockformat))
        list.append(getConfigListEntry(_("Player Skin"), config.plugins.iptvplayer.extplayer_skin))
        list.append(getConfigListEntry(_("Display thumbnails"), config.plugins.iptvplayer.showcover))
        # list.append(getConfigListEntry(_("    Allowed formats of thumbnails"), config.plugins.iptvplayer.allowedcoverformats))
        # list.append(getConfigListEntry("Sort the lists?", config.plugins.iptvplayer.sortuj))
        # list.append(getConfigListEntry(_("Graphic services selector"), config.plugins.iptvplayer.ListaGraficzna))
        # if config.plugins.iptvplayer.ListaGraficzna.value is True:
        list.append(getConfigListEntry(_("Hosts list type"), config.plugins.iptvplayer.hostsListType))
        list.append(getConfigListEntry("    " + _("Enable hosts groups"), config.plugins.iptvplayer.group_hosts))
        if config.plugins.iptvplayer.hostsListType.value == "G":
            list.append(getConfigListEntry("    " + _("Service icon size"), config.plugins.iptvplayer.IconsSize))
        if not GRIDSUPPORT and config.plugins.iptvplayer.hostsListType.value == "G":
            list.append(getConfigListEntry("    " + _("Number of rows"), config.plugins.iptvplayer.numOfRow))
            list.append(getConfigListEntry("    " + _("Number of columns"), config.plugins.iptvplayer.numOfCol))
        # list.append(getConfigListEntry(_("VFD set current title:"), config.plugins.iptvplayer.set_curr_title))
        list.append(getConfigListEntry(_("Create LCD/VFD summary screen"), config.plugins.iptvplayer.extplayer_summary))

        list.append(getConfigListEntry(_("----- PROXIES CONFIGURATION -----"),))
        list.append(getConfigListEntry(_("Alternative proxy server (1)"), config.plugins.iptvplayer.alternative_proxy1))
        list.append(getConfigListEntry(_("Alternative proxy server (2)"), config.plugins.iptvplayer.alternative_proxy2))
        list.append(getConfigListEntry(_("Polish proxy server url"), config.plugins.iptvplayer.proxyurl))
        list.append(getConfigListEntry(_("German proxy server url"), config.plugins.iptvplayer.german_proxyurl))
        list.append(getConfigListEntry(_("Russian proxy server url"), config.plugins.iptvplayer.russian_proxyurl))
        list.append(getConfigListEntry(_("Ukrainian proxy server url"), config.plugins.iptvplayer.ukrainian_proxyurl))

        list.append(getConfigListEntry(_("----- STORAGE CONFIGURATION -----"),))
        list.append(getConfigListEntry(_("Folder for cache data"), config.plugins.iptvplayer.CacheDir))
        list.append(getConfigListEntry(_("Folder for temporary data"), config.plugins.iptvplayer.TmpDir))
        list.append(getConfigListEntry(_("Folder for config data"), config.plugins.iptvplayer.ConfigDir))
        list.append(getConfigListEntry(_("Detail/expert mode"), config.plugins.iptvplayer.storageExpertMode))
        if config.plugins.iptvplayer.storageExpertMode.value:
            list.append(getConfigListEntry("    " + _("Cache"),))
            list.append(getConfigListEntry("    " + _("Delete cookies cache after (days, 0 = never)"), config.plugins.iptvplayer.cookiesCacheDeleteAfterDays))
            list.append(getConfigListEntry("    " + _("Delete cookies cache now"), config.plugins.iptvplayer.fakeCookiesCacheDelete))
            list.append(getConfigListEntry("    " + _("Delete JS cache after (days, 0 = never)"), config.plugins.iptvplayer.jsCacheDeleteAfterDays))
            list.append(getConfigListEntry("    " + _("Delete JS cache now"), config.plugins.iptvplayer.fakeJSCacheDelete))
            list.append(getConfigListEntry("    " + _("Delete subtitles cache after (days, 0 = never)"), config.plugins.iptvplayer.subtitlesCacheDeleteAfterDays))
            list.append(getConfigListEntry("    " + _("Delete subtitles cache now"), config.plugins.iptvplayer.fakeSubtitlesCacheDelete))
            list.append(getConfigListEntry("    " + _("Delete movie metadata cache after (days, 0 = never)"), config.plugins.iptvplayer.movieMetaDataCacheDeleteAfterDays))
            list.append(getConfigListEntry("    " + _("Delete movie metadata cache now"), config.plugins.iptvplayer.fakeMovieMetaDataCacheDelete))
            list.append(getConfigListEntry("    " + _("Remove thumbnails"), config.plugins.iptvplayer.deleteIcons))
            list.append(getConfigListEntry("    " + _("Delete thumbnails cache now"), config.plugins.iptvplayer.fakeIconsCacheDelete))
            list.append(getConfigListEntry("    " + _("Delete all cache files now"), config.plugins.iptvplayer.fakeAllCacheDelete))
            list.append(getConfigListEntry("    " + _("Config"),))
            list.append(getConfigListEntry("    " + _("Delete movie player preferences now"), config.plugins.iptvplayer.fakeMoviePlayerCacheDelete))
            list.append(getConfigListEntry("    " + _("Delete host order and groups now"), config.plugins.iptvplayer.fakeHostOrderCacheDelete))
            list.append(getConfigListEntry("    " + _("The number of items in the search history"), config.plugins.iptvplayer.search_history_size))
            list.append(getConfigListEntry("    " + _("Delete search history now"), config.plugins.iptvplayer.fakeSearchHistoryDelete))
            list.append(getConfigListEntry("    " + _("Delete favourites and watched status now"), config.plugins.iptvplayer.fakeFavouritesCacheDelete))
            list.append(getConfigListEntry("    " + _("Delete all config files now"), config.plugins.iptvplayer.fakeAllConfigDelete))

        list.append(getConfigListEntry(_("----- BUFFERING CONFIGURATION -----"), ))
        list.append(getConfigListEntry(_("[HTTP] buffering"), config.plugins.iptvplayer.buforowanie))
        list.append(getConfigListEntry(_("[HLS/M3U8] buffering"), config.plugins.iptvplayer.buforowanie_m3u8))
        list.append(getConfigListEntry(_("[RTMP] buffering (rtmpdump required)"), config.plugins.iptvplayer.buforowanie_rtmp))
        if config.plugins.iptvplayer.buforowanie.value or config.plugins.iptvplayer.buforowanie_m3u8.value or config.plugins.iptvplayer.buforowanie_rtmp.value:
            list.append(getConfigListEntry("    " + _("Video buffer size [MB]"), config.plugins.iptvplayer.requestedBuffSize))
            list.append(getConfigListEntry("    " + _("Audio buffer size [KB]"), config.plugins.iptvplayer.requestedAudioBuffSize))
            list.append(getConfigListEntry(_("Buffering location"), config.plugins.iptvplayer.bufferingPath))

        list.append(getConfigListEntry(_("----- DOWNLOADING CONFIGURATION -----"), ))
        list.append(getConfigListEntry(_("Downloads location"), config.plugins.iptvplayer.DownloadsDir))
        list.append(getConfigListEntry(_("Start download manager per default"), config.plugins.iptvplayer.IPTVDMRunAtStart))
        list.append(getConfigListEntry(_("Show download manager after adding new item"), config.plugins.iptvplayer.IPTVDMShowAfterAdd))
        list.append(getConfigListEntry(_("Number of downloaded files simultaneously"), config.plugins.iptvplayer.IPTVDMMaxDownloadItem))
        list.append(getConfigListEntry(_("%s e-mail") % ('My JDownloader'), config.plugins.iptvplayer.myjd_login))
        list.append(getConfigListEntry(_("%s password") % ('My JDownloader'), config.plugins.iptvplayer.myjd_password))
        list.append(getConfigListEntry(_("%s device name") % ('My JDownloader'), config.plugins.iptvplayer.myjd_jdname))
        list.append(getConfigListEntry(_("%s API KEY") % 'http://youtube.com/', config.plugins.iptvplayer.api_key_youtube))

        list.append(getConfigListEntry(_("----- CAPTCHA CONFIGURATION -----"), ))
        list.append(getConfigListEntry(_("Default captcha bypass"), config.plugins.iptvplayer.captcha_bypass))
        # list.append(getConfigListEntry(_("Captcha solver order"), config.plugins.iptvplayer.captcha_bypass_order))
        # list.append(getConfigListEntry(_("Captcha bypass free service"), config.plugins.iptvplayer.captcha_bypass_free))
        # list.append(getConfigListEntry(_("Captcha bypass paid service"), config.plugins.iptvplayer.captcha_bypass_pay))
        # if config.plugins.iptvplayer.captcha_bypass_pay.value == "9kw.eu":
        list.append(getConfigListEntry(_("%s API KEY") % 'https://9kw.eu/', config.plugins.iptvplayer.api_key_9kweu))
        # if config.plugins.iptvplayer.captcha_bypass_pay.value == "2captcha.com":
        list.append(getConfigListEntry(_("%s API KEY") % 'http://2captcha.com/', config.plugins.iptvplayer.api_key_2captcha))

        list.append(getConfigListEntry(_("----- SUBTITLES CONFIGURATION -----"), ))
        list.append(getConfigListEntry(_("Use subtitles parser extension if available"), config.plugins.iptvplayer.useSubtitlesParserExtension))
        list.append(getConfigListEntry("https://subsource.net/ " + _("API_KEY"), config.plugins.iptvplayer.subsourceapi))
        list.append(getConfigListEntry("https://subdl.com/ " + _("API Key"), config.plugins.iptvplayer.subdlapi))
        list.append(getConfigListEntry("http://opensubtitles.org/ " + _("login"), config.plugins.iptvplayer.opensuborg_login))
        list.append(getConfigListEntry("http://opensubtitles.org/ " + _("password"), config.plugins.iptvplayer.opensuborg_password))
        list.append(getConfigListEntry("http://napisy24.pl/ " + _("login"), config.plugins.iptvplayer.napisy24pl_login))
        list.append(getConfigListEntry("http://napisy24.pl/ " + _("password"), config.plugins.iptvplayer.napisy24pl_password))
        list.append(getConfigListEntry("http://vk.com/ " + _("login"), config.plugins.iptvplayer.vkcom_login))
        list.append(getConfigListEntry("http://vk.com/ " + _("password"), config.plugins.iptvplayer.vkcom_password))
        list.append(getConfigListEntry("http://1fichier.com/ " + _("e-mail"), config.plugins.iptvplayer.fichiercom_login))
        list.append(getConfigListEntry("http://1fichier.com/ " + _("password"), config.plugins.iptvplayer.fichiercom_password))

        list.append(getConfigListEntry(_("----- PLAYERS & PLAYBACK CONFIGURATION -----"), ))
        list.append(getConfigListEntry(_("Autoplay start delay"), config.plugins.iptvplayer.autoplay_start_delay))
        list.append(getConfigListEntry(_("Block wmv files"), config.plugins.iptvplayer.ZablokujWMV))
        players = []
        list.append(getConfigListEntry(_("Movie player selection list"), config.plugins.iptvplayer.moviePlayerPickerMode))
        list.append(getConfigListEntry(_("First movie player without buffering mode"), config.plugins.iptvplayer.defaultMoviePlayer0))
        players.append(config.plugins.iptvplayer.defaultMoviePlayer0)
        list.append(getConfigListEntry(_("Second movie player without buffering mode"), config.plugins.iptvplayer.alternativeMoviePlayer0))
        players.append(config.plugins.iptvplayer.alternativeMoviePlayer0)
        list.append(getConfigListEntry(_("First movie player in buffering mode"), config.plugins.iptvplayer.defaultMoviePlayer))
        players.append(config.plugins.iptvplayer.defaultMoviePlayer)
        list.append(getConfigListEntry(_("Second movie player in buffering mode"), config.plugins.iptvplayer.alternativeMoviePlayer))
        players.append(config.plugins.iptvplayer.alternativeMoviePlayer)
        playersValues = [player.value for player in players]
        if 'exteplayer' in playersValues or 'extgstplayer' in playersValues or 'auto' in playersValues:
            list.append(getConfigListEntry(_("External movie player config"), config.plugins.iptvplayer.fakExtMoviePlayerList))
        list.append(getConfigListEntry(_("The default aspect ratio for the external player"), config.plugins.iptvplayer.hidden_ext_player_def_aspect_ratio))

        list.append(getConfigListEntry(_("----- OTHER SETTINGS -----"), ))
        list.append(getConfigListEntry(_("Write current title to file:"), config.plugins.iptvplayer.curr_title_file))
        list.append(getConfigListEntry(_("MIPS Floating Point Architecture"), config.plugins.iptvplayer.plarformfpuabi))
        list.append(getConfigListEntry(_("Prefer hlsld for playlist with alt. media"), config.plugins.iptvplayer.prefer_hlsdl_for_pls_with_alt_media))
        list.append(getConfigListEntry(_("Debug logs"), config.plugins.iptvplayer.debugprint))

    def runSetup(self):
        self.list = []
        ConfigMenu.fillConfigList(self.list)
        ConfigBaseWidget.runSetup(self)

    def onSelectionChanged(self):
        currItem = self["config"].getCurrent()[1]
        if currItem in [config.plugins.iptvplayer.fakePin, config.plugins.iptvplayer.fakeHostsList, config.plugins.iptvplayer.fakExtMoviePlayerList,
                         config.plugins.iptvplayer.fakeCookiesCacheDelete, config.plugins.iptvplayer.fakeJSCacheDelete,
                         config.plugins.iptvplayer.fakeSubtitlesCacheDelete, config.plugins.iptvplayer.fakeMovieMetaDataCacheDelete,
                         config.plugins.iptvplayer.fakeIconsCacheDelete, config.plugins.iptvplayer.fakeSearchHistoryDelete,
                         config.plugins.iptvplayer.fakeFavouritesCacheDelete, config.plugins.iptvplayer.fakeAllCacheDelete,
                         config.plugins.iptvplayer.fakeAllConfigDelete,
                         config.plugins.iptvplayer.fakeMoviePlayerCacheDelete, config.plugins.iptvplayer.fakeHostOrderCacheDelete]:
            self.isOkEnabled = True
            self.isSelectable = False
            self.setOKLabel()
        else:
            ConfigBaseWidget.onSelectionChanged(self)

    """
    def saveAndClose(self):
        ConfigBaseWidget.saveAndClose(self)
        if self.showcoverOld != config.plugins.iptvplayer.showcover.value or \
            self.CacheDirOld != config.plugins.iptvplayer.CacheDir.value:
            pass
            # plugin must be restarted if we wont to this options take effect
    """

    def getRuntimeOptionsValues(self):
        valTab = []
        valTab.append(config.plugins.iptvplayer.IPTVWebIterface.value)
        valTab.append(config.plugins.iptvplayer.showinextensions.value)
        valTab.append(config.plugins.iptvplayer.showinMainMenu.value)
        valTab.append(config.plugins.iptvplayer.plugin_autostart.value)
        valTab.append(config.plugins.iptvplayer.plugin_autostart_method.value)
        valTab.append(config.plugins.iptvplayer.disable_live.value)
        valTab.append(config.plugins.iptvplayer.pluginProtectedByPin.value)
        valTab.append(config.plugins.iptvplayer.skin.value)
        valTab.append(config.plugins.iptvplayer.skinforceinternal.value)
        return valTab

    def getMessageAfterSave(self):
        if self.runtimeOptionsValues != self.getRuntimeOptionsValues():
            return _('Some settings will be applied only after GUI restart.')
        else:
            return ''

    def getMessageBeforeClose(self, afterSave):
        return ''

    def closeAfterMessage(self, arg=None):
        self.close()
        """
        if arg:
            # self.doUpdate(True)
            self.close()
        else:
            self.close()
        """

    def keyOK(self):
        curIndex = self["config"].getCurrentIndex()
        currItem = self["config"].list[curIndex][1]
        if isinstance(currItem, ConfigDirectory):
            def SetDirPathCallBack(curIndex, newPath):
                if None is not newPath:
                    self["config"].list[curIndex][1].value = newPath
            self.session.openWithCallback(boundFunction(SetDirPathCallBack, curIndex), IPTVDirectorySelectorWidget, currDir=currItem.value, title=_("Select directory"))
        elif config.plugins.iptvplayer.fakePin == currItem:
            self.changePin(start=True)
        elif config.plugins.iptvplayer.fakeHostsList == currItem:
            self.hostsList()
        elif config.plugins.iptvplayer.fakExtMoviePlayerList == currItem:
            self.extMoviePlayerList()
        elif config.plugins.iptvplayer.fakeCookiesCacheDelete == currItem:
            self.confirmDeleteCacheNow(_("cookies cache"), GetCookieDir())
        elif config.plugins.iptvplayer.fakeJSCacheDelete == currItem:
            self.confirmDeleteCacheNow(_("JS cache"), GetJSCacheDir())
        elif config.plugins.iptvplayer.fakeSubtitlesCacheDelete == currItem:
            self.confirmDeleteCacheNow(_("subtitles cache"), GetSubtitlesDir())
        elif config.plugins.iptvplayer.fakeMovieMetaDataCacheDelete == currItem:
            self.confirmDeleteCacheNow(_("movie metadata cache"), GetMovieMetaDataDir())
        elif config.plugins.iptvplayer.fakeMoviePlayerCacheDelete == currItem:
            self.confirmDeleteCacheNow(_("movie player preferences"), GetMoviePlayerPerHostDir())
        elif config.plugins.iptvplayer.fakeHostOrderCacheDelete == currItem:
            self.confirmDeleteCacheNow(_("host order and groups"), GetHostOrderDir())
        elif config.plugins.iptvplayer.fakeIconsCacheDelete == currItem:
            self.session.openWithCallback(self.deleteIconsCacheNowCallback, MessageBox, _("Do you really want to delete the thumbnails cache now?"), type=MessageBox.TYPE_YESNO, default=False)
        elif config.plugins.iptvplayer.fakeSearchHistoryDelete == currItem:
            self.confirmDeleteCacheNow(_("search history"), GetSearchHistoryDir())
        elif config.plugins.iptvplayer.fakeFavouritesCacheDelete == currItem:
            self.session.openWithCallback(boundFunction(self.deleteCacheNowCallback, GetFavouritesDir()), MessageBox, _("Do you really want to delete ALL favourites and watched status now? This is real user data, not just cache, and cannot be undone."), type=MessageBox.TYPE_YESNO, default=False)
        elif config.plugins.iptvplayer.fakeAllCacheDelete == currItem:
            self.session.openWithCallback(boundFunction(self.deleteCacheNowCallback, config.plugins.iptvplayer.CacheDir.value), MessageBox, _("Do you really want to delete ALL cache data now? This includes cookies, subtitles, movie metadata and thumbnails, and cannot be undone."), type=MessageBox.TYPE_YESNO, default=False)
        elif config.plugins.iptvplayer.fakeAllConfigDelete == currItem:
            self.session.openWithCallback(boundFunction(self.deleteCacheNowCallback, config.plugins.iptvplayer.ConfigDir.value), MessageBox, _("Do you really want to delete ALL config data now? This is real user data, not just cache - it includes favourites, watched status, search history, movie player preferences and host order/groups, and cannot be undone."), type=MessageBox.TYPE_YESNO, default=False)
        else:
            ConfigBaseWidget.keyOK(self)

    def confirmDeleteCacheNow(self, label, path):
        self.session.openWithCallback(boundFunction(self.deleteCacheNowCallback, path), MessageBox, _("Do you really want to delete the %s now?") % label, type=MessageBox.TYPE_YESNO, default=False)

    def deleteCacheNowCallback(self, path, ret=False):
        if ret:
            RemoveDirContents(path)

    def deleteIconsCacheNowCallback(self, ret=False):
        # icon batch dirs live directly under CacheDir (not a fixed
        # "icons/" subfolder like the others), so RemoveDirContents()
        # would also wipe cookies/JSCache/etc. - RemoveAllDirsIconsFromPath
        # only targets the recognized icon-batch-dir naming pattern
        if ret:
            RemoveAllDirsIconsFromPath(config.plugins.iptvplayer.CacheDir.value)

    def keyDefaults(self):
        def keyDefaultsConfirm(result):
            if result:
                for item in self.list:
                    if len(item) > 1:
                        configItem = item[1]
                        if not isinstance(configItem, ConfigText):
                            configItem.value = configItem.default
                self.close()
        message = _("Are you sure you want to reset all settings to their default values?")
        self.session.openWithCallback(keyDefaultsConfirm, MessageBox, text=message, type=MessageBox.TYPE_YESNO)

    def getSubOptionsList(self):
        tab = [
            config.plugins.iptvplayer.buforowanie,
            config.plugins.iptvplayer.buforowanie_m3u8,
            config.plugins.iptvplayer.buforowanie_rtmp,
            config.plugins.iptvplayer.showcover,
            # config.plugins.iptvplayer.ListaGraficzna,
            config.plugins.iptvplayer.pluginProtectedByPin,
            config.plugins.iptvplayer.configProtectedByPin,
            config.plugins.iptvplayer.osk_type,
            config.plugins.iptvplayer.plugin_autostart,
            config.plugins.iptvplayer.favourites_use_watched_flag,
            config.plugins.iptvplayer.storageExpertMode,
            config.plugins.iptvplayer.hostsListType
            # config.plugins.iptvplayer.captcha_bypass_free,
            # config.plugins.iptvplayer.captcha_bypass_pay
        ]
        players = []
        players.append(config.plugins.iptvplayer.defaultMoviePlayer0)
        players.append(config.plugins.iptvplayer.alternativeMoviePlayer0)
        players.append(config.plugins.iptvplayer.defaultMoviePlayer)
        players.append(config.plugins.iptvplayer.alternativeMoviePlayer)
        tab.extend(players)
        return tab

    def changePin(self, pin=None, start=False):
        # 'PUT_OLD_PIN', 'PUT_NEW_PIN', 'CONFIRM_NEW_PIN'
        if True is start:
            self.changingPinState = 'PUT_OLD_PIN'
            self.session.openWithCallback(self.changePin, IPTVPinWidget, title=_("Enter old pin"))
        else:
            if pin is None:
                return
            if 'PUT_OLD_PIN' == self.changingPinState:
                if pin == config.plugins.iptvplayer.pin.value:
                    self.changingPinState = 'PUT_NEW_PIN'
                    self.session.openWithCallback(self.changePin, IPTVPinWidget, title=_("Enter new pin"))
                else:
                    self.session.open(MessageBox, _("Pin incorrect!"), type=MessageBox.TYPE_INFO, timeout=5)
            elif 'PUT_NEW_PIN' == self.changingPinState:
                self.newPin = pin
                self.changingPinState = 'CONFIRM_NEW_PIN'
                self.session.openWithCallback(self.changePin, IPTVPinWidget, title=_("Confirm new pin"))
            elif 'CONFIRM_NEW_PIN' == self.changingPinState:
                if self.newPin == pin:
                    config.plugins.iptvplayer.pin.value = pin
                    config.plugins.iptvplayer.pin.save()
                    configfile.save()
                    self.session.open(MessageBox, _("Pin has been changed."), type=MessageBox.TYPE_INFO, timeout=5)
                else:
                    self.session.open(MessageBox, _("Confirmation error."), type=MessageBox.TYPE_INFO, timeout=5)

    def hostsList(self):
        self.session.open(ConfigHostsMenu, GetListOfHostsNames())

    def extMoviePlayerList(self):
        self.session.open(ConfigExtMoviePlayer)


def GetAvailableMoviePlayers():
    # 'mini'/'standard' are always available (built in); the external ones
    # only when their binary is actually present. Shared by GetMoviePlayer()
    # (default/alternative slot resolution) and the "Select movie player"
    # blue-key menu (lists every one of these directly, not just the two
    # configured slots)
    availablePlayers = []
    if IsExecutable("/usr/bin/exteplayer3"):  # config.plugins.iptvplayer.exteplayer3path.value):
        availablePlayers.append('exteplayer')
    if IsExecutable('/usr/bin/gstplayer'):
        availablePlayers.append('extgstplayer')
    availablePlayers.append('mini')
    availablePlayers.append('standard')
    return availablePlayers


def GetMoviePlayer(buffering=False, useAlternativePlayer=False):
    printDBG("GetMoviePlayer buffering[%r], useAlternativePlayer[%r]" % (buffering, useAlternativePlayer))
    # select movie player
    availablePlayers = GetAvailableMoviePlayers()

    player = None
    alternativePlayer = None

    if buffering:
        player = config.plugins.iptvplayer.defaultMoviePlayer
        alternativePlayer = config.plugins.iptvplayer.alternativeMoviePlayer
    else:
        player = config.plugins.iptvplayer.defaultMoviePlayer0
        alternativePlayer = config.plugins.iptvplayer.alternativeMoviePlayer0

    if player.value == 'auto':
        player = CFakeMoviePlayerOption(availablePlayers[0], GetMoviePlayerName(availablePlayers[0]))
    try:
        availablePlayers.remove(player.value)
    except Exception:
        printExc()

    if alternativePlayer.value == 'auto':
        alternativePlayer = CFakeMoviePlayerOption(availablePlayers[0], GetMoviePlayerName(availablePlayers[0]))
    try:
        availablePlayers.remove(alternativePlayer.value)
    except Exception:
        printExc()

    if useAlternativePlayer:
        return alternativePlayer

    return player
