"""An original ten-second, gently syncopated instrumental cue."""
from pathlib import Path
import wave
import numpy as np

ROOT = Path(__file__).resolve().parent
SR = 48000
DURATION = 10
BEAT = 60 / 96
rng = np.random.default_rng(91)
mix = np.zeros((SR * DURATION, 2), dtype=np.float64)


def add(signal, start, gain=1, pan=0):
    offset = round(start * SR)
    length = min(len(signal), len(mix) - offset)
    if length <= 0:
        return
    angle = (pan + 1) * np.pi / 4
    mix[offset:offset + length, 0] += signal[:length] * gain * np.cos(angle)
    mix[offset:offset + length, 1] += signal[:length] * gain * np.sin(angle)


def tone(note, length=1.5, kind='keys'):
    t = np.arange(round(length * SR)) / SR
    frequency = 440 * 2 ** ((note - 69) / 12)
    attack = 1 - np.exp(-t / 0.007)
    if kind == 'bass':
        sound = (np.sin(2*np.pi*frequency*t) + .15*np.sin(4*np.pi*frequency*t))
        envelope = attack * np.exp(-t / .28)
    elif kind == 'melody':
        sound = np.sin(2*np.pi*frequency*t) * np.exp(-t/.48)
        sound += .24*np.sin(4*np.pi*frequency*t)*np.exp(-t/.20)
        sound += .055*np.sin(6*np.pi*frequency*t)*np.exp(-t/.10)
        envelope = attack
    else:
        sound = np.sin(2*np.pi*frequency*t)*np.exp(-t/.60)
        sound += .23*np.sin(4*np.pi*frequency*t)*np.exp(-t/.25)
        sound += .065*np.sin(6*np.pi*frequency*t)*np.exp(-t/.13)
        envelope = attack
    release = np.minimum(1, (length-t) / .04)
    return sound * envelope * release


# C6 — Am7 — Fmaj7 — C6/G. Four bars at 96 BPM = exactly 10 seconds.
chords = [(60,64,67,69),(57,60,64,67),(53,57,60,64),(55,60,64,69)]
bass_notes = [36,33,29,31]
for bar, chord in enumerate(chords):
    bar_start = bar * 4 * BEAT
    for beat, velocity in [(0,.9),(1.5,.66),(2.5,.76)]:
        for index, note in enumerate(chord):
            add(tone(note),bar_start+beat*BEAT+index*.016,
                .085*velocity,pan=-.28 + index*.13)
    for beat, note in [(0,bass_notes[bar]),(2,bass_notes[bar]+7)]:
        add(tone(note, .75, 'bass'),bar_start+beat*BEAT,.17)

melodies = [
    [(0.5,76),(1.5,79),(2.25,81),(3.0,79)],
    [(0.5,76),(1.5,72),(2.5,74),(3.0,76)],
    [(0.5,77),(1.5,76),(2.25,72),(3.25,69)],
    [(0.0,74),(1.0,76),(2.0,79),(3.0,72)],
]
for bar, notes in enumerate(melodies):
    for i, (beat,note) in enumerate(notes):
        add(tone(note, 1.2, 'melody'),(4*bar+beat)*BEAT,.13,
            pan=.17 if i%2 else -.12)

# Quiet brushed shakers and a rounded kick keep the cue relaxed.
for tick in range(32):
    t = np.arange(round(.115*SR))/SR
    noise = rng.normal(0,1,len(t))
    shaker = np.concatenate(([0],np.diff(noise)))
    shaker *= (1-np.exp(-t/.008))*np.exp(-t/.021)
    add(shaker,tick*BEAT/2,.015 if tick%2 else .010,pan=.35)
for beat in (0,2,4,6,8,10,12,14):
    t = np.arange(round(.23*SR))/SR
    phase = 2*np.pi*(48*t+24*.035*(1-np.exp(-t/.035)))
    kick = np.sin(phase)*(1-np.exp(-t/.003))*np.exp(-t/.06)
    add(kick,beat*BEAT,.13)

# Small stereo echoes add space without obscuring the melody.
dry = mix.copy()
for delay,gain in [(.105,.10),(.173,.075),(.267,.045)]:
    samples = round(delay*SR)
    mix[samples:] += dry[:-samples,::-1]*gain
fade_in = round(.16*SR)
fade_out = round(.65*SR)
mix[:fade_in] *= np.linspace(0,1,fade_in)[:,None]
mix[-fade_out:] *= np.linspace(1,0,fade_out)[:,None]**1.3
mix *= .78 / max(np.max(np.abs(mix)), .001)
pcm = (np.clip(mix,-1,1)*32767).astype('<i2')
with wave.open(str(ROOT/'apple_relaxed_music.wav'),'wb') as output:
    output.setnchannels(2)
    output.setsampwidth(2)
    output.setframerate(SR)
    output.writeframes(pcm.tobytes())
print('Original stereo music written: 10 seconds, 48 kHz.')
