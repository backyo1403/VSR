"""A synthesised score for the film: bright, major-key, building to the prize reveal.

Written rather than sourced. Any real track would need a licence the event does not have,
and a mis-licensed bed in a customer-facing video is a problem that outlives the video.
Everything here is generated from oscillators and noise, so it is unambiguously ours to
use — and if the team later buys a track, build.py takes any WAV in its place.

Key of D major, 100 BPM, I–V–vi–IV. The arrangement opens on pads alone under the title,
adds bass and plucks for the explanation, brings in percussion as the race gets going,
lifts a horn line for the weather and helps, and lands on a sustained major chord.
"""
import io, json, os, subprocess, sys
import numpy as np

HERE  = os.path.dirname(os.path.abspath(__file__))
FFDIR = r"C:\Users\Surface\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin"
FFMPEG = os.path.join(FFDIR, "ffmpeg.exe")

SR   = 48000
BPM  = 100.0
BEAT = 60.0 / BPM          # 0.6 s
BAR  = 4 * BEAT            # 2.4 s
TOTAL = float(sys.argv[1]) if len(sys.argv) > 1 else 200.0
N = int(TOTAL * SR)

rng = np.random.default_rng(7)
L = np.zeros(N, dtype=np.float64)
R = np.zeros(N, dtype=np.float64)


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def add(buf_l, buf_r, at, sig, pan=0.0, gain=1.0):
    i = int(at * SR)
    if i >= N:
        return
    s = sig[:max(0, N - i)] * gain
    lg, rg = np.sqrt((1 - pan) / 2), np.sqrt((1 + pan) / 2)
    buf_l[i:i + len(s)] += s * lg
    buf_r[i:i + len(s)] += s * rg


def env(n, a, d, s, r, sus=None):
    """Straight ADSR in seconds; sus is the level held between decay and release."""
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    sus = s if sus is None else sus
    hold = max(0, n - a - d - r)
    return np.concatenate([
        np.linspace(0, 1, a, endpoint=False) ** 1.5 if a else np.array([]),
        np.linspace(1, sus, d, endpoint=False) if d else np.array([]),
        np.full(hold, sus),
        np.linspace(sus, 0, r) ** 1.6 if r else np.array([]),
    ])[:n]


def saw(f, n, detune=0.0, phase=0.0):
    t = np.arange(n) / SR
    ph = (f * (1 + detune)) * t + phase
    return 2.0 * (ph - np.floor(ph + 0.5))


def tri(f, n, phase=0.0):
    t = np.arange(n) / SR
    ph = (f * t + phase) % 1.0
    return 4 * np.abs(ph - 0.5) - 1


def sine(f, n, phase=0.0):
    return np.sin(2 * np.pi * (f * np.arange(n) / SR + phase))


def lowpass(x, cutoff, res=0.0):
    """Two-pole state-variable filter — cheap, stable, and gentle enough for pads."""
    f = 2.0 * np.sin(np.pi * min(cutoff, SR * 0.45) / SR)
    q = 1.0 - res
    low = np.zeros_like(x)
    band = 0.0
    l = 0.0
    for i in range(len(x)):
        h = x[i] - l - q * band
        band += f * h
        l += f * band
        low[i] = l
    return low


def lowpass_fast(x, cutoff):
    """One-pole; used where a whole voice is filtered and the curve matters less."""
    a = np.exp(-2.0 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def highpass_fast(x, cutoff):
    return x - lowpass_fast(x, cutoff)


# ---------------------------------------------------------------- voices
def pad(root_midi, chord, dur, bright=1500.0):
    """Wide detuned-saw pad: the harmonic bed under everything."""
    n = int(dur * SR)
    out = np.zeros(n)
    for k, m in enumerate(chord):
        f = midi(m)
        for det in (-0.004, 0.0, 0.0045):
            out += saw(f, n, det, phase=rng.random()) * 0.33
    out = lowpass_fast(out, bright)
    return out * env(n, 0.55, 0.4, 0.72, 0.9) / max(1, len(chord))


def horn(m, dur, gain=1.0):
    """Saw stack with a little vibrato and a bite on the attack — stands in for brass."""
    n = int(dur * SR)
    f = midi(m)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * np.arange(n) / SR)
    sig = (saw(f, n, -0.003) + saw(f, n, 0.003) + saw(f, n) * 1.2) / 3.2
    sig = sig * vib
    sig = lowpass_fast(sig, 2600)
    return sig * env(n, 0.05, 0.18, 0.78, 0.30) * gain


