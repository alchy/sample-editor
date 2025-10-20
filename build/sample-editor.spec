# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Sample Mapping Editor
Builds standalone executable with all dependencies included
"""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config', 'config'),  # Include config folder
        ('src', 'src'),  # Include src folder with all modules
        # Sessions folder is created at runtime, no need to include
    ],
    hiddenimports=[
        # Qt/PySide6
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',

        # Audio processing
        'crepe',
        'librosa',
        'librosa.core',
        'librosa.feature',
        'soundfile',
        'sounddevice',
        'numpy',
        'scipy',
        'scipy.signal',
        'resampy',

        # MIDI
        'mido',
        'mido.backends.rtmidi',
        'rtmidi',

        # TensorFlow (required by CREPE)
        'tensorflow',
        'tensorflow.python',
        'tensorflow.python.ops',

        # Other dependencies
        'pathlib',
        'json',
        'logging',
        'hashlib',
        'pickle',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary packages to reduce size
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
        'pandas',
        'pytest',
        'sphinx',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SampleMappingEditor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress with UPX for smaller file size
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/app_icon.ico'  # Application icon
)
