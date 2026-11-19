#!/usr/bin/env python3
"""A finger-plucked acoustic guitar, and the "arrive" figure: a whole-tone hammer-on that rings on the tonic.

Used by make-sounds.py (python3 dev/make-sounds.py); standard library and ffmpeg only.

The figure: a bass note is thumbed, a hair later the first note is plucked by a fingertip and 0.08 s after that it is hammered up a
whole step to the second, which rings and fades. The shipped one (FIGURES["drop-d"]): D2, the low string in drop D, under G3 -> A3
(the 11th of the bass note, then the 12th). FIGURES also has the earlier ones (vii to i, from the film's guitar theme, in G and in C).

The pluck is meant to sound fingerpicked: the pad of a finger, not a nail or a pick. Two things make it so (FINGER): the string is
released over a few ms (a smoothstep ramp), not on one sample, which clicks; and the excitation has less noise, is softer, and the
nail's burst of highs is nearly gone. The thumb note has the same ramp.

The string is a Karplus-Strong loop: a delay line of one period, a one-pole lowpass in the loop (the highs die first, as on a
real string), an allpass for fractional tuning, and a loop gain set from the ring time. Two polarisations per string, a hair
apart in pitch, make the slow beating of a real steel string. The pluck is the string pulled aside at `pos` (a triangle) plus
soft noise, combed at the same position. The hammer-on is the same string: the string is already moving, so there is no second pluck: the first note hands over
(a 16 ms fade as the fret stops it) to a softer, gritless note on the shorter length that eases in over 14 ms, with a small dull thump of
the finger on the board. A first version (0.15 s, a plucked second note, a bigger thump) had a 9.7 dB spike at the hammer over the
note's own sustain and a +6 dB bump in the envelope: it sounded like a second pluck. Now the envelope runs on through the hammer as one decay. The body is a short
impulse response of a few decaying modes (ffmpeg afir); a small room (aecho) is added last.

Levels: the file is set to -24.5 LUFS integrated (what the previous glass tone measured; ffmpeg ebur128 gates at -70 LUFS, so it is
measured twice), peak about -5 to -6 dBFS. The bass level is set against the melody alone (see make_arrive). Checked by pitch, harmonic levels and spectrogram
only; nobody has heard it but the user.
"""
import math, os, random, struct, subprocess, tempfile, wave

RATE = 44100


def string(f, dur, amp, *, pos, soft, t60, s, seed, detune=1.0, grit=0.35):
    """One polarisation of one string: dur seconds of samples (a list), fundamental f."""
    rnd = random.Random(seed)
    f *= detune
    L = RATE / f
    # total loop delay = N (buffer) + s (the lowpass's delay at DC) + d (allpass)
    N = int(L - s - 0.5)
    d = L - s - N                       # in [0.5, 1.5)
    C = (1 - d) / (1 + d)
    rho = 10 ** (-3.0 / (t60 * f))      # round-trip gain that gives t60 seconds to -60 dB at DC

    # excitation: the string pulled aside at `pos` (a triangle: harmonic n is about sin(n pi pos) / n^2, so a pluck a fifth of
    # the way along has a strong 2nd and weak 5th) plus soft noise for the fingertip's texture, combed at the same position
    peak = min(N - 2, max(2, int(N * pos)))
    tri = [(i / peak if i < peak else (N - i) / (N - peak)) for i in range(N)]
    noise = [rnd.uniform(-1, 1) for _ in range(N)]
    lp, a = 0.0, soft                   # soft: 0 keeps every harmonic, near 1 keeps only the lowest
    for i in range(N):
        lp = (1 - a) * noise[i] + a * lp
        noise[i] = lp
    k = max(1, int(N * pos))
    noise = [noise[i] - noise[(i - k) % N] for i in range(N)]
    top = max(abs(x) for x in noise) or 1.0
    ex = [tri[i] + grit * (1 - a) ** 0.5 * noise[i] / top for i in range(N)]
    mean = sum(ex) / N
    ex = [x - mean for x in ex]
    top = max(abs(x) for x in ex) or 1.0
    buf = [x / top for x in ex]

    out = [0.0] * int(dur * RATE)
    idx = 0
    lp_prev = ap_x = ap_y = 0.0
    for n in range(len(out)):
        x = buf[idx]
        out[n] = x * amp
        y = (1 - s) * x + s * lp_prev
        lp_prev = x
        z = C * y + ap_x - C * ap_y
        ap_x, ap_y = y, z
        buf[idx] = rho * z
        idx += 1
        if idx == N:
            idx = 0
    return out


