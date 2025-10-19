# Building Sample Mapping Editor

This guide explains how to build a standalone executable and installer for Sample Mapping Editor.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Build](#quick-build)
3. [Build Process Details](#build-process-details)
4. [Creating an Installer](#creating-an-installer)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- **Python 3.9+** with virtual environment activated
- **PyInstaller** (auto-installed by build script)
- **All project dependencies** installed (`pip install -r requirements.txt`)

### Optional (for installer)

- **Inno Setup 6** - Download from https://jrsoftware.org/isdl.php
- **7-Zip** - For creating ZIP archives (optional)

---

## Quick Build

### Step 1: Activate Virtual Environment

```bash
.venv\Scripts\activate
```

### Step 2: Run Build Script

```bash
build.bat
```

That's it! The executable will be created in `dist\SampleMappingEditor.exe`

---

## Build Process Details

### What the Build Script Does

1. **Checks environment** - Verifies Python and virtual environment
2. **Installs PyInstaller** - If not already installed
3. **Cleans previous builds** - Removes old build artifacts
4. **Builds executable** - Creates standalone .exe file
5. **Tests executable** - Launches app for quick verification
6. **Creates release package** - Organizes files for distribution

### Build Outputs

```
project/
├── build/              # Temporary build files (can be deleted)
├── dist/               # Final executable
│   └── SampleMappingEditor.exe  (~150-200 MB)
└── releases/           # Release packages
    └── SampleMappingEditor-vX.X/
        ├── SampleMappingEditor.exe
        ├── README.md
        └── INSTALL.txt
```

### Build Time

- **First build**: 5-10 minutes (downloads dependencies)
- **Subsequent builds**: 2-5 minutes (uses cache)

---

## Creating an Installer

### Step 1: Install Inno Setup

Download and install from: https://jrsoftware.org/isdl.php

### Step 2: Build Executable First

```bash
build.bat
```

### Step 3: Create Installer

```bash
build_installer.bat
```

### Installer Output

```
installers/
└── SampleMappingEditor-Setup-v2.0.exe  (~150-200 MB)
```

### Installer Features

- ✅ Modern UI
- ✅ Start Menu shortcuts
- ✅ Optional desktop shortcut
- ✅ Uninstaller
- ✅ Version checking
- ✅ Clean uninstall

---

## Troubleshooting

### "Virtual environment not detected"

**Solution**: Activate your virtual environment first:
```bash
.venv\Scripts\activate
```

### "PyInstaller build failed"

**Common causes**:
1. **Missing dependencies** - Run `pip install -r requirements.txt`
2. **Antivirus blocking** - Temporarily disable antivirus during build
3. **Disk space** - Ensure ~500 MB free space

**Check logs**:
```bash
# Look for errors in build output
# Most recent log is in: build/warn-SampleMappingEditor.txt
```

### "ImportError" when running executable

**Solution**: Add missing module to `sample-editor.spec` in `hiddenimports`:
```python
hiddenimports=[
    ...
    'your_missing_module',
],
```

Then rebuild:
```bash
build.bat
```

### Executable is too large (>300 MB)

**Solutions**:
1. **Enable UPX compression** - Already enabled in spec file
2. **Exclude unnecessary packages** - Edit `sample-editor.spec`:
   ```python
   excludes=[
       'matplotlib',  # Add packages you don't need
       'pandas',
       ...
   ],
   ```

### "Inno Setup not found"

**Solution**: Install from https://jrsoftware.org/isdl.php

Or manually compile:
```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

---

## Advanced Options

### Custom Icon

1. Create/download an `.ico` file
2. Place it in `resources/app_icon.ico`
3. Rebuild with `build.bat`

### Build Without Compression

Edit `sample-editor.spec`:
```python
upx=False,  # Disable UPX compression (faster build, larger file)
```

### Debug Build (with console window)

Edit `sample-editor.spec`:
```python
console=True,  # Show console for debugging
```

### Exclude More Packages

Edit `sample-editor.spec` → `excludes` list to reduce file size.

---

## Distribution

### Option 1: Standalone Executable

Share the file in `releases/SampleMappingEditor-vX.X/`

**Pros**: No installation needed
**Cons**: Larger download (~150-200 MB)

### Option 2: Installer

Share `installers/SampleMappingEditor-Setup-v2.0.exe`

**Pros**: Professional, creates shortcuts, uninstaller
**Cons**: Requires installation

### Option 3: ZIP Archive

If 7-Zip is installed, build.bat creates a ZIP automatically.

---

## GitHub Release

### Automated Release (Recommended)

Create a git tag:
```bash
git tag v2.0
git push origin v2.0
```

Then manually upload to GitHub Releases:
1. Go to https://github.com/alchy/sample-editor/releases
2. Click "Draft a new release"
3. Upload the installer or ZIP file

---

## Build Verification Checklist

- [ ] Executable runs without errors
- [ ] All GUI elements display correctly
- [ ] Audio playback works
- [ ] File dialogs work
- [ ] Sessions save/load correctly
- [ ] Export functionality works
- [ ] No console window appears (GUI-only app)

---

## Support

For build issues, check:
1. This BUILD.md file
2. PyInstaller docs: https://pyinstaller.org/
3. Inno Setup docs: https://jrsoftware.org/ishelp/

For application issues:
- GitHub Issues: https://github.com/alchy/sample-editor/issues
