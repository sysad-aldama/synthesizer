"""
Sample waveform synthesizer. Inspired by FM synthesizers such as the Yamaha DX-7.
Creates some simple waveform samples with adjustable parameters.

Written by Irmen de Jong (irmen@razorvine.net) - License: MIT open-source.
"""

import sys
import itertools
import random
import math
from .sample import Sample


__all__ = ["key_num", "key_freq", "note_freq", "octave_notes", "note_alias", "major_chords", "major_chord_keys",
           "WaveSynth", "Sine", "Triangle", "Square", "SquareH", "Sawtooth", "SawtoothH",
           "Pulse", "Harmonics", "WhiteNoise", "Linear",
           "FastSine", "FastPulse", "FastTriangle", "FastSawtooth", "FastSquare",
           "EnvelopeFilter", "MixingFilter", "AmpMudulationFilter", "DelayFilter", "EchoFilter",
           "ClipFilter", "AbsFilter", "NullFilter"]


octave_notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


note_alias = {
    'C': 'C',
    'C#': 'C#',
    'C##': 'D',
    'D': 'D',
    'D#': 'D#',
    'E': 'E',
    'E#': 'F',
    'F': 'F',
    'F#': 'F#',
    'F##': 'G',
    'G': 'G',
    'G#': 'G#',
    'G##': 'A',
    'A': 'A',
    'A#': 'A#',
    'B': 'B',
    'B#': 'C'
}


major_chords = {
    # from https://en.wikipedia.org/wiki/Major_seventh_chord
    # a one in the number tuple means that the note is from the next higher octave
    'C':  (('C', 'E', 'G', 'B'),       (0, 0, 0, 0)),
    'C#': (('C#', 'E#', 'G#', 'B#'),   (0, 0, 0, 1)),
    'D':  (('D', 'F#', 'A', 'C'),      (0, 0, 0, 1)),
    'D#': (('D#', 'F##', 'A#', 'C##'), (0, 0, 0, 1)),
    'E':  (('E', 'G#', 'B', 'D#'),     (0, 0, 0, 1)),
    'F':  (('F', 'A', 'C', 'E'),       (0, 0, 1, 1)),
    'F#': (('F#', 'A#', 'C#', 'E#'),   (0, 0, 1, 1)),
    'G':  (('G', 'B', 'D', 'F#'),      (0, 0, 1, 1)),
    'G#': (('G#', 'B#', 'D#', 'F##'),  (0, 1, 1, 1)),
    'A':  (('A', 'C#', 'E', 'G#'),     (0, 1, 1, 1)),
    'A#': (('A#', 'C##', 'E#', 'G##'), (0, 1, 1, 1)),
    'B':  (('B', 'D#', 'F#', 'A#'),    (0, 1, 1, 1)),
}


def major_chord_keys(rootnote, octave):
    keys, octaves = major_chords[rootnote.upper()]
    return (note_alias[keys[0]], octave+octaves[0]),\
           (note_alias[keys[1]], octave+octaves[1]),\
           (note_alias[keys[2]], octave+octaves[2]),\
           (note_alias[keys[3]], octave+octaves[3])


def key_num(note, octave):
    notes = {
        "C":   4,
        "C#":  5,
        "D":   6,
        "D#":  7,
        "E":   8,
        "F":   9,
        "F#": 10,
        "G":  11,
        "G#": 12,
        "A":  13,
        "A#": 14,
        "B":  15,
    }
    return (octave-1)*12 + notes[note.upper()]


def key_freq(key_number, a4=440.0):
    """
    Return the note frequency for the given piano key number.
    C4 is key 40 and A4 is key 49 (=440 hz).
    https://en.wikipedia.org/wiki/Piano_key_frequencies
    """
    return 2**((key_number-49)/12) * a4


def note_freq(note, octave=None, a4=440.0):
    """
    Return the frequency for the given note in the octave.
    Note can be like 'c#4' (= c# in 4th octave) or just 'c#' + specify octave separately.
    """
    if not octave:
        octave = int(note[-1:])
        note = note[:-1]
    return key_freq(key_num(note, octave), a4)


