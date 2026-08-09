# API keys preferred in /etc/enigma2/ailivesubs.keys (groq=... / gemini=...)
# -*- coding: utf-8 -*-
from Components.config import config, ConfigSubsection, ConfigYesNo, ConfigSelection, ConfigText, ConfigInteger

config.plugins.iptvplayer.ailivesubs = ConfigSubsection()
config.plugins.iptvplayer.ailivesubs.enabled = ConfigYesNo(default=False)
config.plugins.iptvplayer.ailivesubs.provider = ConfigSelection(default="groq", choices=[
    ("groq", "Groq (Recommended - Free)"),
    ("gemini", "Google Gemini"),
])
config.plugins.iptvplayer.ailivesubs.api_key_groq = ConfigText(default="", fixed_size=False)
config.plugins.iptvplayer.ailivesubs.api_key_gemini = ConfigText(default="", fixed_size=False)
config.plugins.iptvplayer.ailivesubs.target_lang = ConfigSelection(default="ar", choices=[
    ("ar", "العربية"),
    ("en", "English"),
    ("fr", "Français"),
    ("tr", "Türkçe"),
    ("de", "Deutsch"),
    ("es", "Español"),
    ("it", "Italiano"),
    ("ru", "Русский"),
    ("pl", "Polski"),
    ("pt", "Português"),
])
config.plugins.iptvplayer.ailivesubs.chunk = ConfigSelection(default="2", choices=[
    ("2", "2 seconds (best sync)"),
    ("3", "3 seconds (fastest / less lag)"),
    ("4", "4 seconds (balanced)"),
    ("5", "5 seconds (more accurate)"),
])
config.plugins.iptvplayer.ailivesubs.position = ConfigSelection(default="bottom", choices=[
    ("bottom", "Bottom of screen"),
    ("top", "Top of screen"),
])

# Font appearance
config.plugins.iptvplayer.ailivesubs.font_name = ConfigSelection(default="Regular", choices=[
    ("Regular", "Regular"),
    ("Regular;Bold", "Bold"),
    ("Arial", "Arial"),
    ("Verdana", "Verdana"),
    ("DejaVuSans", "DejaVu Sans"),
    ("FreeSans", "FreeSans"),
    ("lcd", "LCD"),
])
config.plugins.iptvplayer.ailivesubs.font_size = ConfigInteger(default=34, limits=(18, 72))
config.plugins.iptvplayer.ailivesubs.font_color = ConfigSelection(default="#FFFFFF", choices=[
    ("#FFFFFF", "White"),
    ("#FFFF00", "Yellow"),
    ("#00FF00", "Green"),
    ("#00FFFF", "Cyan"),
    ("#FFD700", "Gold"),
    ("#FFA500", "Orange"),
    ("#FF69B4", "Pink"),
    ("#ADFF2F", "GreenYellow"),
    ("#87CEEB", "SkyBlue"),
    ("#F5F5DC", "Beige"),
])
config.plugins.iptvplayer.ailivesubs.border_enabled = ConfigYesNo(default=True)
config.plugins.iptvplayer.ailivesubs.border_color = ConfigSelection(default="#000000", choices=[
    ("#000000", "Black"),
    ("#222222", "Dark gray"),
    ("#FFFFFF", "White"),
    ("#0000AA", "Dark blue"),
])

config.plugins.iptvplayer.ailivesubs.prefer_srt = ConfigYesNo(default=True)

config.plugins.iptvplayer.ailivesubs.economy_mode = ConfigYesNo(default=False)
config.plugins.iptvplayer.ailivesubs.stt_language = ConfigSelection(default="auto", choices=[
    ("auto", "Auto detect"),
    ("en", "English"),
    ("ar", "Arabic"),
    ("fr", "French"),
    ("tr", "Turkish"),
    ("de", "German"),
    ("es", "Spanish"),
])
config.plugins.iptvplayer.ailivesubs.ai_time_shift = ConfigSelection(default="0", choices=[
    ("-2", "-2 sec (show earlier / less lag feel)"),
    ("-1", "-1 sec"),
    ("0", "0 (normal)"),
    ("1", "+1 sec (show later)"),
    ("2", "+2 sec"),
    ("3", "+3 sec"),
])
