"""
=============================================================================
audio.py - Procedural Sound Synthesizer & MIDI Music Generator
=============================================================================
Educational Note:
Audio Programming in Python:
Many indie and retro games face challenges with audio assets: external .wav
or .mp3 files can be missing, corrupt, or subject to copyright restrictions.

This module demonstrates two powerful techniques:
  1. PROCEDURAL SOUND SYNTHESIS:
     Every sound effect (bumper ping, flipper solenoid snap, slingshot rubber
     recoil, plunger spring release) is generated purely from mathematical
     waveforms (sine, square, triangle, and noise) directly into memory at
     runtime using Python's standard `math` and `array` modules. No external
     WAV files are needed!

  2. PURE-PYTHON MIDI FILE COMPILATION:
     Standard MIDI Files (.mid) are compact binary instruction sets that tell
     a synthesizer which notes to play, on which instrument, at what tempo.
     Using Python's standard `struct` module, we compile a 16-bar retro
     arcade soundtrack into a valid binary SMF file and play it via
     `pygame.mixer.music`.

If the host system has no audio hardware connected, this module provides
safe fallback dummy objects so the game never crashes.
=============================================================================
"""

import os
import math
import array
import struct
import random
from pathlib import Path
import pygame

from constants import MIDI_MUSIC_FILE


# -----------------------------------------------------------------------------
# Pure-Python Standard MIDI File (SMF) Generator
# -----------------------------------------------------------------------------

def encode_variable_length_quantity(value: int) -> bytes:
    """
    Encodes an integer into MIDI's variable-length quantity (VLQ) format.
    
    Educational Note - Binary VLQ Encoding:
    In standard binary, an integer occupies a fixed number of bytes (e.g. 4 bytes).
    In MIDI, delta times between notes can be 0 or small numbers. To save space,
    MIDI encodes numbers 7 bits at a time. The 8th (most significant) bit is set
    to 1 on all bytes except the final byte, which signals the end of the number:
        0 -> 0x00
        127 -> 0x7F
        128 -> 0x81 0x00
        480 -> 0x83 0x60
    """
    buffer = bytearray([value & 0x7F])
    value >>= 7
    while value > 0:
        buffer.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(buffer)


