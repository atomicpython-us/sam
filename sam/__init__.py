"""
SAM (Software Automatic Mouth) - MicroPython Speech Synthesizer

A pure MicroPython port of the classic SAM text-to-speech engine,
originally created for the Commodore 64 in 1982.

Three-stage pipeline:
1. Reciter: English text -> phoneme string
2. Parser:  Phoneme string -> internal phoneme sequence with stress/timing
3. Renderer: Phoneme sequence -> 8-bit PCM audio via formant synthesis

Audio output via PIO-driven PWM on a GPIO pin at 22050 Hz sample rate.
Falls back to timer-based PWM on non-RP2040 platforms.

atomic_voice enhancements:
  - Plugin engine for composable voice processing
  - LF glottal pulse for more natural voicing
  - Formant interpolation for smooth coarticulation
  - Aspiration noise for breathy quality
  - Formant bandwidth widening for softer resonance
  - F0 prosody contour (via ProsodyPlugin)

Usage:
    from sam import SAM
    sam = SAM(pin=0)
    sam.say("hello world")
    sam.say_phonetic("/HEH4LOW WERLD")

    # With enhancements:
    from sam.plugins import ProsodyPlugin, ReverbPlugin
    sam = SAM(pin=0, plugins=[ProsodyPlugin(), ReverbPlugin()])
    sam.say("Hello, how are you today?")

Hardware:
    GPIO pin --[1K resistor]--> speaker --> GND
    Optional: 100nF cap across speaker for LC filtering
"""

__version__ = '2.0.0'

from .reciter import text_to_phonemes
from .phonemes import process_phonemes
from .renderer import render, SAMPLE_RATE, _HAS_NATIVE, _NATIVE_STATUS
from .renderer import FLAG_GLOTTAL_LF, FLAG_ASPIRATION, FLAG_BANDWIDTH, FLAG_INTERPOLATE, FLAG_ALL


# Voice presets: (speed, pitch, mouth, throat)
VOICES = {
    'sam':       (72, 64, 128, 128),   # Default SAM voice
    'robot':     (72, 96, 128, 128),   # Robotic monotone
    'elf':       (72, 72, 110, 160),   # High, thin voice
    'old_man':   (82, 72, 145, 130),   # Slow, deep, gravelly
    'whisper':   (72, 64, 80, 160),    # Breathy whisper
    'alien':     (60, 64, 150, 200),   # Strange, otherworldly
    'giant':     (82, 40, 190, 110),   # Deep, booming
    'child':     (68, 96, 110, 140),   # High, small
    'stuffy':    (72, 64, 160, 100),   # Nasal, congested
    # atomic_voice presets (use enhancement flags)
    'natural':   (72, 64, 128, 128),   # SAM + all enhancements
    'warm':      (76, 58, 140, 120),   # Deep, warm, natural
    'bright':    (68, 80, 115, 145),   # Bright, clear, natural
}