def guitar_note(f, dur, amp, *, pos, soft, t60, s, seed, grit=0.35):
    """Both polarisations: the vertical one (the one the finger drives) and a weaker, slightly sharp, shorter one."""
    a = string(f, dur, amp, pos=pos, soft=soft, t60=t60, s=s, seed=seed, grit=grit)
    b = string(f, dur, amp * 0.42, pos=pos * 1.07, soft=soft, t60=t60 * 0.62, s=s, seed=seed + 7, detune=1.0011, grit=grit)
    return [x + y for x, y in zip(a, b)]


def add(buf, sig, start):
    n0 = int(start * RATE)
    for i, x in enumerate(sig):
        if n0 + i >= len(buf):
            break
        buf[n0 + i] += x


def burst(dur, tau, lo, hi, amp, seed):
    """A short noise burst, band-limited by two one-pole filters (hi pass at `lo`, low pass at `hi`), decaying with tau."""
    rnd = random.Random(seed)
    out, lpf, hpf = [], 0.0, 0.0
    al = math.exp(-2 * math.pi * hi / RATE)
    ah = math.exp(-2 * math.pi * lo / RATE)
    for i in range(int(dur * RATE)):
        x = rnd.uniform(-1, 1)
        lpf = (1 - al) * x + al * lpf
        hpf = (1 - ah) * lpf + ah * hpf
        out.append((lpf - hpf) * math.exp(-i / RATE / tau) * amp)
    return out


def write_wav(path, buf, peak):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, x / peak)) * 32767 * 0.5)) for x in buf))


def body_ir(path):
    """A top-plate / air-cavity impulse response: a flat direct path plus a few decaying modes, each a modest bump.

    A decaying sine's spectral peak is about A * tau * RATE / 2, so each mode's amplitude is set from the peak gain it
    should add over the direct path (1.0), not picked by eye: a first version picked by eye had peaks hundreds of times
    the direct level and carved the string's harmonics away.
    """
    rnd = random.Random(5)
    modes = [(98, 6.0, 0.060), (196, 4.0, 0.045), (292, 2.0, 0.035), (410, 2.0, 0.028), (530, 1.5, 0.022),
             (780, 1.0, 0.016), (1150, 1.0, 0.012)]      # (Hz, dB over the direct path at the peak, decay seconds)
    n = int(0.25 * RATE)
    ir = [0.0] * n
    ir[0] = 1.0
    for f, db, tau in modes:
        amp = 2.0 * (10 ** (db / 20) - 1) / (tau * RATE)
        ph = rnd.uniform(0, 2 * math.pi)
        for i in range(n):
            t = i / RATE
            ir[i] += amp * math.exp(-t / tau) * math.sin(2 * math.pi * f * t + ph)
    peak = max(abs(x) for x in ir)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(x / peak * 32767 * 0.9)) for x in ir))


