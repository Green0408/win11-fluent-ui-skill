#!/usr/bin/env python3
"""tests/slider_thumb_timing.py —— 滑块内点「放大 / 缩小」的速率与曲线判据

规范（XAML SliderThumbStyle VisualState KeyTime）：
  PointerOver / Pressed = ControlNormalAnimationDuration 250ms
  Normal（移开缩回）    = ControlFastAnimationDuration   167ms
  ⇒ 放大 : 缩小 ≈ 250 : 167 = 1.50
曲线：ControlFastOutSlowIn = cubic-bezier(0,0,0,1)，即 y = 3x^(2/3) − 2x
  ⇒ 80% 进度出现在 42% 时长处（不是线性的 80%！这条最能区分"曲线对不对"
     以及"是不是靠 layout 过渡被取整成 3 级台阶"）

判法：node 那边把两个时长 token 同比例放大 4×（1000 / 668ms）后逐帧截图，
这里用**亚像素覆盖量**量每张图的内点直径，然后：
  1) 80% 进度时刻落在标称时长的 30%~55%（理论 42%）
  2) 放大/缩小到位比值 ∈ [1.30, 1.72]
  3) 过程里至少 4 帧处于中间态、且直径至少 5 个不同取值（平滑度：
     改 width 的写法只有 3 级台阶，这一条会挂）

用法：先 node tests/slider_thumb_timing.js，再 python tests/slider_thumb_timing.py
"""
import json
import os
import sys

import numpy as np
from PIL import Image

TMP = os.path.join(os.environ.get("TEMP", "/tmp"), "shots")
T80_BAND = (0.30, 0.55)      # 理论 0.42


def dot_px(path):
    """取图形正中一列的"蓝覆盖量"（亚像素）：直接数整行会在 12/13/14 之间跳格，
    尾段永远落不到终点 —— 覆盖量法能把 AA 边缘折成小数，才能判曲线。"""
    arr = np.array(Image.open(path).convert("RGB"))
    h, w = arr.shape[:2]
    col = arr[:, w // 2].astype(np.float64)
    blueness = np.clip(col[:, 2] - col[:, 0], 0, None)
    peak = blueness.max()
    if peak <= 0:
        return 0.0
    return float((blueness / peak).sum())


def t_at(rows, frac):
    """首次达到 frac 进度的插值时刻（rows 已按 ts 排序，px 为原始覆盖量）。"""
    v0, v1 = rows[0]["px"], rows[-1]["px"]
    goal = v0 + (v1 - v0) * frac
    for a, b in zip(rows, rows[1:]):
        if (b["px"] - goal) * (v1 - v0) >= 0:
            span = b["px"] - a["px"]
            k = 0 if span == 0 else (goal - a["px"]) / span
            return a["ts"] + k * (b["ts"] - a["ts"])
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
        t80 = t_at(rows, 0.8)
        out[tag] = t80
        vals = [round(r["px"] / dsf, 1) for r in rows]
        print(f"{tag:>3}  80% 进度 {t80:5.0f}ms（标称 {meta[key]}ms → {t80/meta[key]:.2f}，"
              f"理论 0.42）  取值 {len(set(vals))} 级")
        print("     " + " ".join(f"{v:.1f}" for v in vals[:12]))

    for tag, key, label in (("in", "dIn", "放大"), ("out", "dOut", "缩回")):
        lo, hi = T80_BAND[0] * meta[key], T80_BAND[1] * meta[key]
        if not lo <= out[tag] <= hi:
            print(f"FAIL  {label}的 80% 时刻 {out[tag]:.0f}ms 不在 {lo:.0f}~{hi:.0f}ms"
                  f"（标称 {meta[key]}ms；理论 {0.42 * meta[key]:.0f}ms）—— 曲线不是 FastOutSlowIn")
            bad += 1

    ratio = out["in"] / max(out["out"], 1)
    ok = 1.30 <= ratio <= 1.72
    print(f"\n放大/缩小 = {out['in']:.0f} / {out['out']:.0f} = {ratio:.2f}"
          f"（期望 ≈ {meta['dIn'] / meta['dOut']:.2f}）  {'OK' if ok else 'FAIL'}")
    if not ok:
        bad += 1

    mid_in = [r for r in series if r["tag"] == "in" and 12.2 < r["px"] / dsf < 13.9]
    ok2 = len(mid_in) >= 4
    print(f"放大过程中间态 {len(mid_in)} 帧处于 (12,14) 之间（≥4）  {'OK' if ok2 else 'FAIL'}")
    if not ok2:
        bad += 1

    levels = len({round(r["px"] / dsf, 1) for r in series if r["tag"] == "in"})
    ok3 = levels >= 5
    print(f"直径取值 {levels} 级（≥5；改 width 的写法只有 3 级台阶）  {'OK' if ok3 else 'FAIL'}")
    if not ok3:
        bad += 1

    print("\n结果：" + ("曲线与速率都符合（进 250 / 出 167，FastOutSlowIn）" if bad == 0 else f"{bad} 项不符"))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