class WaveSynth:
    """
    Waveform sample synthesizer. Can generate various wave forms based on mathematic functions:
    sine, square (perfect or with harmonics), triangle, sawtooth (perfect or with harmonics),
    variable harmonics, white noise.  It also supports an optional LFO for Frequency Modulation.
    The resulting waveform sample data is in integer 16 or 32 bits format.
    """
    def __init__(self, samplerate=Sample.norm_samplerate, samplewidth=Sample.norm_samplewidth):
        if samplewidth not in (2, 4):
            raise ValueError("only sample widths 2 and 4 are supported")
        self.samplerate = samplerate
        self.samplewidth = samplewidth

    def sine(self, frequency, duration, amplitude=0.9999, phase=0.0, bias=0.0, fm_lfo=None):
        """Simple sine wave. Optional FM using a supplied LFO."""
        wave = self.__sine(frequency, amplitude, phase, bias, fm_lfo)
        return self.__render_sample(duration, wave)

    def sine_gen(self, frequency, amplitude=0.9999, phase=0.0, bias=0.0, fm_lfo=None):
        """Simple sine wave generator. Optional FM using a supplied LFO."""
        wave = self.__sine(frequency, amplitude, phase, bias, fm_lfo).generator()
        while True:
            yield int(next(wave))

    def square(self, frequency, duration, amplitude=0.75, phase=0.0, bias=0.0, fm_lfo=None):
        """
        A perfect square wave [max/-max].
        It is fast, but the square wave is not as 'natural' sounding as the ones
        generated by the square_h function (which is based on harmonics).
        """
        wave = self.__square(frequency, amplitude, phase, bias, fm_lfo)
        return self.__render_sample(duration, wave)

    def square_gen(self, frequency, amplitude=0.75, phase=0.0, bias=0.0, fm_lfo=None):
        """
        Generator for a perfect square wave [max/-max].
        It is fast, but the square wave is not as 'natural' sounding as the ones
        generated by the square_h function (which is based on harmonics).
        """
        wave = self.__square(frequency, amplitude, phase, bias, fm_lfo).generator()
        while True:
            yield int(next(wave))

    def square_h(self, frequency, duration, num_harmonics=16, amplitude=0.9999, phase=0.0, bias=0.0, fm_lfo=None):
        """A square wave based on harmonic sine waves (more natural sounding than pure square)"""
        wave = self.__square_h(frequency, num_harmonics, amplitude, phase, bias, fm_lfo)
        return self.__render_sample(duration, wave)

    def square_h_gen(self, frequency, num_harmonics=16, amplitude=0.9999, phase=0.0, bias=0.0, fm_lfo=None):
        """Generator for a square wave based on harmonic sine waves (more natural sounding than pure square)"""
        wave = self.__square_h(frequency, num_harmonics, amplitude, phase, bias, fm_lfo).generator()
        while True:
            yield int(next(wave))

    def triangle(self, frequency, duration, amplitude=0.9999, phase=0.0, bias=0.0, fm_lfo=None):
        """Perfect triangle waveform (not using harmonics). Optional FM using a supplied LFO."""
        wave = self.__triangle(frequency, amplitude, phase, bias, fm_lfo)
        return self.__render_sample(duration, wave)

    def triangle_gen(self, frequency, amplitude=0.9999, phase=0.0, bias=0.0, fm_lfo=None):
        """Generator for a perfect triangle waveform (not using harmonics). Optional FM using a supplied LFO."""
        wave = self.__triangle(frequency, amplitude, phase, bias, fm_lfo).generator()
        while True:
            yield int(next(wave))

    def sawtooth(self, frequency, duration, amplitude=0.75, phase=0.0, bias=0.0, fm_lfo=None):
        """Perfect sawtooth waveform (not using harmonics)."""
        wave = self.__sawtooth(frequency, amplitude, phase, bias, fm_lfo)
        return self.__render_sample(duration, wave)

    def sawtooth_gen(self, frequency, amplitude=0.75, phase=0.0, bias=0.0, fm_lfo=None):
        """Generator for a perfect sawtooth waveform (not using harmonics)."""
        wave = self.__sawtooth(frequency, amplitude, phase, bias, fm_lfo).generator()
        while True:
            yield int(next(wave))

    def sawtooth_h(self, frequency, duration, num_harmonics=16, amplitude=0.5, phase=0.0, bias=0.0, fm_lfo=None):
        """Sawtooth waveform based on harmonic sine waves"""
        wave = self.__sawtooth_h(frequency, num_harmonics, amplitude, phase, bias, fm_lfo)
        return self.__render_sample(duration, wave)

    def sawtooth_h_gen(self, frequency, num_harmonics=16, amplitude=0.5, phase=0.0, bias=0.0, fm_lfo=None):
        """Generator for a Sawtooth waveform based on harmonic sine waves"""
        wave = self.__sawtooth_h(frequency, num_harmonics, amplitude, phase, bias, fm_lfo).generator()
        while True:
            yield int(next(wave))

    def pulse(self, frequency, duration, amplitude=0.75, phase=0.0, bias=0.0, pulsewidth=0.1, fm_lfo=None, pwm_lfo=None):
        """
        Perfect pulse waveform (not using harmonics).
        Optional FM and/or Pulse-width modulation. If you use PWM, pulsewidth is ignored.
        The pwm_lfo oscillator should yield values between 0 and 1 (=the pulse width factor), or it will be clipped.
        """
        wave = self.__pulse(frequency, amplitude, phase, bias, pulsewidth, fm_lfo, pwm_lfo)
        return self.__render_sample(duration, wave)

    def pulse_gen(self, frequency, amplitude=0.75, phase=0.0, bias=0.0, pulsewidth=0.1, fm_lfo=None, pwm_lfo=None):
        """
        Generator for perfect pulse waveform (not using harmonics).
        Optional FM and/or Pulse-width modulation. If you use PWM, pulsewidth is ignored.
        The pwm_lfo oscillator should yield values between 0 and 1 (=the pulse width factor), or it will be clipped.
        """
        wave = self.__pulse(frequency, amplitude, phase, bias, pulsewidth, fm_lfo, pwm_lfo).generator()
        while True:
            yield int(next(wave))

    def harmonics(self, frequency, duration, harmonics, amplitude=0.5, phase=0.0, bias=0.0, fm_lfo=None):
        """Makes a waveform based on harmonics. This is slow because many sine waves are added together."""
        wave = self.__harmonics(frequency, harmonics, amplitude, phase, bias, fm_lfo)
        return self.__render_sample(duration, wave)

    def harmonics_gen(self, frequency, harmonics, amplitude=0.5, phase=0.0, bias=0.0, fm_lfo=None):
        """Generator for a waveform based on harmonics. This is slow because many sine waves are added together."""
        wave = self.__harmonics(frequency, harmonics, amplitude, phase, bias, fm_lfo).generator()
        while True:
            yield int(next(wave))

    def white_noise(self, frequency, duration, amplitude=0.9999, bias=0.0):
        """White noise (randomness) waveform."""
        wave = self.__white_noise(frequency, amplitude, bias)
        return self.__render_sample(duration, wave)

    def white_noise_gen(self, frequency, amplitude=0.9999, bias=0.0):
        """Generator for White noise (randomness) waveform."""
        wave = self.__white_noise(frequency, amplitude, bias).generator()
        while True:
            yield int(next(wave))

    def linear(self, duration, start_amp, finish_amp):
        """A linear constant or sloped waveform."""
        wave = self.__linear(duration, start_amp, finish_amp)
        return self.__render_sample(duration, wave)

    def linear_gen(self, duration, startamp, finishamp):
        """Generator for linear constant or sloped waveform (it ends when it reaches the specified duration)"""
        wave = self.__linear(duration, startamp, finishamp).generator()
        for _ in range(int(duration*self.samplerate)):
            yield int(next(wave))

    def __sine(self, frequency, amplitude, phase, bias, fm_lfo):
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        if fm_lfo:
            return Sine(frequency, amplitude*scale, phase, bias*scale, fm_lfo=fm_lfo, samplerate=self.samplerate)
        else:
            return FastSine(frequency, amplitude*scale, phase, bias*scale, samplerate=self.samplerate)

    def __square(self, frequency, amplitude, phase, bias, fm_lfo):
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        if fm_lfo:
            return Square(frequency, amplitude*scale, phase, bias*scale, fm_lfo=fm_lfo, samplerate=self.samplerate)
        else:
            return FastSquare(frequency, amplitude*scale, phase, bias*scale, samplerate=self.samplerate)

    def __square_h(self, frequency, num_harmonics, amplitude, phase, bias, fm_lfo):
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        return SquareH(frequency, num_harmonics, amplitude*scale, phase, bias*scale, fm_lfo=fm_lfo, samplerate=self.samplerate)

    def __triangle(self, frequency, amplitude, phase, bias, fm_lfo):
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        if fm_lfo:
            return Triangle(frequency, amplitude*scale, phase, bias*scale, fm_lfo=fm_lfo, samplerate=self.samplerate)
        else:
            return FastTriangle(frequency, amplitude*scale, phase, bias*scale, samplerate=self.samplerate)

    def __sawtooth(self, frequency, amplitude, phase, bias, fm_lfo):
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        if fm_lfo:
            return Sawtooth(frequency, amplitude*scale, phase, bias*scale, fm_lfo=fm_lfo, samplerate=self.samplerate)
        else:
            return FastSawtooth(frequency, amplitude*scale, phase, bias*scale, samplerate=self.samplerate)

    def __sawtooth_h(self, frequency, num_harmonics, amplitude, phase, bias, fm_lfo):
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        return SawtoothH(frequency, num_harmonics, amplitude*scale, phase, bias*scale, fm_lfo=fm_lfo, samplerate=self.samplerate)

    def __pulse(self, frequency, amplitude, phase, bias, pulsewidth, fm_lfo, pwm_lfo):
        assert 0 <= pulsewidth <= 1
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        if fm_lfo:
            return Pulse(frequency, amplitude*scale, phase, bias*scale, pulsewidth, fm_lfo=fm_lfo, pwm_lfo=pwm_lfo, samplerate=self.samplerate)
        else:
            return FastPulse(frequency, amplitude*scale, phase, bias*scale, pulsewidth, pwm_lfo=pwm_lfo, samplerate=self.samplerate)

    def __harmonics(self, frequency, harmonics, amplitude, phase, bias, fm_lfo):
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        return Harmonics(frequency, harmonics, amplitude*scale, phase, bias*scale, fm_lfo=fm_lfo, samplerate=self.samplerate)

    def __white_noise(self, frequency, amplitude, bias):
        scale = self.__check_and_get_scale(frequency, amplitude, bias)
        return WhiteNoise(frequency, amplitude*scale, bias*scale, samplerate=self.samplerate)

    def __linear(self, duration, start_amp, finish_amp):
        num_samples = int(duration*self.samplerate)
        increment = (finish_amp - start_amp) / (num_samples - 1)
        return Linear(start_amp, increment, samplerate=self.samplerate)

    def __check_and_get_scale(self, freq, amplitude, bias):
        assert freq <= self.samplerate/2    # don't exceed the Nyquist frequency
        assert 0 <= amplitude <= 1.0
        assert -1 <= bias <= 1.0
        scale = 2 ** (self.samplewidth * 8 - 1) - 1
        return scale

    def __render_sample(self, duration, wave):
        wave = iter(wave)
        samples = Sample.get_array(self.samplewidth, [int(next(wave)) for _ in range(int(duration*self.samplerate))])
        return Sample.from_array(samples, self.samplerate, 1)


