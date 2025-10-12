# Sample Editor (PySide6 GUI)

Professional sample mapping and export tool for musicians and sound designers. This repository contains a desktop GUI application built with Python and PySide6 (Qt for Python). It analyzes audio samples (pitch via CREPE, amplitude/RMS), lets you map them across the keyboard with velocity layers, and exports organized WAV files.

This README adds technical details for setup, running, tests, and project structure. The detailed feature documentation from the previous README is kept below for convenience.

## Overview
- Language: Python 3.x
- Frameworks/Libraries: PySide6 (Qt), sounddevice, soundfile, librosa, TensorFlow + CREPE (for pitch detection)
- Package manager: pip (requirements.txt / requirements-dev.txt)
- Entry point: main.py (launches the GUI)

## Requirements
- Python: 3.9–3.12 recommended
- OS: Windows, macOS, or Linux with system audio configured
- Runtime deps: see requirements.txt
- Dev/test deps (optional): see requirements-dev.txt

Install dependencies:
- Windows (PowerShell)
  - python -m venv .venv
  - .venv\\Scripts\\Activate
  - pip install --upgrade pip
  - pip install -r requirements.txt
- macOS/Linux (bash)
  - python3 -m venv .venv
  - source .venv/bin/activate
  - python -m pip install --upgrade pip
  - pip install -r requirements.txt

Notes:
- Optional heavy deps (TensorFlow + CREPE) are included in requirements.txt for full pitch-detection functionality.
- requirements.txt appears to contain a corrupted trailing line. If installation fails near the end, open the file and remove the last non-ASCII line. TODO: Clean the file and pin only necessary versions.

## Setup and Run
- Activate your virtual environment
- Install dependencies (see above)
- Launch the application:
  - Windows: python .\\main.py
  - macOS/Linux: python3 ./main.py

The GUI will open. On first run with CREPE/TensorFlow, model load can take tens of seconds.

## Scripts and Common Commands
There is no pyproject.toml or setup.py with defined scripts. Use these direct commands instead:
- Run app: python main.py
- Run tests: pytest
- Run tests with markers:
  - unit only: pytest -m unit
  - integration only: pytest -m integration
  - include slow tests: pytest -m "unit or integration or slow"
- Verbose, short tracebacks (default via pytest.ini): pytest -v --tb=short
- Lint/format (if you installed requirements-dev.txt):
  - flake8
  - black .
  - mypy .

## Environment Variables
No required environment variables are defined by the project at this time. Potential optional variables you might consider for your environment:
- TODO AUDIODEVICE or SOUNDDEVICE-related configuration to force a specific audio device
- TODO QT_QPA_PLATFORM to change Qt backend in headless/CI runs (e.g., "offscreen")
- TODO TensorFlow settings (e.g., to disable GPU if needed: CUDA_VISIBLE_DEVICES="")

If you intend to run GUI tests in CI, you may need a virtual display (Xvfb on Linux) or to set Qt to offscreen.

## Tests
- Framework: pytest (configured via pytest.ini)
- Test locations: tests/
- Markers (see pytest.ini): unit, integration, slow
- GUI testing helpers: pytest-qt is present in runtime requirements

Examples:
- Run all: pytest
- Run unit tests only: pytest -m unit
- Show durations of slow tests: pytest -m slow -vv

## Project Structure
High-level layout of this repository:
- main.py — GUI entry point (sets up QApplication, MainWindow, graceful shutdown, audio worker shutdown)
- main_window.py — Main window and menu/shortcut wiring
- sample_editor_widget.py — Central editor UI widgets
- audio_analyzer.py, pitch_detector.py, session_aware_analyzer*.py — Analysis logic (CREPE/RMS, caching)
- audio_player.py, audio_worker.py — Playback and background audio worker
- drag_drop_* — Drag & drop helpers and mapping matrix components
- export_thread.py, export_utils.py — Asynchronous export and helpers
- sessions/ — Session files (JSON) persisted by the app
- tests/ — Unit and integration tests (pytest)
- requirements.txt — Runtime dependencies (note: last line may be corrupted; see TODO above)
- requirements-dev.txt — Dev/test tooling (pytest, black, flake8, mypy, etc.)
- pytest.ini — Pytest configuration (paths, markers, options)
- core/, models.py, midi_utils.py, inline_midi_editor.py, amplitude_*.py — Supporting modules
- src/ — Present in repo; currently not the primary entrypoint path

