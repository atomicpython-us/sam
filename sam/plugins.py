"""
Plugin engine for atomic_voice — extensible voice enhancement pipeline.

Plugins can modify phoneme data, pitch contours, and post-process audio.
All plugins are optional and composable.

Usage:
    from sam import SAM
    from sam.plugins import ProsodyPlugin, ReverbPlugin, CompressorPlugin

    sam = SAM(pin=0, plugins=[
        ProsodyPlugin(),
        ReverbPlugin(delay_ms=30, decay=0.2),
        CompressorPlugin(threshold=0.7),
    ])
    sam.say("Hello, how are you today?")
"""


class VoicePlugin:
    """Base class for voice enhancement plugins.

    Subclass and override any of the three processing stages:
      - process_phonemes: modify phoneme data before rendering
      - process_pitches: modify pitch contour after frame creation
      - process_audio: post-process rendered audio buffer
    """
    name = "base"

    def process_phonemes(self, phoneme_index, phoneme_length, stress):
        """Modify phoneme data before rendering.

        Args:
            phoneme_index: list of phoneme indices
            phoneme_length: list of phoneme durations
            stress: list of stress values

        Returns:
            (phoneme_index, phoneme_length, stress) tuple
        """
        return phoneme_index, phoneme_length, stress

    def process_pitches(self, pitches, stress, text=""):
        """Modify pitch contour after frame creation.

        Args:
            pitches: bytearray of per-frame pitch values
            stress: list/bytearray of per-phoneme stress values
            text: original text (for sentence-type detection)

        Returns:
            pitches bytearray (may be modified in place)
        """
        return pitches

    def process_audio(self, audio_buffer):
        """Post-process rendered audio buffer.

        Args:
            audio_buffer: bytearray of 8-bit unsigned PCM at 22050 Hz

        Returns:
            bytearray of processed audio
        """
        return audio_buffer


class ProsodyPlugin(VoicePlugin):
    """Intonation and stress patterns — applies F0 contour rules.

    Raises pitch on stressed syllables, lowers on unstressed,
    adds question intonation and statement declination,
    plus slight random jitter for naturalness.
    """
    name = "prosody"

    def process_pitches(self, pitches, stress, text=""):
        from .prosody import apply_prosody
        is_question = text.rstrip().endswith('?')
        return apply_prosody(pitches, stress, is_question=is_question)


class ReverbPlugin(VoicePlugin):
    """Simple delay-based reverb/echo effect.

    Args:
        delay_ms: Echo delay in milliseconds (default 50)
        decay: Echo amplitude multiplier 0.0-1.0 (default 0.3)
        sample_rate: Audio sample rate (default 22050)
    """
    name = "reverb"

    def __init__(self, delay_ms=50, decay=0.3, sample_rate=22050):
        self.delay_samples = (sample_rate * delay_ms) // 1000
        self.decay = decay
        # Pre-compute fixed-point decay (8-bit: 0-255 maps to 0.0-1.0)
        self._decay_fp = int(decay * 256)

    def process_audio(self, audio_buffer):
        n = len(audio_buffer)
        delay = self.delay_samples
        decay_fp = self._decay_fp
        if delay >= n or delay == 0:
            return audio_buffer
        # Work on a copy to avoid feedback artifacts in single-pass
        out = bytearray(n)
        for i in range(n):
            sample = audio_buffer[i]
            if i >= delay:
                # Mix echo from earlier sample (centered at 128)
                echo_raw = audio_buffer[i - delay] - 128
                echo = (echo_raw * decay_fp) >> 8
                mixed = sample - 128 + echo
                # Clamp to 8-bit unsigned
                if mixed > 127:
                    mixed = 127
                elif mixed < -128:
                    mixed = -128
                out[i] = mixed + 128
            else:
                out[i] = sample
        return out


