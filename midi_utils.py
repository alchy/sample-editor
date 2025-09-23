"""
midi_utils.py - Utility funkce pro práci s MIDI notami
"""

from typing import List, Tuple


class MidiUtils:
    """Utility funkce pro MIDI operace"""

    # Piano rozsah
    PIANO_MIN_MIDI = 21  # A0
    PIANO_MAX_MIDI = 108  # C8

    # MIDI nota názvy
    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    @staticmethod
    def midi_to_note_name(midi_note: int) -> str:
        """Převede MIDI notu na jméno (např. 60 -> 'C4')"""
        if not (0 <= midi_note <= 127):
            raise ValueError(f"MIDI nota musí být mezi 0-127, dostáno: {midi_note}")

        octave = (midi_note // 12) - 1
        note_name = MidiUtils.NOTE_NAMES[midi_note % 12]
        return f"{note_name}{octave}"

    @staticmethod
    def midi_to_frequency(midi_note: int) -> float:
        """Převede MIDI notu na frekvenci v Hz (A4 = 440 Hz)"""
        return 440.0 * (2 ** ((midi_note - 69) / 12))

    @staticmethod
    def frequency_to_midi(frequency: float) -> float:
        """Převede frekvenci na plovoucí MIDI hodnotu"""
        if frequency <= 0:
            raise ValueError("Frekvence musí být kladná")
        return 12 * (frequency / 440.0).bit_length() + 69

    @staticmethod
    def is_piano_range(midi_note: int) -> bool:
        """Zkontroluje, zda je MIDI nota v piano rozsahu"""
        return MidiUtils.PIANO_MIN_MIDI <= midi_note <= MidiUtils.PIANO_MAX_MIDI

    @staticmethod
    def is_white_key(midi_note: int) -> bool:
        """Zkontroluje, zda je MIDI nota bílá klávesa"""
        return (midi_note % 12) in {0, 2, 4, 5, 7, 9, 11}  # C, D, E, F, G, A, B

    @staticmethod
    def is_black_key(midi_note: int) -> bool:
        """Zkontroluje, zda je MIDI nota černá klávesa"""
        return (midi_note % 12) in {1, 3, 6, 8, 10}  # C#, D#, F#, G#, A#

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
    def generate_filename(midi_note: int, velocity: int, sample_rate: int = 48000) -> str:
        """Generuje název souboru podle specifikace: mXXX-velY-fZZ.wav"""
        if not (0 <= velocity <= 7):
            raise ValueError(f"Velocity musí být 0-7, dostáno: {velocity}")

        # Určení sample rate suffixu
        if sample_rate == 44100:
            sr_suffix = "f44"
        elif sample_rate == 48000:
            sr_suffix = "f48"
        elif sample_rate == 96000:
            sr_suffix = "f96"
        else:
            # Pro ostatní sample rates použij zkrácení
            sr_khz = int(sample_rate / 1000)
            sr_suffix = f"f{sr_khz:02d}"

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

    VELOCITY_LEVELS = 8  # 0-7

    @staticmethod
    def validate_velocity(velocity: int) -> bool:
        """Ověří, zda je velocity v platném rozsahu"""
        return 0 <= velocity <= 7

    @staticmethod
    def velocity_to_description(velocity: int) -> str:
        """Převede velocity číslo na popisný text"""
        descriptions = {
            0: "Velmi tiché",
            1: "Tiché",
            2: "Měkce",
            3: "Středně tiché",
            4: "Středně",
            5: "Středně hlasité",
            6: "Hlasité",
            7: "Velmi hlasité"
        }
        return descriptions.get(velocity, f"Neznámé ({velocity})")

    @staticmethod
    def rms_db_to_velocity(rms_db: float, thresholds: List[float]) -> int:
        """Převede RMS dB na velocity level podle thresholds"""
        if not thresholds:
            return 0

        for velocity, threshold in enumerate(thresholds):
            if rms_db <= threshold:
                return velocity

        return len(thresholds)  # Nejvyšší velocity