# -*- coding: utf-8 -*-
"""
Dedicated file for AI Live Subtitles API keys.
Path: /etc/enigma2/ailivesubs.keys

Format (one per line):
  groq=gsk_xxxx
  gemini=xxxx
"""
import os

KEYS_FILE = "/etc/enigma2/ailivesubs.keys"
_FALLBACK = "/hdd/ailivesubs.keys"

def _path():
    # prefer /etc/enigma2, fallback to /hdd if not writable
    try:
        d = os.path.dirname(KEYS_FILE)
        if os.path.isdir(d) and os.access(d, os.W_OK):
            return KEYS_FILE
    except Exception:
        pass
    return _FALLBACK

def load_keys():
    """Return dict: {'groq': '...', 'gemini': '...'}"""
    out = {"groq": "", "gemini": "", "opensubtitles": ""}
    path = _path()
    # also try both locations for read
    for p in (KEYS_FILE, _FALLBACK, path):
        try:
            if not os.path.exists(p):
                continue
            with open(p, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip().lower()
                    v = v.strip().strip('"').strip("'")
                    if k in ("groq", "api_key_groq", "groq_api_key"):
                        out["groq"] = v
                    elif k in ("gemini", "api_key_gemini", "gemini_api_key"):
                        out["gemini"] = v
                    elif k in ("opensubtitles", "opensubtitles_api", "os_api", "opensubtitles_key"):
                        out["opensubtitles"] = v
            if out["groq"] or out["gemini"]:
                break
        except Exception:
            pass
    return out

def save_keys(groq="", gemini=""):
    """Write keys file. Empty string keeps existing value if not provided carefully —
    pass the full values you want stored."""
    path = _path()
    try:
        # merge with existing so we don't wipe the other key accidentally
        cur = load_keys()
        if groq is not None:
            cur["groq"] = groq.strip() if isinstance(groq, str) else cur["groq"]
        if gemini is not None:
            cur["gemini"] = gemini.strip() if isinstance(gemini, str) else cur["gemini"]
        lines = [
            "# AI Live Subtitles API keys — do not share this file",
            "groq=%s" % cur.get("groq", ""),
            "gemini=%s" % cur.get("gemini", ""),
            "opensubtitles=%s" % cur.get("opensubtitles", ""),
            "",
        ]
        with open(path, "w") as f:
            f.write("\n".join(lines))
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass
        return path
    except Exception as e:
        print("[AILiveSubs] save_keys error:", e)
        return None

def get_groq_key():
    # 1) dedicated file
    k = load_keys().get("groq", "").strip()
    if k:
        return k
    # 2) fallback to enigma2 settings (legacy)
    try:
        from Components.config import config
        k = config.plugins.iptvplayer.ailivesubs.api_key_groq.value.strip()
        if k:
            return k
    except Exception:
        pass
    return ""

def get_gemini_key():
    k = load_keys().get("gemini", "").strip()
    if k:
        return k
    try:
        from Components.config import config
        k = config.plugins.iptvplayer.ailivesubs.api_key_gemini.value.strip()
        if k:
            return k
    except Exception:
        pass
    return ""

def sync_from_config():
    """If user typed keys in e2iplayer settings, copy them into the keys file."""
    try:
        from Components.config import config
        g = config.plugins.iptvplayer.ailivesubs.api_key_groq.value.strip()
        m = config.plugins.iptvplayer.ailivesubs.api_key_gemini.value.strip()
        if g or m:
            save_keys(groq=g or None, gemini=m or None)
            # optional: clear from settings so key is only in the file
            # (keep values in config too for UI display if desired)
    except Exception as e:
        print("[AILiveSubs] sync_from_config:", e)
