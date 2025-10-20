"""
create_icon.py - Generate application icon for Ithaca Sample Editor

Creates a modern icon combining piano keys and waveform elements.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size=256):
    """Create application icon with piano keys and waveform."""

    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background gradient (dark blue to lighter blue)
    for y in range(size):
        progress = y / size
        r = int(20 + progress * 20)
        g = int(30 + progress * 40)
        b = int(60 + progress * 80)
        draw.rectangle([(0, y), (size, y+1)], fill=(r, g, b, 255))

    # Add rounded corners
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    corner_radius = size // 8
    mask_draw.rounded_rectangle([(0, 0), (size, size)], radius=corner_radius, fill=255)

    # Apply rounded corners
    output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    output.paste(img, (0, 0), mask)
    draw = ImageDraw.Draw(output)

    # Piano keys at bottom (simplified)
    key_section_height = size // 3
    key_y_start = size - key_section_height

    # White keys
    white_key_count = 7
    white_key_width = size // white_key_count

    for i in range(white_key_count):
        x1 = i * white_key_width
        x2 = x1 + white_key_width - 2
        y1 = key_y_start
        y2 = size - 10

        # White key with gradient
        for y in range(y1, y2):
            progress = (y - y1) / (y2 - y1)
            brightness = int(240 - progress * 20)
            draw.rectangle([(x1, y), (x2, y+1)], fill=(brightness, brightness, brightness, 255))

        # Key border
        draw.rectangle([(x1, y1), (x2, y2)], outline=(100, 100, 100, 255), width=2)

    # Black keys
    black_key_positions = [0, 1, 3, 4, 5]  # Position of black keys
    black_key_width = white_key_width // 2
    black_key_height = key_section_height * 2 // 3

    for pos in black_key_positions:
        x1 = int((pos + 0.7) * white_key_width)
        x2 = x1 + black_key_width
        y1 = key_y_start
        y2 = key_y_start + black_key_height

        # Black key with gradient
        for y in range(y1, y2):
            progress = (y - y1) / (y2 - y1)
            brightness = int(20 + progress * 30)
            draw.rectangle([(x1, y), (x2, y+1)], fill=(brightness, brightness, brightness, 255))

        # Black key border
        draw.rectangle([(x1, y1), (x2, y2)], outline=(0, 0, 0, 255), width=2)

    # Waveform in upper section
    waveform_y_center = key_y_start // 2
    waveform_amplitude = size // 8
    waveform_color = (100, 200, 255, 255)  # Light blue

    # Draw stylized waveform
    points = []
    for x in range(10, size - 10):
        # Create smooth wave pattern
        import math
        t = (x - 10) / (size - 20)

        # Combine multiple sine waves for complex waveform
        y_offset = (
            math.sin(t * 8 * math.pi) * 0.4 +
            math.sin(t * 16 * math.pi) * 0.3 +
            math.sin(t * 32 * math.pi) * 0.2
        )

        y = waveform_y_center + int(y_offset * waveform_amplitude)
        points.append((x, y))

    # Draw waveform with glow effect
    for offset in [4, 3, 2, 1]:
        alpha = int(50 / offset)
        for i in range(len(points) - 1):
            draw.line([points[i], points[i+1]],
                     fill=(*waveform_color[:3], alpha),
                     width=offset*2)

    # Draw main waveform line
    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]],
                 fill=waveform_color,
                 width=3)

    # Add velocity layer indicators (dots on the side)
    dot_x = size - 20
    dot_count = 8
    dot_spacing = (key_y_start - 40) // (dot_count + 1)

    for i in range(dot_count):
        y = 40 + (i + 1) * dot_spacing

        # Gradient from green (quiet) to red (loud)
        progress = i / (dot_count - 1)
        r = int(100 + progress * 155)
        g = int(200 - progress * 150)
        b = 50

        # Draw dot with glow
        for radius in [6, 5, 4, 3]:
            alpha = 255 if radius == 3 else 100
            draw.ellipse([(dot_x - radius, y - radius),
                         (dot_x + radius, y + radius)],
                        fill=(r, g, b, alpha))

    return output


def save_icon_formats(img, base_path):
    """Save icon in multiple formats and sizes."""

    # Create resources directory if it doesn't exist
    resources_dir = os.path.dirname(base_path)
    os.makedirs(resources_dir, exist_ok=True)

    # Save as PNG (high quality)
    png_path = base_path.replace('.ico', '.png')
    img.save(png_path, 'PNG')
    print(f"[OK] Saved: {png_path}")

    # Save as ICO with multiple sizes (for Windows)
    ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    ico_images = []

    for size in ico_sizes:
        resized = img.resize(size, Image.Resampling.LANCZOS)
        ico_images.append(resized)

    ico_path = base_path
    ico_images[0].save(ico_path, format='ICO', sizes=ico_sizes)
    print(f"[OK] Saved: {ico_path}")

    # Save additional common sizes as PNG
    for size in [512, 256, 128, 64]:
        size_path = base_path.replace('.ico', f'_{size}x{size}.png')
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(size_path, 'PNG')
        print(f"[OK] Saved: {size_path}")


if __name__ == "__main__":
    print("Creating Ithaca Sample Editor icon...")

    # Create high-resolution icon
    icon = create_icon(512)

    # Save in multiple formats
    base_path = "resources/app_icon.ico"
    save_icon_formats(icon, base_path)

    print("\n[OK] Icon creation complete!")
    print(f"  Main icon: {base_path}")
    print(f"  PNG version: {base_path.replace('.ico', '.png')}")
    print("\nIcon features:")
    print("  - Piano keys at bottom (7 white + 5 black)")
    print("  - Audio waveform in center")
    print("  - Velocity layer indicators (green to red)")
    print("  - Modern gradient background")
    print("  - Rounded corners")
