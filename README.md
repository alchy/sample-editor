# Sampler Editor

Kompletní nástroj pro analýzu, úpravu a mapování audio samples s podporou drag & drop a automatického přehrávání transponovaných tónů.

## Funkce

### Klíčové vlastnosti
- **Celý piano rozsah**: A0-C8 (88 kláves) v jednom scrollovatelném zobrazení
- **Automatická analýza**: Detekce MIDI noty a velocity levelů ze audio souborů
- **Drag & Drop mapování**: Přetahování samples mezi pozicemi v mapovací matici
- **MIDI editor**: Úprava MIDI parametrů s automatickým přehráváním transponovaných tónů
- **Audio přehrávání**: Srovnávací přehrávání samples a referenčních tónů
- **Export**: Standardizovaná konvence názvů (mXXX-velY-fZZ.wav)

### Audio funkce
- **Přehrávání samples**: MEZERNÍK pro přímé přehrání
- **Srovnávací přehrávání**: S klávesa (tón → pauza → sample)
- **Simultánní přehrávání**: D klávesa (tón + sample současně)
- **Referenční MIDI tóny**: Klik na MIDI čísla v matici
- **Automatické transponované přehrávání**: Při úpravě MIDI noty

## Požadavky

```
Python 3.8+
PySide6
numpy
librosa
soundfile
```

## Instalace

```bash
# Klonování repository
git clone [repository-url]
cd sample-editor

# Vytvoření virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# nebo
.venv\Scripts\activate     # Windows

# Instalace závislostí
pip install -r requirements.txt
```

## Spuštění

```bash
python main.py
```

## Použití

### 1. Načtení samples
1. Klikněte na "Vstupní složka..." a vyberte složku s audio soubory
2. Aplikace automaticky analyzuje všechny podporované formáty
3. Samples se zobrazí v seznamu s detekovanými MIDI parametry

### 2. Úprava MIDI parametrů
1. Vyberte sample ze seznamu kliknutím
2. V MIDI editoru použijte transpozice tlačítka:
   - **+1/-1**: Půltón nahoru/dolů
   - **+12/-12**: Oktáva nahoru/dolů
3. Při transpozici se automaticky přehraje nový referenční tón
4. Auto-přehrávání lze vypnout tlačítkem "Auto-přehrávání: ZAP/VYP"

### 3. Mapování do matice
1. **Drag & Drop ze seznamu**: Přetáhněte sample ze seznamu do požadované pozice v matici
2. **Přesun v matici**: Táhněte sample mezi pozicemi v matici pro přeuspořádání
3. **Přehrávání**: Levý klik na buňku přehraje namapovaný sample
4. **Info**: Pravý klik na buňku zobrazí detailní informace

### 4. Navigace v mapovací matici
- **Celý piano rozsah**: A0 (MIDI 21) až C8 (MIDI 108) v jednom zobrazení
- **Scrollování**: Vertikální scroll pro navigaci (nejvyšší frekvence nahoře)
- **MIDI tóny**: Klik na modrá MIDI čísla přehraje referenční tón
- **Auto-scroll**: Při výběru namapovaného sample se matice automaticky posune

### 5. Export
1. Vyberte "Výstupní složka..." pro export
2. Klikněte "Export" pro vytvoření souborů
3. Soubory se exportují s konvencí: `mXXX-velY-fZZ.wav`
   - `XXX`: MIDI číslo (021-108)
   - `Y`: Velocity level (0-7)
   - `ZZ`: Číslo souboru při duplicitách

## Klávesové zkratky

### V seznamu samples
- **MEZERNÍK**: Přehrát vybraný sample
- **S**: Srovnávací přehrávání (referenční tón → pauza → sample)
- **D**: Simultánní přehrávání (referenční tón + sample současně)

### Globální
- **ESC**: Zastavit přehrávání

## Struktura projektu

```
sample-editor/
├── main.py                     # Hlavní aplikace
├── models.py                   # Datové modely (SampleMetadata)
├── audio_analyzer.py           # Analýza audio souborů
├── midi_utils.py              # MIDI utility funkce
├── audio_player.py            # Audio přehrávání
├── sample_editor_widget.py    # MIDI editor widget
├── drag_drop_components.py    # Drag & drop komponenty
├── export_utils.py            # Export functionality
└── README.md                  # Tato dokumentace
```

## Podporované formáty

- **Audio**: WAV, AIFF, FLAC, MP3, OGG
- **Export**: WAV (48kHz, mono/stereo podle originálu)

## Mapovací matice

### Rozhraní
- **Řádky**: MIDI noty (C8 nahoře → A0 dole)
- **Sloupce**: Velocity levels (V0-V7)
- **Barvy**: 
  - Zelené buňky = namapované samples
  - Bílé buňky = volné pozice
  - Modré tlačítka = MIDI čísla (klik = referenční tón)

### Operace
- **Drop ze seznamu**: Nové mapování
- **Drop v matici**: Přesun mezi pozicemi
- **Přepsání**: Potvrzovací dialog při kolizi
- **Auto-scroll**: Na pozici vybraného sample

## MIDI Editor

### Zobrazení
- **MIDI Nota**: Aktuální nota sample (např. C4 (60))
- **Velocity**: Detekovaná úroveň hlasitosti
- **Confidence**: Přesnost pitch detekce

### Transpozice
- **Půltóny**: +1/-1 tlačítka (červená/zelená)
- **Oktávy**: +12/-12 tlačítka (tmavě červená/zelená)
- **Auto-přehrávání**: Automatické přehrání nového tónu po transpozici
- **Manuální přehrání**: Tlačítko "Přehrát tón"

## Tipy pro použití

1. **Rychlá navigace**: Použijte scroll wheel pro rychlou navigaci v matici
2. **Batch mapování**: Vyberte správnou velocity úroveň před drag & drop
3. **Audio porovnání**: Použijte S klávesu pro srovnání s referenčním tónem
4. **Transpozice**: Upravte MIDI notu před mapováním pro přesnější výsledky
5. **Organizace**: Využijte celý rozsah matice pro logické rozmístění samples