class Oscillator:
    """
    Oscillator base class for several types of waveforms.
    You can also apply FM to an osc, and/or an ADSR envelope.
    These are generic oscillators and as such have floating-point inputs and result values
    with variable amplitude (though usually -1.0...1.0), depending on what parameters you use.
    Using a FM LFO is computationally quite heavy, so if you know you don't use FM,
    consider using the Fast versions instead. They contain optimized algorithms but
    some of their parameters cannot be changed.
    """
    def __init__(self, source=None, samplerate=None):
        self._samplerate = samplerate or source._samplerate
        self._source = source

    def __iter__(self):
        return self.generator()

    def generator(self):
        yield from self._source


class EnvelopeFilter(Oscillator):
    """
    Applies an ADSR volume envelope to the source.
    A,D,S,R are in seconds, sustain_level is an amplitude factor.
    """
    def __init__(self, source, attack, decay, sustain, sustain_level, release, stop_at_end=False, cycle=False):
        assert attack >= 0 and decay >= 0 and sustain >= 0 and release >= 0
        assert 0 <= sustain_level <= 1
        super().__init__(source)
        self._attack = attack
        self._decay = decay
        self._sustain = sustain
        self._sustain_level = sustain_level
        self._release = release
        self._stop_at_end = stop_at_end
        self._cycle = cycle

    def generator(self):
        oscillator = iter(self._source)
        while True:
            time = 0.0
            end_time_decay = self._attack + self._decay
            end_time_sustain = end_time_decay + self._sustain
            end_time_release = end_time_sustain + self._release
            increment = 1/self._samplerate
            if self._attack:
                amp_change = 1.0/self._attack*increment
                amp = 0.0
                while time < self._attack:
                    yield next(oscillator)*amp
                    amp += amp_change
                    time += increment
            if self._decay:
                amp = 1.0
                amp_change = (self._sustain_level-1.0)/self._decay*increment
                while time < end_time_decay:
                    yield next(oscillator)*amp
                    amp += amp_change
                    time += increment
            while time < end_time_sustain:
                yield next(oscillator)*self._sustain_level
                time += increment
            if self._release:
                amp = self._sustain_level
                amp_change = (-self._sustain_level)/self._release*increment
                while time < end_time_release:
                    yield next(oscillator)*amp
                    amp += amp_change
                    time += increment
                if amp > 0.0:
                    yield next(oscillator)*amp
            if not self._cycle:
                break
        if not self._stop_at_end:
            while True:
                yield 0.0


