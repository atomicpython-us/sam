// Generate reference WAV files from the JS SAM implementation
const SamJs = require('sam-js');
const fs = require('fs');

function saveWav(filename, buffer, sampleRate) {
    const numSamples = buffer.length;
    const dataSize = numSamples;
    const fileSize = 36 + dataSize;
    const wav = Buffer.alloc(44 + dataSize);
    wav.write('RIFF', 0);
    wav.writeUInt32LE(fileSize, 4);
    wav.write('WAVE', 8);
    wav.write('fmt ', 12);
    wav.writeUInt32LE(16, 16);
    wav.writeUInt16LE(1, 20);
    wav.writeUInt16LE(1, 22);
    wav.writeUInt32LE(sampleRate, 24);
    wav.writeUInt32LE(sampleRate, 28);
    wav.writeUInt16LE(1, 32);
    wav.writeUInt16LE(8, 34);
    wav.write('data', 36);
    wav.writeUInt32LE(dataSize, 40);
    for (let i = 0; i < numSamples; i++) {
        wav[44 + i] = buffer[i];
    }
    fs.writeFileSync(filename, wav);
    console.log(`  ${filename}: ${numSamples} samples @ ${sampleRate}Hz = ${(numSamples/sampleRate).toFixed(2)}s`);
}

const phrases = [
    ["Hello", "ref_hello.wav"],
    ["Hello World", "ref_hello_world.wav"],
    ["Testing one two three", "ref_123.wav"],
    ["How are you today", "ref_how.wav"],
    ["I am Sam", "ref_sam.wav"],
];

console.log("Generating JS SAM reference WAVs at 22050 Hz\n");

for (const [text, filename] of phrases) {
    const sam = new SamJs({ phonetic: false, pitch: 64, speed: 72, mouth: 128, throat: 128 });
    const buf = sam.buf8(text);
    if (buf) {
        saveWav(filename, buf, 22050);
    } else {
        console.log(`  FAILED: ${text}`);
    }
}

console.log("\nDone!");