class ChorusPlugin(VoicePlugin):
    """Slight pitch/timing variation for richness.

    Creates a detuned copy mixed with the original signal.

    Args:
        depth: Detune amount in samples (default 3)
        mix: Wet/dry mix 0.0-1.0 (default 0.4)
    """
    name = "chorus"

    def __init__(self, depth=3, mix=0.4):
        self.depth = depth
        self._mix_fp = int(mix * 256)

    def process_audio(self, audio_buffer):
        n = len(audio_buffer)
        depth = self.depth
        mix_fp = self._mix_fp
        dry_fp = 256 - mix_fp
        if n < depth * 4:
            return audio_buffer
        out = bytearray(n)
        # Simple chorus: mix original with a slightly offset copy
        # Use a slowly varying offset via triangle LFO
        lfo_period = max(1, n // 8)
        for i in range(n):
            # Triangle LFO: offset varies from 0 to depth and back
            lfo_pos = i % (lfo_period * 2)
            if lfo_pos < lfo_period:
                offset = (depth * lfo_pos) // lfo_period
            else:
                offset = (depth * (lfo_period * 2 - lfo_pos)) // lfo_period
            j = i + offset
            if j >= n:
                j = n - 1
            dry = audio_buffer[i] - 128
            wet = audio_buffer[j] - 128
            mixed = ((dry * dry_fp) + (wet * mix_fp)) >> 8
            if mixed > 127:
                mixed = 127
            elif mixed < -128:
                mixed = -128
            out[i] = mixed + 128
        return out


class CompressorPlugin(VoicePlugin):
    """Dynamic range compression for consistent volume.

    Reduces loud peaks and boosts quiet sections.

    Args:
        threshold: Compression threshold 0.0-1.0 (default 0.7)
        ratio: Compression ratio (default 3.0 means 3:1)
        makeup_gain: Post-compression gain multiplier (default 1.3)
    """
    name = "compressor"

    def __init__(self, threshold=0.7, ratio=3.0, makeup_gain=1.3):
        # Threshold in 8-bit amplitude (0-127 range, since centered at 128)
        self.threshold = int(threshold * 127)
        self.ratio = ratio
        self._makeup_fp = int(makeup_gain * 256)

    def process_audio(self, audio_buffer):
        n = len(audio_buffer)
        thresh = self.threshold
        ratio = self.ratio
        makeup_fp = self._makeup_fp
        out = bytearray(n)
        for i in range(n):
            sample = audio_buffer[i] - 128  # signed: -128..127
            sign = 1 if sample >= 0 else -1
            magnitude = abs(sample)
            if magnitude > thresh:
                # Compress: excess above threshold reduced by ratio
                excess = magnitude - thresh
                compressed_excess = int(excess / ratio)
                magnitude = thresh + compressed_excess
            # Apply makeup gain
            magnitude = (magnitude * makeup_fp) >> 8
            if magnitude > 127:
                magnitude = 127
            out[i] = (sign * magnitude) + 128
        return out


class EQPlugin(VoicePlugin):
    """Simple frequency shaping via moving-average filters.

    Boosts low frequencies (warmth) and optionally cuts high
    frequencies (reduces harshness).

    Args:
        bass_boost: Low-frequency boost factor 0.0-2.0 (default 1.3)
        treble_cut: High-frequency reduction 0.0-1.0 (default 0.2)
    """
    name = "eq"

    def __init__(self, bass_boost=1.3, treble_cut=0.2):
        self._bass_fp = int(bass_boost * 256)
        self._treble_cut_fp = int(treble_cut * 256)

    def process_audio(self, audio_buffer):
        n = len(audio_buffer)
        if n < 8:
            return audio_buffer
        bass_fp = self._bass_fp
        treble_fp = self._treble_cut_fp
        out = bytearray(n)
        # Extract bass via 4-sample moving average, add scaled bass back
        for i in range(n):
            sample = audio_buffer[i] - 128
            # Low-pass: average of nearby samples
            total = 0
            count = 0
            for j in range(max(0, i - 2), min(n, i + 3)):
                total += audio_buffer[j] - 128
                count += 1
            low = total // count if count > 0 else 0
            high = sample - low
            # Boost bass, cut treble
            result = ((low * bass_fp) >> 8) + ((high * (256 - treble_fp)) >> 8)
            if result > 127:
                result = 127
            elif result < -128:
                result = -128
            out[i] = result + 128
        return out