class MixingFilter(Oscillator):
    """Mixes (adds) the wave from various sources together into one output wave."""
    def __init__(self, *sources):
        super().__init__(sources[0])
        self._sources = sources

    def generator(self):
        sources = [iter(src) for src in self._sources]
        while True:
            yield sum([next(src) for src in sources])


class AmpMudulationFilter(Oscillator):
    """Modulate the amplitude of the wave of the oscillator by another oscillator (the modulator)."""
    def __init__(self, source, modulator):
        super().__init__(source)
        self.modulator = modulator

    def generator(self):
        for v in self._source:
            yield v*next(self.modulator)


class DelayFilter(Oscillator):
    """
    Delays the source, or skips ahead in time (when using a negative delay value).
    Note that if you want to precisely phase-shift an oscillator, you should
    use the phase parameter on the oscillator function itself instead.
    """
    def __init__(self, source, seconds):
        super().__init__(source)
        self._seconds = seconds

    def generator(self):
        src = iter(self._source)
        if self._seconds < 0.0:
            for _ in range(int(-self._samplerate*self._seconds)):
                next(src)
        else:
            for _ in range(int(self._samplerate*self._seconds)):
                yield 0.0
        yield from src


class EchoFilter(Oscillator):
    """
    Mix given number of echos of the oscillator into itself.
    The decay is the factor with which each echo is decayed in volume (can be >1 to increase in volume instead).
    If you use a very short delay the echos blend into the sound and the effect is more like a reverb.
    """
    def __init__(self, source, after, amount, delay, decay):
        super().__init__(source)
        if decay < 1:
            # avoid computing echos that have virtually zero amplitude:
            amount = int(min(amount, math.log(0.000001, decay)))
        self._after = after
        self._amount = amount
        self._delay = delay
        self._decay = decay
        self.echo_duration = self._after + self._amount*self._delay

    def generator(self):
        oscillator = iter(self._source)
        # first play the first part till the echos start
        for _ in range(int(self._samplerate*self._after)):
            yield next(oscillator)
        # now start mixing the echos
        amp = self._decay
        echo_oscs = [Oscillator(src, samplerate=self._samplerate) for src in itertools.tee(oscillator, self._amount+1)]
        echos = [echo_oscs[0]]
        echo_delay = self._delay
        for echo in echo_oscs[1:]:
            echo = DelayFilter(echo, echo_delay)
            echo = AmpMudulationFilter(echo, itertools.repeat(amp))
            # @todo sometimes mixing the echos causes pops and clicks. Perhaps solvable by using a (very fast) fadein on the echo osc?
            echos.append(echo)
            echo_delay += self._delay
            amp *= self._decay
        echos = [iter(echo) for echo in echos]
        while True:
            yield sum([next(echo) for echo in echos])