class SAM:
    """
    SAM Speech Synthesizer - main public API.

    Args:
        pin: GPIO pin number for PWM audio output (default 0)
        speed: Speech speed (1-255, default 72). Lower = slower.
        pitch: Voice pitch (1-255, default 64). Higher = higher pitch.
        mouth: Mouth shape (1-255, default 128). Affects formant balance.
        throat: Throat shape (1-255, default 128). Affects formant balance.
        voice: Optional preset name (overrides speed/pitch/mouth/throat).
        plugins: List of VoicePlugin instances for voice enhancement.
        enh_flags: Enhancement bit flags for C renderer (default 0 = original SAM).
                   Use FLAG_ALL for all enhancements, or combine individual flags.
    """

    def __init__(self, pin=0, speed=72, pitch=64, mouth=128, throat=128,
                 voice=None, plugins=None, enh_flags=0):
        self._pin = pin
        self._audio = None
        self.plugins = plugins or []
        self.enh_flags = enh_flags
        if voice:
            self.set_voice(voice)
        else:
            self.speed = speed
            self.pitch = pitch
            self.mouth = mouth
            self.throat = throat

    def add_plugin(self, plugin):
        """Add a voice enhancement plugin to the processing chain.

        Args:
            plugin: VoicePlugin instance
        """
        self.plugins.append(plugin)

    def remove_plugin(self, name):
        """Remove a plugin by name.

        Args:
            name: Plugin name string
        """
        self.plugins = [p for p in self.plugins if p.name != name]

    def _get_audio(self):
        """Lazy-initialize the audio driver. Prefers PIO on RP2040."""
        if self._audio is None:
            try:
                from .audio import PIOAudio, _HAS_PIO
                if _HAS_PIO:
                    self._audio = PIOAudio(pin=self._pin, sample_rate=SAMPLE_RATE)
                else:
                    raise ImportError
            except (ImportError, Exception):
                from .audio import PWMAudio
                self._audio = PWMAudio(pin=self._pin, sample_rate=SAMPLE_RATE)
        return self._audio

    def say(self, text, chunk_words=3):
        """
        Speak English text. Automatically chunks long text to avoid
        memory errors, rendering and playing a few words at a time.

        Args:
            text: English text string to speak
            chunk_words: Max words per chunk (default 3). Lower = less RAM.
        """
        import gc, time
        for chunk, pause_ms in self._chunk_text(text, chunk_words):
            gc.collect()
            phonemes = text_to_phonemes(chunk)
            if phonemes and phonemes.strip():
                self._say_phonetic_with_text(phonemes, text)
                if pause_ms:
                    time.sleep_ms(pause_ms)

    def _say_phonetic_with_text(self, phoneme_str, original_text=""):
        """Internal: speak phonemes with original text context for plugins."""
        import gc
        gc.collect()

        if phoneme_str.startswith('/'):
            phoneme_str = phoneme_str[1:]

        phoneme_index, phoneme_length, stress = process_phonemes(
            phoneme_str, self.speed
        )

        # Plugin stage 1: process phonemes
        for plugin in self.plugins:
            phoneme_index, phoneme_length, stress = plugin.process_phonemes(
                phoneme_index, phoneme_length, stress
            )

        gc.collect()

        # Render to audio samples (with enhancement flags)
        buffer = render(
            phoneme_index, phoneme_length, stress,
            speed=self.speed, pitch=self.pitch,
            mouth=self.mouth, throat=self.throat,
            enh_flags=self.enh_flags
        )

        # Plugin stage 2: process pitches
        # (Pitches are baked into the rendered buffer at this point for C renderer,
        #  but we can still apply prosody-aware post-processing)
        # Note: For full pitch control, ProsodyPlugin modifies the pitch array
        # before rendering. This is done via the generate path. For the play path,
        # audio-level plugins still apply.

        # Plugin stage 3: process audio
        for plugin in self.plugins:
            buffer = plugin.process_audio(buffer)

        # Play through PWM
        audio = self._get_audio()
        audio.play(buffer)

    def say_phonetic(self, phoneme_str):
        """
        Speak from a phoneme string directly (bypass the reciter).

        Phoneme format uses SAM phoneme codes:
            /HEH4LOW WERLD
        Stress markers 1-8 follow the stressed vowel.

        Args:
            phoneme_str: SAM phoneme string
        """
        self._say_phonetic_with_text(phoneme_str, "")

    @staticmethod
    def _split_token(word):
        """Split a single token on embedded punctuation.
        Handles IP addresses, versions, etc. (e.g. '192.168.1.207').
        Yields (sub_token, pause_ms) tuples."""
        _PAUSE = {'.': 150, '!': 400, '?': 400, ';': 250, ':': 250, ',': 150}
        current = []
        for ch in word:
            if ch in _PAUSE:
                token = ''.join(current).strip()
                if token:
                    yield (token, _PAUSE[ch])
                current = []
            else:
                current.append(ch)
        token = ''.join(current).strip()
        if token:
            yield (token, 0)

    @staticmethod
    def _chunk_text(text, chunk_words):
        """Split text into small speakable chunks to limit memory usage.
        Yields (chunk_text, pause_ms) tuples.

        First splits on whitespace, then breaks individual tokens that
        contain embedded punctuation (IP addresses, version numbers, etc.)
        into separate sub-tokens. Finally groups plain words up to
        chunk_words per group."""
        raw_words = text.split()
        # Flatten all tokens, splitting on embedded punctuation
        tokens = []  # list of (text, pause_ms)
        for word in raw_words:
            has_punct = False
            for ch in word:
                if ch in '.!?;,:':
                    has_punct = True
                    break
            if has_punct:
                for tok, pause in SAM._split_token(word):
                    tokens.append((tok, pause))
            else:
                tokens.append((word, 0))

        # Group consecutive no-pause tokens up to chunk_words
        group = []
        for tok, pause in tokens:
            group.append(tok)
            if pause or len(group) >= chunk_words:
                yield (' '.join(group), pause)
                group = []
        if group:
            yield (' '.join(group), 0)

    def sing(self, melody, bpm=80):
        """
        Sing a melody with precise beat timing.

        Each entry in melody is (pitch, phonemes, beats):
            pitch:    SAM pitch value (lower = higher note), 0 = rest
            phonemes: SAM phoneme string for the syllable
            beats:    Duration in beats (float, e.g. 1.5 for dotted quarter)

        Renders syllables to exact durations and plays them as continuous
        phrases to eliminate gaps between notes.

        Args:
            melody: List of (pitch, phonemes, beats) tuples
            bpm: Tempo in beats per minute (default 80)
        """
        import gc

        samples_per_beat = (60 * SAMPLE_RATE) // bpm
        orig_pitch = self.pitch
        orig_speed = self.speed
        audio = self._get_audio()
        fade_len = SAMPLE_RATE // 20  # 50ms fade-out

        # Process melody in groups that fit in ~40KB
        i = 0
        while i < len(melody):
            # Find how many notes fit in this group
            group_samples = 0
            j = i
            while j < len(melody):
                _, _, beats = melody[j]
                n = int(samples_per_beat * beats)
                if group_samples + n > 40000 and j > i:
                    break
                group_samples += n
                j += 1

            # Build the phrase buffer (pre-filled with silence)
            buf = bytearray(b'\x80' * group_samples)
            pos = 0
            for k in range(i, j):
                pitch, phonemes, beats = melody[k]
                target = int(samples_per_beat * beats)
                if pitch > 0 and phonemes:
                    self.pitch = pitch
                    # Scale speed to beat duration: longer notes get more sustain
                    self.speed = max(40, min(200, int(100 * beats)))
                    raw = self.generate_phonetic(phonemes)
                    copy_len = min(len(raw), target)
                    buf[pos:pos + copy_len] = raw[:copy_len]
                    # Fade out to silence at the end of this note
                    fade = min(fade_len, copy_len)
                    fade_start = pos + copy_len - fade
                    for m in range(fade):
                        t = fade - m  # counts down from fade to 0
                        buf[fade_start + m] = 128 + ((buf[fade_start + m] - 128) * t) // fade
                    del raw
                pos += target

            # Apply audio plugins to the phrase
            for plugin in self.plugins:
                buf = plugin.process_audio(buf)

            audio.play(buf)
            del buf
            gc.collect()
            i = j

        self.pitch = orig_pitch
        self.speed = orig_speed

    def generate(self, text):
        """
        Generate audio buffer from text without playing it.
        Useful for saving to WAV or custom output.

        Args:
            text: English text string

        Returns:
            bytearray of 8-bit unsigned PCM at ~22,050 Hz
        """
        phonemes = text_to_phonemes(text)
        if not phonemes:
            return bytearray(0)
        return self._generate_phonetic_with_text(phonemes, text)

    def _generate_phonetic_with_text(self, phoneme_str, original_text=""):
        """Internal: generate audio with full plugin pipeline."""
        if phoneme_str.startswith('/'):
            phoneme_str = phoneme_str[1:]

        phoneme_index, phoneme_length, stress = process_phonemes(
            phoneme_str, self.speed
        )

        # Plugin stage 1: process phonemes
        for plugin in self.plugins:
            phoneme_index, phoneme_length, stress = plugin.process_phonemes(
                phoneme_index, phoneme_length, stress
            )

        # Plugin stage 2: process pitches (before rendering)
        # We need to create frames first to get the pitch array, then let plugins modify it
        from .renderer import create_frames
        result = create_frames(phoneme_index, phoneme_length, stress,
                               self.pitch, self.mouth, self.throat)
        fr1, fr2, fr3, am1, am2, am3, pitches, samp_flags, num_frames = result

        if num_frames == 0:
            return bytearray(0)

        # Let plugins modify the pitch contour
        for plugin in self.plugins:
            pitches = plugin.process_pitches(pitches, stress, original_text)

        # Render with pre-built frames (call C module or Python fallback directly)
        from .renderer import _HAS_NATIVE
        if _HAS_NATIVE:
            from .renderer import _native
            buffer = _native.process_frames(
                fr1, fr2, fr3, am1, am2, am3,
                pitches, samp_flags, num_frames, self.speed, self.enh_flags
            )
        else:
            # For Python fallback, we need to use the render loop directly
            # Pass the pre-built frames through the synthesis loop
            buffer = _render_from_frames(
                fr1, fr2, fr3, am1, am2, am3,
                pitches, samp_flags, num_frames, self.speed, self.enh_flags
            )

        # Plugin stage 3: process audio
        for plugin in self.plugins:
            buffer = plugin.process_audio(buffer)

        return buffer

    def generate_phonetic(self, phoneme_str):
        """
        Generate audio buffer from phoneme string without playing.

        Args:
            phoneme_str: SAM phoneme string

        Returns:
            bytearray of 8-bit unsigned PCM at ~22,050 Hz
        """
        if self.plugins:
            return self._generate_phonetic_with_text(phoneme_str, "")

        # Fast path: no plugins, use render() directly
        if phoneme_str.startswith('/'):
            phoneme_str = phoneme_str[1:]

        phoneme_index, phoneme_length, stress = process_phonemes(
            phoneme_str, self.speed
        )

        return render(
            phoneme_index, phoneme_length, stress,
            speed=self.speed, pitch=self.pitch,
            mouth=self.mouth, throat=self.throat,
            enh_flags=self.enh_flags
        )

    def text_to_phonemes(self, text):
        """
        Convert English text to SAM phoneme string (for debugging/tuning).

        Args:
            text: English text

        Returns:
            Phoneme string
        """
        return text_to_phonemes(text)

    def set_voice(self, name):
        """Apply a voice preset by name. Use list_voices() to see options.

        The 'natural', 'warm', and 'bright' presets automatically enable
        all enhancement flags for the most realistic output.
        """
        name = name.lower()
        if name not in VOICES:
            raise ValueError('Unknown voice: ' + name + '. Use list_voices().')
        self.speed, self.pitch, self.mouth, self.throat = VOICES[name]
        # Enable all enhancements for the new atomic_voice presets
        if name in ('natural', 'warm', 'bright'):
            self.enh_flags = FLAG_ALL

    @staticmethod
    def list_voices():
        """Print available voice presets."""
        for name, (spd, pit, mou, thr) in VOICES.items():
            print('  {:10s} speed={} pitch={} mouth={} throat={}'.format(
                name, spd, pit, mou, thr))

    def set_speed(self, speed):
        """Set speech speed (1-255, default 72). Lower = slower."""
        self.speed = max(1, min(255, speed))

    def set_pitch(self, pitch):
        """Set voice pitch (1-255, default 64). Higher = higher pitch."""
        self.pitch = max(1, min(255, pitch))

    def set_mouth(self, mouth):
        """Set mouth shape (1-255, default 128)."""
        self.mouth = max(1, min(255, mouth))

    def set_throat(self, throat):
        """Set throat shape (1-255, default 128)."""
        self.throat = max(1, min(255, throat))

    def save_wav(self, text, filename, chunk_words=3):
        """
        Render text to speech and save as a WAV file.
        Handles large text by chunking, same as say().

        Args:
            text: English text to speak
            filename: Output WAV file path
            chunk_words: Max words per chunk (default 3)
        """
        import struct
        chunks = []
        total_samples = 0
        for chunk, pause_ms in self._chunk_text(text, chunk_words):
            phonemes = text_to_phonemes(chunk)
            if phonemes and phonemes.strip():
                buf = self._generate_phonetic_with_text(phonemes, text) if self.plugins else self.generate_phonetic(phonemes)
                chunks.append(buf)
                total_samples += len(buf)
                if pause_ms:
                    silence_len = (SAMPLE_RATE * pause_ms) // 1000
                    chunks.append(bytearray(b'\x80' * silence_len))
                    total_samples += silence_len

        with open(filename, 'wb') as f:
            # WAV header
            f.write(b'RIFF')
            f.write(struct.pack('<I', 36 + total_samples))
            f.write(b'WAVE')
            f.write(b'fmt ')
            f.write(struct.pack('<IHHIIHH', 16, 1, 1,
                    SAMPLE_RATE, SAMPLE_RATE, 1, 8))
            f.write(b'data')
            f.write(struct.pack('<I', total_samples))
            for buf in chunks:
                f.write(bytes(buf))

        return filename

    def save_wav_sing(self, melody, filename, bpm=80):
        """
        Render a melody to a WAV file (no hardware needed).

        Args:
            melody: List of (pitch, phonemes, beats) tuples
            filename: Output WAV file path
            bpm: Tempo in beats per minute (default 80)
        """
        import struct

        samples_per_beat = (60 * SAMPLE_RATE) // bpm
        orig_pitch = self.pitch
        orig_speed = self.speed
        fade_len = SAMPLE_RATE // 20  # 50ms fade-out

        # Calculate total samples
        total_samples = 0
        for _, _, beats in melody:
            total_samples += int(samples_per_beat * beats)

        # Build complete buffer
        buf = bytearray(b'\x80' * total_samples)
        pos = 0
        for pitch, phonemes, beats in melody:
            target = int(samples_per_beat * beats)
            if pitch > 0 and phonemes:
                self.pitch = pitch
                self.speed = max(40, min(200, int(100 * beats)))
                raw = self.generate_phonetic(phonemes)
                copy_len = min(len(raw), target)
                buf[pos:pos + copy_len] = raw[:copy_len]
                # Fade out
                fade = min(fade_len, copy_len)
                fade_start = pos + copy_len - fade
                for m in range(fade):
                    t = fade - m
                    buf[fade_start + m] = 128 + ((buf[fade_start + m] - 128) * t) // fade
            pos += target

        self.pitch = orig_pitch
        self.speed = orig_speed

        # Apply audio plugins
        for plugin in self.plugins:
            buf = plugin.process_audio(buf)

        # Write WAV
        with open(filename, 'wb') as f:
            f.write(b'RIFF')
            f.write(struct.pack('<I', 36 + total_samples))
            f.write(b'WAVE')
            f.write(b'fmt ')
            f.write(struct.pack('<IHHIIHH', 16, 1, 1,
                    SAMPLE_RATE, SAMPLE_RATE, 1, 8))
            f.write(b'data')
            f.write(struct.pack('<I', total_samples))
            f.write(bytes(buf))

        return filename

    def info(self):
        """Print diagnostic info about the SAM configuration."""
        from .audio import _HAS_PIO
        audio = self._get_audio()
        audio_type = type(audio).__name__
        print('SAM Speech Synthesizer v' + __version__)
        print('  sample rate:', SAMPLE_RATE, 'Hz')
        print('  native C renderer:', _NATIVE_STATUS)
        print('  audio driver:', audio_type)
        print('  PIO available:', _HAS_PIO)
        print('  pin:', self._pin)
        print('  speed:', self.speed, ' pitch:', self.pitch,
              ' mouth:', self.mouth, ' throat:', self.throat)
        print('  enhancement flags: 0x{:02x}'.format(self.enh_flags))
        enh_names = []
        if self.enh_flags & FLAG_GLOTTAL_LF: enh_names.append('glottal_lf')
        if self.enh_flags & FLAG_ASPIRATION: enh_names.append('aspiration')
        if self.enh_flags & FLAG_BANDWIDTH: enh_names.append('bandwidth')
        if self.enh_flags & FLAG_INTERPOLATE: enh_names.append('interpolate')
        print('  enhancements:', ', '.join(enh_names) if enh_names else 'none (original SAM)')
        if self.plugins:
            print('  plugins:', ', '.join(p.name for p in self.plugins))
        else:
            print('  plugins: none')

    def stop(self):
        """Stop any current playback and release hardware."""
        if self._audio:
            self._audio.stop()
            self._audio = None