def generate_retro_midi_track(output_path: Path):
    """
    Composes an authentic, high-energy 16-bar retro arcade pinball soundtrack
    and saves it to disk as a Standard MIDI File (SMF Type 0).
    
    Educational Note - Musical Structure of the Track:
    - Channel 0: Lead Synthesizer (General MIDI Program 80: Lead 1 - Square Wave)
    - Channel 1: Punchy Synth Bass (General MIDI Program 38: Synth Bass 1)
    - Channel 9: Standard MIDI Percussion (36: Kick, 38: Snare, 42: Closed Hat)
    """
    ticks_per_beat = 480
    events: list[tuple[int, bytes]] = []

    # 1. Set Tempo: 144 BPM (Arcade pace)
    # Microseconds per beat = 60,000,000 / 144 = 416,666 microseconds
    tempo_us = 416666
    events.append((0, b'\xFF\x51\x03' + struct.pack('>I', tempo_us)[1:]))

    # 2. Select General MIDI Instruments (Program Change)
    events.append((0, bytes([0xC0, 80])))  # Channel 0: Square Lead Synth
    events.append((0, bytes([0xC1, 38])))  # Channel 1: Synth Bass 1

    # 3. Musical Composition: 16 Measures in A Minor / Dorian Retro Scale
    # Step duration = 16th note (ticks_per_beat / 4 = 120 ticks)
    step_ticks = ticks_per_beat // 4

    # Bassline pattern (A minor groove)
    bass_notes = [
        # Measure 1-4: Driving A minor
        45, 45, 57, 45,  48, 45, 55, 57,  45, 45, 57, 45,  50, 48, 47, 45,
        # Measure 5-8: F to G transition
        41, 41, 53, 41,  43, 43, 55, 43,  45, 45, 57, 45,  48, 47, 45, 43,
        # Measure 9-12: Melodic climb
        45, 45, 57, 45,  48, 50, 52, 55,  41, 41, 53, 41,  43, 43, 55, 43,
        # Measure 13-16: High-voltage turnaround
        45, 48, 52, 57,  55, 52, 48, 45,  43, 47, 50, 55,  40, 43, 47, 52
    ]

    # Lead melody pattern
    lead_notes = [
        # Bars 1-4
        69, 0, 72, 76,  79, 0, 76, 0,    74, 0, 72, 0,    69, 71, 72, 74,
        76, 0, 79, 81,  84, 0, 81, 0,    79, 0, 76, 0,    74, 76, 74, 72,
        # Bars 5-8
        77, 0, 76, 74,  72, 0, 74, 0,    76, 0, 79, 0,    81, 0, 84, 0,
        86, 0, 84, 81,  79, 0, 76, 0,    74, 0, 72, 71,   69, 0, 0,  0,
        # Bars 9-12 (Arpeggiated fast sequence)
        69, 72, 76, 81, 76, 72, 69, 72,  71, 74, 77, 83,  77, 74, 71, 74,
        72, 76, 79, 84, 79, 76, 72, 76,  74, 77, 81, 86,  81, 77, 74, 77,
        # Bars 13-16 (Climax resolution)
        81, 0, 84, 0,   86, 0, 88, 0,    84, 0, 81, 0,    79, 76, 74, 72,
        71, 0, 74, 0,   76, 0, 79, 0,    69, 0, 0, 0,     0, 0, 0, 0
    ]

    total_steps = len(bass_notes)  # 64 steps = 16 bars

    for step in range(total_steps):
        current_tick = step * step_ticks

        # --- Lead Note ---
        l_note = lead_notes[step % len(lead_notes)]
        if l_note > 0:
            events.append((current_tick, bytes([0x90, l_note, 88])))
            events.append((current_tick + step_ticks - 15, bytes([0x80, l_note, 0])))

        # --- Bass Note ---
        b_note = bass_notes[step % len(bass_notes)]
        if b_note > 0:
            events.append((current_tick, bytes([0x91, b_note, 98])))
            events.append((current_tick + step_ticks - 20, bytes([0x81, b_note, 0])))

        # --- Arcade Drums (Channel 9 / MIDI 10) ---
        # Closed Hi-Hat on every 16th note (note 42)
        events.append((current_tick, bytes([0x99, 42, 60])))
        events.append((current_tick + 40, bytes([0x89, 42, 0])))

        # Bass Kick Drum on beats 1 and 3 (step % 4 == 0) (note 36)
        if step % 4 == 0:
            events.append((current_tick, bytes([0x99, 36, 100])))
            events.append((current_tick + 100, bytes([0x89, 36, 0])))

        # Snare Drum on beats 2 and 4 (step % 4 == 2) (note 38)
        if step % 4 == 2:
            events.append((current_tick, bytes([0x99, 38, 92])))
            events.append((current_tick + 100, bytes([0x89, 38, 0])))

    # Sort all events chronologically by tick timestamp
    events.sort(key=lambda item: item[0])

    # Convert sorted absolute ticks into relative Delta Times
    track_data = bytearray()
    last_tick = 0
    for tick, event_bytes in events:
        delta = tick - last_tick
        track_data.extend(encode_variable_length_quantity(delta))
        track_data.extend(event_bytes)
        last_tick = tick

    # End of Track Meta-Event
    track_data.extend(encode_variable_length_quantity(0))
    track_data.extend(b'\xFF\x2F\x00')

    # Construct Standard MIDI File Header (MThd chunk)
    # Format: 0 (single track), Tracks: 1, Division: 480
    header_chunk = b'MThd' + struct.pack('>IHHH', 6, 0, 1, ticks_per_beat)
    track_chunk = b'MTrk' + struct.pack('>I', len(track_data)) + bytes(track_data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(header_chunk + track_chunk)


# -----------------------------------------------------------------------------
# Procedural Audio Synthesizer (8-Bit / 16-Bit Sound Effects)
# -----------------------------------------------------------------------------

class DummySound:
    """Safe fallback that mimics pygame.mixer.Sound when audio hardware is unavailable."""
    def play(self, *args, **kwargs):
        pass
    def stop(self):
        pass
    def set_volume(self, volume):
        pass


class SoundManager:
    """
    Generates and plays all procedural retro sound effects and controls MIDI music.
    
    Educational Note - Mathematical Waveform Generation:
    Sound is pressure waves oscillating over time.
    At 44,100 samples per second, 1 second of audio contains 44,100 numbers:
      - Sine Wave: y = sin(2 * π * freq * t) -> Pure chime, bell, or flute
      - Square Wave: y = 1.0 if sin(...) >= 0 else -1.0 -> Classic 8-bit NES/Arcade
      - White Noise: random float [-1.0, 1.0] -> Mechanical snaps, snare hits, explosions
      - Frequency Modulation (Sweep): frequency changes over time (chirps and drops)
    """
    def __init__(self):
        self.audio_available = False
        self.sounds: dict[str, pygame.mixer.Sound | DummySound] = {}
        self.sample_rate = 44100
        self.music_playing = False
        self.music_muted = False
        self.sfx_muted = False

        try:
            if not pygame.mixer.get_init():
                # Initialize 16-bit signed stereo audio at 44.1 kHz
                pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=2, buffer=512)
            self.audio_available = True
        except Exception as e:
            print(f"[SoundManager] Audio initialization notice: {e}")
            self.audio_available = False

        if self.audio_available:
            self._synthesize_all_sound_effects()
            self._init_midi_music()

    def _create_sound_from_pcm(self, samples_left: list[float], samples_right: list[float] | None = None) -> pygame.mixer.Sound:
        """
        Converts floating-point audio samples [-1.0, 1.0] into a 16-bit signed
        stereo integer buffer and creates a playable pygame Sound object.
        """
        if samples_right is None:
            samples_right = samples_left

        interleaved = array.array('h')
        for l_val, r_val in zip(samples_left, samples_right):
            # Clamp and scale float [-1.0, 1.0] to signed 16-bit int [-32767, 32767]
            il = int(max(-1.0, min(1.0, l_val)) * 32767)
            ir = int(max(-1.0, min(1.0, r_val)) * 32767)
            interleaved.append(il)
            interleaved.append(ir)

        return pygame.mixer.Sound(buffer=interleaved)

    def _synthesize_all_sound_effects(self):
        """Synthesizes all authentic pinball arcade sound effects from scratch."""
        try:
            self.sounds["bumper"] = self._synth_bumper_chirp()
            self.sounds["slingshot"] = self._synth_slingshot_kick()
            self.sounds["flipper_up"] = self._synth_flipper_snap(True)
            self.sounds["flipper_down"] = self._synth_flipper_snap(False)
            self.sounds["plunger_pull"] = self._synth_plunger_pull()
            self.sounds["plunger_release"] = self._synth_plunger_release()
            self.sounds["target_hit"] = self._synth_target_chime()
            self.sounds["bank_cleared"] = self._synth_bank_fanfare()
            self.sounds["rollover"] = self._synth_rollover_bell()
            self.sounds["spinner"] = self._synth_spinner_click()
            self.sounds["drain"] = self._synth_drain_glissando()
            self.sounds["tilt"] = self._synth_tilt_buzzer()
            self.sounds["high_score"] = self._synth_high_score_jingle()
        except Exception as e:
            print(f"[SoundManager] Warning during sound synthesis: {e}")

    # --- Individual Sound Effect Synthesizers ---

    def _synth_bumper_chirp(self) -> pygame.mixer.Sound:
        """Crisp high-frequency dual-tone chime for pop bumpers."""
        duration = 0.12
        num_samples = int(self.sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            env = math.exp(-18.0 * t)  # Fast exponential decay
            # Arpeggiates upward from 880 Hz to 1320 Hz
            freq = 880.0 if t < 0.05 else 1320.0
            val = 0.6 * math.sin(2.0 * math.pi * freq * t) * env
            samples.append(val)
        return self._create_sound_from_pcm(samples)

    def _synth_slingshot_kick(self) -> pygame.mixer.Sound:
        """Punchy rubber band recoil with mechanical pop."""
        duration = 0.09
        num_samples = int(self.sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            env = math.exp(-25.0 * t)
            # Rapid downward pitch sweep (380 Hz down to 90 Hz)
            freq = max(90.0, 380.0 - (t / duration) * 290.0)
            tone = math.sin(2.0 * math.pi * freq * t)
            noise = (random.random() * 2.0 - 1.0) * 0.3 * env
            samples.append((0.7 * tone + noise) * env)
        return self._create_sound_from_pcm(samples)

    def _synth_flipper_snap(self, up: bool) -> pygame.mixer.Sound:
        """Mechanical solenoid click when flippers energize or release."""
        duration = 0.05 if up else 0.04
        num_samples = int(self.sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            env = math.exp(-55.0 * t)
            # Upward snap has higher punch frequency
            freq = 420.0 if up else 240.0
            square = 1.0 if math.sin(2.0 * math.pi * freq * t) > 0 else -1.0
            click = (random.random() * 2.0 - 1.0) * 0.4
            samples.append((0.4 * square + click) * env * 0.5)
        return self._create_sound_from_pcm(samples)

    def _synth_plunger_pull(self) -> pygame.mixer.Sound:
        """Subtle ratcheting click when pulling plunger back."""
        duration = 0.03
        num_samples = int(self.sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            env = math.exp(-70.0 * t)
            click = (random.random() * 2.0 - 1.0) * 0.5 * env
            samples.append(click)
        return self._create_sound_from_pcm(samples)

    def _synth_plunger_release(self) -> pygame.mixer.Sound:
        """Heavy spring snap when plunger fires the ball."""
        duration = 0.16
        num_samples = int(self.sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            env = math.exp(-15.0 * t)
            freq = max(60.0, 500.0 * math.exp(-22.0 * t))
            thump = math.sin(2.0 * math.pi * freq * t)
            snap = (random.random() * 2.0 - 1.0) * 0.35 * math.exp(-40.0 * t)
            samples.append((0.7 * thump + snap) * env)
        return self._create_sound_from_pcm(samples)

    def _synth_target_chime(self) -> pygame.mixer.Sound:
        """Crisp metallic ping for stand-up targets."""
        duration = 0.14
        num_samples = int(self.sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            env = math.exp(-14.0 * t)
            # High metallic bell harmonic (1600 Hz + 2400 Hz)
            val = 0.5 * math.sin(2.0 * math.pi * 1600.0 * t) + 0.3 * math.sin(2.0 * math.pi * 2400.0 * t)
            samples.append(val * env * 0.6)
        return self._create_sound_from_pcm(samples)

    def _synth_bank_fanfare(self) -> pygame.mixer.Sound:
        """Ascending 4-tone victory arpeggio when all targets are dropped."""
        notes = [523.25, 659.25, 783.99, 1046.50]  # C5, E5, G5, C6
        note_dur = 0.08
        total_dur = note_dur * len(notes)
        num_samples = int(self.sample_rate * total_dur)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            note_idx = min(len(notes) - 1, int(t / note_dur))
            local_t = t - (note_idx * note_dur)
            freq = notes[note_idx]
            env = math.exp(-10.0 * local_t)
            square = 1.0 if math.sin(2.0 * math.pi * freq * local_t) > 0 else -1.0
            sine = math.sin(2.0 * math.pi * freq * local_t)
            samples.append((0.4 * square + 0.4 * sine) * env * 0.7)
        return self._create_sound_from_pcm(samples)

    def _synth_rollover_bell(self) -> pygame.mixer.Sound:
        """High-pitched crystal bell when crossing top rollover lanes."""
        duration = 0.20
        num_samples = int(self.sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            env = math.exp(-9.0 * t)
            bell = math.sin(2.0 * math.pi * 2093.0 * t) * 0.6  # C7
            samples.append(bell * env)
        return self._create_sound_from_pcm(samples)

    def _synth_spinner_click(self) -> pygame.mixer.Sound:
        """Fast flutter/whir click when spinning gate rotates."""
        duration = 0.04
        num_samples = int(self.sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            env = math.exp(-40.0 * t)
            freq = 750.0
            tone = 1.0 if math.sin(2.0 * math.pi * freq * t) > 0 else -1.0
            samples.append(tone * env * 0.35)
        return self._create_sound_from_pcm(samples)

    def _synth_drain_glissando(self) -> pygame.mixer.Sound:
        """Melancholic descending slide when ball falls into the drain."""
        duration = 0.55
        num_samples = int(self.sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            progress = t / duration
            # Exponential pitch fall from 600 Hz down to 80 Hz
            freq = 600.0 * math.pow(0.12, progress)
            env = 1.0 - progress
            tone = 1.0 if math.sin(2.0 * math.pi * freq * t) > 0 else -1.0
            samples.append(tone * env * 0.4)
        return self._create_sound_from_pcm(samples)

    def _synth_tilt_buzzer(self) -> pygame.mixer.Sound:
        """Harsh industrial buzzer when table is nudged too violently."""
        duration = 0.35
        num_samples = int(self.sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            env = 0.8 if t < 0.3 else (0.35 - t) / 0.05
            # Low 110 Hz buzzy waveform with odd harmonics
            freq = 110.0
            saw = (2.0 * ((t * freq) % 1.0)) - 1.0
            samples.append(saw * max(0.0, env) * 0.6)
        return self._create_sound_from_pcm(samples)

    def _synth_high_score_jingle(self) -> pygame.mixer.Sound:
        """Grand celebratory 8-bit fanfare for top score achievement."""
        melody = [(523.25, 0.10), (659.25, 0.10), (783.99, 0.10), (1046.50, 0.25)]
        samples = []
        for freq, dur in melody:
            num = int(self.sample_rate * dur)
            for i in range(num):
                t = i / self.sample_rate
                env = math.exp(-5.0 * t)
                tone = 1.0 if math.sin(2.0 * math.pi * freq * t) > 0 else -1.0
                samples.append(tone * env * 0.5)
        return self._create_sound_from_pcm(samples)

    # --- Music & Playback API ---

    def _init_midi_music(self):
        """Generates the MIDI music file if missing and prepares mixer."""
        try:
            if not MIDI_MUSIC_FILE.exists():
                generate_retro_midi_track(MIDI_MUSIC_FILE)
            pygame.mixer.music.load(str(MIDI_MUSIC_FILE))
            pygame.mixer.music.set_volume(0.65)
        except Exception as e:
            print(f"[SoundManager] Notice loading MIDI music: {e}")

    def play_sound(self, name: str):
        """Plays a synthesized sound effect by name."""
        if self.sfx_muted or not self.audio_available:
            return
        sound = self.sounds.get(name)
        if sound:
            try:
                sound.play()
            except Exception:
                pass

    def start_music(self):
        """Starts looping the background retro MIDI music."""
        if not self.audio_available or self.music_muted:
            return
        try:
            if not pygame.mixer.music.get_busy():
                pygame.mixer.music.play(-1)  # -1 means loop indefinitely
                self.music_playing = True
        except Exception as e:
            print(f"[SoundManager] Could not play MIDI music: {e}")

    def stop_music(self):
        """Stops background MIDI music."""
        if self.audio_available:
            try:
                pygame.mixer.music.stop()
                self.music_playing = False
            except Exception:
                pass

    def toggle_music(self) -> bool:
        """Toggles music on or off. Returns current muted state."""
        self.music_muted = not self.music_muted
        if self.music_muted:
            self.stop_music()
        else:
            self.start_music()
        return not self.music_muted

    def toggle_sfx(self) -> bool:
        """Toggles sound effects on or off. Returns current enabled state."""
        self.sfx_muted = not self.sfx_muted
        return not self.sfx_muted
