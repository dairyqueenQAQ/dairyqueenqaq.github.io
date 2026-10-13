"""Build the web-sized Lost in the Sands images from the Figma source images.

Sources are read from Assets/LostInTheSands and are never modified.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "Assets" / "LostInTheSands"
OUTPUT = ROOT / "media" / "lostinthesands"
# Output name: (source file, longest edge in pixels, WebP quality).
IMAGES = {
    # The grain in the background and sand textures compresses poorly.
    "background": ("background.png", 2200, 70),
    "title": ("title.png", 2200, 90),
    "poster-landscape": ("poster-landscape.jpg", 1400, 84),
    "poster-cover": ("poster-cover.jpg", 1400, 82),
    "poster-portrait": ("poster-portrait.jpg", 1600, 84),
    "postcard": ("postcard.jpg", 1400, 82),
    "tag-texture": ("tag-texture.jpg", 1000, 75),
    "icon-user-gear": ("icon-user-gear.png", 216, 90),
}


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, (filename, longest_edge, quality) in IMAGES.items():
        with Image.open(SOURCES / filename) as original:
            image = ImageOps.exif_transpose(original)
            image.thumbnail((longest_edge, longest_edge), Image.Resampling.LANCZOS)
            has_alpha = "A" in image.getbands() and image.getextrema()[-1][0] < 255
            image = image.convert("RGBA" if has_alpha else "RGB")
            output = OUTPUT / f"{name}.webp"
            image.save(output, "WEBP", quality=quality, method=4)
            print(f"{output.relative_to(ROOT).as_posix()}: {image.width}x{image.height} "
                  f"{image.mode}, {output.stat().st_size / 1024:.0f} KiB")


if __name__ == "__main__":
    main()
