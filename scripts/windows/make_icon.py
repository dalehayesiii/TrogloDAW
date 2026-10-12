"""Draw TrogloDAW's cave/wave mark as the Windows multi-size icon."""

import sys
from PIL import Image, ImageDraw

size = 1024
image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.polygon(
    [
        (128, 848),
        (80, 512),
        (208, 192),
        (496, 80),
        (816, 192),
        (944, 544),
        (880, 864),
        (640, 944),
        (352, 912),
    ],
    fill="#A331A3",
)
draw.rounded_rectangle((286, 338, 755, 825), radius=230, fill="#291532")
draw.rectangle((286, 567, 755, 825), fill="#291532")
for x, top, bottom in [(366, 562, 674), (464, 466, 758), (562, 530, 707), (661, 578, 660)]:
    draw.line((x, top, x, bottom), fill="#C2CD8B", width=54)
    draw.ellipse((x - 27, top - 27, x + 27, top + 27), fill="#C2CD8B")
    draw.ellipse((x - 27, bottom - 27, x + 27, bottom + 27), fill="#C2CD8B")
image.save(
    sys.argv[1], sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
)
