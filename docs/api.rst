API Reference
=============

SAM Class
---------

.. module:: sam

.. class:: SAM(pin=0, speed=72, pitch=64, mouth=128, throat=128)

   Main public API for the SAM speech synthesizer.

   :param int pin: GPIO pin number for PWM audio output.
   :param int speed: Speech speed (1-255, default 72). Lower values produce slower speech.
   :param int pitch: Voice pitch (1-255, default 64). Higher values produce a higher-pitched voice.
   :param int mouth: Mouth shape parameter (1-255, default 128). Affects formant balance.
   :param int throat: Throat shape parameter (1-255, default 128). Affects formant balance.

   .. method:: say(text)

      Speak English text. Converts text to phonemes using the reciter, then
      synthesizes and plays the audio through PWM.

      :param str text: English text to speak.

      .. code-block:: python

         sam.say("Hello World")

   .. method:: say_phonetic(phoneme_str)

      Speak from a SAM phoneme string directly, bypassing the reciter.

      :param str phoneme_str: SAM phoneme string (e.g. ``"/HEH4LOW WERLD"``).

      .. code-block:: python

         sam.say_phonetic("/HEH4LOW WERLD")

   .. method:: generate(text)

      Generate audio buffer from English text without playing it.

      :param str text: English text to speak.
      :returns: 8-bit unsigned PCM audio data.
      :rtype: bytearray

   .. method:: generate_phonetic(phoneme_str)

      Generate audio buffer from a phoneme string without playing.

      :param str phoneme_str: SAM phoneme string.
      :returns: 8-bit unsigned PCM audio data.
      :rtype: bytearray

   .. method:: text_to_phonemes(text)

      Convert English text to a SAM phoneme string. Useful for debugging
      and tuning pronunciation.

      :param str text: English text.
      :returns: Phoneme string.
      :rtype: str

      .. code-block:: python

         >>> sam.text_to_phonemes("Hello")
         '/HEHLOW'

   .. method:: set_speed(speed)

      Set speech speed.

      :param int speed: Speed value 1-255 (default 72). Lower = slower.

   .. method:: set_pitch(pitch)

      Set voice pitch.

      :param int pitch: Pitch value 1-255 (default 64). Higher = higher pitch.

   .. method:: set_mouth(mouth)

      Set mouth shape parameter. Affects first formant (F1) balance.

      :param int mouth: Mouth value 1-255 (default 128).

   .. method:: set_throat(throat)

      Set throat shape parameter. Affects second formant (F2) balance.

      :param int throat: Throat value 1-255 (default 128).

   .. method:: save_wav(text, filename)

      Render text to speech and save as a WAV file.

      :param str text: English text to speak.
      :param str filename: Output WAV file path.
      :returns: The filename.
      :rtype: str

   .. method:: stop()

      Stop any current playback and release hardware resources (PWM, timer).


Audio Output
------------

.. module:: sam.audio

.. class:: PWMAudio(pin=0, sample_rate=8000)

   PWM-based audio output driver.

   :param int pin: GPIO pin number.
   :param int sample_rate: Playback sample rate in Hz.

   .. method:: play(buffer)

      Play an audio buffer through PWM. Uses a timer interrupt for sample
      timing, with a tight-loop fallback.

      :param buffer: 8-bit unsigned PCM samples.
      :type buffer: bytearray or bytes

   .. method:: stop()

      Stop playback and release PWM hardware.

   .. attribute:: is_playing
      :type: bool

      ``True`` if audio is currently playing.

.. class:: WavWriter(filename, sample_rate=8000)

   Write audio samples to a WAV file.

   :param str filename: Output file path.
   :param int sample_rate: Sample rate for the WAV header.

   .. method:: write(buffer)

      Write 8-bit unsigned PCM buffer as a WAV file.

      :param buffer: Audio sample data.
      :type buffer: bytearray or bytes


Renderer
--------

.. module:: sam.renderer

.. data:: SAMPLE_RATE
   :value: 7350

   The output sample rate in Hz after 3:1 downsampling from 22050 Hz.

.. function:: render(phoneme_index, phoneme_length, stress, speed=72, pitch=64, mouth=128, throat=128)

   Render processed phoneme data to an audio buffer. If the native C module
   ``sam_render`` is available, uses it for ~100x faster rendering.

   :param list phoneme_index: Phoneme index array from ``process_phonemes()``.
   :param list phoneme_length: Duration array from ``process_phonemes()``.
   :param list stress: Stress array from ``process_phonemes()``.
   :param int speed: Synthesis speed (ticks per frame).
   :param int pitch: Base pitch value.
   :param int mouth: Mouth shape parameter.
   :param int throat: Throat shape parameter.
   :returns: 8-bit unsigned PCM audio data.
   :rtype: bytearray


Phoneme Processor
-----------------

.. module:: sam.phonemes

.. function:: process_phonemes(input_str, speed=72)

   Full phoneme processing pipeline. Converts a phoneme string into
   arrays ready for rendering.

   Stages:

   1. Parse phoneme codes to internal indices
   2. Apply transformation rules (diphthongs, affricates, consonant clusters)
   3. Propagate stress markers
   4. Assign phoneme durations
   5. Apply context-dependent length adjustments
   6. Insert breath pauses

   :param str input_str: SAM phoneme string (e.g. ``"HEH4LOW WERLD"``).
   :param int speed: Speech speed (kept for API compatibility).
   :returns: Tuple of ``(phoneme_index, phoneme_length, stress)``.
   :rtype: tuple


Reciter
-------

.. module:: sam.reciter

.. function:: text_to_phonemes(text)

   Convert English text to a SAM phoneme string using rule-based pronunciation.

   The reciter uses over 200 context-sensitive rules organized by starting letter.
   Rules use pattern matching with wildcards for prefixes and suffixes.

   :param str text: English text.
   :returns: SAM phoneme string with stress markers.
   :rtype: str

   .. code-block:: python

      >>> text_to_phonemes("Hello World")
      '/HEHLOW WERLD'
      >>> text_to_phonemes("Testing")
      'TEHSTIHNX'
