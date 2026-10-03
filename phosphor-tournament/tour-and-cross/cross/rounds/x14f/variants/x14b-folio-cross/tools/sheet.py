# Lay a tall phone shot out as columns, scaled down, for a quick look.
import sys
from PIL import Image
src, out = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 4
im = Image.open(src).convert("RGB")
w, h = im.size
scale = 0.5
im = im.resize((int(w * scale), int(h * scale)))
w, h = im.size
seg = -(-h // cols)
sheet = Image.new("RGB", (w * cols + 10 * (cols - 1), seg), (40, 40, 40))
for i in range(cols):
    part = im.crop((0, i * seg, w, min(h, (i + 1) * seg)))
    sheet.paste(part, (i * (w + 10), 0))
sheet.save(out)
print(sheet.size)
