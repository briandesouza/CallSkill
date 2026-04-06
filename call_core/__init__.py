"""Portable audio core for call mode."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "AudioClip",
    "AudioPlaybackError",
    "CallCoreError",
    "ElevenLabsSTTProvider",
    "ElevenLabsTTSProvider",
    "Recorder",
    "STTError",
    "STTProvider",
    "SpeechConfigurationError",
    "SpeechProviderError",
    "TTSError",
    "TTSProvider",
    "pcm_to_wav",
    "play_audio_clip",
]

_EXPORTS = {
    "AudioClip": ("call_core.audio", "AudioClip"),
    "AudioPlaybackError": ("call_core.errors", "AudioPlaybackError"),
    "CallCoreError": ("call_core.errors", "CallCoreError"),
    "ElevenLabsSTTProvider": ("call_core.stt", "ElevenLabsSTTProvider"),
    "ElevenLabsTTSProvider": ("call_core.tts", "ElevenLabsTTSProvider"),
    "Recorder": ("call_core.recorder", "Recorder"),
    "STTError": ("call_core.errors", "STTError"),
    "STTProvider": ("call_core.stt", "STTProvider"),
    "SpeechConfigurationError": ("call_core.errors", "SpeechConfigurationError"),
    "SpeechProviderError": ("call_core.errors", "SpeechProviderError"),
    "TTSError": ("call_core.errors", "TTSError"),
    "TTSProvider": ("call_core.tts", "TTSProvider"),
    "pcm_to_wav": ("call_core.recorder", "pcm_to_wav"),
    "play_audio_clip": ("call_core.audio", "play_audio_clip"),
}


def __getattr__(name: str):
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = import_module(module_name)
    return getattr(module, attr_name)