def pluck(m, dur, gain=1.0):
    n = int(dur * SR)
    f = midi(m)
    sig = tri(f, n) * 0.7 + sine(f * 2, n) * 0.2
    return sig * env(n, 0.004, 0.16, 0.12, max(0.06, dur - 0.2)) * gain


def bass(m, dur, gain=1.0):
    n = int(dur * SR)
    f = midi(m)
    sig = sine(f, n) * 0.85 + saw(f, n) * 0.18
    sig = lowpass_fast(sig, 420)
    return sig * env(n, 0.012, 0.10, 0.85, 0.12) * gain


def kick(gain=1.0):
    n = int(0.42 * SR)
    t = np.arange(n) / SR
    f = 118 * np.exp(-t * 26) + 44
    sig = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return sig * np.exp(-t * 8.5) * gain


def snare(gain=1.0):
    n = int(0.30 * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 22) * 0.5
    nz = highpass_fast(rng.standard_normal(n), 1400) * np.exp(-t * 16)
    return (body + nz * 0.85) * gain


def hat(gain=1.0, dur=0.06):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return highpass_fast(rng.standard_normal(n), 7000) * np.exp(-t * 60) * gain


def swell(dur=2.6, gain=1.0):
    """Reverse-cymbal rise, used into the title and into the prize card."""
    n = int(dur * SR)
    nz = highpass_fast(rng.standard_normal(n), 2500)
    return nz * (np.linspace(0, 1, n) ** 2.6) * gain


def boom(gain=1.0):
    n = int(1.5 * SR)
    t = np.arange(n) / SR
    f = 78 * np.exp(-t * 5) + 36
    sig = np.sin(2 * np.pi * np.cumsum(f) / SR)
    nz = lowpass_fast(rng.standard_normal(n), 180) * 0.35
    return (sig + nz) * np.exp(-t * 3.0) * gain


# ---------------------------------------------------------------- arrangement
# I  V  vi  IV  in D major
CHORDS = [
    ("D",  [50, 57, 62, 66, 69]),   # D2 A2 D3 F#3 A3
    ("A",  [45, 57, 61, 64, 69]),   # A1 A2 C#3 E3 A3
    ("Bm", [47, 59, 62, 66, 71]),   # B1 B2 D3 F#3 B3
    ("G",  [43, 55, 62, 67, 71]),   # G1 G2 D3 G3 B3
]
ROOTS = [38, 33, 35, 31]            # bass notes, one octave lower
ARP = [[62, 66, 69, 74], [61, 64, 69, 73], [62, 66, 71, 74], [62, 67, 71, 74]]
MELODY = [  # (bar offset within a 4-bar cycle, beat, midi, beats long)
    (0, 0.0, 74, 1.5), (0, 1.5, 76, 0.5), (0, 2.0, 78, 2.0),
    (1, 0.0, 76, 1.0), (1, 1.0, 73, 1.0), (1, 2.0, 69, 2.0),
    (2, 0.0, 71, 1.5), (2, 1.5, 74, 0.5), (2, 2.0, 78, 2.0),
    (3, 0.0, 76, 2.0), (3, 2.0, 74, 2.0),
]

