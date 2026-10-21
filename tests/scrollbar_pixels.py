#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scrollbar_pixels.py —— 从截图像素里量滚动条的实际宽度与颜色

为什么需要它：`::-webkit-scrollbar` 是浏览器内部伪元素，`getComputedStyle(el, '::-webkit-scrollbar-thumb')`
在 Chromium 里拿不到任何东西；而 cdp_check 又以 `--hide-scrollbars` 启动、占宽恒为 0。
所以「到底画出来多粗、什么颜色」只能靠截图像素说话。

用法：
    python tests/scrollbar_pixels.py shot.png --scan row --y 300 --edge right
    python tests/scrollbar_pixels.py shot.png --scan col --x 60 --edge bottom
    python tests/scrollbar_pixels.py shot.png --y 300 --expect-width 6 --expect-min 140

判定：
    · 找「与相邻背景明显不同」的连续色带（默认在贴边 ~16px 内找）
    · --expect-width 允许 ±1（抗次像素渲染）
    · --expect-min 是色带相对背景的最小亮度差，用来确认「看得见」
退出码：0 = 符合；1 = 不符
"""
import argparse
import sys

import numpy as np
from PIL import Image


def luminance(rgb):
    r, g, b = [float(v) for v in rgb[:3]]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def bands(vals, bg, min_delta):
    """把一维颜色序列里「与背景差异 > min_delta」的连续段找出来"""
    out, start = [], None
    for i, v in enumerate(vals):
        diff = abs(luminance(v) - luminance(bg))
        if diff > min_delta:
            if start is None:
                start = i
        else:
            if start is not None:
                out.append((start, i - 1))
                start = None
    if start is not None:
        out.append((start, len(vals) - 1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png")
    ap.add_argument("--scan", choices=["row", "col"], default="row")
    ap.add_argument("--y", type=int, default=None, help="row 扫描的行号（默认取图高 1/3）")
    ap.add_argument("--x", type=int, default=None, help="col 扫描的列号（默认取图宽 1/2）")
    ap.add_argument("--edge", choices=["right", "left", "bottom", "top"], default="right",
                    help="从哪一侧往内找（另一侧作背景参考）")
    ap.add_argument("--window", type=int, default=20, help="贴边搜索窗口像素数")
    ap.add_argument("--min-delta", type=float, default=12.0, help="与背景的亮度差阈值")
    ap.add_argument("--expect-width", type=int, default=None)
    ap.add_argument("--expect-min", type=float, default=None, help="色带与背景的最小亮度差")
    ap.add_argument("--ignore-faint", type=float, default=30.0,
                    help="亮度差低于此值的色带视为边缘/抗锯齿，不参与判定（默认 30）")
    args = ap.parse_args()

    arr = np.array(Image.open(args.png).convert("RGB")).astype(int)
    h, w, _ = arr.shape

    if args.scan == "row":
        y = args.y if args.y is not None else h // 3
        line = arr[y]
        if args.edge in ("right", "left"):
            sl = slice(w - args.window, w) if args.edge == "right" else slice(0, args.window)
            vals, offset = line[sl], (w - args.window if args.edge == "right" else 0)
        else:
            print("row 扫描只支持 --edge right/left")
            return 1
    else:
        x = args.x if args.x is not None else w // 2
        line = arr[:, x]
        if args.edge in ("bottom", "top"):
            sl = slice(h - args.window, h) if args.edge == "bottom" else slice(0, args.window)
            vals, offset = line[sl], (h - args.window if args.edge == "bottom" else 0)
        else:
            print("col 扫描只支持 --edge bottom/top")
            return 1

    # 背景 = 窗口里出现次数最多的颜色（滚动条只占少数几列）
    colors, counts = np.unique(vals.reshape(-1, 3), axis=0, return_counts=True)
    bg = colors[counts.argmax()]
    segs = bands(vals, bg, args.min_delta)

    print(f"图 {w}×{h}  扫描 {'row y=' + str(y) if args.scan == 'row' else 'col x=' + str(x)}  "
          f"窗口 {args.window}px  背景 rgb{tuple(int(v) for v in bg)}")
    if not segs:
        print("FAIL   窗口里没找到任何色带 —— 滚动条没画出来（或颜色与背景无差别）")
        return 1

    bad = 0
    for s, e in segs:
        width = e - s + 1
        mid = vals[(s + e) // 2]
        delta = abs(luminance(mid) - luminance(bg))
        pos = offset + s
        if delta < args.ignore_faint:
            print(f"  色带 起={pos} 宽={width}px  rgb{tuple(int(v) for v in mid)}  "
                  f"亮度差={delta:.0f}  忽略（边框/抗锯齿）")
            continue
        ok = True
        if args.expect_width is not None and abs(width - args.expect_width) > 1:
            ok = False
        if args.expect_min is not None and delta < args.expect_min:
            ok = False
        if not ok:
            bad += 1
        print(f"  色带 起={pos} 宽={width}px  颜色 rgb{tuple(int(v) for v in mid)}  "
              f"与背景亮度差={delta:.0f}  {'OK' if ok else 'FAIL'}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
