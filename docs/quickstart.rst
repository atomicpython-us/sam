Quick Start
===========

Requirements
------------

- Raspberry Pi Pico (RP2040) or ESP32 running MicroPython
- A speaker or piezo buzzer
- 1K resistor

Hardware Setup
--------------

.. code-block:: text

   GPIO pin --[1K resistor]--> Speaker(+) --> GND

Optionally add a 100nF capacitor across the speaker terminals for filtering.

Installation
------------

Copy the ``sam/`` folder to your MicroPython board's filesystem:

.. code-block:: bash

   mpremote cp -r sam :sam

For faster rendering, also install the native C module:

.. code-block:: bash

   mpremote cp natmod/build/sam_render.mpy :lib/sam_render.mpy

Basic Usage
-----------

.. code-block:: python

   from sam import SAM

   # Create SAM on GPIO 0
   sam = SAM(pin=0)

   # Speak English text
   sam.say("Hello World")

   # Clean up when done
   sam.stop()

Voice Customization
-------------------

.. code-block:: python

   sam = SAM(pin=0)

   # Adjust parameters
   sam.set_speed(72)     # Speech rate (1-255, default 72). Lower = slower.
   sam.set_pitch(64)     # Voice pitch (1-255, default 64). Higher = squeakier.
   sam.set_mouth(128)    # Mouth shape (1-255, default 128).
   sam.set_throat(128)   # Throat shape (1-255, default 128).

   # Robot voice
   sam.set_pitch(40)
   sam.set_mouth(150)
   sam.set_throat(90)
   sam.say("I am a robot")

   # High-pitched voice
   sam.set_pitch(96)
   sam.say("Hello there")

Speaking Phonemes Directly
--------------------------

Bypass the English-to-phoneme reciter for precise control:

.. code-block:: python

   sam.say_phonetic("/HEH4LOW WERLD")

Use ``text_to_phonemes()`` to see what the reciter generates:

.. code-block:: python

   phonemes = sam.text_to_phonemes("Hello World")
   print(phonemes)  # /HEHLOW WERLD

Saving to WAV
-------------

Generate WAV files for testing on desktop Python or saving to SD card:

.. code-block:: python

   sam.save_wav("Hello World", "hello.wav")

Desktop Testing
---------------

The library also works on standard desktop Python for testing:

.. code-block:: bash

   python test_desktop.py

This generates WAV files you can play to verify speech quality without hardware.
