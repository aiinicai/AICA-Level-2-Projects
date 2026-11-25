"""Zero-dependency pure-Python ISO/IEC 18004 QR Code generator (Byte mode, EC Level M).

Generates crisp SVG strings (and optional PIL Images) for printable asset QR stickers
without requiring external QR packages.
"""

from __future__ import annotations

from typing import Sequence

# GF(256) tables for QR Reed-Solomon (primitive polynomial 0x11d)
_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _rs_generator_poly(degree: int) -> list[int]:
    poly = [1]
    for i in range(degree):
        factor = [1, _EXP[i]]
        nxt = [0] * (len(poly) + 1)
        for j, a in enumerate(poly):
            for k, b in enumerate(factor):
                nxt[j + k] ^= _gf_mul(a, b)
        poly = nxt
    return poly


def _rs_encode(data: Sequence[int], ec_count: int) -> list[int]:
    gen = _rs_generator_poly(ec_count)
    res = list(data) + [0] * ec_count
    for i in range(len(data)):
        coef = res[i]
        if coef != 0:
            for j in range(1, len(gen)):
                res[i + j] ^= _gf_mul(gen[j], coef)
    return res[len(data):]


# Version specs for Error Correction Level M:
# version: (total_data_codewords, ec_per_block, group1_blocks, group1_data, group2_blocks, group2_data, align_centers)
_VERSION_M_SPECS: dict[int, tuple[int, int, int, int, int, int, list[int]]] = {
    1: (16, 10, 1, 16, 0, 0, []),
    2: (28, 16, 1, 28, 0, 0, [6, 18]),
    3: (44, 26, 1, 44, 0, 0, [6, 22]),
    4: (64, 18, 2, 32, 0, 0, [6, 26]),
    5: (86, 24, 2, 43, 0, 0, [6, 30]),
    6: (108, 16, 4, 27, 0, 0, [6, 34]),
    7: (124, 18, 4, 31, 0, 0, [6, 22, 38]),
    8: (154, 22, 2, 38, 2, 39, [6, 24, 42]),
    9: (182, 22, 3, 36, 2, 37, [6, 26, 46]),
    10: (216, 26, 4, 43, 1, 44, [6, 28, 50]),
}

# Precomputed 15-bit format strings for EC Level M (00) + mask 0..7 (with BCH + 0x5412 mask)
_FORMAT_BITS_M = [
    0x5412,
    0x5125,
    0x5E7C,
    0x5B4B,
    0x45F9,
    0x40CE,
    0x4F97,
    0x4AA0,
]

# Precomputed 18-bit version info for versions 7..10
_VERSION_BITS = {
    7: 0x07C94,
    8: 0x085BC,
    9: 0x09A99,
    10: 0x0A4D3,
}


def _select_version(byte_len: int) -> int:
    for v in range(1, 11):
        cap = _VERSION_M_SPECS[v][0]
        header_bits = 4 + (8 if v <= 9 else 16)
        max_bytes = (cap * 8 - header_bits) // 8
        if byte_len <= max_bytes:
            return v
    raise ValueError("QR payload too long (max ~213 UTF-8 bytes supported).")


def _encode_data_codewords(payload: bytes, version: int) -> list[int]:
    total_data_cw = _VERSION_M_SPECS[version][0]
    bits: list[int] = []

    def push_bits(val: int, count: int) -> None:
        for shift in range(count - 1, -1, -1):
            bits.append((val >> shift) & 1)

    # Byte mode indicator: 0100
    push_bits(0b0100, 4)
    push_bits(len(payload), 8 if version <= 9 else 16)
    for b in payload:
        push_bits(b, 8)

    # Terminator up to 4 zero bits
    max_bits = total_data_cw * 8
    term = min(4, max_bits - len(bits))
    bits.extend([0] * term)
    # Pad to byte boundary
    while len(bits) % 8 != 0:
        bits.append(0)

    codewords: list[int] = []
    for i in range(0, len(bits), 8):
        byte_val = 0
        for b in bits[i : i + 8]:
            byte_val = (byte_val << 1) | b
        codewords.append(byte_val)

    pad_cycle = (0xEC, 0x11)
    idx = 0
    while len(codewords) < total_data_cw:
        codewords.append(pad_cycle[idx % 2])
        idx += 1
    return codewords