def _render_from_frames(fr1, fr2, fr3, am1, am2, am3, pitches, samp_flags,
                        num_frames, speed, enh_flags=0):
    """Render from pre-built frame arrays (used when plugins modify pitches).

    This calls the Python fallback renderer's synthesis loop with
    pre-computed frame data, bypassing create_frames().
    """
    from . import tables
    from .renderer import GLOTTAL_LF, FLAG_GLOTTAL_LF, FLAG_ASPIRATION, FLAG_BANDWIDTH, FLAG_INTERPOLATE

    bufsize = 4 * speed * num_frames + 4096
    buf = bytearray(bufsize)

    if enh_flags & FLAG_GLOTTAL_LF:
        sin_t = GLOTTAL_LF
    else:
        sin_t = tables.SINUS

    rec_t = tables.RECTANGLE
    mul_t = tables.MULT_TABLE
    sam_t = tables.SAMPLE_TABLE
    sam_t_len = len(sam_t)
    tt = tables.TIME_TABLE
    t48 = tables.TAB48426

    use_aspiration = bool(enh_flags & FLAG_ASPIRATION)
    use_bandwidth = bool(enh_flags & FLAG_BANDWIDTH)
    use_interp = bool(enh_flags & FLAG_INTERPOLATE)

    bufpos = 0
    old_ti = 0
    phase1 = 0; phase2 = 0; phase3 = 0
    m_off = 0
    y = 0
    k = num_frames
    speedcounter = speed
    glottal_pulse = pitches[0]
    n = glottal_pulse - (glottal_pulse >> 2)

    lcg_state = 0xDEADBEEF
    prev_f1 = fr1[0]; prev_f2 = fr2[0]; prev_f3 = fr3[0]
    interp_counter = 0

    while k:
        flags = samp_flags[y] if y < num_frames else 0

        if flags & 248:
            hibyte = ((flags & 7) - 1) & 0xFF
            hi = hibyte * 256
            pitchl = flags & 248

            if pitchl == 0:
                pitchl = pitches[y] >> 4
                off = m_off & 0xFF
                vph = (pitchl ^ 255) & 0xFF
                while True:
                    sample = sam_t[hi + off] if hi + off < sam_t_len else 0
                    for _ in range(8):
                        if sample & 128:
                            bufpos += tt[old_ti][3]; old_ti = 3
                            p = bufpos // 50
                            if p + 4 < bufsize:
                                buf[p]=160;buf[p+1]=160;buf[p+2]=160;buf[p+3]=160;buf[p+4]=160
                        else:
                            bufpos += tt[old_ti][4]; old_ti = 4
                            p = bufpos // 50
                            if p + 4 < bufsize:
                                buf[p]=96;buf[p+1]=96;buf[p+2]=96;buf[p+3]=96;buf[p+4]=96
                        sample = (sample << 1) & 0xFF
                    off = (off + 1) & 0xFF
                    vph = (vph + 1) & 0xFF
                    if vph == 0: break
                m_off = off
            else:
                off = (pitchl ^ 255) & 0xFF
                m_val = t48[hibyte] if hibyte < len(t48) else 0x18
                v0 = (m_val & 15) * 16
                while True:
                    sample = sam_t[hi + off] if hi + off < sam_t_len else 0
                    for _ in range(8):
                        if sample & 128:
                            bufpos += tt[old_ti][2]; old_ti = 2
                            p = bufpos // 50
                            if p + 4 < bufsize:
                                buf[p]=80;buf[p+1]=80;buf[p+2]=80;buf[p+3]=80;buf[p+4]=80
                        else:
                            bufpos += tt[old_ti][1]; old_ti = 1
                            p = bufpos // 50
                            if p + 4 < bufsize:
                                buf[p]=v0;buf[p+1]=v0;buf[p+2]=v0;buf[p+3]=v0;buf[p+4]=v0
                        sample = (sample << 1) & 0xFF
                    off = (off + 1) & 0xFF
                    if off == 0: break

            y = (y + 2) & 0xFF
            k = (k - 2) & 0xFF
            speedcounter = speed
            if y < num_frames:
                prev_f1 = fr1[y]; prev_f2 = fr2[y]; prev_f3 = fr3[y]
            interp_counter = 0
        else:
            if use_interp and speed > 0:
                t_interp = interp_counter
                total = speed
                cur_f1 = prev_f1 + ((fr1[y] - prev_f1) * t_interp) // total
                cur_f2 = prev_f2 + ((fr2[y] - prev_f2) * t_interp) // total
                cur_f3 = prev_f3 + ((fr3[y] - prev_f3) * t_interp) // total
            else:
                cur_f1 = fr1[y]; cur_f2 = fr2[y]; cur_f3 = fr3[y]

            tmp = mul_t[sin_t[phase1] | am1[y]]
            tmp += mul_t[sin_t[phase2] | am2[y]]
            if tmp > 255: tmp += 1
            tmp += mul_t[rec_t[phase3] | am3[y]]

            if use_bandwidth:
                tmp = ((tmp * 13 + 384) >> 4) & 0xFF

            tmp = ((tmp + 136) >> 4) & 0x0F

            if use_aspiration and am1[y] > 0:
                noise = (lcg_state >> 16) & 0x0F
                lcg_state = (lcg_state * 1664525 + 1013904223) & 0xFFFFFFFF
                tmp = ((tmp * 14 + noise) >> 4) & 0x0F

            bufpos += tt[old_ti][0]; old_ti = 0
            p = bufpos // 50
            if p + 4 < bufsize:
                v = tmp * 16
                buf[p]=v;buf[p+1]=v;buf[p+2]=v;buf[p+3]=v;buf[p+4]=v

            interp_counter += 1
            speedcounter = (speedcounter - 1) & 0xFF
            if speedcounter == 0:
                prev_f1 = fr1[y]; prev_f2 = fr2[y]; prev_f3 = fr3[y]
                interp_counter = 0
                y = (y + 1) & 0xFF
                k = (k - 1) & 0xFF
                if k == 0: break
                speedcounter = speed

            glottal_pulse = (glottal_pulse - 1) & 0xFF
            if glottal_pulse != 0:
                n = (n - 1) & 0xFF
                if (n != 0) or (flags == 0):
                    phase1 = (phase1 + cur_f1) & 0xFF
                    phase2 = (phase2 + cur_f2) & 0xFF
                    phase3 = (phase3 + cur_f3) & 0xFF
                    continue

                hibyte = ((flags & 7) - 1) & 0xFF
                hi = hibyte * 256
                pitchl = pitches[y] >> 4
                off = m_off & 0xFF
                vph = (pitchl ^ 255) & 0xFF
                while True:
                    sample = sam_t[hi + off] if hi + off < sam_t_len else 0
                    for _ in range(8):
                        if sample & 128:
                            bufpos += tt[old_ti][3]; old_ti = 3
                            p = bufpos // 50
                            if p + 4 < bufsize:
                                buf[p]=160;buf[p+1]=160;buf[p+2]=160;buf[p+3]=160;buf[p+4]=160
                        else:
                            bufpos += tt[old_ti][4]; old_ti = 4
                            p = bufpos // 50
                            if p + 4 < bufsize:
                                buf[p]=96;buf[p+1]=96;buf[p+2]=96;buf[p+3]=96;buf[p+4]=96
                        sample = (sample << 1) & 0xFF
                    off = (off + 1) & 0xFF
                    vph = (vph + 1) & 0xFF
                    if vph == 0: break
                m_off = off

        glottal_pulse = pitches[y]
        n = glottal_pulse - (glottal_pulse >> 2)
        phase1 = 0; phase2 = 0; phase3 = 0

    end = bufpos // 50
    return buf[:end]
