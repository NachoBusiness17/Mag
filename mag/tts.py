"""Default text-to-speech for Mag (Windows-first, zero-dependency).

Speaks Mag's answers and notifications out loud by default so the operator
can hear results while working elsewhere on the machine.

Backend chain (first available wins):
  1. pyttsx3            — cross-platform, if installed
  2. PowerShell SAPI    — Windows native (System.Speech), zero deps
  3. no-op + log        — headless / non-Windows fallback

Disable with env MAG_TTS=0 or MAG_TTS=off. Rate/volume via MAG_TTS_RATE.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from config import ROOT

LOG = ROOT / "logs" / "tts.log"


def _enabled() -> bool:
    v = os.environ.get("MAG_TTS", "1").strip().lower()
    return v not in ("0", "off", "false", "no", "none")


def _log(msg: str) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def _backend_pyttsx3(text: str, rate: int) -> bool:
    try:
        import pyttsx3

        engine = pyttsx3.init()
        engine.setProperty("rate", rate)
        engine.say(text)
        engine.runAndWait()
        return True
    except Exception as e:
        _log(f"pyttsx3 failed: {e}")
        return False


def _backend_powershell(text: str, rate: int) -> bool:
    """Windows SAPI via PowerShell System.Speech (zero deps)."""
    if sys.platform != "win32":
        return False
    # Escape for single-quoted PS string: double any single quotes.
    safe = text.replace("'", "''")
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.Rate = {max(-10, min(10, (rate - 150) // 15))}; "
        f"$s.Speak('{safe}')"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if r.returncode == 0:
            return True
        _log(f"powershell SAPI rc={r.returncode}: {r.stderr[:200]}")
        return False
    except Exception as e:
        _log(f"powershell SAPI error: {e}")
        return False


def speak(text: str, *, force: bool = False) -> bool:
    """Speak `text` out loud. Returns True if a backend produced audio.

    Default-on unless MAG_TTS=0. `force=True` bypasses the env gate.
    """
    if not text or not text.strip():
        return False
    if not force and not _enabled():
        return False

    # Trim to a reasonable spoken length (TTS is linear-time; keep it snappy).
    spoken = " ".join(text.strip().split())
    if len(spoken) > 1200:
        spoken = spoken[:1200] + " ..."

    rate = int(os.environ.get("MAG_TTS_RATE", "170") or "170")

    if _backend_pyttsx3(spoken, rate):
        return True
    if _backend_powershell(spoken, rate):
        return True
    _log(f"no TTS backend available; would speak: {spoken[:200]}")
    return False


def speak_async(text: str, *, force: bool = False) -> None:
    """Speak in a background thread so the caller never blocks."""
    import threading

    def _run() -> None:
        try:
            speak(text, force=force)
        except Exception as e:
            _log(f"async speak error: {e}")

    threading.Thread(target=_run, name="mag-tts", daemon=True).start()


if __name__ == "__main__":
    # CLI: python -m mag.tts "hello from Mag"
    msg = " ".join(sys.argv[1:]) or "Mag text to speech is online."
    ok = speak(msg, force=True)
    print(f"tts ok={ok} backend={'audio' if ok else 'none'}")
