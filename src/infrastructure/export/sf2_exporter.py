"""
SoundFont 2.01 (.sf2) exporter.

SF2 je RIFF-based formát s veřejnou specifikací (Creative Labs, 1996/1998).
Struktura: RIFF sfbk → LIST INFO + LIST sdta (smpl) + LIST pdta (phdr/pbag/pmod/pgen/inst/ibag/imod/igen/shdr)

Mapping {(midi_note, vel_layer): Path} → jeden SF2 soubor s jedním instrumentem.
Každá kombinace (nota, velocity vrstva) = jedna zone s keyRange + velRange + sampleID generátory.
"""

import io
import logging
import struct
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import soundfile as sf_io

logger = logging.getLogger(__name__)


# ── SF2 strukturní helper funkce ─────────────────────────────────────────────

def _chunk(tag: str, data: bytes) -> bytes:
    """RIFF chunk: tag(4) + size(4,LE) + data (padded na sudý počet bytů)."""
    if len(data) % 2:
        data += b'\x00'
    return tag.encode('ascii')[:4] + struct.pack('<I', len(data)) + data


def _list_chunk(list_type: str, data: bytes) -> bytes:
    """RIFF LIST chunk: LIST(4) + size(4,LE) + listType(4) + sub-chunks."""
    inner = list_type.encode('ascii')[:4] + data
    if len(inner) % 2:
        inner += b'\x00'
    return b'LIST' + struct.pack('<I', len(inner)) + inner


def _str20(s: str) -> bytes:
    """Fixed 20-byte null-padded ASCII string (SF2 konvence pro jména)."""
    return s.encode('ascii', errors='replace')[:19].ljust(20, b'\x00')


# ── Generator opcodes (SF2 spec §8.1.2) ──────────────────────────────────────
_GEN_KEY_RANGE  = 43
_GEN_VEL_RANGE  = 44
_GEN_INSTRUMENT = 41
_GEN_SAMPLE_ID  = 53

# SF2 sample type (§8.1.4)
_SAMPLE_MONO = 1


