# -*- coding: utf-8 -*-
"""
Local subtitles finder + encoding/format helpers.
Supports: .srt .vtt .ass (ass/vtt converted to srt when needed)
"""
import os
import re
import codecs

HDD_SUB_DIRS = (
    "/hdd/subtitles",
    "/hdd/subtitle",
    "/media/hdd/subtitles",
    "/media/hdd/subtitle",
    "/hdd/movie/subtitles",
    "/hdd/movie/subtitle",
)
CACHE_DIR = "/tmp/e2i_ai_srt"
SUB_EXTS = (".srt", ".vtt", ".ass", ".ssa")


def _sub_root():
    for d in HDD_SUB_DIRS:
        try:
            parent = os.path.dirname(d.rstrip("/"))
            if parent and not os.path.isdir(parent):
                continue
            if not os.path.isdir(d):
                os.makedirs(d)
            if os.path.isdir(d) and os.access(d, os.W_OK):
                return d
        except Exception:
            pass
    try:
        if not os.path.isdir(CACHE_DIR):
            os.makedirs(CACHE_DIR)
    except Exception:
        pass
    return CACHE_DIR


def _clean_title(title):
    if not title:
        return ""
    t = title
    t = re.sub(r"\s*[-–]\s*\[.*?\]\s*$", "", t)
    t = re.sub(r"\.(720p|1080p|2160p|4k|bluray|web-?dl|hdrip|x264|x265|hevc).*", "", t, flags=re.I)
    t = re.sub(r"[_\.]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _basename_title(path):
    if not path:
        return ""
    try:
        base = os.path.basename(str(path).replace("file://", "").split("?")[0])
        name, ext = os.path.splitext(base)
        ext = ext.lower()
        if ext in (".ts", ".mts", ".m2ts", ".mp4", ".mkv", ".avi", ".mpg", ".mpeg", ".flv", ".mov", ".wmv"):
            return name
        if name.startswith(".iptv_buffering"):
            return ""
        return name
    except Exception:
        return ""


def _score_name(title, filename_stem):
    from difflib import SequenceMatcher
    NOISE = {
        "the", "and", "or", "of", "a", "an", "le", "la", "el", "al",
        "720p", "1080p", "2160p", "4k", "bluray", "webrip", "webdl", "x264", "x265", "hevc",
        "srt", "vtt", "ass", "ssa", "sub", "subs", "ar", "en", "fr", "ara", "eng",
        "arabic", "english", "yify", "rarbg",
    }

    def normalize(s):
        s = (s or "").lower().replace("&", " and ")
        s = re.sub(r"[\[\(].*?[\]\)]", " ", s)
        for ch in "._-+,'\"!?:;":
            s = s.replace(ch, " ")
        return " ".join(s.split())

    def toks(s):
        years, words = [], []
        for w in normalize(s).split():
            w2 = "".join(c for c in w if c.isalnum())
            if not w2:
                continue
            if w2.isdigit() and len(w2) == 4 and w2.startswith(("19", "20")):
                years.append(w2)
                continue
            if w2 in NOISE or len(w2) < 2:
                continue
            words.append(w2)
        return words, years

    tw, ty = toks(title)
    fw, fy = toks(filename_stem)
    if not tw:
        tw = [w for w in normalize(title).split() if len(w) >= 2]
    if not tw or not fw:
        return 0.0

    r = SequenceMatcher(None, " ".join(tw), " ".join(fw)).ratio()
    hits = sum(1 for w in tw if w in fw)
    cov = float(hits) / float(len(tw))
    conf = r * 50 + cov * 35 + hits * 5
    if ty and fy:
        conf += 15 if ty[0] in fy else -25
    if tw[0] == fw[0]:
        conf += 8
    n = len(tw)
    ok = False
    if r >= 0.78:
        ok = True
    if n == 1 and (tw[0] in fw or r >= 0.72):
        ok = True
    if n >= 2 and hits >= max(2, int(round(n * 0.6))) and r >= 0.55:
        ok = True
    if n >= 2 and cov >= 0.75 and hits >= 2:
        ok = True
    if "".join(tw) == "".join(fw):
        ok = True
        conf = max(conf, 90)
    if not ok or conf < 40:
        return 0.0
    if ty and fy and ty[0] not in fy and r < 0.90:
        return 0.0
    return conf


def find_all_local_subs(title, local_file="", extra_titles=None):
    """Return list of (score, path) sorted best-first for .srt/.vtt/.ass."""
    _sub_root()
    names = []
    for t in [title, _basename_title(local_file)] + list(extra_titles or []):
        t = _clean_title(t) or (t or "").strip()
        if t and t not in names:
            names.append(t)
    if not names:
        return []

    bases = []
    for d in list(HDD_SUB_DIRS) + [_sub_root(),]:
        if d and d not in bases:
            bases.append(d)
    if local_file:
        try:
            d = os.path.dirname(local_file)
            if d and d not in bases:
                bases.append(d)
        except Exception:
            pass
    try:
        from Components.config import config
        d = config.plugins.iptvplayer.NaszaSciezka.value
        if d and d not in bases:
            bases.append(d)
    except Exception:
        pass
    for d in ("/hdd/movie", "/media/hdd/movie", CACHE_DIR, "/tmp"):
        if d not in bases:
            bases.append(d)

    found = {}
    for base in bases:
        if not base or not os.path.isdir(base):
            continue
        try:
            files = os.listdir(base)
        except Exception:
            continue
        for fn in files:
            low = fn.lower()
            if not any(low.endswith(ext) for ext in SUB_EXTS):
                continue
            stem = fn.rsplit(".", 1)[0]
            best = 0.0
            for name in names:
                sc = _score_name(name, stem)
                if sc > best:
                    best = sc
            if best <= 0:
                continue
            path = os.path.join(base, fn)
            prev = found.get(path)
            if prev is None or best > prev:
                found[path] = best

    items = [(sc, path) for path, sc in found.items()]
    items.sort(key=lambda x: -x[0])
    return items


def find_local_srt(title, local_file="", lang=None):
    items = find_all_local_subs(title, local_file=local_file)
    return items[0][1] if items else ""


def fetch_best_srt(title, local_file="", lang=None, extra_titles=None):
    items = find_all_local_subs(title, local_file=local_file, extra_titles=extra_titles)
    if not items:
        print("[SRT] no local match")
        return ""
    print("[SRT] best conf=%.1f -> %s (total %d)" % (items[0][0], items[0][1], len(items)))
    return items[0][1]


def _read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def _decode_sub_bytes(data):
    """Try UTF-8 / CP1256 / Latin-1 for Arabic-friendly decoding."""
    if data.startswith(codecs.BOM_UTF8):
        return data[3:].decode("utf-8", "ignore"), "utf-8-sig"
    for enc in ("utf-8", "cp1256", "iso-8859-6", "windows-1256", "cp1252", "iso-8859-1", "latin-1"):
        try:
            text = data.decode(enc)
            # heuristic: if many replacement-looking issues skip
            if enc == "utf-8" or True:
                return text, enc
        except Exception:
            continue
    return data.decode("utf-8", "ignore"), "utf-8"


def vtt_to_srt(text):
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out = []
    idx = 1
    i = 0
    if lines and lines[0].strip().upper().startswith("WEBVTT"):
        i = 1
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        # optional cue id
        if "-->" not in line and i < len(lines) and "-->" in lines[i]:
            line = lines[i].strip()
            i += 1
        if "-->" not in line:
            continue
        timing = line.replace(".", ",").split("-->")
        if len(timing) != 2:
            continue
        start = timing[0].strip()
        end = timing[1].strip().split(" ")[0].strip()
        # normalize to srt time HH:MM:SS,mmm
        def fix_t(t):
            t = t.replace(".", ",")
            if t.count(":") == 1:
                t = "00:" + t
            return t
        start, end = fix_t(start), fix_t(end)
        body = []
        while i < len(lines) and lines[i].strip():
            body.append(re.sub(r"<[^>]+>", "", lines[i].strip()))
            i += 1
        if not body:
            continue
        out.append(str(idx))
        out.append("%s --> %s" % (start, end))
        out.extend(body)
        out.append("")
        idx += 1
    return "\n".join(out)


def ass_to_srt(text):
    """Very small ASS/SSA dialogue extractor."""
    out = []
    idx = 1
    for line in text.replace("\r\n", "\n").split("\n"):
        if not line.startswith("Dialogue:"):
            continue
        # Dialogue: Layer, Start, End, Style, Name, M,L,V, Effect, Text
        try:
            payload = line[len("Dialogue:"):].strip()
            parts = payload.split(",", 9)
            if len(parts) < 10:
                continue
            start, end, body = parts[1].strip(), parts[2].strip(), parts[9]
            body = re.sub(r"\{[^}]*\}", "", body).replace("\\N", "\n").replace("\\n", "\n")
            body = body.strip()
            if not body:
                continue

            def ass_time(t):
                # H:MM:SS.cs -> HH:MM:SS,mmm
                h, m, s = t.split(":")
                if "." in s:
                    sec, cs = s.split(".", 1)
                    ms = int((cs + "00")[:2]) * 10
                else:
                    sec, ms = s, 0
                return "%02d:%02d:%02d,%03d" % (int(h), int(m), int(sec), ms)

            out.append(str(idx))
            out.append("%s --> %s" % (ass_time(start), ass_time(end)))
            out.extend(body.split("\n"))
            out.append("")
            idx += 1
        except Exception:
            continue
    return "\n".join(out)


def prepare_sub_file(path, delay_ms=0):
    """
    Normalize subtitle file to UTF-8 SRT.
    Optionally shift all cues by delay_ms (can be negative).
    Returns path to usable file (may be original or /tmp copy).
    """
    if not path or not os.path.exists(path):
        return ""
    low = path.lower()
    data = _read_bytes(path)
    text, enc = _decode_sub_bytes(data)
    print("[SRT] decoded as", enc, "from", path)

    if low.endswith(".vtt"):
        text = vtt_to_srt(text)
        low = ".srt"
    elif low.endswith(".ass") or low.endswith(".ssa"):
        text = ass_to_srt(text)
        low = ".srt"

    if delay_ms:
        text = shift_srt_delay(text, delay_ms)

    # Always write UTF-8 cleaned copy when encoding wasn't utf-8 or converted/shifted
    need_copy = (enc not in ("utf-8", "utf-8-sig")) or delay_ms or path.lower().endswith((".vtt", ".ass", ".ssa"))
    if not need_copy:
        # still ensure it looks like srt
        return path

    _sub_root()
    out = os.path.join(CACHE_DIR, "prepared_%s.srt" % abs(hash(path + str(delay_ms))) % 10**10)
    try:
        if not os.path.isdir(CACHE_DIR):
            os.makedirs(CACHE_DIR)
        with open(out, "wb") as f:
            f.write(text.encode("utf-8"))
        return out
    except Exception as e:
        print("[SRT] prepare failed:", e)
        return path


def shift_srt_delay(text, delay_ms):
    def shift_ts(ts):
        # 00:00:01,000
        m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)", ts.strip())
        if not m:
            return ts
        h, mi, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int((m.group(4) + "000")[:3])
        total = ((h * 60 + mi) * 60 + s) * 1000 + ms + int(delay_ms)
        if total < 0:
            total = 0
        ms = total % 1000
        total //= 1000
        s = total % 60
        total //= 60
        mi = total % 60
        h = total // 60
        return "%02d:%02d:%02d,%03d" % (h, mi, s, ms)

    out_lines = []
    for line in text.splitlines():
        if "-->" in line:
            a, b = line.split("-->", 1)
            out_lines.append("%s --> %s" % (shift_ts(a), shift_ts(b.split()[0] if b.strip() else b)))
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def detect_subssupport():
    try:
        __import__("Plugins.Extensions.SubsSupportPro.plugin")
        return "pro"
    except Exception:
        pass
    try:
        __import__("Plugins.Extensions.SubsSupport.plugin")
        return "classic"
    except Exception:
        pass
    return None