def lufs(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    tail = r[r.rindex("Integrated loudness"):]
    return float(tail.split("I:")[1].split("LUFS")[0])


def compose(from_hz, to_hz, bass_hz=None, bass_amp=0.17, bass_s=0.30, bass_pos=0.2, bass_grit=0.35, parts=("bass", "melody"), seconds=3.0, hammer_at=0.08, lead=0.03,
         bass_ramp=0.0, pluck_grit=0.35, pluck_soft=0.35, pluck_nail=0.18, pluck_ramp=0.0, pluck_s=0.30, pluck_pos=0.22,
         hammer_amp=0.5, hammer_grit=0.0, hammer_soft=0.7, hammer_ramp=0.014, thump=0.07, stop_tau=0.016):
    buf = [0.0] * int(seconds * RATE)

    # 0. the thumb: an open bass string, plucked a hair before the fingers, soft and dark, ringing under everything
    if bass_hz and "bass" in parts:
        thumb = guitar_note(bass_hz, seconds, bass_amp, pos=bass_pos, soft=0.72, t60=4.2, s=bass_s, seed=41, grit=bass_grit)
        for i in range(min(int(bass_ramp * RATE), len(thumb))):
            u = i / int(bass_ramp * RATE)
            thumb[i] *= u * u * (3 - 2 * u)
        add(buf, thumb, 0.0)
        add(buf, burst(0.03, 0.008, 80, 500, 0.12 * bass_amp, 17), 0.0)

    if "melody" not in parts:
        return buf
    # 1. the pluck: the lower note, a fingertip, a little brighter than the hammered note
    first = guitar_note(from_hz, seconds, 1.0, pos=pluck_pos, soft=pluck_soft, t60=2.6, s=pluck_s, seed=11, grit=pluck_grit)
    nr0 = int(pluck_ramp * RATE)                                      # the finger pad: the string is let go over a few ms, not instantly
    for i in range(min(nr0, len(first))):
        u = i / nr0
        first[i] *= u * u * (3 - 2 * u)
    # the fret stops it: an exponential fade over a few ms (stop_tau), so the old note hands over instead of ending in a tick
    n_h = int(hammer_at * RATE)
    for i in range(n_h, len(first)):
        first[i] *= math.exp(-(i - n_h) / RATE / stop_tau)
    add(buf, first[: n_h + int(0.12 * RATE)], lead)
    add(buf, burst(0.012, 0.003, 1500, 6500, pluck_nail, 3), lead)    # the nail/fingertip on the string

    # 2. the hammer-on: the tonic on the shorter string. No pluck: the string is already moving, so the new note is softer, has
    # no fingertip grit, and comes in over hammer_ramp seconds (a smoothstep), with only a small dull thump of the finger on the board
    second = guitar_note(to_hz, seconds - hammer_at, hammer_amp, pos=0.11, soft=hammer_soft, t60=3.6, s=0.30, seed=23, grit=hammer_grit)
    nr = int(hammer_ramp * RATE)
    for i in range(min(nr, len(second))):
        u = i / nr
        second[i] *= u * u * (3 - 2 * u)
    add(buf, second, lead + hammer_at)
    add(buf, burst(0.05, 0.015, 100, 450, thump, 9), lead + hammer_at)

    return buf


def make(name, outdir, from_hz, to_hz, target_lufs=-24.5, seconds=3.0, **kw):
    buf = compose(from_hz, to_hz, seconds=seconds, **kw)
    peak = max(abs(x) for x in buf) or 1.0
    with tempfile.TemporaryDirectory() as tmp:
        dry = os.path.join(tmp, "dry.wav")
        ir = os.path.join(tmp, "ir.wav")
        wet = os.path.join(tmp, "wet.wav")
        write_wav(dry, buf, peak)
        body_ir(ir)
        # highpass at 40 Hz, not 70: the bass is C2 (65 Hz) and a 70 Hz high-pass took 3 dB off it
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", dry, "-i", ir, "-filter_complex",
                        "[0][1]afir=gtype=none,"
                        "highpass=f=40,lowpass=f=7000,"
                        "aecho=0.8:0.55:38|71|113:0.20|0.14|0.09,"
                        "alimiter=limit=0.9:level=disabled[o]", "-map", "[o]", "-c:a", "pcm_f32le", wet], check=True)
        faded = os.path.join(tmp, "faded.wav")
        fade = f"afade=t=out:st={seconds - 0.6:.2f}:d=0.6"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wet, "-af", fade, "-c:a", "pcm_f32le", faded], check=True)
        # ebur128 gates at -70 LUFS, so a quiet file measures wrong: bring it near the target first, then correct
        near = os.path.join(tmp, "near.wav")
        gain = target_lufs - lufs(faded)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", faded, "-af", f"volume={gain:.2f}dB", "-c:a", "pcm_f32le", near], check=True)
        gain += target_lufs - lufs(near)                   # level set on what is actually heard, fade included
        wav = os.path.join(tmp, name + ".wav")
        out = os.path.join(outdir, name + ".ogg")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", faded, "-af", f"volume={gain:.2f}dB", wav], check=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", "3", out], check=True)
    print("wrote", out)


