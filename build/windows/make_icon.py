"""Generate the Music Maker .ico (kept as code so no binaries live in the repo). Usage: make_icon.py out.ico"""
import sys
from PIL import Image, ImageDraw

S = 1024
im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
for r in range(S // 2, 0, -2):  # radial gradient disc
    t = r / (S / 2)
    d.ellipse([S / 2 - r, S / 2 - r, S / 2 + r, S / 2 + r], fill=(int(120 + 100 * t), int(40 + 30 * t), int(200 - 60 * t), 255))
w = (255, 255, 255, 255)
d.ellipse([250, 600, 450, 760], fill=w); d.ellipse([560, 540, 760, 700], fill=w)       # note heads
d.rectangle([410, 260, 450, 690], fill=w); d.rectangle([720, 200, 760, 630], fill=w)   # stems
d.polygon([(410, 260), (760, 200), (760, 300), (410, 360)], fill=w)                    # beam
im.save(sys.argv[1], sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
