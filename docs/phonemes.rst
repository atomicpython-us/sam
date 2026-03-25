Phoneme Reference
=================

SAM uses a set of 81 phoneme codes. Phonemes can be specified directly
using ``say_phonetic()`` for precise control over pronunciation.

Vowels
------

.. list-table::
   :header-rows: 1
   :widths: 10 15 25

   * - Code
     - Sound
     - Example
   * - IY
     - ee
     - b\ **ea**\ t
   * - IH
     - i
     - b\ **i**\ t
   * - EH
     - e
     - b\ **e**\ t
   * - AE
     - a
     - b\ **a**\ t
   * - AA
     - ah
     - f\ **a**\ ther
   * - AH
     - u
     - b\ **u**\ t
   * - AO
     - aw
     - b\ **ough**\ t
   * - UH
     - oo
     - b\ **oo**\ k
   * - AX
     - a
     - \ **a**\ bout
   * - IX
     - i
     - ros\ **e**\ s
   * - ER
     - er
     - b\ **ir**\ d
   * - UX
     - oo
     - b\ **oo**\ t
   * - OH
     - o
     - g\ **o**

Diphthongs
----------

.. list-table::
   :header-rows: 1
   :widths: 10 15 25

   * - Code
     - Sound
     - Example
   * - EY
     - ay
     - d\ **ay**
   * - AY
     - eye
     - m\ **y**
   * - OY
     - oy
     - b\ **oy**
   * - AW
     - ow
     - h\ **ow**
   * - OW
     - oh
     - g\ **o**
   * - UW
     - oo
     - t\ **oo**

Consonants
----------

.. list-table::
   :header-rows: 1
   :widths: 10 15 25

   * - Code
     - Sound
     - Example
   * - P
     - p
     - **p**\ at
   * - B
     - b
     - **b**\ at
   * - T
     - t
     - **t**\ ap
   * - D
     - d
     - **d**\ og
   * - K
     - k
     - **c**\ at
   * - G
     - g
     - **g**\ et
   * - M
     - m
     - **m**\ an
   * - N
     - n
     - **n**\ o
   * - NX
     - ng
     - si\ **ng**
   * - L
     - l
     - **l**\ et
   * - R
     - r
     - **r**\ ed
   * - W
     - w
     - **w**\ et
   * - Y
     - y
     - **y**\ es
   * - S
     - s
     - **s**\ it
   * - Z
     - z
     - **z**\ oo
   * - SH
     - sh
     - **sh**\ ip
   * - ZH
     - zh
     - mea\ **s**\ ure
   * - F
     - f
     - **f**\ in
   * - V
     - v
     - **v**\ an
   * - TH
     - th
     - **th**\ in
   * - DH
     - dh
     - **th**\ is
   * - /H
     - h
     - **h**\ at
   * - CH
     - ch
     - **ch**\ in
   * - J
     - j
     - **j**\ udge
   * - WH
     - wh
     - **wh**\ at
   * - Q
     - (stop)
     - glottal stop

Stress Markers
--------------

Stress markers (1-8) are placed after a vowel to indicate emphasis.
Primary stress is ``4``.

.. code-block:: text

   HEH4LOW       -- stress on the first syllable
   TAADEY5       -- stress on the second syllable

Higher stress values produce higher pitch on the stressed syllable.

Examples
--------

.. code-block:: python

   # Direct phoneme input
   sam.say_phonetic("/HEH4LOW WERLD")

   # See what the reciter generates
   print(sam.text_to_phonemes("computer"))
   # KAHMSPYUW4TER

   # Fine-tune pronunciation by editing phonemes
   sam.say_phonetic("AY4 AEM SAE4M")
