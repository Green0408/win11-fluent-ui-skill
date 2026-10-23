#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nav_strip.py —— 把 tests/nav_shots.js 的四张截图拼成对照图 tests/nav-responsive.png

用法： python tests/nav_strip.py <截图目录>
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
src = Path(sys.argv[1] if len(sys.argv) > 1 else HERE)
shots = [("1200px 展开 240", "nav-1200.png"), ("800px 紧凑 48", "nav-800.png"),
         ("500px 收起 + 汉堡", "nav-500-0.png"), ("500px 点汉堡浮出", "nav-500-1.png")]

ims = [(label, Image.open(src / name).convert("RGB")) for label, name in shots]
# 统一高度，宽度按原比例缩放（1200 那张缩到 560 以内）
TARGET_H = 460
scaled = []
for label, im in ims:
    w = round(im.width * TARGET_H / im.height)
    scaled.append((label, im.resize((w, TARGET_H), Image.LANCZOS)))

pad, lab = 14, 26
W = sum(im.width for _, im in scaled) + pad * (len(scaled) + 1)
canvas = Image.new("RGB", (W, TARGET_H + lab + pad * 2), (32, 32, 34))
draw = ImageDraw.Draw(canvas)
x = pad
for label, im in scaled:
    canvas.paste(im, (x, pad + lab))
    draw.text((x + 2, pad + 7), label, fill=(236, 236, 236))
    x += im.width + pad

out = HERE / "nav-responsive.png"
canvas.save(out)
print(f"saved {out}  {canvas.size[0]}x{canvas.size[1]}")