def open_subssupport_search(session, title=""):
    if session is None:
        return False
    titles = []
    ct = _clean_title(title)
    if ct:
        titles.append(ct)
    if title and title not in titles:
        titles.append(title)
    try:
        from Plugins.Extensions.SubsSupportPro.subtitles import E2SubsSeeker, SubsProSearch, initSubsProSettings
        settings = initSubsProSettings().search
        session.open(SubsProSearch, E2SubsSeeker(session, settings), settings, searchTitles=titles or [""], standAlone=True)
        return True
    except Exception as e:
        print("[SRT] Pro open failed:", e)
    try:
        from Plugins.Extensions.SubsSupport.subtitles import E2SubsSeeker, SubsSearch, initSubsSettings
        settings = initSubsSettings().search
        session.open(SubsSearch, E2SubsSeeker(session, settings), settings, searchTitles=titles or [""], standAlone=True)
        return True
    except Exception as e:
        print("[SRT] classic open failed:", e)
    for mod in ("Plugins.Extensions.SubsSupportPro.plugin", "Plugins.Extensions.SubsSupport.plugin"):
        try:
            m = __import__(mod, fromlist=["openSubtitlesSearch"])
            fn = getattr(m, "openSubtitlesSearch", None)
            if fn:
                fn(session)
                return True
        except Exception:
            pass
    return False