For a quick file list, see the sections below or your IDE’s project tree.

## License
No LICENSE file is present in the repository. Until a license is added, treat this code as “All rights reserved” and do not redistribute. TODO: Add an explicit LICENSE (e.g., MIT/Apache-2.0) and update this section.

---

Below is the original, detailed feature guide retained for users.

# Sampler Editor - Professional Version

Professional sample mapping tool with advanced pitch detection, velocity analysis, and intelligent session management.

## 🎯 Key Features

### Core Functionality
- **🎵 CREPE Pitch Detection** - High-accuracy neural pitch detection (TensorFlow CREPE)
- **📊 RMS Velocity Analysis** - Intelligent amplitude analysis (500ms window)
- **🎨 Drag & Drop Interface** - Visual sample mapping with dedicated drag buttons
- **💾 Session Management** - Project-based workflow with MD5-based caching
- **📤 Multi-format Export** - Simultaneous export to 44.1kHz and 48kHz

### Advanced Features
- **⚡ Hash-based Caching** - Lightning-fast project reloading (MD5 validation)
- **🎹 Full Piano Range** - A0-C8 support (MIDI 21-108)
- **✏️ Inline MIDI Editor** - Real-time transpose with -12/-1/+1/+12 buttons
- **🎯 Smart Auto-assign** - Center-based velocity mapping algorithm
- **🔊 Dual Audio Preview** - Sample playback + reference MIDI tone comparison
- **🎛️ Configurable Velocity Layers** - 1-8 velocity layers per session
- **📋 GUI Menu Integration** - All keyboard shortcuts accessible via menu

## 🚀 Installation

### Requirements
- Python 3.8+
- PySide6 (Qt6)
- Audio libraries (sounddevice, soundfile, librosa)
- TensorFlow + CREPE (optional, for pitch detection)

```bash
pip install -r requirements.txt
```

### Optional Dependencies
```bash
# For CREPE pitch detection (recommended)
pip install crepe tensorflow

# For enhanced audio support
pip install librosa
```

## 📖 Quick Start

### 1. Launch Application
```bash
python main.py
```

### 2. Create/Select Session
- **First launch:** Create new session with custom name
- **Configure:** Set velocity layers (1-8, default: 4)
- **Sessions folder:** `sessions/session-name.json`

### 3. Load Samples
- **Menu:** `File → Set Input Folder` (`Ctrl+I`)
- **Auto-analysis:** Pitch and RMS detection begins automatically
- **Cache:** Previously analyzed samples load instantly

### 4. Map Samples
- **Drag & Drop:** Click drag button (⋮⋮) and drop to matrix
- **Auto-assign:** Click ⚡ button for automatic velocity distribution
- **Manual edit:** Use transpose buttons (-12/-1/+1/+12) for pitch correction

### 5. Preview & Compare
- **Green ♪ button:** Play audio sample
- **Pink ♫ button:** Play reference MIDI tone (for pitch comparison)
- **Keyboard:** `Space` = play sample, `M` = play MIDI tone, `Esc` = stop

### 6. Export
- **Menu:** `File → Export Samples` (`Ctrl+E`)
- **Output:** Set folder (`Ctrl+O`)
- **Format:** `mXXX-velY-fZZ.wav` (MIDI-velocity-samplerate)

## 🎮 Interface Guide

