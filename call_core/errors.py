"""Shared exceptions for speech providers and playback."""


class CallCoreError(RuntimeError):
    """Base error for call core failures."""


class SpeechConfigurationError(CallCoreError):
    """Raised when local speech-provider configuration is missing or invalid."""


class SpeechProviderError(CallCoreError):
    """Raised when a remote speech provider request fails."""


class STTError(SpeechProviderError):
    """Raised when speech-to-text fails."""


class TTSError(SpeechProviderError):
    """Raised when text-to-speech fails."""


class AudioPlaybackError(CallCoreError):
    """Raised when local audio playback fails."""
