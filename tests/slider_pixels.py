#!/usr/bin/env python3
"""tests/slider_pixels.py —— 滑块「已填充段」的像素级验证

先看清楚一个物理事实（否则判据会立错）：
  thumb 外圈是 4px 的实色环（SliderOuterThumbBackground），它画在轨道之上。
  所以填充段的**真实末端**在靠近 thumb 时是不可见的：可见末端最多到 `thumb 左缘 - 环宽`。
  => 「填充宽到底是不是 6 + p×(W-12)」无法用像素判，只能靠 CDP 读渐变解析后的 px 停点
     （tests/cdp_check.js 的「填充宽 calc 解析」那条）。
  => 像素层能判、也值得判的是：**有没有填充、从哪起算、有没有贴到 thumb、比例是否生效**。

用法：
  python tests/slider_pixels.py shot.png --pcts 0.3,1
  （pcts 按图面自上而下对应检测到的填充段，用于打印对照）
"""
import argparse
import sys

import numpy as np
from PIL import Image


def accent_mask(arr):
    """accent 蓝：蓝通道显著高于红通道。灰轨道/白字/白底/暗色都不命中。"""
    a = arr.astype(np.int16)
    return (a[:, :, 2] - a[:, :, 0] > 40) & (a[:, :, 2] > 90)


def runs_of(row, min_len=5):
    out, start = [], None
    for x, v in enumerate(row):
        if v and start is None:
            start = x
        elif not v and start is not None:
            if x - start >= min_len:
                out.append((start, x - 1))
            start = None
    if start is not None and len(row) - start >= min_len:
        out.append((start, len(row) - 1))
    return out


def scan_rows(mask, min_fill=80):
    """逐行找「填充段 + 紧随其后的 thumb 段」。返回 [{y, fill_s, fill_e, thumb_s, thumb_e}]"""
    hits = []
    for y in range(mask.shape[0]):
        rs = runs_of(mask[y])
        if not rs:
            continue
        fill = max(rs, key=lambda r: r[1] - r[0])
        if fill[1] - fill[0] + 1 < min_fill:
            continue
        thumb = None
        for r in rs:
            if r[0] > fill[1] and 2 <= r[0] - fill[1] - 1 <= 16 and 8 <= r[1] - r[0] + 1 <= 64:
                thumb = r
        hits.append({"y": y, "fill_s": fill[0], "fill_e": fill[1],
                     "thumb_s": thumb[0] if thumb else None, "thumb_e": thumb[1] if thumb else None})
    return hits


def group(hits, gap=20):
    """按纵向邻近合并成滑块；同一滑块的填充起点、thumb 位置应稳定。"""
    out, cur = [], None
    for h in sorted(hits, key=lambda d: d["y"]):
        if cur and h["y"] - cur["y1"] <= gap and abs(h["fill_s"] - cur["fill_s"]) <= 3:
            cur["y1"] = h["y"]
            cur["fills"].append((h["fill_s"], h["fill_e"]))
            if h["thumb_s"] is not None:
                cur["thumbs"].append((h["thumb_s"], h["thumb_e"]))
        else:
            if cur:
                out.append(cur)
            cur = {"y0": h["y"], "y1": h["y"], "fill_s": h["fill_s"],
                   "fills": [(h["fill_s"], h["fill_e"])],
                   "thumbs": [] if h["thumb_s"] is None else [(h["thumb_s"], h["thumb_e"])]}
    if cur:
        out.append(cur)
    for b in out:
        b["fill_s"] = int(np.median([f[0] for f in b["fills"]]))
        b["fill_e"] = int(np.median([f[1] for f in b["fills"]]))
        b["thumb"] = (int(np.median([t[0] for t in b["thumbs"]])),
                      int(np.median([t[1] for t in b["thumbs"]]))) if b["thumbs"] else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png")
    ap.add_argument("--pcts", default="0.3,1", help="按图面自上而下对应的值比例，仅用于打对照表")
    ap.add_argument("--tolerance", type=float, default=2.0, help="起点一致性允许误差（设备像素）")
    args = ap.parse_args()

    arr = np.array(Image.open(args.png).convert("RGB"))
    all_bands = group(scan_rows(accent_mask(arr)))
    # 页面上还有别的 accent 色块（主按钮、勾选框、开关轨道），它们认不出「环 + thumb」的结构
    bands = [b for b in all_bands if b["thumb"] is not None]
    pcts = [float(x) for x in args.pcts.split(",")]
    print(f"图面 {arr.shape[1]}×{arr.shape[0]}：accent 色带 {len(all_bands)} 条，"
          f"其中带 thumb 结构的填充段 {len(bands)} 条（其余非滑块，已忽略）")
    if not bands:
        print("FAIL   一条填充段都没有 —— 轨道仍是整条单色（渐变没生效或 --fl-slider-pct 未写入）")
        return 1
    if len(bands) < len(pcts):
        print(f"FAIL   只认出 {len(bands)} 条填充段，期望 {len(pcts)} 条（pct=0 的滑块本来就没有填充，"
              f"若页面里它就是最小可判据，请把它从 --pcts 里去掉）")

    bad = 0
    print(f"\n{'y':>6} {'起点':>6} {'末端':>6} {'thumb 左缘':>10} {'末端-左缘':>9}  判定")
    for i, b in enumerate(bands):
        p = pcts[i] if i < len(pcts) else None
        ts, te = b["thumb"]
        d = b["fill_e"] - ts
        ok = -16 <= d <= 1     # 填充末端应落在 thumb 左缘之前一点点（被 4px 环遮住），且不得越过左缘
        if not ok:
            bad += 1
        print(f"{b['y0']:>6} {b['fill_s']:>6} {b['fill_e']:>6} {ts:>10} {d:>9}  "
              f"{'OK' if ok else 'FAIL'}  pct={p if p is not None else '?'}")

    # 1) 起点一致：所有填充段都必须从轨道左端起算
    starts = [b["fill_s"] for b in bands]
    if max(starts) - min(starts) > args.tolerance:
        print(f"FAIL   填充段起点不一致（{starts}）—— 渐变不是从轨道左端起算，可能 RTL 规则误命中或停点写反")
        bad += 1

    # 2) 比例生效：不同值的填充段长度必须不同（否则是固定宽度的假填充）
    lens = [b["fill_e"] - b["fill_s"] + 1 for b in bands]
    if len(lens) >= 2 and len(set(lens)) == 1:
        print(f"FAIL   各滑块填充段长度完全相同（{lens}）—— 比例没有进入渐变")
        bad += 1

    # 3) 递增：越靠下（值越大）的填充段应越长（selftest 的顺序约定）
    if lens != sorted(lens):
        print(f"WARN   填充段长度非递增 {lens}（如果页面顺序不是值升序，可忽略）")

    print(f"\n结果：{len(bands) - bad}/{len(bands)} 通过")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