nbars = int(TOTAL / BAR) + 1
for b in range(nbars):
    t0 = b * BAR
    ci = b % 4
    name, chord = CHORDS[ci]

    # sections
    intro = b < 4
    sec_a = 4 <= b < 20
    sec_b = 20 <= b < 40
    sec_c = 40 <= b < 62
    sec_d = 62 <= b < 76
    outro = b >= 76

    pad_gain = 0.16 if intro else (0.20 if sec_a else 0.22)
    bright = 900 if intro else (1500 if sec_a else 2200)
    add(L, R, t0, pad(chord[0], chord, BAR * 1.02, bright), -0.25, pad_gain)
    add(L, R, t0, pad(chord[0], chord, BAR * 1.02, bright * 0.92), 0.25, pad_gain)

    if not intro:
        add(L, R, t0, bass(ROOTS[ci], BEAT * 3.2), 0.0, 0.30)
        add(L, R, t0 + BEAT * 2, bass(ROOTS[ci], BEAT * 1.6), 0.0, 0.20)

    if sec_a or sec_b or sec_c or sec_d:
        for k in range(8):
            m = ARP[ci][k % 4] + (12 if (sec_c or sec_d) and k % 4 == 3 else 0)
            g = 0.085 if sec_a else 0.10
            add(L, R, t0 + k * BEAT / 2, pluck(m, BEAT * 0.9), -0.4 + 0.8 * (k % 2), g)

    if sec_b or sec_c or sec_d:
        add(L, R, t0, kick(0.42))
        add(L, R, t0 + BEAT * 2, kick(0.34))
        for k in range(8):
            add(L, R, t0 + k * BEAT / 2, hat(0.045 if k % 2 else 0.075), 0.3)

    if sec_c or sec_d:
        add(L, R, t0 + BEAT * 1, snare(0.26), -0.1)
        add(L, R, t0 + BEAT * 3, snare(0.26), 0.1)
        if b % 4 == 3:
            add(L, R, t0 + BEAT * 3.5, snare(0.20), 0.0)

    if sec_c or sec_d or outro:
        for (bo, beat, m, blen) in MELODY:
            if b % 4 == bo:
                add(L, R, t0 + beat * BEAT, horn(m, blen * BEAT * 0.96), 0.0,
                    0.15 if sec_c else 0.19)

    # accents
    if b == 3:
        add(L, R, t0 + BAR - 2.4, swell(2.4, 0.10), 0.0)
    if b == 4:
        add(L, R, t0, boom(0.42))
    if b == 40 or b == 62:
        add(L, R, t0 - 2.0, swell(2.0, 0.09), 0.0)
        add(L, R, t0, boom(0.34))

# a pair of short delays for depth, then a soft-knee limiter
def delay(x, ms, fb, mix):
    d = int(ms / 1000.0 * SR)
    y = x.copy()
    buf = np.zeros(len(x) + d)
    buf[:len(x)] = x
    for i in range(d, len(x)):
        buf[i] += buf[i - d] * fb
    return (1 - mix) * y + mix * buf[:len(x)]

L = delay(L, 231, 0.26, 0.18)
R = delay(R, 287, 0.26, 0.18)

# fade the very top and tail
fi, fo = int(2.5 * SR), int(4.5 * SR)
ramp_in = np.linspace(0, 1, fi) ** 1.4
ramp_out = np.linspace(1, 0, fo) ** 1.2
for buf in (L, R):
    buf[:fi] *= ramp_in
    buf[-fo:] *= ramp_out

stereo = np.stack([L, R], axis=1)
peak = np.max(np.abs(stereo))
stereo = stereo / peak * 0.72                      # headroom; the mix ducks it further
stereo = np.tanh(stereo * 1.15) * 0.88             # gentle saturation instead of clipping

raw = os.path.join(HERE, "music_raw.f32")
stereo.astype(np.float32).tofile(raw)
out = os.path.join(HERE, "music.wav")
subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR),
                "-ac", "2", "-i", raw, "-c:a", "pcm_s16le", out], check=True)
os.remove(raw)
print("wrote %s  %.1fs  %.1f MB" % (out, TOTAL, os.path.getsize(out) / 1e6))
