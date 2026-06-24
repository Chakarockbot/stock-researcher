"""
Generates StockResearcher.ico — run once to produce the icon file.
Uses only Python stdlib (no Pillow needed).
"""
import struct
import zlib
import os

W, H = 32, 32
BG     = (8,   12,  16,  255)   # #080c10 dark navy
GRID   = (26,  40,  64,  180)   # subtle grid
ACCENT = (0,   212, 255, 255)   # #00d4ff cyan
GLOW   = (0,   212, 255, 120)   # softer cyan for thickness

pixels = [[list(BG)] * W for _ in range(H)]

def put(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        pixels[y][x] = list(color)

# Subtle grid
for gx in range(0, W, 8):
    for gy in range(H):
        put(gx, gy, GRID)
for gy in range(0, H, 8):
    for gx in range(W):
        put(gx, gy, GRID)

# Upward trend line (bresenham between keypoints)
keypoints = [(2,27),(6,23),(10,20),(14,17),(18,13),(22,10),(26,7),(30,4)]

def line(x1, y1, x2, y2):
    dx, dy = abs(x2-x1), abs(y2-y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy
    while True:
        put(x1, y1, ACCENT)
        # 2px thick — also paint one pixel above
        put(x1, y1-1, GLOW)
        if x1 == x2 and y1 == y2:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy; x1 += sx
        if e2 < dx:
            err += dx; y1 += sy

for i in range(len(keypoints) - 1):
    line(*keypoints[i], *keypoints[i+1])

# Small dot at the last point
lx, ly = keypoints[-1]
for ox, oy in [(-1,0),(0,0),(1,0),(0,-1),(0,1)]:
    put(lx+ox, ly+oy, ACCENT)


# ── Encode pixels as PNG ──────────────────────────────────────────

def encode_png(pixels, w, h):
    def row(y):
        return b'\x00' + bytes([c for px in pixels[y] for c in px])
    raw = b''.join(row(y) for y in range(h))
    compressed = zlib.compress(raw, 9)

    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    sig    = b'\x89PNG\r\n\x1a\n'
    ihdr   = chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
    idat   = chunk(b'IDAT', compressed)
    iend   = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend

png_data = encode_png(pixels, W, H)

# ── Wrap PNG in ICO ───────────────────────────────────────────────

ico_dir    = struct.pack('<HHH', 0, 1, 1)          # reserved, type=1, count=1
img_offset = 6 + 16                                 # header + one dir entry
dir_entry  = struct.pack('<BBBBHHII',
    W, H,       # width, height (0 = 256)
    0,          # color count (0 = no palette)
    0,          # reserved
    1,          # planes
    32,         # bit count
    len(png_data),
    img_offset,
)

ico_bytes = ico_dir + dir_entry + png_data

out_path = os.path.join(os.path.dirname(__file__), "StockResearcher.ico")
with open(out_path, "wb") as f:
    f.write(ico_bytes)

print(f"Created {out_path} ({len(ico_bytes)} bytes)")
