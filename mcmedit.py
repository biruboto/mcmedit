#!/usr/bin/env python3
"""
mcmedit.py

Converts MAX7456-style text .mcm fonts (Betaflight analog OSD fonts) to/from a single PNG sheet
AND can inject a pre-tiled logo sheet into glyph indices 0xA0..0xFF.

Your constraints:
- Base font is a text .mcm (header 'MAX7456', then 256*64 lines of 8-bit binary strings)
- Glyphs are 12x18 pixels
- Logo sheet is already "ready to insert": correct palette and tile alignment
- Logo tiles are written sequentially from hex A0 to FF (96 glyphs)

Palette mapping (exact RGB values):
- Black   #000000 => value 0 (black/shadow)
- Gray    #808080 (OR Green  #00FF00) => value 1 (transparent)
- White   #FFFFFF => value 2 (white/foreground)

The encoder never emits value 3.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from PIL import Image

GLYPH_W = 12
GLYPH_H = 18
GRID = 16
SHEET_W = GLYPH_W * GRID  # 192
SHEET_H = GLYPH_H * GRID  # 288
GLYPHS = 256

BYTES_PER_GLYPH = 64
DATA_BYTES_PER_GLYPH = 54
PADDING_BYTES = BYTES_PER_GLYPH - DATA_BYTES_PER_GLYPH  # 10

# Exact palette (RGB)
RGB_BLACK = (0, 0, 0)
RGB_GRAY = (128, 128, 128)   # transparency placeholder
RGB_WHITE = (255, 255, 255)
RGB_GREEN = (0, 255, 0)  # Betaflight logo chroma-key transparency

# 2-bit values used in .mcm
VAL_BLACK = 0
VAL_TRANSPARENT = 1
VAL_WHITE = 2

# Injection range
INJECT_START = 0xA0
INJECT_END = 0xFF
INJECT_COUNT = INJECT_END - INJECT_START + 1  # 96

USE_COLOR = sys.stderr.isatty() or sys.stdout.isatty()

GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


def _ok(msg: str) -> None:
    if USE_COLOR:
        print(f"{GREEN}OK:{RESET} {msg}")
    else:
        print(f"OK: {msg}")

def _err(msg: str, code: int = 2):
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _read_mcm_text(path: Path) -> List[bytes]:
    lines = path.read_text(encoding="ascii", errors="strict").splitlines()
    if not lines or lines[0].strip() != "MAX7456":
        raise ValueError("Not a MAX7456 text .mcm file (missing 'MAX7456' header).")

    data_lines = lines[1:]
    expected = GLYPHS * BYTES_PER_GLYPH
    if len(data_lines) != expected:
        raise ValueError(
            f"Unexpected line count: got {len(data_lines)}, expected {expected} "
            f"(256 glyphs * 64 bytes per glyph)."
        )

    glyph_bytes: List[bytes] = []
    for gi in range(GLYPHS):
        chunk = data_lines[gi * BYTES_PER_GLYPH : (gi + 1) * BYTES_PER_GLYPH]
        b = bytearray()
        for s in chunk:
            s = s.strip()
            if len(s) != 8 or any(c not in "01" for c in s):
                raise ValueError(f"Invalid byte line at glyph {gi}: {s!r}")
            b.append(int(s, 2))
        glyph_bytes.append(bytes(b))

    return glyph_bytes


def _write_mcm_text(glyph_bytes: List[bytes], out_mcm: Path) -> None:
    if len(glyph_bytes) != GLYPHS:
        raise ValueError("Need exactly 256 glyphs to write .mcm")

    lines: List[str] = ["MAX7456"]
    for g in glyph_bytes:
        if len(g) != BYTES_PER_GLYPH:
            raise ValueError("Glyph byte length mismatch while writing.")
        for b in g:
            lines.append(f"{b:08b}")

    out_mcm.write_text("\n".join(lines) + "\n", encoding="ascii")


def _decode_glyph_to_values(glyph64: bytes) -> List[int]:
    """Return flat list of 12*18 2-bit values."""
    if len(glyph64) != BYTES_PER_GLYPH:
        raise ValueError("Glyph size mismatch.")
    data = glyph64[:DATA_BYTES_PER_GLYPH]

    vals: List[int] = [VAL_TRANSPARENT] * (GLYPH_W * GLYPH_H)
    for y in range(GLYPH_H):
        row = data[y * 3 : (y + 1) * 3]  # 24 bits
        bits = int.from_bytes(row, "big")
        for x in range(GLYPH_W):
            shift = (GLYPH_W - 1 - x) * 2
            v = (bits >> shift) & 0b11
            # If 3 appears, display as white; we won't emit 3 on encode.
            if v == 3:
                v = VAL_WHITE
            vals[y * GLYPH_W + x] = v
    return vals


def _rgb_to_val(rgb):
    if rgb == RGB_BLACK:
        return VAL_BLACK
    if rgb == RGB_WHITE:
        return VAL_WHITE
    if rgb == RGB_GRAY or rgb == RGB_GREEN:
        return VAL_TRANSPARENT
    raise ValueError(
        f"Illegal pixel color {rgb}. Allowed: black {RGB_BLACK}, gray {RGB_GRAY}, green {RGB_GREEN}, white {RGB_WHITE}."
    )


def _tile_to_glyph_bytes(tile_rgb: Image.Image) -> bytes:
    """Encode one 12x18 RGB tile into 64 bytes (54 data + 10 padding)"""
    if tile_rgb.size != (GLYPH_W, GLYPH_H):
        raise ValueError(f"Tile must be {GLYPH_W}x{GLYPH_H}, got {tile_rgb.size}")

    px = tile_rgb.load()
    data = bytearray()

    for y in range(GLYPH_H):
        bits24 = 0
        for x in range(GLYPH_W):
            v = _rgb_to_val(px[x, y])  # 0/1/2 only
            bits24 = (bits24 << 2) | (v & 0b11)
        data.extend(bits24.to_bytes(3, "big"))

    # pad to 64 bytes
    data.extend(b"\x00" * PADDING_BYTES)
    return bytes(data)


def mcm_to_sheet(mcm_path: Path, out_png: Path) -> None:
    glyphs = _read_mcm_text(mcm_path)

    sheet = Image.new("RGB", (SHEET_W, SHEET_H), RGB_GRAY)
    for gi, g in enumerate(glyphs):
        vals = _decode_glyph_to_values(g)

        tile = Image.new("RGB", (GLYPH_W, GLYPH_H), RGB_GRAY)
        tpx = tile.load()
        for y in range(GLYPH_H):
            for x in range(GLYPH_W):
                v = vals[y * GLYPH_W + x]
                if v == VAL_BLACK:
                    tpx[x, y] = RGB_BLACK
                elif v == VAL_TRANSPARENT:
                    tpx[x, y] = RGB_GRAY
                else:
                    tpx[x, y] = RGB_WHITE

        sx = (gi % GRID) * GLYPH_W
        sy = (gi // GRID) * GLYPH_H
        sheet.paste(tile, (sx, sy))

    sheet.save(out_png, optimize=False)


def sheet_to_mcm(sheet_path: Path, out_mcm: Path) -> None:
    img = Image.open(sheet_path).convert("RGB")
    if img.size != (SHEET_W, SHEET_H):
        raise ValueError(f"Sheet must be exactly {SHEET_W}x{SHEET_H}, got {img.size}.")

    px = img.load()

    glyph_bytes: List[bytes] = []
    for gi in range(GLYPHS):
        sx = (gi % GRID) * GLYPH_W
        sy = (gi // GRID) * GLYPH_H

        tile = Image.new("RGB", (GLYPH_W, GLYPH_H))
        tpx = tile.load()
        for y in range(GLYPH_H):
            for x in range(GLYPH_W):
                tpx[x, y] = px[sx + x, sy + y]

        glyph_bytes.append(_tile_to_glyph_bytes(tile))

    _write_mcm_text(glyph_bytes, out_mcm)


def inject_logo(base_mcm: Path, logo_png: Path, out_mcm: Path) -> None:
    """
    Inject a pre-tiled logo PNG into glyph indices 0xA0..0xFF sequentially.

    Logo PNG requirements:
    - Must be RGB (we convert)
    - Must be aligned to 12x18 tiles
    - Must contain exactly 96 tiles total
    Common layout is 16 columns x 6 rows => 192x108 px.
    We don't require 16x6 specifically, only that:
      (width % 12 == 0), (height % 18 == 0), and (tiles == 96).
    """
    glyphs = _read_mcm_text(base_mcm)

    logo = Image.open(logo_png).convert("RGB")
    w, h = logo.size
    if w % GLYPH_W != 0 or h % GLYPH_H != 0:
        raise ValueError(
            f"Logo image must be divisible by {GLYPH_W}x{GLYPH_H}. Got {w}x{h}."
        )

    cols = w // GLYPH_W
    rows = h // GLYPH_H
    tiles = cols * rows
    if tiles != INJECT_COUNT:
        raise ValueError(
            f"Logo must contain exactly {INJECT_COUNT} tiles for A0-FF. "
            f"Got {tiles} tiles ({cols}x{rows}) from {w}x{h}."
        )

    # Slice and overwrite glyphs sequentially
    idx = INJECT_START
    for r in range(rows):
        for c in range(cols):
            x0 = c * GLYPH_W
            y0 = r * GLYPH_H
            tile = logo.crop((x0, y0, x0 + GLYPH_W, y0 + GLYPH_H))
            glyphs[idx] = _tile_to_glyph_bytes(tile)
            idx += 1

    _write_mcm_text(glyphs, out_mcm)


def main() -> None:
    p = argparse.ArgumentParser(
        description="Edit MAX7456 / AT7456E OSD fonts (.mcm)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  mcmedit.py mcm2sheet font.mcm sheet.png
  mcmedit.py sheet2mcm sheet.png font.mcm
  mcmedit.py inject-logo font.mcm logo_288x72.png font_with_logo.mcm
""",
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    # mcm2sheet
    p_a = sub.add_parser(
        "mcm2sheet",
        help="Convert .mcm -> 192x288 PNG sheet",
        description="Extract all 256 glyphs into a 16x16 PNG sheet (12x18 per glyph).",
    )
    p_a.add_argument("mcm", type=Path, metavar="FONT.mcm")
    p_a.add_argument("png", type=Path, metavar="SHEET.png")

    # sheet2mcm
    p_b = sub.add_parser(
        "sheet2mcm",
        help="Convert 192x288 PNG sheet -> .mcm",
        description="Build a full .mcm font from a 192x288 glyph sheet.",
    )
    p_b.add_argument("png", type=Path, metavar="SHEET.png")
    p_b.add_argument("mcm", type=Path, metavar="FONT.mcm")

    # inject-logo
    p_c = sub.add_parser(
        "inject-logo",
        help="Inject pre-tiled logo PNG into glyphs 0xA0–0xFF",
        description="""
Injects a pre-tiled logo into glyph indices 0xA0–0xFF (96 tiles).

example:
  mcmedit.py inject-logo base_font.mcm logo_288x72.png out.mcm
""",
    )
    p_c.add_argument("base_mcm", type=Path, metavar="BASE_FONT.mcm")
    p_c.add_argument("logo_png", type=Path, metavar="LOGO.png")
    p_c.add_argument("out_mcm", type=Path, metavar="OUTPUT.mcm")

    args = p.parse_args()

    # Simple up-front existence checks (user-friendly errors)
    # (We only check inputs, not outputs.)
    if args.cmd == "mcm2sheet":
        if not args.mcm.exists():
            _err(f"Input font not found: {args.mcm}")
        mcm_to_sheet(args.mcm, args.png)
        _ok(f"Wrote {args.png} ({SHEET_W}x{SHEET_H}) from {args.mcm}")

    elif args.cmd == "sheet2mcm":
        if not args.png.exists():
            _err(f"Input sheet not found: {args.png}")
        sheet_to_mcm(args.png, args.mcm)
        _ok(f"Wrote {args.mcm} from {args.png}")

    elif args.cmd == "inject-logo":
        if not args.base_mcm.exists():
            _err(f"Base font not found: {args.base_mcm}")
        if not args.logo_png.exists():
            _err(f"Logo PNG not found: {args.logo_png}")
        inject_logo(args.base_mcm, args.logo_png, args.out_mcm)
        _ok(f"Wrote {args.out_mcm} (logo injected A0–FF)")

    else:
        _err("Unknown command", code=2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except (FileNotFoundError, PermissionError) as e:
        _err(str(e), code=2)
    except (ValueError, OSError) as e:
        # OSError catches PIL image decode errors nicely too.
        _err(str(e), code=2)
    except Exception as e:
        # True “something went sideways” case.
        print(
        f"{RED}FATAL:{RESET} {e.__class__.__name__}: {e}"
        if USE_COLOR else
        f"FATAL: {e.__class__.__name__}: {e}",
        file=sys.stderr
)

