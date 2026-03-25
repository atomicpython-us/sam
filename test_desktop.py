"""
Desktop test: generate WAV files and compare against JS SAM reference.
"""
import sys
sys.path.insert(0, '.')

from sam.reciter import text_to_phonemes
from sam.phonemes import process_phonemes
from sam.renderer import render, SAMPLE_RATE
from sam.audio import WavWriter


def generate_wav(text, filename, speed=72, pitch=64, mouth=128, throat=128):
    phonemes = text_to_phonemes(text)
    print(f"  '{text}' -> {phonemes}")
    if not phonemes:
        print("  ERROR: no phonemes")
        return
    phoneme_index, phoneme_length, stress = process_phonemes(phonemes, speed)
    buffer = render(phoneme_index, phoneme_length, stress,
                    speed=speed, pitch=pitch, mouth=mouth, throat=throat)
    WavWriter(filename, sample_rate=SAMPLE_RATE).write(buffer)
    print(f"  {len(buffer)} samples @ {SAMPLE_RATE} Hz = {len(buffer)/SAMPLE_RATE:.2f}s -> {filename}")


if __name__ == '__main__':
    print(f"SAM Test (sample rate: {SAMPLE_RATE} Hz)\n")
    generate_wav("Hello", "test_hello.wav")
    generate_wav("Hello World", "test_hello_world.wav")
    generate_wav("Testing one two three", "test_123.wav")
    generate_wav("How are you today", "test_how.wav")
    generate_wav("I am Sam", "test_sam.wav")
    print("\nCompare against ref_*.wav from gen_reference.js")
