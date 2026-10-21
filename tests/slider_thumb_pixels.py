#!/usr/bin/env python3
"""tests/slider_thumb_pixels.py —— 滑块 thumb 三态的像素判据

要判的事（用户原话）：**外框尺寸三态恒定，只有蓝色内点变大/变小**。
XAML SliderThumbStyle 是两层：Border（ControlSolidFill 实体盘）+ Ellipse（accent 内点），
VisualState 只对 Ellipse 做 ScaleTransform（0.86 / 1.167 / 0.71 → 12 / 14 / 10）。

为什么必须看像素：`::-webkit-slider-thumb` 是伪元素，`getComputedStyle(el, "::-webkit-slider-thumb")`
在 Chromium 里拿不到计算样式；而且"外框会不会跟着变大"是绘制结果，不是任何可读的声明。

用法：
  node tests/slider_thumb_shots.js          # 先出三张图（rest/hover/pressed）
  python tests/slider_thumb_pixels.py --dsf 2
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

TMP = os.path.join(os.environ.get("TEMP", "/tmp"), "shots")
EXPECT = {          # CSS px
    "rest":    {"puck": 20.0, "dot": 12.0},
    "hover":   {"puck": 20.0, "dot": 14.0},
    "pressed": {"puck": 20.0, "dot": 10.0},
}
TOL = 1.0


def profile(arr):
    """取图形正中的一列：外框 = 与背景差异显著的连续段；内点 = 蓝色段。"""
    h, w = arr.shape[0], arr.shape[1]
    col = arr[:, w // 2].astype(np.int16)
    bg = arr[2, w // 2].astype(np.int16)
    diff = np.abs(col - bg).max(axis=1)
    on = diff > 8                      # 外框（含内点）
    blue = (col[:, 2] - col[:, 0] > 40) & (col[:, 2] > 90)
    return int(on.sum()), int(blue.sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsf", type=float, default=0,
                    help="每 CSS px 的像素数；0 = 按图幅宽 / --clip-css 自动推断")
    ap.add_argument("--clip-css", type=float, default=32.0)
    args = ap.parse_args()

    bad = 0
    print(f"{'态':<8}{'外框':>8}{'内点':>8}   期望(外框/内点)   （边缘 AA 会少吃 ~0.5px，容差 ±1）")
    for state, exp in EXPECT.items():
        f = os.path.join(TMP, f"slider-{state}.png")
        if not os.path.exists(f):
            print(f"FAIL  缺图 {f}（先跑 node tests/slider_thumb_shots.js）")
            bad += 1
            continue
        arr = np.array(Image.open(f).convert("RGB"))
        dsf = args.dsf or arr.shape[1] / args.clip_css
        puck_px, dot_px = profile(arr)
        puck, dot = puck_px / dsf, dot_px / dsf
        ok = abs(puck - exp["puck"]) <= TOL and abs(dot - exp["dot"]) <= TOL
        print(f"{state:<8}{puck:>7.1f}px{dot:>7.1f}px   "
              f"{exp['puck']:.0f} / {exp['dot']:.0f}   {'OK' if ok else 'FAIL'}")
        if not ok:
            bad += 1

    # 过渡有没有"中间态"：慢放条（2400ms）取两个时刻 —— 跳变的话第一张就已经是 14
    slow = [os.path.join(TMP, "slider-slow-a.png"), os.path.join(TMP, "slider-slow-b.png")]
    if all(os.path.exists(f) for f in slow):
        vals = []
        for f in slow:
            arr = np.array(Image.open(f).convert("RGB"))
            dsf = args.dsf or arr.shape[1] / args.clip_css
            _, dot_px = profile(arr)
            vals.append(dot_px / dsf)
        ok = 12.3 < vals[0] < 13.9 and vals[1] > vals[0]
        print(f"慢放（2400ms）  {vals[0]:>6.1f} → {vals[1]:>6.1f}px   中间态   {'OK' if ok else 'FAIL'}")
        if not ok:
            bad += 1

    if bad == 0:
        print("\n结果：外框三态恒 20px，内点 12 → 14 → 10（与模板的 0.86 / 1.167 / 0.71 一致）")
    else:
        print(f"\n结果：{bad} 项不符")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