### Sample List (Left Panel - 40%)
| Element | Function |
|---------|----------|
| **⋮⋮ Drag button** | Drag sample to mapping matrix |
| **☐ Disable checkbox** | Temporarily exclude sample |
| **MIDI number** | Detected MIDI note |
| **Note name** | Musical note (e.g., C4, F#3) |
| **RMS value** | Amplitude (velocity) measurement |
| **-12/-1/+1/+12** | Transpose pitch detection |
| **♪ Green button** | Play audio sample |
| **♫ Pink button** | Play reference MIDI tone |

### Mapping Matrix (Right Panel - 60%)
| Element | Function |
|---------|----------|
| **♪ Play MIDI** | Generate reference tone for that MIDI note |
| **⌫ Reset** | Clear all samples for MIDI note |
| **⚡ Auto-assign** | Automatic velocity mapping (center-based algorithm) |
| **Matrix cells** | Drag samples here, left-click to play/remove |
| **Velocity layers** | V0-V7 (or custom 1-8 layers) |

### Audio Player Panel
- **Volume control** - Adjust playback volume
- **MIDI output** - Virtual MIDI device for reference tones
- **Stop button** - Halt playback

## ⌨️ Keyboard Shortcuts

### File Operations
| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New Session |
| `Ctrl+I` | Set Input Folder |
| `Ctrl+O` | Set Output Folder |
| `Ctrl+E` | Export Samples |
| `Ctrl+Q` | Exit Application |

### Edit Operations
| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Clear Matrix |
| `F5` | Refresh Samples |
| `T` | Sort by MIDI and RMS |

### Playback Controls
| Shortcut | Action |
|----------|--------|
| `Space` | Play Current Sample |
| `M` | Play Reference MIDI Tone |
| `Esc` | Stop Playback |

### Sample List Shortcuts
| Shortcut | Action |
|----------|--------|
| `S` | Compare playback |
| `D` | Simultaneous playback |
| `T` | Sort samples |

## 💾 Session Management

### Automatic Caching
Sessions store and cache:
- ✅ **Pitch Detection Results** - MD5-based sample analysis
- ✅ **Amplitude Data** - RMS velocity measurements
- ✅ **MIDI Mappings** - Sample-to-position assignments
- ✅ **Transposition Changes** - Modified pitch values
- ✅ **Folder Paths** - Input/output preferences
- ✅ **Velocity Layer Config** - Session-specific settings

### Session File Structure
`sessions/session-name.json`:
```json
{
  "session_name": "DrumKit2024",
  "created": "2025-10-12T10:30:00",
  "velocity_layers": 4,
  "folders": {
    "input": "/path/to/samples",
    "output": "/path/to/export"
  },
  "samples_cache": {
    "abc123def456...": {
      "filename": "kick_01.wav",
      "detected_midi": 36,
      "detected_frequency": 65.41,
      "velocity_amplitude": 0.456789,
      "analyzed": true
    }
  },
  "mapping": {
    "36,0": "abc123def456...",
    "36,1": "def789ghi012..."
  }
}
```

### Cache Benefits
- 🚀 **Instant Loading:** Previously analyzed samples load in milliseconds
- 💡 **Smart Updates:** Only re-analyzes changed files (MD5 validation)
- 🔒 **Data Persistence:** All edits and transposes saved automatically
- 📊 **Session Stats:** Track cached vs newly analyzed samples

## 📦 Export Format

### Naming Convention
```
mXXX-velY-fZZ.wav
```
- `XXX` = MIDI note (021-108, zero-padded)
- `Y` = Velocity level (0-7 or custom)
- `ZZ` = Sample rate (44 or 48)

### Examples
- `m036-vel0-f44.wav` → C2, softest velocity, 44.1kHz
- `m060-vel4-f48.wav` → C4 (Middle C), medium velocity, 48kHz
- `m108-vel7-f44.wav` → C8, loudest velocity, 44.1kHz

### Export Specifications
- **Format:** 16-bit PCM WAV
- **Sample Rates:** 44.1kHz and 48kHz (simultaneous)
- **Channels:** Mono or Stereo (preserves source)
- **Processing:** Direct copy (no pitch shifting)

## 🎼 Supported Audio Formats

**Input:**
- WAV (all bit depths)
- FLAC (lossless)
- AIFF (Apple)
- MP3 (via librosa)

**Output:**
- WAV (16-bit PCM, professional standard)

## 🔧 Workflow Example

### Complete Session Walkthrough

1. **Create Session**
   - Name: "DrumKit2024"
   - Velocity layers: 4

2. **Load Samples**
   - Input folder: `/samples/kicks/`
   - Auto-analysis: 12 kick samples detected
   - Cache: Results stored with MD5 hashes

3. **Review & Correct**
   - Sample `kick_07.wav` detected as C2 (MIDI 36)
   - Click pink ♫ button → hear reference C2 tone
   - Click green ♪ button → hear actual sample
   - Sample sounds like C#2 → click `+1` transpose button
   - Verify with pink ♫ button → now plays C#2 reference

4. **Auto-assign Mapping**
   - Click ⚡ button on C#2 row (MIDI 37)
   - Algorithm distributes 12 samples across 4 velocity layers
   - Center-based: finds best RMS match for each layer

5. **Manual Adjustments**
   - Drag `kick_01.wav` from V0 to V1 (preference)
   - Left-click matrix cells to preview
   - Use keyboard `T` to re-sort list

6. **Export**
   - Set output: `/export/drumkit/`
   - Press `Ctrl+E`
   - Generates 24 files (12 samples × 2 sample rates)

7. **Next Session**
   - Reload session → instant loading (cached)
   - All mappings and transposes preserved

## 🛠️ Troubleshooting

### Audio Issues

**No playback:**
```bash
pip install sounddevice soundfile
# Check system audio settings
```

**Crackling/distortion:**
- Increase buffer size in audio player settings
- Check CPU usage

### Analysis Issues

**Slow first run:**
- Normal: CREPE model loading (~30 seconds)
- Subsequent analyses use cache

**Wrong pitch detection:**
- Use transpose buttons (-12/-1/+1/+12)
- Compare with pink ♫ reference tone
- Session saves corrections automatically

**Missing samples:**
- Check input folder path
- Verify audio format support
- Review console logs

### Export Issues

**Export fails:**
- Verify output folder write permissions
- Check available disk space (samples are copied, not moved)
- Review error message in dialog

**Wrong naming:**
- Check MIDI note assignments in matrix
- Verify velocity layer configuration

### Session Issues

**Cache not loading:**
- Check `sessions/` folder exists
- Verify JSON file not corrupted
- Review MD5 hash mismatches in log

**Lost mappings:**
- Ensure session saved before closing (`Ctrl+S` or auto-save)
- Check session file modification time

## 🏗️ Technical Architecture

### Technology Stack
- **GUI Framework:** PySide6 (Qt6 for Python)
- **Audio I/O:** sounddevice, soundfile
- **Audio Analysis:** librosa (spectral analysis)
- **Pitch Detection:** TensorFlow + CREPE neural network
- **Session Storage:** JSON with MD5 hashing
- **Threading:** Multi-threaded analysis, async export

### Architecture Pattern
- **Clean Architecture:** Domain/Application/Infrastructure layers
- **Repository Pattern:** Session data persistence
- **Observer Pattern:** Signal-based UI updates
- **Factory Pattern:** Audio analyzer creation

### Performance Optimizations
- **Progressive UI Creation:** QTimer-based incremental loading
- **Drag Operation Locking:** Race condition prevention
- **MD5 Caching:** Instant cache validation
- **Batch Analysis:** Multi-sample processing

### Safety Features
- **UI Creation Lock:** Prevents drag during progressive loading
- **Drag Operation Lock:** Prevents rebuild during drag
- **Session Auto-save:** On close and after major operations
- **Hash Validation:** Detects file modifications

## 📊 Project Statistics

- **Lines of Code:** ~8,000+
- **Modules:** 20+ Python files
- **Test Coverage:** Unit tests for core domain logic
- **Session Format:** JSON (human-readable)
- **Supported Platforms:** Windows, macOS, Linux

## 🔮 Future Enhancements

Potential features:
- [ ] Real-time pitch shifting on export
- [ ] Batch transpose operations
- [ ] Sample trimming/cropping
- [ ] Advanced filtering options
- [ ] Multi-session management
- [ ] MIDI file import for mapping templates

## 📝 License

Professional sample editor for music production workflows.

**Version:** 2.0
**Framework:** PySide6

---

**Tip:** Press `F1` in the application for quick help, or check the `Help → About` menu for version info.
