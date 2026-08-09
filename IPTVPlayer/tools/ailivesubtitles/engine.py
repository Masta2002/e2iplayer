# -*- coding: utf-8 -*-
"""
AI Live Subtitles — sync-optimized.
Strategy:
 1) Short chunks (2–3s)
 2) Capture at exact playback position
 3) Show STT text immediately, then replace with translation
 4) Prefetch next audio while STT/TR runs
"""
import os
import time
import threading
import subprocess
import requests
from Components.config import config
try:
    from Plugins.Extensions.IPTVPlayer.tools.ailivesubtitles.keys import get_groq_key
except Exception:
    def get_groq_key():
        try:
            return config.plugins.iptvplayer.ailivesubs.api_key_groq.value.strip()
        except Exception:
            return ""

class _NullOverlay(object):
    active = False
    def setStatus(self, *a, **k): pass
    def setSubtitle(self, *a, **k): pass
    def clear(self, *a, **k): pass
    def reactivate(self, *a, **k): pass

class AIEngine:
    def __init__(self, overlay, stream_url="", headers=None, local_file="", get_time_callback=None):
        self.overlay = overlay
        self.stream_url = (stream_url or "").strip()
        self.local_file = (local_file or "").strip()
        self.headers = headers or {}
        self.get_time = get_time_callback
        self.running = False
        self.thread = None
        self.proc = None
        self._cap_lock = threading.Lock()
        self.wav_a = "/tmp/e2i_ai_a.wav"
        self.wav_b = "/tmp/e2i_ai_b.wav"
        self._last_sub_time = 0
        try:
            self.chunk = int(config.plugins.iptvplayer.ailivesubs.chunk.value)
        except Exception:
            self.chunk = 2
        # Economy mode: longer chunks = fewer API calls
        economy = False
        try:
            economy = bool(config.plugins.iptvplayer.ailivesubs.economy_mode.value)
        except Exception:
            pass
        if economy:
            self.chunk = max(self.chunk, 5)
            self.chunk = min(self.chunk, 8)
        else:
            self.chunk = max(2, min(int(self.chunk), 3))
        self.economy = economy
        try:
            self.ai_shift = float(config.plugins.iptvplayer.ailivesubs.ai_time_shift.value)
        except Exception:
            self.ai_shift = 0.0

    def start(self):
        if self.running:
            return
        self.running = True
        self._last_sub_time = 0
        self.thread = threading.Thread(target=self._loop)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        try:
            self.overlay.clear()
        except Exception:
            pass
        self._kill_proc()
        for p in (self.wav_a, self.wav_b):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        self.overlay = _NullOverlay()

    def _kill_proc(self):
        try:
            if self.proc is not None and self.proc.poll() is None:
                self.proc.kill()
                try:
                    self.proc.wait(timeout=1)
                except Exception:
                    pass
        except Exception:
            pass
        self.proc = None

    def _capture_pos(self):
        """Playback position adjusted by AI time shift (negative = look further ahead)."""
        pos = self._current_sec()
        shift = float(getattr(self, "ai_shift", 0) or 0)
        # Negative shift: capture slightly ahead so text matches later display better
        if shift < 0:
            pos = max(0, int(pos - shift))  # -shift is positive
        return pos

    def _current_sec(self):
        try:
            if self.get_time:
                t = self.get_time()
                if t is None:
                    return 0
                t = int(t)
                return t if t > 0 else 0
        except Exception:
            pass
        return 0

    def _loop(self):
        use_a = True
        self.overlay.setStatus("Capturing...")
        pos = self._capture_pos()
        cur = self.wav_a
        self._capture_audio(pos, cur)

        while self.running:
            try:
                # Clear stale line after 6s (shorter = less "stuck" feel)
                if self._last_sub_time and (time.time() - self._last_sub_time) > 6:
                    try:
                        self.overlay.setSubtitle("")
                    except Exception:
                        pass
                    self._last_sub_time = 0

                if not os.path.exists(cur) or os.path.getsize(cur) < 8000:
                    pos = self._capture_pos()
                    self.overlay.setStatus("Capturing @%ds..." % pos)
                    if not self._capture_audio(pos, cur):
                        self.overlay.setStatus("Capture failed")
                        time.sleep(0.8)
                        continue

                # Prefetch NEXT chunk at near-live position while we process current
                nxt = self.wav_b if use_a else self.wav_a
                next_ok = {"v": False}

                def _prefetch():
                    # Slight lead: capture from current time so next cycle is fresher
                    next_ok["v"] = self._capture_audio(self._capture_pos(), nxt)

                pref = threading.Thread(target=_prefetch)
                pref.daemon = True
                pref.start()

                try:
                    sz = os.path.getsize(cur)
                except Exception:
                    sz = 0
                if sz < 8000:
                    pref.join(timeout=self.chunk + 10)
                    if next_ok["v"]:
                        use_a = not use_a
                        cur = nxt
                    continue

                self.overlay.setStatus("STT...")
                text = self._transcribe(cur)
                if not self.running:
                    break

                text = (text or "").strip()
                if not text or text in (".", "..", "...", "?", "!", "-", "…"):
                    self.overlay.setStatus("")
                    pref.join(timeout=self.chunk + 10)
                    if next_ok["v"]:
                        use_a = not use_a
                        cur = nxt
                    continue

                target = "ar"
                try:
                    target = config.plugins.iptvplayer.ailivesubs.target_lang.value
                except Exception:
                    pass

                # Show ONLY the final language (no original English flash before Arabic)
                if target == "en":
                    show = text
                else:
                    self.overlay.setStatus("TR...")
                    translated = self._translate(text)
                    if not self.running:
                        break
                    show = (translated or text).strip()

                if show and show not in (".", "..", "...", "…"):
                    # AI time shift: positive = show later, negative = show ASAP (no extra wait)
                    shift = float(getattr(self, "ai_shift", 0) or 0)
                    if shift > 0:
                        time.sleep(min(shift, 3.0))
                    if not self.running:
                        break
                    self.overlay.setSubtitle(show)
                    self.overlay.setStatus("")
                    self._last_sub_time = time.time()
                else:
                    self.overlay.setStatus("")

                pref.join(timeout=self.chunk + 10)
                if next_ok["v"]:
                    use_a = not use_a
                    cur = nxt
                else:
                    try:
                        if os.path.exists(cur):
                            os.remove(cur)
                    except Exception:
                        pass

            except Exception as e:
                self.overlay.setStatus("Err: %s" % str(e)[:48])
                time.sleep(1)

            # Minimal gap between cycles
            time.sleep(0.05)

    def _run_ffmpeg(self, cmd, out_path, timeout_sec):
        with self._cap_lock:
            self._kill_proc()
            try:
                if os.path.exists(out_path):
                    os.remove(out_path)
            except Exception:
                pass
            try:
                self.proc = subprocess.Popen(
                    cmd, shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.proc.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                self._kill_proc()
            except Exception as e:
                print("[AIEngine] ffmpeg:", e)
                self._kill_proc()
            self.proc = None
            try:
                return os.path.exists(out_path) and os.path.getsize(out_path) > 8000
            except Exception:
                return False

    def _find_buffer_file(self):
        paths = []
        if self.local_file:
            paths.append(self.local_file)
        try:
            base = config.plugins.iptvplayer.NaszaSciezka.value
            if base:
                paths.append(os.path.join(base, ".iptv_buffering.flv"))
        except Exception:
            pass
        paths.extend([
            "/hdd/movie/.iptv_buffering.flv",
            "/hdd/movie//.iptv_buffering.flv",
            "/media/hdd/movie/.iptv_buffering.flv",
            "/tmp/.iptv_buffering.flv",
        ])
        best, best_sz = "", 0
        for p in paths:
            try:
                if p and os.path.exists(p):
                    sz = os.path.getsize(p)
                    if sz > best_sz:
                        best, best_sz = p, sz
            except Exception:
                pass
        return best if best_sz > 30000 else ""

    def _capture_audio(self, pos_sec, out_path):
        buf = self._find_buffer_file()
        if buf and self._capture_from_file(buf, pos_sec, out_path):
            return True
        if self.stream_url.startswith("http") and self._capture_from_stream(pos_sec, out_path):
            return True
        return False

    def _capture_from_file(self, path, pos_sec, out_path):
        common = (
            "nice -n 10 timeout %d ffmpeg -y -hide_banner -loglevel error "
            "-fflags +genpts+discardcorrupt -err_detect ignore_err "
            "-probesize 1M -analyzeduration 500k "
        ) % (self.chunk + 8)

        # Exact position (no -1 offset) → better match to what user hears soon
        if pos_sec > 0:
            start = max(0, int(pos_sec))
            cmd = (
                common +
                "-ss %d -i \"%s\" -t %d -vn -map 0:a:0? -ac 1 -ar 16000 -c:a pcm_s16le "
                "-threads 1 \"%s\""
            ) % (start, path, self.chunk, out_path)
            if self._run_ffmpeg(cmd, out_path, self.chunk + 10):
                return True
            cmd = (
                common +
                "-i \"%s\" -ss %d -t %d -vn -map 0:a:0? -ac 1 -ar 16000 -c:a pcm_s16le "
                "-threads 1 \"%s\""
            ) % (path, start, self.chunk, out_path)
            if self._run_ffmpeg(cmd, out_path, self.chunk + 12):
                return True

        try:
            sz = os.path.getsize(path)
            guess = max(0, int(sz / 1000000) - self.chunk - 1)
            if guess > 3:
                cmd = (
                    common +
                    "-ss %d -i \"%s\" -t %d -vn -map 0:a:0? -ac 1 -ar 16000 -c:a pcm_s16le "
                    "-threads 1 \"%s\""
                ) % (guess, path, self.chunk, out_path)
                if self._run_ffmpeg(cmd, out_path, self.chunk + 10):
                    return True
        except Exception:
            pass

        cmd = (
            common +
            "-i \"%s\" -t %d -vn -map 0:a:0? -ac 1 -ar 16000 -c:a pcm_s16le "
            "-threads 1 \"%s\""
        ) % (path, self.chunk, out_path)
        return self._run_ffmpeg(cmd, out_path, self.chunk + 10)

    def _capture_from_stream(self, pos_sec, out_path):
        ua = self.headers.get("User-Agent", "Mozilla/5.0")
        referer = self.headers.get("Referer", "")
        origin = self.headers.get("Origin", "")
        hdr = "User-Agent: %s\\r\\n" % ua.replace('"', "")
        if referer:
            hdr += "Referer: %s\\r\\n" % referer.replace('"', "")
        if origin:
            hdr += "Origin: %s\\r\\n" % origin.replace('"', "")
        url = self.stream_url.replace('"', "").replace("`", "")
        ss = ("-ss %d " % max(0, int(pos_sec))) if pos_sec > 0 else ""
        cmd = (
            "nice -n 10 timeout %d ffmpeg -y -hide_banner -loglevel error "
            "-fflags +genpts -headers \"%s\" %s-i \"%s\" -t %d -vn -map 0:a:0? "
            "-ac 1 -ar 16000 -c:a pcm_s16le -threads 1 \"%s\""
        ) % (self.chunk + 14, hdr, ss, url, self.chunk, out_path)
        return self._run_ffmpeg(cmd, out_path, self.chunk + 16)

    def _transcribe(self, wav_path):
        api_key = get_groq_key()
        if not api_key:
            self.overlay.setStatus("No Groq API key")
            time.sleep(1.2)
            return None

        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": "Bearer " + api_key}
        for model in ("whisper-large-v3-turbo", "whisper-large-v3"):
            try:
                stt_lang = "auto"
                try:
                    stt_lang = config.plugins.iptvplayer.ailivesubs.stt_language.value
                except Exception:
                    pass
                with open(wav_path, "rb") as f:
                    files = {
                        "file": ("audio.wav", f, "audio/wav"),
                        "model": (None, model),
                        "response_format": (None, "json"),
                        "temperature": (None, "0"),
                    }
                    if stt_lang and stt_lang != "auto":
                        files["language"] = (None, stt_lang)
                    r = requests.post(url, headers=headers, files=files, timeout=15 if not getattr(self, "economy", False) else 25)
                if r.status_code == 200:
                    return (r.json().get("text") or "").strip()
                if r.status_code in (401, 403):
                    self.overlay.setStatus("API key invalid")
                    time.sleep(2)
                    return None
                if r.status_code == 429:
                    self.overlay.setStatus("API rate limit")
                    time.sleep(2)
                    return None
                if r.status_code == 400 and model == "whisper-large-v3-turbo":
                    with open(wav_path, "rb") as f:
                        files = {
                            "file": ("audio.wav", f, "audio/wav"),
                            "model": (None, model),
                            "response_format": (None, "json"),
                            "temperature": (None, "0"),
                        }
                        r = requests.post(url, headers=headers, files=files, timeout=15)
                    if r.status_code == 200:
                        return (r.json().get("text") or "").strip()
            except Exception as e:
                print("[AIEngine] STT", model, e)
        return None

    def _translate(self, text):
        if len(text.strip()) < 1:
            return ""
        api_key = get_groq_key()
        if not api_key:
            return text

        target = "ar"
        try:
            target = config.plugins.iptvplayer.ailivesubs.target_lang.value
        except Exception:
            pass
        if target == "en":
            return text

        lang_map = {
            "ar": "Arabic", "fr": "French", "tr": "Turkish",
            "de": "German", "es": "Spanish", "it": "Italian",
            "ru": "Russian", "pl": "Polish", "pt": "Portuguese"
        }
        target_name = lang_map.get(target, "Arabic")
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json"
        }
        # Fast model first; accurate fallback only if needed
        system_msg = (
            "You are a professional movie-subtitle translator to %s.\n"
            "STRICT RULES:\n"
            "1) Output ONLY the translated dialogue.\n"
            "2) Never write explanations, apologies, or meta text.\n"
            "3) Never write phrases like: I cannot, I don't know, no translation, "
            "here is the translation, translation:, sorry, as an AI.\n"
            "4) Never invent that a translation is missing — always translate the words given.\n"
            "5) Keep it natural spoken style, max 2 short lines for on-screen subtitles.\n"
            "6) Preserve names when appropriate."
        ) % target_name

        models = ("llama-3.1-8b-instant", "llama-3.3-70b-versatile")
        for model in models:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.0,
                "max_tokens": 90
            }
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=12 if "8b" in model else 18)
                if r.status_code != 200:
                    print("[AIEngine] TR", model, r.status_code, r.text[:120])
                    continue
                out = r.json()["choices"][0]["message"]["content"].strip()
                if len(out) >= 2 and out[0] == out[-1] and out[0] in "\"'":
                    out = out[1:-1].strip()
                out = self._clean_translation(out)
                if out:
                    return out
            except Exception as e:
                print("[AIEngine] Translate:", model, e)
        # Never return AI filler — fall back to original speech text
        return text

    def _clean_translation(self, out):
        """Strip AI meta-phrases; keep only real subtitle text."""
        if not out:
            return ""
        s = out.strip()
        low = s.lower()
        # English meta
        bad_en = (
            "i cannot", "i can't", "i could not", "i don't know", "i do not know",
            "no translation", "cannot translate", "can't translate", "as an ai",
            "as a language model", "here is the translation", "here's the translation",
            "translation:", "sorry,", "i'm sorry", "i am sorry", "unable to",
            "not able to", "no speech", "empty",
        )
        # Arabic meta / filler often produced by models
        bad_ar = (
            "لا يمكنني", "لم أجد", "لا أستطيع", "عذراً", "عذرا", "كذكاء اصطناعي",
            "لا توجد ترجمة", "تعذر الترجمة", "غير قادر", "آسف", "الترجمة:",
            "إليك الترجمة", "ها هي الترجمة", "لا أعرف",
        )
        for b in bad_en:
            if low.startswith(b) or low == b or ("translation" in low and len(s) < 40 and ":" in s):
                # drop pure meta lines
                if len(s) < 80 and any(x in low for x in ("cannot", "can't", "sorry", "unable", "as an ai", "no translation")):
                    return ""
        for b in bad_ar:
            if s.startswith(b) or b in s[:30]:
                if len(s) < 60:
                    return ""
        # Remove leading labels like "Translation:" / "الترجمة:"
        for prefix in ("translation:", "translated:", "arabic:", "الترجمة:", "ترجمة:"):
            if low.startswith(prefix) or s.startswith(prefix):
                s = s.split(":", 1)[-1].strip()
                low = s.lower()
        # Drop if still looks like meta after cleanup
        if not s or len(s) < 1:
            return ""
        if any(x in low for x in ("as an ai", "language model", "i cannot translate")):
            return ""
        return s

