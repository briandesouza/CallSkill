"""Microphone recording with WebRTC VAD silence detection.

Records audio from the default input device. Uses webrtcvad to detect when
the user starts and stops speaking. Returns raw PCM audio (16kHz, 16-bit, mono).

State machine:
    IDLE (waiting for speech)
      | 3 of last 5 frames contain speech
    RECORDING (user is talking)
      | 2 seconds of consecutive non-speech frames
    DONE -> return audio
"""

from __future__ import annotations

import collections
import io
import queue
import wave

import sounddevice as sd
import webrtcvad

SAMPLE_RATE = 16000
FRAME_DURATION_MS = 20
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)  # 320 samples
CHANNELS = 1


class Recorder:
    """Records audio from the microphone with automatic silence detection."""

    def __init__(
        self,
        silence_threshold_sec: float = 2.0,
        max_wait_sec: float = 30.0,
        vad_aggressiveness: int = 3,
        on_event: callable = None,
    ):
        self.silence_threshold_sec = silence_threshold_sec
        self.max_wait_sec = max_wait_sec
        self.vad = webrtcvad.Vad(vad_aggressiveness)
        self._on_event = on_event

    def record(self) -> bytes | None:
        """Record audio until silence is detected after speech.

        Returns raw PCM bytes (16kHz, 16-bit, mono), or None if no speech
        was detected within max_wait_sec.
        """
        audio_queue: queue.Queue[bytes] = queue.Queue()

        def callback(indata, frames, time, status):
            audio_queue.put(bytes(indata))

        IDLE, RECORDING, DONE = 0, 1, 2
        state = IDLE

        recorded_frames: list[bytes] = []
        # Keep ~300ms of audio before speech onset so we don't clip the beginning
        pre_buffer: collections.deque[bytes] = collections.deque(maxlen=15)

        silence_frame_count = 0
        silence_threshold_frames = int(
            self.silence_threshold_sec * 1000 / FRAME_DURATION_MS
        )
        max_wait_frames = int(self.max_wait_sec * 1000 / FRAME_DURATION_MS)

        # Smooth speech onset: require 3 of last 5 frames to be speech
        speech_ring: collections.deque[bool] = collections.deque(maxlen=5)
        idle_frames = 0
        recording_frames = 0
        frames_per_sec = int(1000 / FRAME_DURATION_MS)  # 50

        def _notify(event, data=None):
            if self._on_event:
                self._on_event(event, data or {})

        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=FRAME_SIZE,
            dtype="int16",
            channels=CHANNELS,
            callback=callback,
        ):
            _notify("idle")
            while state != DONE:
                frame = audio_queue.get()
                is_speech = self.vad.is_speech(frame, SAMPLE_RATE)

                if state == IDLE:
                    speech_ring.append(is_speech)
                    pre_buffer.append(frame)
                    idle_frames += 1

                    if sum(speech_ring) >= 3:
                        state = RECORDING
                        _notify("recording")
                        recorded_frames.extend(pre_buffer)

                    if idle_frames >= max_wait_frames:
                        _notify("timeout")
                        return None

                elif state == RECORDING:
                    recorded_frames.append(frame)
                    recording_frames += 1

                    if is_speech:
                        silence_frame_count = 0
                    else:
                        silence_frame_count += 1
                        if silence_frame_count >= silence_threshold_frames:
                            _notify("done")
                            state = DONE

                    if recording_frames % frames_per_sec == 0:
                        silence_sec = silence_frame_count * FRAME_DURATION_MS / 1000
                        recording_sec = recording_frames * FRAME_DURATION_MS / 1000
                        _notify("progress", {
                            "recording_sec": recording_sec,
                            "silence_sec": silence_sec,
                        })

        return b"".join(recorded_frames)


def pcm_to_wav(pcm_data: bytes) -> bytes:
    """Wrap raw PCM bytes in a WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data)
    return buf.getvalue()


if __name__ == "__main__":
    import sys

    def _on_event(event, data):
        if event == "idle":
            print("Listening... speak now (2s silence to stop, 30s timeout)")
        elif event == "recording":
            print("Speech detected, recording...")
        elif event == "progress":
            rec = data["recording_sec"]
            silence = data["silence_sec"]
            if silence > 0:
                print(f"  {rec:.0f}s recording | quiet for {silence:.1f}s (stops at 2.0s)")
            else:
                print(f"  {rec:.0f}s recording | hearing speech")
        elif event == "done":
            print("Silence detected, stopping.")
        elif event == "timeout":
            print("No speech detected (timed out).")

    recorder = Recorder(on_event=_on_event)
    pcm = recorder.record()

    if pcm is None:
        sys.exit(0)

    duration_sec = len(pcm) / (SAMPLE_RATE * 2)  # 2 bytes per sample
    print(f"Recorded {duration_sec:.1f}s of audio ({len(pcm)} bytes)")

    out_path = "test_recording.wav"
    with open(out_path, "wb") as f:
        f.write(pcm_to_wav(pcm))
    print(f"Saved to {out_path}")