def _interleave_blocks(codewords: list[int], version: int) -> list[int]:
    _, ec_len, g1_cnt, g1_len, g2_cnt, g2_len, _ = _VERSION_M_SPECS[version]
    data_blocks: list[list[int]] = []
    ec_blocks: list[list[int]] = []
    offset = 0
    for _ in range(g1_cnt):
        blk = codewords[offset : offset + g1_len]
        offset += g1_len
        data_blocks.append(blk)
        ec_blocks.append(_rs_encode(blk, ec_len))
    for _ in range(g2_cnt):
        blk = codewords[offset : offset + g2_len]
        offset += g2_len
        data_blocks.append(blk)
        ec_blocks.append(_rs_encode(blk, ec_len))

    result: list[int] = []
    max_data = max(len(b) for b in data_blocks)
    for i in range(max_data):
        for blk in data_blocks:
            if i < len(blk):
                result.append(blk[i])
    for i in range(ec_len):
        for blk in ec_blocks:
            result.append(blk[i])
    return result


def _build_matrix(text: str) -> list[list[int]]:
    payload = text.encode("utf-8")
    version = _select_version(len(payload))
    size = 17 + 4 * version
    matrix = [[0] * size for _ in range(size)]
    is_func = [[False] * size for _ in range(size)]

    def set_func(r: int, c: int, val: int) -> None:
        matrix[r][c] = val
        is_func[r][c] = True

    def place_finder(top: int, left: int) -> None:
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = top + dr, left + dc
                if 0 <= r < size and 0 <= c < size:
                    in_outer = 0 <= dr <= 6 and 0 <= dc <= 6
                    on_border = dr in (0, 6) or dc in (0, 6)
                    in_center = 2 <= dr <= 4 and 2 <= dc <= 4
                    set_func(r, c, 1 if (in_outer and (on_border or in_center)) else 0)

    place_finder(0, 0)
    place_finder(0, size - 7)
    place_finder(size - 7, 0)

    # Alignment patterns
    centers = _VERSION_M_SPECS[version][6]
    for r0 in centers:
        for c0 in centers:
            if is_func[r0][c0]:
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    val = 1 if max(abs(dr), abs(dc)) in (0, 2) else 0
                    set_func(r0 + dr, c0 + dc, val)

    # Timing patterns
    for i in range(8, size - 8):
        if not is_func[6][i]:
            set_func(6, i, 1 if i % 2 == 0 else 0)
        if not is_func[i][6]:
            set_func(i, 6, 1 if i % 2 == 0 else 0)

    # Dark module
    set_func(size - 8, 8, 1)

    # Reserve format info cells
    for i in range(9):
        if i != 6:
            is_func[8][i] = True
            is_func[i][8] = True
    for i in range(8):
        is_func[8][size - 1 - i] = True
        is_func[size - 1 - i][8] = True

    # Version info for v >= 7
    if version >= 7:
        vbits = _VERSION_BITS[version]
        for i in range(18):
            bit = (vbits >> i) & 1
            r = i // 3
            c = size - 11 + (i % 3)
            set_func(r, c, bit)
            set_func(c, r, bit)

    # Encode and place data bits in zigzag
    codewords = _encode_data_codewords(payload, version)
    stream = _interleave_blocks(codewords, version)
    bit_stream: list[int] = []
    for cw in stream:
        for s in range(7, -1, -1):
            bit_stream.append((cw >> s) & 1)

    bit_idx = 0
    upward = True
    col = size - 1
    while col > 0:
        if col == 6:
            col -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for r in rows:
            for dc in (0, -1):
                c = col + dc
                if not is_func[r][c]:
                    matrix[r][c] = bit_stream[bit_idx] if bit_idx < len(bit_stream) else 0
                    bit_idx += 1
        col -= 2
        upward = not upward

    # Evaluate all 8 mask patterns and choose lowest penalty
    mask_fns = [
        lambda r, c: (r + c) % 2 == 0,
        lambda r, c: r % 2 == 0,
        lambda r, c: c % 3 == 0,
        lambda r, c: (r + c) % 3 == 0,
        lambda r, c: ((r // 2) + (c // 3)) % 2 == 0,
        lambda r, c: ((r * c) % 2) + ((r * c) % 3) == 0,
        lambda r, c: (((r * c) % 2) + ((r * c) % 3)) % 2 == 0,
        lambda r, c: (((r + c) % 2) + ((r * c) % 3)) % 2 == 0,
    ]

    def apply_format(grid: list[list[int]], mask_id: int) -> None:
        fb = _FORMAT_BITS_M[mask_id]
        for i in range(6):
            grid[8][i] = (fb >> (14 - i)) & 1
        grid[8][7] = (fb >> 8) & 1
        grid[8][8] = (fb >> 7) & 1
        grid[7][8] = (fb >> 6) & 1
        for i in range(6):
            grid[5 - i][8] = (fb >> (5 - i)) & 1

        for i in range(8):
            grid[8][size - 1 - i] = (fb >> i) & 1
        for i in range(7):
            grid[size - 1 - i][8] = (fb >> (14 - i)) & 1

    def penalty(grid: list[list[int]]) -> int:
        score = 0
        # Rule 1: runs of 5+
        for r in range(size):
            run = 1
            for c in range(1, size):
                if grid[r][c] == grid[r][c - 1]:
                    run += 1
                else:
                    if run >= 5:
                        score += 3 + (run - 5)
                    run = 1
            if run >= 5:
                score += 3 + (run - 5)
        for c in range(size):
            run = 1
            for r in range(1, size):
                if grid[r][c] == grid[r - 1][c]:
                    run += 1
                else:
                    if run >= 5:
                        score += 3 + (run - 5)
                    run = 1
            if run >= 5:
                score += 3 + (run - 5)
        # Rule 2: 2x2 blocks
        for r in range(size - 1):
            for c in range(size - 1):
                v = grid[r][c]
                if v == grid[r][c + 1] == grid[r + 1][c] == grid[r + 1][c + 1]:
                    score += 3
        return score

    best_grid: list[list[int]] | None = None
    best_score = 10**9
    for mask_id, fn in enumerate(mask_fns):
        cand = [row[:] for row in matrix]
        for r in range(size):
            for c in range(size):
                if not is_func[r][c] and fn(r, c):
                    cand[r][c] ^= 1
        apply_format(cand, mask_id)
        sc = penalty(cand)
        if sc < best_score:
            best_score = sc
            best_grid = cand

    return best_grid or matrix


def generate_qr_svg(text: str, module_size: int = 6, border: int = 4) -> str:
    """Return a crisp, self-contained SVG string encoding `text` as a QR code."""
    grid = _build_matrix(text)
    size = len(grid)
    total = (size + 2 * border) * module_size
    rects: list[str] = []
    for r, row in enumerate(grid):
        for c, val in enumerate(row):
            if val:
                x = (c + border) * module_size
                y = (r + border) * module_size
                rects.append(f'<rect x="{x}" y="{y}" width="{module_size}" height="{module_size}"/>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}" '
        f'width="{total}" height="{total}" shape-rendering="crispEdges">'
        f'<rect width="100%" height="100%" fill="#ffffff"/>'
        f'<g fill="#0f172a">{"".join(rects)}</g>'
        f"</svg>"
    )


def generate_qr_matrix(text: str) -> list[list[int]]:
    """Return raw 0/1 QR matrix (useful for raster rendering or verification)."""
    return _build_matrix(text)
