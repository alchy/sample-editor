# Application Icon

This folder should contain the application icon: `app_icon.ico`

## Creating an Icon

### Option 1: Use Online Converter (Easiest)

1. Create or find a square image (PNG recommended, 256x256 or larger)
2. Go to https://convertio.co/png-ico/ or https://www.icoconverter.com/
3. Upload your image
4. Download as `app_icon.ico`
5. Place it in this `resources/` folder

### Option 2: Use GIMP (Free Software)

1. Download GIMP: https://www.gimp.org/
2. Create/Open your image (256x256 recommended)
3. File → Export As → name it `app_icon.ico`
4. Select "Windows Icon" format
5. Place in this folder

### Option 3: Use ImageMagick (Command Line)

```bash
# Install ImageMagick from https://imagemagick.org/
convert input.png -define icon:auto-resize=256,128,96,64,48,32,16 app_icon.ico
```

## Icon Specifications

- **Format**: .ICO (Windows Icon)
- **Sizes**: Multiple sizes embedded (16x16, 32x32, 48x48, 256x256)
- **Color depth**: 32-bit with transparency
- **Recommended source**: 256x256 PNG or larger

## Icon Design Tips

For a Sample Mapping Editor icon, consider:
- Musical note symbol (♪ or ♫)
- Piano keyboard
- Waveform
- Grid/matrix pattern
- Combination of above elements

Use simple, bold designs that are recognizable at small sizes (16x16).

## Temporary Placeholder

If you don't have an icon yet, the build will work but use the default Python icon.
You can add a custom icon later and rebuild.

## After Adding Icon

1. Place `app_icon.ico` in this folder
2. Run `build.bat` to rebuild with the new icon
3. The icon will appear on the .exe file and in the Start Menu