class ClipFilter(Oscillator):
    """Clips the values from a source at the given mininum and/or maximum value."""
    def __init__(self, source, minimum=sys.float_info.min, maximum=sys.float_info.max):
        super().__init__(source)
        self.min = minimum
        self.max = maximum

    def generator(self):
        for v in self._source:
            yield max(min(v, self.max), self.min)


class AbsFilter(Oscillator):
    """Returns the absolute value of the source values."""
    def __init__(self, source):
        super().__init__(source)

    def generator(self):
        fabs = math.fabs  # optimization
        for v in self._source:
            yield fabs(v)


class NullFilter(Oscillator):
    """Wraps an oscillator but does nothing."""
    def __init__(self, source):
        super().__init__(source)

    def generator(self):
        yield from self._source


class Sine(Oscillator):
    """Sine Wave oscillator."""
    def __init__(self, frequency, amplitude=1.0, phase=0.0, bias=0.0, fm_lfo=None, samplerate=Sample.norm_samplerate):
        # The FM compensates for the phase change by means of phase_correction.
        # See http://stackoverflow.com/questions/3089832/sine-wave-glissando-from-one-pitch-to-another-in-numpy
        # and http://stackoverflow.com/questions/28185219/generating-vibrato-sine-wave
        # The same idea is applied to the other waveforms to correct their phase with FM.
        super().__init__(samplerate=samplerate)
        self.frequency = frequency
        self.amplitude = amplitude
        self.bias = bias
        self.fm = iter(fm_lfo or itertools.repeat(0.0))
        self._phase = phase

    def generator(self):
        phase_correction = self._phase*2*math.pi
        freq_previous = self.frequency
        increment = 2.0*math.pi/self._samplerate
        t = 0.0
        sin = math.sin  # optimization
        while True:
            freq = self.frequency*(1.0+next(self.fm))
            phase_correction += (freq_previous-freq)*t
            freq_previous = freq
            yield sin(t*freq+phase_correction)*self.amplitude+self.bias
            t += increment


class Triangle(Oscillator):
    """Perfect triangle wave oscillator (not using harmonics)."""
    def __init__(self, frequency, amplitude=1.0, phase=0.0, bias=0.0, fm_lfo=None, samplerate=Sample.norm_samplerate):
        super().__init__(samplerate=samplerate)
        self.frequency = frequency
        self.amplitude = amplitude
        self.bias = bias
        self.fm = iter(fm_lfo or itertools.repeat(0.0))
        self._phase = phase

    def generator(self):
        phase_correction = self._phase
        freq_previous = self.frequency
        increment = 1.0/self._samplerate
        t = 0.0
        fabs = math.fabs  # optimization
        while True:
            freq = self.frequency * (1.0+next(self.fm))
            phase_correction += (freq_previous-freq)*t
            freq_previous = freq
            tt = t*freq+phase_correction
            yield 4.0*self.amplitude*(fabs((tt+0.75) % 1.0 - 0.5)-0.25)+self.bias
            t += increment


