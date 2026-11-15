"""滑块拼图验证码：品牌化出题器。

背景使用产品页面截图，图块使用品牌 Logo；缺口横坐标只保存在服务端 Redis，
前端拖动到正确位置后由服务端校验。
"""

from __future__ import annotations

import base64
import random
from pathlib import Path

WIDTH = 320
HEIGHT = 160
PIECE = 48
KNOB = 7
PIECE_WIDTH = PIECE + KNOB
RADIUS = 8

_ASSET_DIR = Path(__file__).parent / "assets"


def _read_asset_data_uri(name: str, mime: str) -> str:
    path = _ASSET_DIR / name
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


LOGO_IMAGE = _read_asset_data_uri("logo.svg", "image/svg+xml")


BG_PALETTES = [
    ("#1B2140", "#2A1F45", "#0E2233", "#4F6BFF", "#6D5BFF"),
    ("#0B1826", "#1A2036", "#08111C", "#0EA5E9", "#6D5BFF"),
    ("#241A35", "#141B2E", "#0B0F1A", "#A855F7", "#4F6BFF"),
    ("#11231F", "#10202B", "#0A1216", "#22C55E", "#0EA5E9"),
]


def _random_background(rnd: random.Random) -> str:
    """按验证码 key 随机生成品牌化抽象背景。"""
    base1, base2, base3, accent1, accent2 = rnd.choice(BG_PALETTES)
    angle = rnd.choice([(0, 0, 1, 1), (0, 1, 1, 0), (0, 0, 1, 0)])
    parts = [
        "<defs>",
        f'<linearGradient id="bg" x1="{angle[0]}" y1="{angle[1]}" x2="{angle[2]}" y2="{angle[3]}">'
        f'<stop offset="0" stop-color="{base1}"/>'
        f'<stop offset="0.55" stop-color="{base2}"/>'
        f'<stop offset="1" stop-color="{base3}"/>'
        "</linearGradient>",
        '<filter id="blob"><feGaussianBlur stdDeviation="9"/></filter>',
        "</defs>",
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="url(#bg)"/>',
    ]
    for _ in range(rnd.randint(7, 11)):
        color = rnd.choice([accent1, accent2, "#ffffff"])
        parts.append(
            f'<circle cx="{rnd.randint(-20, WIDTH + 20)}" cy="{rnd.randint(-20, HEIGHT + 20)}" '
            f'r="{rnd.randint(24, 78)}" fill="{color}" '
            f'opacity="{round(rnd.uniform(0.1, 0.3), 2)}" filter="url(#blob)"/>'
        )
    for _ in range(3):
        parts.append(
            f'<circle cx="{rnd.randint(20, WIDTH - 20)}" cy="{rnd.randint(10, HEIGHT - 10)}" '
            f'r="{rnd.randint(22, 58)}" fill="none" stroke="#ffffff" '
            f'stroke-opacity="{round(rnd.uniform(0.08, 0.18), 2)}"/>'
        )
    parts.append(
        f'<path d="M0 {rnd.randint(40, HEIGHT - 40)} C {WIDTH // 3} {rnd.randint(0, HEIGHT)}, '
        f'{WIDTH * 2 // 3} {rnd.randint(0, HEIGHT)}, {WIDTH} {rnd.randint(30, HEIGHT - 30)}" '
        'fill="none" stroke="#ffffff" stroke-opacity="0.12"/>'
    )
    return "".join(parts)


def _svg_data(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode()


def _fallback_background() -> str:
    return '<rect width="320" height="160" fill="#1b2140"/><circle cx="250" cy="50" r="70" fill="#4f6bff" opacity="0.3"/><circle cx="80" cy="120" r="60" fill="#6d5bff" opacity="0.28"/>'


def build_puzzle(key: str) -> dict:
    """返回背景、图块与缺口坐标；target_x 写入 Redis，不下发前端。"""
    rnd = random.Random(key)
    target_x = rnd.randint(80, WIDTH - PIECE_WIDTH - 16)
    target_y = rnd.randint(12, HEIGHT - PIECE - 12)

    bg_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}">'
        f"{_random_background(rnd)}"
        f'<rect x="{target_x}" y="{target_y}" width="{PIECE}" height="{PIECE}" '
        f'rx="{RADIUS}" fill="#080a10" opacity="0.55"/>'
        f'<circle cx="{target_x + PIECE}" cy="{target_y + PIECE // 2}" r="{KNOB}" '
        f'fill="#080a10" opacity="0.55"/>'
        f'<rect x="{target_x}" y="{target_y}" width="{PIECE}" height="{PIECE}" '
        f'rx="{RADIUS}" fill="none" stroke="#ffffff" stroke-opacity="0.6"/>'
        f'<circle cx="{target_x + PIECE}" cy="{target_y + PIECE // 2}" r="{KNOB}" '
        f'fill="none" stroke="#ffffff" stroke-opacity="0.6"/>'
        "</svg>"
    )

    piece_content = (
        f'<image href="{LOGO_IMAGE}" x="4" y="4" width="{PIECE - 8}" height="{PIECE - 8}" preserveAspectRatio="xMidYMid meet"/>' if LOGO_IMAGE else '<rect width="48" height="48" fill="#4f6bff"/>'
    )
    piece_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PIECE_WIDTH}" height="{PIECE}" '
        f'viewBox="0 0 {PIECE_WIDTH} {PIECE}">'
        "<defs>"
        '<clipPath id="piece">'
        f'<rect width="{PIECE}" height="{PIECE}" rx="{RADIUS}"/>'
        f'<circle cx="{PIECE}" cy="{PIECE // 2}" r="{KNOB}"/>'
        "</clipPath>"
        "</defs>"
        '<g clip-path="url(#piece)">'
        '<rect width="48" height="48" fill="#141824"/>'
        f"{piece_content}"
        "</g>"
        f'<rect x="0.5" y="0.5" width="{PIECE - 1}" height="{PIECE - 1}" rx="{RADIUS}" '
        'fill="none" stroke="#ffffff" stroke-opacity="0.85"/>'
        f'<circle cx="{PIECE}" cy="{PIECE // 2}" r="{KNOB}" fill="none" '
        'stroke="#ffffff" stroke-opacity="0.85"/>'
        "</svg>"
    )

    return {
        "target_x": target_x,
        "piece_y": target_y,
        "piece_width": PIECE_WIDTH,
        "piece_height": PIECE,
        "bg_width": WIDTH,
        "bg_height": HEIGHT,
        "img_base": _svg_data(bg_svg),
        "piece_base": _svg_data(piece_svg),
    }
