"""
Prosody module for atomic_voice — F0 contour (pitch variation).

Modifies pitch values based on stress patterns and sentence type
to produce more natural-sounding intonation.

Rules:
  - Question (text ends with '?'): raise pitch 30% on last stressed syllable
  - Statement: lower pitch 20% on final syllable
  - Stressed syllables (stress >= 4): raise pitch 10%
  - Unstressed (stress 1-3): lower 5%
  - Random jitter (+-2%) on every pitch value for naturalness
"""

try:
    from os import urandom
    def _rand_byte():
        return urandom(1)[0]
except (ImportError, OSError):
    # Fallback: simple LCG for environments without urandom
    _lcg = [0xA5]
    def _rand_byte():
        _lcg[0] = (_lcg[0] * 173 + 37) & 0xFF
        return _lcg[0]


def apply_prosody(pitches, stress, is_question=False):
    """Apply prosodic pitch contour to a pitch array.

    Args:
        pitches: bytearray of pitch values (one per frame), modified in place
        stress: list/bytearray of stress values per phoneme (not per frame)
        is_question: True if the utterance is a question (raise final pitch)

    Returns:
        pitches (modified in place for efficiency, also returned for chaining)
    """
    n = len(pitches)
    if n == 0:
        return pitches

    # Build a per-frame stress map from the phoneme-level stress array.
    # Since we don't have the exact phoneme->frame mapping here, we use
    # a simple heuristic: divide frames evenly across stress entries.
    ns = len(stress)
    if ns == 0:
        return pitches

    # Find the last stressed syllable index (stress >= 4)
    last_stressed = -1
    for i in range(ns - 1, -1, -1):
        if stress[i] >= 4:
            last_stressed = i
            break

    for frame_idx in range(n):
        # Map frame index to stress index
        s_idx = (frame_idx * ns) // n
        if s_idx >= ns:
            s_idx = ns - 1
        s = stress[s_idx]

        p = pitches[frame_idx]
        if p == 0:
            continue

        # Base pitch modification based on stress level
        if s >= 4:
            # Stressed: raise pitch 10%
            p = min(255, (p * 110 + 50) // 100)
        elif s >= 1:
            # Unstressed: lower pitch 5%
            p = max(1, (p * 95 + 50) // 100)

        # Question intonation: raise last stressed syllable 30%
        if is_question and last_stressed >= 0 and s_idx == last_stressed:
            p = min(255, (p * 130 + 50) // 100)

        # Statement: lower final 20% of frames by 20%
        if not is_question and frame_idx >= (n * 4) // 5:
            p = max(1, (p * 80 + 50) // 100)

        # Random jitter: +-2%
        jitter = _rand_byte()
        # Map 0-255 to -2% .. +2%: (jitter - 128) * 2 / 12800
        jitter_factor = 100 + ((jitter - 128) * 2) // 64  # roughly +-2%
        jitter_factor = max(98, min(102, jitter_factor))
        p = max(1, min(255, (p * jitter_factor + 50) // 100))

        pitches[frame_idx] = p

    return pitches