class Square(Oscillator):
    """Perfect square wave [max/-max] oscillator (not using harmonics)."""
    def __init__(self, frequency, amplitude=1.0, phase=0.0, bias=0.0, fm_lfo=None, samplerate=Sample.norm_samplerate):
        super().__init__(samplerate=samplerate)
        self.frequency = frequency
        self.amplitude = amplitude
        self.bias = bias
        self.fm = iter(fm_lfo or itertools.repeat(0.0))
        self._phase = phase

    def generator(self):
        phase_correction = self._phase
        freq_previous = self.frequency
        increment = 1.0/self._samplerate
        t = 0.0
        while True:
            freq = self.frequency*(1.0+next(self.fm))
            phase_correction += (freq_previous-freq)*t
            freq_previous = freq
            tt = t*freq + phase_correction
            yield (-self.amplitude if int(tt*2) % 2 else self.amplitude)+self.bias
            t += increment


class Sawtooth(Oscillator):
    """Perfect sawtooth waveform oscillator (not using harmonics)."""
    def __init__(self, frequency, amplitude=1.0, phase=0.0, bias=0.0, fm_lfo=None, samplerate=Sample.norm_samplerate):
        super().__init__(samplerate=samplerate)
        self.frequency = frequency
        self.amplitude = amplitude
        self.bias = bias
        self.fm = iter(fm_lfo or itertools.repeat(0.0))
        self._phase = phase

    def generator(self):
        increment = 1.0/self._samplerate
        freq_previous = self.frequency
        phase_correction = self._phase
        t = 0.0
        floor = math.floor   # optimization
        while True:
            freq = self.frequency*(1.0+next(self.fm))
            phase_correction += (freq_previous-freq)*t
            freq_previous = freq
            tt = t*freq + phase_correction
            yield self.bias+self.amplitude*2.0*(tt - floor(0.5+tt))
            t += increment


class Pulse(Oscillator):
    """
    Oscillator for a perfect pulse waveform (not using harmonics).
    Optional FM and/or Pulse-width modulation. If you use PWM, pulsewidth is ignored.
    The pwm_lfo oscillator will be clipped between 0 and 1 as pulse width factor.
    """
    def __init__(self, frequency, amplitude=1.0, phase=0.0, bias=0.0, pulsewidth=0.1, fm_lfo=None, pwm_lfo=None, samplerate=Sample.norm_samplerate):
        assert 0 <= pulsewidth <= 1
        super().__init__(samplerate=samplerate)
        self.frequency = frequency
        self.amplitude = amplitude
        self.bias = bias
        self.pulsewidth = pulsewidth
        self.fm = iter(fm_lfo or itertools.repeat(0.0))
        self.pwm = iter(pwm_lfo or itertools.repeat(pulsewidth))
        self._phase = phase

    def generator(self):
        epsilon = sys.float_info.epsilon
        increment = 1.0/self._samplerate
        freq_previous = self.frequency
        phase_correction = self._phase
        t = 0.0
        while True:
            pw = next(self.pwm)
            if pw <= 0.0:
                pw = epsilon
            elif pw >= 1.0:
                pw = 1.0-epsilon
            freq = self.frequency*(1.0+next(self.fm))
            phase_correction += (freq_previous-freq)*t
            freq_previous = freq
            tt = t*freq+phase_correction
            yield (self.amplitude if tt % 1.0 < pw else -self.amplitude)+self.bias
            t += increment


class Harmonics(Oscillator):
    """
    Oscillator that produces a waveform based on harmonics.
    This is computationally intensive because many sine waves are added together.
    """
    def __init__(self, frequency, harmonics, amplitude=1.0, phase=0.0, bias=0.0, fm_lfo=None, samplerate=Sample.norm_samplerate):
        super().__init__(samplerate=samplerate)
        self.frequency = frequency
        self.amplitude = amplitude
        self.bias = bias
        self.fm = iter(fm_lfo or itertools.repeat(0.0))
        self._phase = phase
        self.harmonics = harmonics

    def generator(self):
        increment = 2.0*math.pi/self._samplerate
        phase_correction = self._phase*2.0*math.pi
        freq_previous = self.frequency
        t = 0.0
        # only keep harmonics below the Nyquist frequency
        harmonics = list(filter(lambda h: h[0]*self.frequency <= self._samplerate/2, self.harmonics))
        sin = math.sin  # optimization
        while True:
            h = 0.0
            freq = self.frequency*(1.0+next(self.fm))
            phase_correction += (freq_previous-freq)*t
            freq_previous = freq
            q = t*freq + phase_correction
            for k, amp in harmonics:
                h += sin(q*k)*amp
            yield h*self.amplitude+self.bias
            t += increment