class Sf2Exporter:
    """
    Generuje SoundFont 2.01 soubor z mapování {(midi_note, vel_layer): Path}.

    Výsledný SF2 obsahuje:
      - Jeden preset (bank 0, program 0)
      - Jeden instrument
      - N zón — každá s keyRange, velRange a sampleID generátory
      - Audio data (int16 mono) v smpl chunku
    """

    def export(
        self,
        mapping: Dict[Tuple[int, int], Path],
        instrument_name: str = "Custom Bank",
        velocity_layers: int = 8,
    ) -> bytes:
        """
        Sestaví SF2 soubor a vrátí jeho bytes.

        Args:
            mapping:          {(midi_note, vel_layer): cesta_k_wav}
            instrument_name:  Název instrumentu v SF2 metadatech
            velocity_layers:  Počet velocity vrstev (pro výpočet vel. rozsahů)

        Returns:
            Bytes SF2 souboru připravené pro zápis nebo download.
        """
        entries = sorted(mapping.items())
        if not entries:
            raise ValueError("Mapping je prázdné — nelze vytvořit SF2.")

        # ── 1. Načti audio, sestav smpl chunk ────────────────────────
        zones = []
        smpl_io = io.BytesIO()
        offset = 0

        for (midi_note, vel_layer), path in entries:
            try:
                audio, sr = sf_io.read(str(path), dtype='int16', always_2d=False)
            except Exception as exc:
                logger.warning(f"SF2: přeskočen {path.name}: {exc}")
                continue

            # Stereo → mono průměrováním kanálů
            if audio.ndim > 1:
                audio = audio.mean(axis=1).astype(np.int16)

            start = offset
            end = start + len(audio)

            smpl_io.write(audio.tobytes())
            # SF2 spec: 46 nulových int16 vzorků za každým samplem
            smpl_io.write(b'\x00' * 92)

            # Velocity rozsah z vrstvy: rovnoměrné dělení 0-127
            lo_vel = (vel_layer * 128) // velocity_layers
            hi_vel = ((vel_layer + 1) * 128) // velocity_layers - 1

            zones.append({
                'idx':       len(zones),
                'midi_note': midi_note,
                'vel_layer': vel_layer,
                'lo_vel':    lo_vel,
                'hi_vel':    hi_vel,
                'start':     start,
                'end':       end,
                'sr':        sr,
            })

            offset = end + 46  # posun o délku dat + padding
            logger.debug(f"SF2: načten {path.name} → nota {midi_note}, vel {lo_vel}-{hi_vel}")

        if not zones:
            raise ValueError("Žádný sample se nepodařilo načíst — SF2 nelze vytvořit.")

        # Závěrečný blok ticha (SF2 spec)
        smpl_io.write(b'\x00' * 92)
        smpl_data = smpl_io.getvalue()
        N = len(zones)

        logger.info(f"SF2: {N} zón načteno, smpl chunk {len(smpl_data)//1024} kB")

        # ── 2. SHDR — sample headers (46 bytů/záznam) ────────────────
        # Struktura: name[20] + start(4) + end(4) + loopStart(4) + loopEnd(4)
        #            + sampleRate(4) + origPitch(1) + pitchCorr(1) + link(2) + type(2)
        shdr_io = io.BytesIO()
        for z in zones:
            shdr_io.write(_str20(f"n{z['midi_note']:03d}v{z['vel_layer']}"))
            shdr_io.write(struct.pack('<IIIII',
                z['start'], z['end'],
                z['end'],   # loopStart = end (bez smyčky)
                z['end'],   # loopEnd   = end
                z['sr']))
            shdr_io.write(struct.pack('<BbHH',
                z['midi_note'],  # byOriginalPitch
                0,               # chPitchCorrection (centů)
                0,               # wSampleLink (0 = none)
                _SAMPLE_MONO))   # sfSampleType
        # Terminální záznam EOS
        shdr_io.write(_str20('EOS'))
        shdr_io.write(b'\x00' * 26)

        # ── 3. INST — instrument header (22 bytů/záznam) ─────────────
        inst_io = io.BytesIO()
        inst_io.write(_str20(instrument_name[:19]))
        inst_io.write(struct.pack('<H', 0))   # wInstBagNdx = 0 (první ibag)
        # Terminální EOI — wInstBagNdx = celkový počet ibag záznamů
        inst_io.write(_str20('EOI'))
        inst_io.write(struct.pack('<H', N + 1))  # N zón + terminální ibag

        # ── 4. IBAG — instrument bags (4 byty/záznam) ────────────────
        # Každá zone má 3 generátory (keyRange, velRange, sampleID)
        # První zone s sampleID generátorem = NENÍ globální zone (SF2 spec §7.7)
        ibag_io = io.BytesIO()
        for i in range(N):
            ibag_io.write(struct.pack('<HH', i * 3, 0))
        ibag_io.write(struct.pack('<HH', N * 3, 0))  # terminální ibag

        # ── 5. IMOD — prázdný (terminální záznam 10 bytů) ────────────
        imod_data = b'\x00' * 10

        # ── 6. IGEN — instrument generators (4 byty/záznam) ──────────
        igen_io = io.BytesIO()
        for z in zones:
            # keyRange: lo a hi MIDI nota (exact-note mapping)
            igen_io.write(struct.pack('<HBB', _GEN_KEY_RANGE, z['midi_note'], z['midi_note']))
            # velRange: lo a hi velocity
            igen_io.write(struct.pack('<HBB', _GEN_VEL_RANGE, z['lo_vel'], z['hi_vel']))
            # sampleID: index samplu v SHDR
            igen_io.write(struct.pack('<Hh',  _GEN_SAMPLE_ID, z['idx']))
        igen_io.write(b'\x00' * 4)  # terminální igen

        # ── 7. PHDR — preset header (38 bytů/záznam) ─────────────────
        phdr_io = io.BytesIO()
        phdr_io.write(_str20(instrument_name[:19]))
        phdr_io.write(struct.pack('<HHH', 0, 0, 0))   # preset=0, bank=0, bagNdx=0
        phdr_io.write(struct.pack('<III', 0, 0, 0))    # library, genre, morphology
        # Terminální EOP
        phdr_io.write(_str20('EOP'))
        phdr_io.write(struct.pack('<HHH', 255, 255, 2))  # wPresetBagNdx = 2 (celkem pbagů)
        phdr_io.write(struct.pack('<III', 0, 0, 0))

        # ── 8. PBAG — preset bags (4 byty/záznam) ────────────────────
        pbag_io = io.BytesIO()
        pbag_io.write(struct.pack('<HH', 0, 0))  # zone 0: genNdx=0
        pbag_io.write(struct.pack('<HH', 1, 0))  # terminální pbag: genNdx=1

        # ── 9. PMOD — prázdný ─────────────────────────────────────────
        pmod_data = b'\x00' * 10

        # ── 10. PGEN — preset generator: instrument=0 ─────────────────
        pgen_io = io.BytesIO()
        pgen_io.write(struct.pack('<Hh', _GEN_INSTRUMENT, 0))
        pgen_io.write(b'\x00' * 4)  # terminální pgen

        # ── 11. Sestavení INFO chunku ─────────────────────────────────
        inam = (instrument_name + '\x00').encode('utf-8')
        info_data = (
            _chunk('ifil', struct.pack('<HH', 2, 1)) +   # SF2 verze 2.01
            _chunk('isng', b'EMU8000\x00') +
            _chunk('INAM', inam)
        )

        # ── 12. Sestavení pdta chunku ────────────────────────────────
        pdta_data = (
            _chunk('phdr', phdr_io.getvalue()) +
            _chunk('pbag', pbag_io.getvalue()) +
            _chunk('pmod', pmod_data) +
            _chunk('pgen', pgen_io.getvalue()) +
            _chunk('inst', inst_io.getvalue()) +
            _chunk('ibag', ibag_io.getvalue()) +
            _chunk('imod', imod_data) +
            _chunk('igen', igen_io.getvalue()) +
            _chunk('shdr', shdr_io.getvalue())
        )

        # ── 13. Finální RIFF sfbk ─────────────────────────────────────
        sfbk = (
            b'sfbk' +
            _list_chunk('INFO', info_data) +
            _list_chunk('sdta', _chunk('smpl', smpl_data)) +
            _list_chunk('pdta', pdta_data)
        )

        sf2_bytes = b'RIFF' + struct.pack('<I', len(sfbk)) + sfbk
        logger.info(f"SF2: vygenerován, velikost {len(sf2_bytes)//1024} kB")
        return sf2_bytes
