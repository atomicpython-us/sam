Hardware Setup
==============

Supported Platforms
-------------------

- **Raspberry Pi Pico** (RP2040) -- primary target, native C module included
- **ESP32** -- compatible (Python code works, native C module requires Xtensa compiler to build)
- **Desktop Python** -- WAV file generation for testing

.. note::

   The pure Python code runs on any MicroPython board with PWM support.
   The native C module (for fast rendering) must be compiled separately
   for each architecture. A pre-built module is included for RP2040.
   See :doc:`native_module` for building on other platforms.

Circuit
-------

Minimal setup requires just a GPIO pin, a resistor, and a speaker:

.. code-block:: text

       Pico                    Speaker
   +---------+              +----------+
   |         |   1K ohm     |          |
   |  GP0  --+---[====]-----+  (+)     |
   |         |              |          |
   |   GND --+--------------+  (-)     |
   |         |              |          |
   +---------+              +----------+

**Components:**

- **1K resistor** -- limits current to protect the GPIO pin
- **Speaker** -- 8 ohm or piezo buzzer
- **100nF capacitor** (optional) -- across speaker terminals for LC filtering

Pin Selection
-------------

**Raspberry Pi Pico:**

Any GPIO pin works. The default is GP0.

.. code-block:: python

   sam = SAM(pin=0)   # GP0
   sam = SAM(pin=15)  # GP15

**ESP32:**

Use any GPIO capable of PWM output. GPIO 25 and 26 are common choices.

.. code-block:: python

   sam = SAM(pin=25)

PWM Audio Details
-----------------

Audio is output as a PWM signal with the following characteristics:

.. list-table::
   :widths: 30 20 20

   * - Parameter
     - Pico (RP2040)
     - ESP32
   * - PWM frequency
     - 62.5 kHz
     - 40 kHz
   * - PWM resolution
     - ~10-bit effective
     - ~10-bit effective
   * - Sample rate
     - 8000 Hz
     - 8000 Hz

The PWM carrier frequency is well above the audible range. The duty cycle
modulation encodes the audio waveform.

Improving Audio Quality
-----------------------

For better sound quality:

1. **RC low-pass filter** -- Add a 10K resistor + 10nF capacitor between the
   GPIO and speaker to filter the PWM carrier.

2. **Audio amplifier** -- Use a PAM8403 or LM386 amplifier module for louder,
   cleaner output.

3. **Larger speaker** -- A 40mm or larger speaker produces clearer speech than
   a piezo buzzer.