class SquareH(Harmonics):
    """
    Oscillator that produces a square wave based on harmonic sine waves.
    It is a lot heavier to generate than square because it has to add many individual sine waves.
    It's done by adding only odd-integer harmonics, see https://en.wikipedia.org/wiki/Square_wave
    """
    def __init__(self, frequency, num_harmonics=16, amplitude=0.9999, phase=0.0, bias=0.0, fm_lfo=None, samplerate=Sample.norm_samplerate):
        harmonics = [(n, 1.0/n) for n in range(1, num_harmonics*2, 2)]  # only the odd harmonics
        super().__init__(frequency, harmonics, amplitude, phase, bias, fm_lfo=fm_lfo, samplerate=samplerate)


class SawtoothH(Harmonics):
    """
    Oscillator that produces a sawtooth wave based on harmonic sine waves.
    It is a lot heavier to generate than square because it has to add many individual sine waves.
    It's done by adding all harmonics, see https://en.wikipedia.org/wiki/Sawtooth_wave
    """
    def __init__(self, frequency, num_harmonics=16, amplitude=0.9999, phase=0.0, bias=0.0, fm_lfo=None, samplerate=Sample.norm_samplerate):
        harmonics = [(n, 1.0/n) for n in range(1, num_harmonics+1)]  # all harmonics
        super().__init__(frequency, harmonics, amplitude, phase+0.5, bias, fm_lfo=fm_lfo, samplerate=samplerate)

    def generator(self):
        for y in super().generator():
            yield self.bias*2.0-y


class WhiteNoise(Oscillator):
    """Oscillator that produces white noise (randomness) waveform."""
    def __init__(self, frequency, amplitude=1.0, bias=0.0, samplerate=Sample.norm_samplerate):
        super().__init__(samplerate=samplerate)
        self.amplitude = amplitude
        self.bias = bias
        self.frequency = frequency
        self.frequency = frequency

    def generator(self):
        cycles = int(self._samplerate / self.frequency)
        while True:
            value = random.uniform(-self.amplitude, self.amplitude) + self.bias
            yield from [value] * cycles


class Linear(Oscillator):
    """Oscillator that produces a linear sloped value, until it reaches a maximum or minimum value."""
    def __init__(self, startlevel, increment=0.0, min_value=-1.0, max_value=1.0, samplerate=Sample.norm_samplerate):
        super().__init__(samplerate=samplerate)
        self.value = startlevel
        self.increment = increment
        self.min_value = min_value
        self.max_value = max_value

    def generator(self):
        while True:
            yield self.value
            if self.increment:
                self.value = min(self.max_value, max(self.min_value, self.value+self.increment))


class FastSine(Oscillator):
    """Fast sine wave oscillator. Some parameters cannot be changed."""
    def __init__(self, frequency, amplitude=1.0, phase=0.0, bias=0.0, samplerate=Sample.norm_samplerate):
        super().__init__(samplerate=samplerate)
        self._frequency = frequency
        self._phase = phase
        self.amplitude = amplitude
        self.bias = bias

    def generator(self):
        rate = self._samplerate/self._frequency
        increment = 2.0*math.pi/rate
        t = self._phase*2.0*math.pi
        sin = math.sin  # optimization
        while True:
            yield sin(t)*self.amplitude+self.bias
            t += increment


class FastTriangle(Oscillator):
    """Fast perfect triangle wave oscillator (not using harmonics). Some parameters cannot be changed."""
    def __init__(self, frequency, amplitude=1.0, phase=0.0, bias=0.0, samplerate=Sample.norm_samplerate):
        super().__init__(samplerate=samplerate)
        self._frequency = frequency
        self._phase = phase
        self.amplitude = amplitude
        self.bias = bias

    def generator(self):
        freq = self._frequency
        t = self._phase/freq
        increment = 1.0/self._samplerate
        fabs = math.fabs  # optimization
        while True:
            yield 4.0*self.amplitude*(fabs((t*freq+0.75) % 1.0 - 0.5)-0.25)+self.bias
            t += increment


class FastSquare(Oscillator):
    """Fast perfect square wave [max/-max] oscillator (not using harmonics). Some parameters cannot be changed."""
    def __init__(self, frequency, amplitude=1.0, phase=0.0, bias=0.0, samplerate=Sample.norm_samplerate):
        super().__init__(samplerate=samplerate)
        self._frequency = frequency
        self._phase = phase
        self.amplitude = amplitude
        self.bias = bias

    def generator(self):
        freq = self._frequency
        t = self._phase/freq
        increment = 1.0/self._samplerate
        while True:
            yield (-self.amplitude if int(t*freq*2) % 2 else self.amplitude)+self.bias
            t += increment


