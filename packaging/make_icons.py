#!/usr/bin/env python3
"""Generate the app icons (packaging/icon.ico + icon-*.png) and the Android
launcher mipmaps from one drawing, so every frontend looks the same:
a dark rounded square with the accent 'look-through' lens ring.

  python3 packaging/make_icons.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
BG = (18, 21, 31, 255)
ACCENT = (255, 196, 61, 255)


def draw(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = size // 5  # corner radius
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BG)
    cx = cy = size / 2
    ring = max(2, size // 12)
    d.ellipse([cx - size * 0.30, cy - size * 0.30, cx + size * 0.30, cy + size * 0.30],
              outline=ACCENT, width=ring)
    d.ellipse([cx - size * 0.10, cy - size * 0.10, cx + size * 0.10, cy + size * 0.10], fill=ACCENT)
    return img


def main():
    # packaging icons (favicon / .desktop / Windows .ico)
    for s in (16, 32, 48, 64, 128, 256, 512):
        draw(s).save(ROOT / "packaging" / f"icon-{s}.png")
    ico = draw(256)
    ico.save(ROOT / "packaging" / "icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    (ROOT / "web" / "favicon.png").write_bytes((ROOT / "packaging" / "icon-64.png").read_bytes())
    # Android launcher mipmaps
    for density, s in (("mdpi", 48), ("hdpi", 72), ("xhdpi", 96), ("xxhdpi", 144), ("xxxhdpi", 192)):
        d = ROOT / "android" / "app" / "src" / "main" / "res" / f"mipmap-{density}"
        d.mkdir(parents=True, exist_ok=True)
        draw(s).save(d / "ic_launcher.png")
        draw(s).save(d / "ic_launcher_round.png")
    print("icons written to packaging/ and android/app/src/main/res/mipmap-*/")


if __name__ == "__main__":
    main()