# The figures, as MIDI note numbers (A4 = 69 = 440 Hz): the bass string, then the note hammered from and the note hammered to.
# `bass_amp` is measured against the melody alone (K-weighted, and for what a small speaker keeps, above 150 Hz): the lower the
# bass, the more it needs, because a small speaker barely plays it and the loudness measure discounts it too.
FIGURES = {
    # D2 (73.4 Hz, the low string in drop D), G3 -> A3 (196 -> 220 Hz): G is the 11th of the bass note, A the 12th (the fifth).
    # Shipped from 2026-11-19. 0.75: 1.6 LU under the melody, 9.6 for a small speaker.
    "drop-d": dict(bass=38, hammer=(55, 57), bass_amp=0.75),
    # vii -> i in C: C2, B-flat3 -> C4 (the figure in G moved down a fifth). 0.7: 1.9 and 9.4.
    "vii-i-c": dict(bass=36, hammer=(58, 60), bass_amp=0.7),
    # vii -> i in G: G2, F4 -> G4 (the film's theme; the first figure picked). 0.5: 4.0 and 8.6.
    "vii-i-g": dict(bass=43, hammer=(65, 67), bass_amp=0.5),
    # iv -> v in G: G2, C4 -> D4. 0.5: 3.9 and 8.9.
    "iv-v-g": dict(bass=43, hammer=(60, 62), bass_amp=0.5),
}


def midi_hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


# The fingerpicked attack (2026-11-19: "soften the attack a bit, mimicking finger picking"). The defaults of compose() are the earlier,
# harder pluck (a nail's burst of highs, a grittier excitation, the string let go on a single sample, which clicks). Measured on the
# melody alone, against that pluck: the highs in the first 20 ms are 4 dB lower (-14.6 to -19.0 dB of the energy), the centroid of the
# first 20 ms 392 to 290 Hz, the high-frequency peak at the onset 7 dB lower, mostly the click. SOFTER is a step further, for comparison.
FINGER = dict(pluck_nail=0.08, pluck_grit=0.22, pluck_soft=0.45, pluck_ramp=0.0025, pluck_s=0.33, bass_ramp=0.003)
SOFTER = dict(pluck_nail=0.0, pluck_grit=0.15, pluck_soft=0.55, pluck_ramp=0.004, pluck_s=0.36, bass_ramp=0.004)


def make_arrive(outdir, figure="drop-d", bass_amp=None, attack=FINGER):
    """sounds/arrive.ogg: a hammer-on over a bass note (FIGURES; the bass note is the key's root, or the string it is played on).

    The hammer-on is a whole step. Its octave and the key were moved around on 2026-11-19: G4 first, then G3 (F3 -> G3), then
    iv -> v, then vii -> i again, then down a fifth; the figures here are the ones worth coming back to.
    """
    f = FIGURES[figure]
    lo, hi = (midi_hz(n) for n in f["hammer"])
    # Bass: brighter and plucked nearer the bridge so its harmonics carry on a small speaker; the fundamental alone does not.
    # (First level: -12.5 LU and dark: "i don't really hear it".)
    make("arrive", outdir, lo, hi, bass_hz=midi_hz(f["bass"]), bass_amp=bass_amp if bass_amp is not None else f["bass_amp"],
         bass_s=0.15, bass_pos=0.12, bass_grit=0.4, **attack)