class FastSawtooth(Oscillator):
    """Fast perfect sawtooth waveform oscillator (not using harmonics). Some parameters canot be changed."""
    def __init__(self, frequency, amplitude=1.0, phase=0.0, bias=0.0, samplerate=Sample.norm_samplerate):
        super().__init__(samplerate=samplerate)
        self._frequency = frequency
        self._phase = phase
        self.amplitude = amplitude
        self.bias = bias

    def generator(self):
        freq = self._frequency
        t = self._phase/freq
        increment = 1.0/self._samplerate
        floor = math.floor  # optimization
        while True:
            tt = t*freq
            yield self.bias+2.0*self.amplitude*(tt - floor(0.5+tt))
            t += increment


class FastPulse(Oscillator):
    """
    Fast oscillator that produces a perfect pulse waveform (not using harmonics).
    Some parameters cannot be changed.
    Optional Pulse-width modulation. If used, the pulsewidth argument is ignored.
    The pwm_lfo oscillator will be clipped between 0 and 1 as pulse width factor.
    """
    def __init__(self, frequency, amplitude=1.0, phase=0.0, bias=0.0, pulsewidth=0.1, pwm_lfo=None, samplerate=Sample.norm_samplerate):
        assert 0 <= pulsewidth <= 1
        super().__init__(samplerate=samplerate)
        self._frequency = frequency
        self._phase = phase
        self._pulsewidth = pulsewidth
        self._pwm = pwm_lfo
        self.amplitude = amplitude
        self.bias = bias

    def generator(self):
        if self._pwm:
            # optimized loop without FM, but with PWM
            epsilon = sys.float_info.epsilon
            freq = self._frequency
            pwm = iter(self._pwm)
            t = self._phase/freq
            increment = 1.0/self._samplerate
            while True:
                pw = next(pwm)
                if pw <= 0.0:
                    pw = epsilon
                elif pw >= 1.0:
                    pw = 1.0-epsilon
                yield (self.amplitude if t*freq % 1.0 < pw else -self.amplitude)+self.bias
                t += increment
        else:
            # no FM, no PWM
            freq = self._frequency
            pw = self._pulsewidth
            t = self._phase/freq
            increment = 1.0/self._samplerate
            while True:
                yield (self.amplitude if t*freq % 1.0 < pw else -self.amplitude)+self.bias
                t += increment


if __name__ == "__main__":
    # check the wavesynth and generators
    ws = WaveSynth(samplerate=1000)
    s = ws.sine(440, 1)
    sgen = ws.sine_gen(440)
    s2 = [next(sgen) for _ in range(1000)]
    assert list(s.get_frame_array()) == s2
    s = ws.square(440, 1)
    sgen = ws.square_gen(440)
    s2 = [next(sgen) for _ in range(1000)]
    assert list(s.get_frame_array()) == s2
    s = ws.square_h(440, 1)
    sgen = ws.square_h_gen(440)
    s2 = [next(sgen) for _ in range(1000)]
    assert list(s.get_frame_array()) == s2
    s = ws.triangle(440, 1)
    sgen = ws.triangle_gen(440)
    s2 = [next(sgen) for _ in range(1000)]
    assert list(s.get_frame_array()) == s2
    s = ws.sawtooth(440, 1)
    sgen = ws.sawtooth_gen(440)
    s2 = [next(sgen) for _ in range(1000)]
    assert list(s.get_frame_array()) == s2
    s = ws.sawtooth_h(440, 1)
    sgen = ws.sawtooth_h_gen(440)
    s2 = [next(sgen) for _ in range(1000)]
    assert list(s.get_frame_array()) == s2
    s = ws.pulse(440, 1)
    sgen = ws.pulse_gen(440)
    s2 = [next(sgen) for _ in range(1000)]
    assert list(s.get_frame_array()) == s2
    s = ws.harmonics(440, 1, [(n, 1/n) for n in range(1, 8)])
    sgen = ws.harmonics_gen(440, [(n, 1/n) for n in range(1, 8)])
    s2 = [next(sgen) for _ in range(1000)]
    assert list(s.get_frame_array()) == s2
    s = ws.linear(1, 0.1, 0.9)
    sgen = ws.linear_gen(1, 0.1, 0.9)
    s2 = [next(sgen) for _ in range(1000)]
    assert list(s.get_frame_array()) == s2
    s = ws.white_noise(440, 1)
    sgen = ws.white_noise_gen(440)
    s2 = [next(sgen) for _ in range(1000)]
    assert len(s) == len(s2) == 1000
