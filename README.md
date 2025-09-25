# Sampler Editor - Professional Version

Python sample mapping tool with pitch detection, RMS velocity analysis, and hash-based session caching.

## Features

### Core Functionality
- **CREPE Pitch Detection** - High-accuracy pitch detection using TensorFlow CREPE
- **RMS Velocity Analysis** - Amplitude analysis for velocity mapping (500ms window)
- **Drag & Drop Interface** - Visual sample mapping with dedicated drag buttons
- **Session Management** - Project-based workflow with automatic caching
- **Multi-format Export** - Export to 44.1kHz and 48kHz simultaneously

### Advanced Features
- **Hash-based Caching** - MD5-based sample caching for fast project reloading
- **Piano Range Mapping** - Full A0-C8 piano range support (MIDI 21-108)
- **Inline MIDI Editor** - Transpose samples directly in the interface
- **Auto-assign Algorithm** - Center-based automatic velocity mapping
- **Real-time Audio Preview** - Play samples and MIDI tones during mapping

## Installation

### Requirements
```bash
pip install -r requirements.txt
```

## Quick Start

1. **Launch Application**
   ```bash
   python main.py
   ```

2. **Create/Select Session**
   - Create new session or select existing one
   - Sessions are stored in `sessions/` folder

3. **Set Input Folder**
   - `Ctrl+I` or File → Set Input Folder
   - Select folder containing audio samples
   - Automatic analysis begins (cached samples load instantly)

4. **Map Samples**
   - Use drag buttons (⋮⋮) to drag samples to matrix
   - Or use auto-assign buttons (⚡) for automatic mapping
   - Left-click matrix cells to play/remove samples

5. **Export**
   - `Ctrl+E` or File → Export Samples  
   - Set output folder (`Ctrl+O`)
   - Exports in format: `mXXX-velY-fZZ.wav`

## Interface

### Sample List (Left Panel)
- **Drag Buttons (⋮⋮)** - Drag samples to mapping matrix
- **Transpose Buttons** - Adjust pitch detection (-12, -1, +1, +12 semitones)
- **Play Button (♪)** - Preview sample audio
- **Disable Checkbox** - Temporarily disable sample

### Mapping Matrix (Right Panel)
- **Piano Range** - A0-C8 (MIDI 21-108)
- **Velocity Levels** - 8 levels (V0-V7) based on RMS analysis
- **Play MIDI (♪)** - Generate reference tones
- **Reset (⌫)** - Clear all samples for MIDI note
- **Auto-assign (⚡)** - Automatic velocity mapping

### Keyboard Shortcuts
- `Ctrl+N` - New Session
- `Ctrl+I` - Input Folder
- `Ctrl+O` - Output Folder  
- `Ctrl+E` - Export
- `Ctrl+K` - Clear Matrix
- `F5` - Refresh
- `Space` - Play selected sample
- `ESC` - Stop audio
- `T` - Sort samples by MIDI/RMS

## Session Management

Sessions automatically cache:
- **Sample Analysis** - MD5-based caching of pitch/amplitude data
- **MIDI Mappings** - Sample-to-MIDI position assignments
- **Folder Paths** - Input/output folder preferences
- **Transpozice Changes** - Modified pitch values

### Session Files
Located in `sessions/session-name.json`:
```json
{
  "samples_cache": {
    "md5_hash": {
      "detected_midi": 60,
      "velocity_amplitude": 0.123456,
      "analyzed_timestamp": "2024-01-01T12:00:00"
    }
  },
  "mapping": {
    "60,0": "md5_hash"
  }
}
```

## Export Format

Exported files follow naming convention:
```
mXXX-velY-fZZ.wav
```
- `XXX` - MIDI note number (021-108)
- `Y` - Velocity level (0-7)
- `ZZ` - Sample rate (44/48)

Example: `m060-vel4-f44.wav` = Middle C, medium velocity, 44.1kHz

## Supported Audio Formats

**Input:** WAV, FLAC, AIFF, MP3 (via soundfile/librosa)  
**Output:** WAV (16-bit PCM)

## Workflow Example

1. Create session "DrumKit2024"
2. Set input folder to `/samples/kicks/`
3. Analysis detects 12 samples, caches results
4. Auto-assign samples to C2 (MIDI 36) across 8 velocity levels
5. Manual adjustment: transpose kick_07.wav from C2 to C#2
6. Export generates 24 files (12 samples × 2 sample rates)
7. Next session reload: instant loading from cache

## Troubleshooting

**No audio playback:**
- Install: `pip install sounddevice soundfile`
- Check system audio device

**Analysis too slow:**
- First run always slower (CREPE model loading)
- Subsequent runs use cached results

**Export fails:**
- Verify output folder write permissions
- Check available disk space

## Technical Details

- **Framework:** PySide6 (Qt6)
- **Audio Processing:** librosa, soundfile
- **Pitch Detection:** TensorFlow CREPE
- **Session Storage:** JSON with MD5 hashing
- **Architecture:** Multi-threaded analysis, async export

## License

Professional sample editor for music production workflows.