"""
midi_utils.py - Utility funkce pro práci s MIDI notami
"""

from typing import List, Tuple
from config import AUDIO


class MidiUtils:
    """Utility funkce pro MIDI operace"""

    # Import konstant z centrální konfigurace
    PIANO_MIN_MIDI = AUDIO.MIDI.PIANO_MIN_MIDI
    PIANO_MAX_MIDI = AUDIO.MIDI.PIANO_MAX_MIDI
    NOTE_NAMES = AUDIO.MIDI.NOTE_NAMES

    @staticmethod
    def midi_to_note_name(midi_note: int) -> str:
        """Převede MIDI notu na jméno (např. 60 -> 'C4')"""
        if not (AUDIO.MIDI.MIN_MIDI <= midi_note <= AUDIO.MIDI.MAX_MIDI):
            raise ValueError(f"MIDI nota musí být mezi {AUDIO.MIDI.MIN_MIDI}-{AUDIO.MIDI.MAX_MIDI}, dostáno: {midi_note}")

        octave = (midi_note // 12) - 1
        note_name = MidiUtils.NOTE_NAMES[midi_note % 12]
        return f"{note_name}{octave}"

    @staticmethod
    def midi_to_frequency(midi_note: int) -> float:
        """Převede MIDI notu na frekvenci v Hz (A4 = 440 Hz)"""
        return AUDIO.MIDI.A4_FREQUENCY * (2 ** ((midi_note - AUDIO.MIDI.A4_MIDI) / 12))

    @staticmethod
    def frequency_to_midi(frequency: float) -> float:
        """Převede frekvenci na plovoucí MIDI hodnotu"""
        if frequency <= 0:
            raise ValueError("Frekvence musí být kladná")
        return 12 * (frequency / AUDIO.MIDI.A4_FREQUENCY).bit_length() + AUDIO.MIDI.A4_MIDI

    @staticmethod
    def is_piano_range(midi_note: int) -> bool:
        """Zkontroluje, zda je MIDI nota v piano rozsahu"""
        return MidiUtils.PIANO_MIN_MIDI <= midi_note <= MidiUtils.PIANO_MAX_MIDI

    @staticmethod
    def is_white_key(midi_note: int) -> bool:
        """Zkontroluje, zda je MIDI nota bílá klávesa"""
        return (midi_note % 12) in AUDIO.MIDI.WHITE_KEYS

    @staticmethod
    def is_black_key(midi_note: int) -> bool:
        """Zkontroluje, zda je MIDI nota černá klávesa"""
        return (midi_note % 12) in AUDIO.MIDI.BLACK_KEYS

    @staticmethod
    def get_piano_notes_range(start_midi: int = None, end_midi: int = None) -> List[int]:
        """Vrátí seznam MIDI not v zadaném rozsahu (default: celé piano)"""
        start = start_midi if start_midi is not None else MidiUtils.PIANO_MIN_MIDI
        end = end_midi if end_midi is not None else MidiUtils.PIANO_MAX_MIDI

        start = max(start, MidiUtils.PIANO_MIN_MIDI)
        end = min(end, MidiUtils.PIANO_MAX_MIDI)

        return list(range(start, end + 1))

    @staticmethod
    def get_octave_notes(octave: int) -> List[int]:
        """Vrátí všechny MIDI noty pro danou oktávu"""
        start_midi = (octave + 1) * 12
        return list(range(start_midi, start_midi + 12))

    @staticmethod
    def generate_filename(midi_note: int, velocity: int, sample_rate: int = None) -> str:
        """Generuje název souboru podle specifikace: mXXX-velY-fZZ.wav"""
        if not (AUDIO.Velocity.EXPORT_MIN <= velocity <= AUDIO.Velocity.EXPORT_MAX):
            raise ValueError(f"Velocity musí být {AUDIO.Velocity.EXPORT_MIN}-{AUDIO.Velocity.EXPORT_MAX}, dostáno: {velocity}")

        # Use default sample rate if not specified
        if sample_rate is None:
            sample_rate = AUDIO.Audio.DEFAULT_SAMPLE_RATE

        # Získání sample rate suffixu z konfigurace
        sr_suffix = AUDIO.SampleRateMapping.get_suffix(sample_rate)

        return f"m{midi_note:03d}-vel{velocity}-{sr_suffix}.wav"

    @staticmethod
    def parse_filename(filename: str) -> Tuple[int, int, int]:
        """Parsuje název souboru podle specifikace, vrací (midi, velocity, sample_rate)"""
        # Odstraň příponu
        name_without_ext = filename.rsplit('.', 1)[0]

        try:
            parts = name_without_ext.split('-')
            if len(parts) != 3:
                raise ValueError("Neplatný formát názvu")

            # Parse MIDI (mXXX)
            midi_part = parts[0]
            if not midi_part.startswith('m'):
                raise ValueError("MIDI část musí začínat 'm'")
            midi_note = int(midi_part[1:])

            # Parse velocity (velY)
            vel_part = parts[1]
            if not vel_part.startswith('vel'):
                raise ValueError("Velocity část musí začínat 'vel'")
            velocity = int(vel_part[3:])

            # Parse sample rate (fZZ)
            sr_part = parts[2]
            if not sr_part.startswith('f'):
                raise ValueError("Sample rate část musí začínat 'f'")
            sr_khz = int(sr_part[1:])
            sample_rate = sr_khz * 1000

            return midi_note, velocity, sample_rate

        except (ValueError, IndexError) as e:
            raise ValueError(f"Nelze parsovat název souboru '{filename}': {e}")


class VelocityUtils:
    """Utility funkce pro práci s velocity"""

    VELOCITY_LEVELS = AUDIO.Velocity.EXPORT_MAX + 1  # 0-7 = 8 levels

    @staticmethod
    def validate_velocity(velocity: int) -> bool:
        """Ověří, zda je velocity v platném rozsahu"""
        return AUDIO.Velocity.EXPORT_MIN <= velocity <= AUDIO.Velocity.EXPORT_MAX

    @staticmethod
    def velocity_to_description(velocity: int) -> str:
        """Převede velocity číslo na popisný text"""
        return AUDIO.Velocity.LEVEL_DESCRIPTIONS.get(velocity, f"Neznámé ({velocity})")

    @staticmethod
    def rms_db_to_velocity(rms_db: float, thresholds: List[float]) -> int:
        """Převede RMS dB na velocity level podle thresholds"""
        if not thresholds:
            return 0

        for velocity, threshold in enumerate(thresholds):
            if rms_db <= threshold:
                return velocity

        return len(thresholds)  # Nejvyšší velocity