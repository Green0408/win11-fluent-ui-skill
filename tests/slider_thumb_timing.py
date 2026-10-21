#!/usr/bin/env python3
"""tests/slider_thumb_timing.py —— 滑块内点「放大 / 缩小」的速率判据

规范（XAML SliderThumbStyle VisualState KeyTime）：
  PointerOver / Pressed = ControlNormalAnimationDuration 250ms
  Normal（移开缩回）    = ControlFastAnimationDuration   167ms
  ⇒ 放大 : 缩小 ≈ 250 : 167 = 1.50

判法：node 那边把两个时长 token 同比例放大 4×（1000 / 668ms）后逐帧截图，
这里量每张图的内点直径，找出各自"到位"的时刻，比较：
  1) 放大到位落在标称时长的 50%~95%、缩回同理（这条曲线尾段极长：
     y=3x^(2/3)-2x，视觉上 ~69% 时长就走完 96%，实测正是 691/1000 与 465/668）
  2) 两者比值 ∈ [1.30, 1.72] —— 只要有人把两个状态写成同一个时长，这里立刻不平
  3) 中间至少有 2 帧处于 (12, 14) 之间 —— 证明是动画而不是跳变

用法：先 node tests/slider_thumb_timing.js，再 python tests/slider_thumb_timing.py
"""
import json
import os
import sys

import numpy as np
from PIL import Image

TMP = os.path.join(os.environ.get("TEMP", "/tmp"), "shots")
BAND = (0.50, 0.95)


def dot_px(path):
    """取图形正中一列的"蓝覆盖量"（亚像素）：直接数整行会在 12/13/14 之间跳格，
    尾段永远落不到终点值 —— 覆盖量法能把 AA 边缘折成小数，才能判到位时刻。"""
    arr = np.array(Image.open(path).convert("RGB"))
    h, w = arr.shape[:2]
    col = arr[:, w // 2].astype(np.float64)
    blueness = np.clip(col[:, 2] - col[:, 0], 0, None)
    peak = blueness.max()
    if peak <= 0:
        return 0.0
    return float((blueness / peak).sum())


def settle_time(rows, final_px, dsf, eps=1.0):
    """第一次达到终值（±eps CSS px）且之后不再变化 → 返回该帧的时刻。"""
    for k, r in enumerate(rows):
        v = r["px"] / dsf
        if abs(v - final_px) <= eps and all(abs(x["px"] / dsf - final_px) <= eps for x in rows[k:]):
            return r["ts"]
    return rows[-1]["ts"]


def main():
    f = os.path.join(TMP, "timing.json")
    if not os.path.exists(f):
        print("FAIL  缺 timing.json（先跑 node tests/slider_thumb_timing.js）")
        return 1
    data = json.load(open(f))
    meta, series = data["meta"], data["series"]
    dsf = Image.open(series[0]["f"]).width / meta["clipCss"]   # 截图 = 设备比 × clip.scale
    for r in series:
        r["px"] = dot_px(r["f"])

    bad = 0
    out = {}
    for tag, key in (("in", "dIn"), ("out", "dOut")):
        rows = sorted([r for r in series if r["tag"] == tag], key=lambda r: r["ts"])
        final = rows[-1]["px"] / dsf
        t = settle_time(rows, final, dsf, eps=0.3)
        out[tag] = t
        print(f"{tag:>3}  终值 {final:5.1f}px  到位 {t:5.0f}ms（期望 {meta[key]}ms）  "
              + " ".join(f"{r['px'] / dsf:.1f}" for r in rows[:10]))

    for tag, key, label in (("in", "dIn", "放大"), ("out", "dOut", "缩回")):
        lo, hi = BAND[0] * meta[key], BAND[1] * meta[key]
        if not lo <= out[tag] <= hi:
            print(f"FAIL  {label}到位 {out[tag]:.0f}ms 不在 {lo:.0f}~{hi:.0f}ms（标称 {meta[key]}ms）")
            bad += 1

    ratio = out["in"] / max(out["out"], 1)
    ok = 1.30 <= ratio <= 1.72
    print(f"\n放大/缩小 = {out['in']:.0f} / {out['out']:.0f} = {ratio:.2f}"
          f"（期望 ≈ {meta['dIn'] / meta['dOut']:.2f}）  {'OK' if ok else 'FAIL'}")
    if not ok:
        bad += 1

    mid_in = [r for r in series if r["tag"] == "in" and 12.2 < r["px"] / dsf < 13.9]
    ok2 = len(mid_in) >= 2
    print(f"放大过程中间态 {len(mid_in)} 帧处于 (12,14) 之间  {'OK' if ok2 else 'FAIL'}")
    if not ok2:
        bad += 1

    print("\n结果：" + ("速率符合 250ms 进 / 167ms 出" if bad == 0 else f"{bad} 项不符"))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
