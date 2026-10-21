#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""analyze_video.py — 从录屏反解 Win11 Fluent 的整屏动效与控件形态（报告优先）

范围约定（见 VIDEO-ALIGN.md）：
  第一优先 = 整屏动效（页面转场 / 浮层出入场 / 大块入场 / 编排节奏 / 质量体检）
  第二优先 = 控件形态及其微动效
  颜色不参考（一律用官方 --fl-* token），本脚本不提供取色功能。

设计要点：
  * 流式解码，不落全帧 PNG（1080p 十秒的全帧 PNG 就是几百 MB）。只有 `extract`
    会导出「供人眼查看」的采样静帧；所有量测都在解码循环里直接算指标。
  * 所有时间一律用容器 pts 换算成毫秒，不用帧序号（防 VFR 时间轴漂移）。
  * 时长判定一律映射到官方档位 83 / 167 / 250 / 333ms，并显式标注可信度；
    fps < 45 时 83ms 档只有 2~3 帧，标记为「不可分辨」，绝不硬报毫秒。

子命令：
  probe     元信息与素材质量评估
  demo      生成一段带已知动效的合成片（用于自检本工具）
  extract   导出采样静帧供人眼查看 + frames.csv
  segments  逐帧差分切分静态段/动效段 → timeline.json
  motion    多 ROI 整屏级量测（类型 / 档位 / 联动 / 重叠 / 质量）
  quality   只输出整屏动效质量体检（读 motion 结果或现场重算）
  micro     控件级微动效（形式判定）
  measure   标定像素尺度并量控件几何
  sheet     contact sheet + 每个动效段的帧条
  compare   视频静帧控件区域 × 模板控件截图 → 并排图
  report    汇总为 report.md（10 节）

依赖：av、numpy、pillow（装在隔离 venv 里）
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from fractions import Fraction
from pathlib import Path

try:
    import numpy as np
except ImportError:  # pragma: no cover
    sys.exit("缺少 numpy：pip install numpy")

try:
    import av
except ImportError:  # pragma: no cover
    av = None

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    Image = None


# ---------------------------------------------------------------- 常量

TIERS = [83, 167, 250, 333]          # 官方动效档位（ms）
TIER_NAMES = {
    83: "Fade / 控件状态快档",
    167: "Direct Entrance·Exit / 浮层",
    250: "Point to Point / 页面转场",
    333: "Strong Entrance / 大块入场",
}
DIFF_THR = 6                          # 灰度差阈值（抗压缩噪声）
ACTIVE_RATIO = 0.0015                # 变化像素占比超过它才算「活动」
ANALYSIS_WIDTH = 320                 # segments 用低分辨率算全局曲线
SHIFT_EVIDENCE = 0.25                # 平移必须让残差下降 ≥25%，否则判为伪位移
SEG_NOISE_PEAK = 0.004                # 变化像素占比低于 0.4% 的段视为噪声段
                                     # （局部控件如开关 knob 在整屏上只占千分之几，
                                     #   这类要走 micro + ROI 在原始分辨率上量）


# ---------------------------------------------------------------- 工具

def die(msg: str, code: int = 2):
    print("错误：" + msg, file=sys.stderr)
    sys.exit(code)


def slug(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z_\-]+", "_", s).strip("_") or "x"


def round_list(vals, nd=2):
    return [round(float(v), nd) for v in vals]


def parse_roi(s: str):
    """name:x,y,w,h  或  x,y,w,h"""
    name = "roi"
    body = s
    if ":" in s:
        name, body = s.split(":", 1)
    parts = [p.strip() for p in body.split(",")]
    if len(parts) != 4:
        die(f"ROI 格式应为 name:x,y,w,h，收到：{s}")
    x, y, w, h = (int(float(p)) for p in parts)
    return name, (x, y, w, h)


def load_timeline(work: Path):
    p = work / "timeline.json"
    if not p.exists():
        die(f"缺少 {p}，先跑 segments")
    return json.loads(p.read_text(encoding="utf-8"))


def load_probe(work: Path):
    p = work / "video-probe.json"
    if not p.exists():
        die(f"缺少 {p}，先跑 probe")
    return json.loads(p.read_text(encoding="utf-8"))


def work_dir(args) -> Path:
    if args.work:
        return Path(args.work).expanduser().resolve()
    stem = Path(args.video).stem
    return (Path.cwd() / "video-analysis" / stem).resolve()


def frame_ms(frame, tb):
    if frame.pts is not None:
        return float(frame.pts * tb) * 1000.0
    if frame.time is not None:
        return float(frame.time) * 1000.0
    return None


def iter_gray(video: Path, t0_ms=None, t1_ms=None, width=None, gray=True):
    """流式产出 (pts_ms, ndarray)。t0/t1 为毫秒窗口，会 seek 到 t0 前 1.2s 再过滤。"""
    if av is None:
        die("缺少 PyAV：pip install av")
    with av.open(str(video)) as c:
        vs = c.streams.video[0]
        tb = vs.time_base
        if t0_ms is not None and t0_ms > 1200:
            try:
                c.seek(int((t0_ms - 1200) / 1000.0 / tb), stream=vs, backward=True)
            except Exception:
                pass
        for frame in c.decode(vs):
            t = frame_ms(frame, tb)
            if t is None:
                continue
            if t1_ms is not None and t > t1_ms:
                break
            if t0_ms is not None and t < t0_ms - 1e-6:
                continue
            if width:
                w, h = frame.width, frame.height
                nh = max(2, int(round(h * width / w)))
                frame = frame.reformat(width=width, height=nh, format="gray" if gray else "rgb24")
            arr = frame.to_ndarray(format="gray" if gray else "rgb24")
            yield t, arr


def crop_gray(gray: np.ndarray, box):
    """按 box 裁出 ROI（自动夹到画面内），返回 float32。"""
    h_img, w_img = gray.shape[:2]
    x, y, w, h = box
    x0, y0 = max(0, int(x)), max(0, int(y))
    x1, y1 = min(w_img, int(x + w)), min(h_img, int(y + h))
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    return gray[y0:y1, x0:x1].astype(np.float32)


def phase_shift(prev: np.ndarray, cur: np.ndarray):
    """相位相关求两帧之间的整体平移 (dy, dx)（cur 相对 prev）。

    这是整屏动效的核心：内容整体换页时，质心会被内容差异带偏，
    而相位相关只取「占主导的刚体位移」，方向与幅度都更接近真实运动。
    """
    h, w = prev.shape
    win = np.outer(np.hanning(h), np.hanning(w))
    a = (prev - prev.mean()) * win
    b = (cur - cur.mean()) * win
    A = np.fft.rfft2(a)
    B = np.fft.rfft2(b)
    R = A * np.conj(B)
    mag = np.abs(R)
    R = R / (mag + 1e-9)
    r = np.fft.irfft2(R, s=(h, w))
    idx = int(np.argmax(r))
    dy, dx = divmod(idx, w)
    if dy > h // 2:
        dy -= h
    if dx > w // 2:
        dx -= w
    peak = float(r[dy % h, dx % w])
    # 峰值旁瓣比（PSR）：真平移的峰尖锐孤立，内容整块换页时峰是散的
    mask = np.ones_like(r, dtype=bool)
    y0, y1 = max(0, dy - 4), min(h, dy + 5)
    x0, x1 = max(0, dx - 4), min(w, dx + 5)
    mask[y0:y1, x0:x1] = False
    side = float(r[mask].max()) if mask.any() else 0.0
    psr = peak / (side + 1e-9)
    # 互相关峰值 = 内容位移的反向；取负后语义为「元素位移」（上移/左移为负）
    return -dy, -dx, psr


def change_bbox(cur: np.ndarray, ref: np.ndarray, thr: float = 8.0):
    """相对参考帧的变化区域 bbox 与面积占比（用于判展开/淡入淡出）。"""
    if cur.shape != ref.shape:
        return {"cbx": 0, "cby": 0, "cbw": 0, "cbh": 0, "cfill": 0.0}
    d = np.abs(cur - ref)
    m = d > thr
    if not m.any():
        return {"cbx": 0, "cby": 0, "cbw": 0, "cbh": 0, "cfill": 0.0}
    yy, xx = np.nonzero(m)
    return {"cbx": int(xx.min()), "cby": int(yy.min()),
            "cbw": int(xx.max() - xx.min() + 1),
            "cbh": int(yy.max() - yy.min() + 1),
            "cfill": round(float(m.mean()), 4)}


def roi_metrics(crop: np.ndarray) -> dict:
    """单个 ROI 单帧的静态描述：亮度、结构能量、质心、内容 bbox。"""
    if crop is None:
        return {"lum": 0.0, "mass": 0.0, "cx": 0.0, "cy": 0.0,
                "bx": 0, "by": 0, "bw": 0, "bh": 0}
    lum = float(crop.mean())
    bg = float(np.median(crop))
    dev = np.abs(crop - bg)
    mass = float(dev.mean())
    wgt = dev * dev
    tot = float(wgt.sum())
    if tot < 1e-6:
        cx, cy = crop.shape[1] / 2.0, crop.shape[0] / 2.0
        bx, by, bw, bh = 0, 0, crop.shape[1], crop.shape[0]
    else:
        ys, xs = np.indices(dev.shape, dtype=np.float32)
        cx = float((wgt * xs).sum() / tot)
        cy = float((wgt * ys).sum() / tot)
        thr = max(DIFF_THR * 0.8, float(dev.max()) * 0.22)
        m = dev > thr
        if m.any():
            yy, xx = np.nonzero(m)
            bx, by = int(xx.min()), int(yy.min())
            bw, bh = int(xx.max() - xx.min() + 1), int(yy.max() - yy.min() + 1)
        else:
            bx, by, bw, bh = 0, 0, crop.shape[1], crop.shape[0]
    return {"lum": round(lum, 2), "mass": round(mass, 2),
            "cx": round(cx, 2), "cy": round(cy, 2),
            "bx": bx, "by": by, "bw": bw, "bh": bh}


# ---------------------------------------------------------------- probe

def cmd_encode(args):
    """把帧序列编码成 CFR mp4（给只有图片序列的情况用，例如 CDP 逐帧抓取）。"""
    if av is None:
        die("缺少 PyAV：pip install av")
    src = Path(args.frames).expanduser().resolve()
    files = sorted(src.glob("*.png")) or sorted(src.glob("*.jpg"))
    if not files:
        die(f"{src} 里没有 png/jpg")
    first = Image.open(files[0])
    w, h = first.size
    w -= w % 2
    h -= h % 2
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    fps = args.fps
    rate = Fraction(fps).limit_denominator(1001) if float(fps) != int(fps) else int(fps)

    container = av.open(str(out), "w")
    try:
        stream = container.add_stream("libx264", rate=rate)
    except Exception:
        stream = container.add_stream("mpeg4", rate=rate)
    stream.width, stream.height, stream.pix_fmt = w, h, "yuv420p"
    if stream.codec_context.name == "libx264":
        stream.options = {"crf": "16", "g": "30"}
    for p in files:
        im = Image.open(p).convert("RGB")
        if im.size != (w, h):
            im = im.resize((w, h), Image.LANCZOS)
        arr = np.asarray(im, dtype=np.uint8)
        frm = av.VideoFrame.from_ndarray(arr, format="rgb24")
        for pkt in stream.encode(frm):
            container.mux(pkt)
    for pkt in stream.encode():
        container.mux(pkt)
    container.close()
    print(f"已编码 {len(files)} 帧 → {out}  ({w}×{h} @ {fps}fps, "
          f"{len(files) / fps:.2f}s)")


def cmd_probe(args):
    if av is None:
        die("缺少 PyAV：pip install av")
    video = Path(args.video).expanduser().resolve()
    if not video.exists():
        die(f"找不到视频：{video}")
    work = work_dir(args)
    work.mkdir(parents=True, exist_ok=True)

    with av.open(str(video)) as c:
        vs = c.streams.video[0]
        fps = None
        for cand in (vs.average_rate, vs.guessed_rate, vs.base_rate):
            if cand:
                try:
                    fps = float(cand)
                    break
                except Exception:
                    pass
        tb = vs.time_base
        dur = float(c.duration) / 1e6 if c.duration else None
        packets = 0
        keys = 0
        for pkt in c.demux(vs):
            if pkt.size == 0:
                continue
            packets += 1
            if pkt.is_keyframe:
                keys += 1
        frames = int(vs.frames) if getattr(vs, "frames", 0) else packets
        if dur is None and fps:
            dur = frames / fps
        size_bytes = getattr(c, "size", 0) or video.stat().st_size

    dur = dur or 0.0
    fps = fps or (frames / dur if dur else 0.0)
    w, h = vs.codec_context.width, vs.codec_context.height
    bitrate = (size_bytes * 8 / dur) if dur else 0.0
    bpp = bitrate / (w * h * fps) if (w and h and fps) else 0.0
    gop_s = frames / keys / fps if (keys and fps) else 0.0
    frame_ms_res = 1000.0 / fps if fps else 0.0

    warnings = []
    if fps < 45:
        warnings.append(
            f"帧率 {fps:.2f}fps → 时间分辨率 {frame_ms_res:.1f}ms；"
            f"83ms 档只有 {83 / max(frame_ms_res, 1e-6):.1f} 帧，标记为不可分辨")
    if fps >= 45:
        warnings.append("帧率充足，83ms 档也可分辨")
    # 码率密度只作「重度转码」的粗筛：内容简单的界面本身码率就低，阈值取严避免误报
    if bpp and bpp < 0.004:
        warnings.append(f"码率密度极低（{bpp:.4f} bit/px/帧）→ 疑似重度二次转码"
                        f"（微信/QQ 转发），时间轴与细节可能已失真，建议重发原始文件")
    if gop_s and gop_s > 6.0:
        warnings.append(f"关键帧间隔 {gop_s:.1f}s 异常大 → 疑似重编码（正常录屏多在 1~5s）")

    info = {
        "video": str(video),
        "codec": vs.codec_context.name,
        "pix_fmt": str(vs.codec_context.pix_fmt),
        "width": w, "height": h,
        "fps": round(fps, 3),
        "frame_count": frames,
        "duration_ms": round(dur * 1000, 1),
        "bitrate_kbps": round(bitrate / 1000, 1),
        "bits_per_pixel_frame": round(bpp, 5),
        "keyframe_count": keys,
        "gop_seconds": round(gop_s, 2),
        "frame_interval_ms": round(frame_ms_res, 2),
        "tier_resolvable": {str(t): (t / frame_ms_res if frame_ms_res else None)
                            for t in TIERS},
        "warnings": warnings,
    }
    (work / "video-probe.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return
    print(f"文件      {video.name}  ({size_bytes / 1048576:.1f} MB)")
    print(f"编码      {info['codec']} / {info['pix_fmt']}")
    print(f"尺寸      {w} × {h}")
    print(f"帧率      {fps:.3f} fps   帧间隔 {frame_ms_res:.2f} ms")
    print(f"时长      {dur:.2f} s   帧数 {frames}   关键帧 {keys} (GOP {gop_s:.1f}s)")
    print(f"码率      {bitrate / 1000:.0f} kbps   {bpp:.4f} bit/px/帧")
    print("档位可分辨性（该档位能采到几帧）：")
    for t in TIERS:
        n = t / frame_ms_res if frame_ms_res else 0
        verdict = "测量可得" if n >= 4 else ("勉强" if n >= 3 else "不可分辨")
        print(f"  {t:>3}ms → {n:>4.1f} 帧  {verdict}")
    if warnings:
        print("素材提示：")
        for w_ in warnings:
            print("  · " + w_)


# ---------------------------------------------------------------- demo

def cmd_demo(args):
    """生成一段带已知动效的合成片，用来验证本工具的判定逻辑。

    时间轴（30fps）：0.00–1.00 静态 → 1.00–1.25 交叉淡化 + 上滑 12px
                    1.60–1.767 浮层缩放淡入 → 2.40 瞬变（无过渡）→ 2.60–3.10 stagger 三段
    """
    if av is None:
        die("缺少 PyAV：pip install av")
    W, H, FPS = 960, 640, 30
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    def page(seed, tint):
        img = Image.new("L", (W, H), 32 if tint else 24)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 48], fill=44 if tint else 36)          # 标题栏
        d.rectangle([0, 48, 220, H], fill=38 if tint else 28)        # 导航
        rng = np.random.default_rng(seed)
        for k in range(7):
            y = 90 + k * 62
            d.rectangle([260, y, 260 + int(rng.integers(240, 520)), y + 16],
                        fill=210 if tint else 190)
            d.rectangle([260, y + 24, 260 + int(rng.integers(140, 360)), y + 32], fill=120)
        return np.asarray(img, dtype=np.float32)

    def ease(t):
        return 1 - (1 - t) ** 3

    page_a = page(1, False)
    page_b = page(2, True)
    page_c = page(3, False)
    panel = np.zeros((H, W), dtype=np.float32)
    d = ImageDraw.Draw(Image.fromarray(panel.astype(np.uint8)))
    pimg = Image.fromarray(panel.astype(np.uint8))
    dr = ImageDraw.Draw(pimg)
    dr.rounded_rectangle([600, 120, 900, 340], radius=8, fill=70)
    for k in range(4):
        dr.rectangle([620, 150 + k * 44, 860, 162 + k * 44], fill=190)
    panel = np.asarray(pimg, dtype=np.float32)

    frames = []
    n = int(3.15 * FPS)
    for i in range(n):
        t = i / FPS
        img = page_a.copy()
        if 1.00 <= t < 1.25:                       # 交叉淡化 + 上滑 12px
            u = (t - 1.00) / 0.25
            k_op = u                                # 不透明度线性（贴近 Win11 转场）
            k_mv = ease(u)                          # 位移减速
            a = np.roll(page_a, int(round(-12 * k_mv)), axis=0)
            b = np.roll(page_b, int(round(12 * (1 - k_mv))), axis=0)
            img = a * (1 - k_op) + b * k_op
        elif t >= 1.25:
            img = page_b.copy()
        if 1.60 <= t < 1.767:                      # 浮层：缩放 + 淡入
            u = (t - 1.60) / 0.167
            k_op, k_mv = u, ease(u)
            p = np.roll(panel, int(round(-8 * (1 - k_mv))), axis=0)
            img = img * (1 - 0.55 * k_op) + p * (0.55 * k_op)
        elif t >= 1.767:
            img = page_b.copy()
            img = np.maximum(img, panel * 0.55)
        if t >= 2.40:                               # 瞬变：无过渡
            img = page_c.copy()
        if 2.60 <= t < 3.10:                        # stagger：三段依次淡入
            base = page_c.copy()
            for j in range(3):
                st = 2.60 + j * 0.083
                k = 0.0 if t < st else min(1.0, ease((t - st) / 0.167))
                y0, y1 = 120 + j * 120, 210 + j * 120
                if k > 0:
                    base[y0:y1, 300:700] = (base[y0:y1, 300:700] * (1 - k)
                                            + 230 * k)
            img = base
        frames.append(np.clip(img, 0, 255).astype(np.uint8))

    container = av.open(str(out), "w")
    codec = "libx264"
    try:
        stream = container.add_stream(codec, rate=FPS)
    except Exception:
        codec = "mpeg4"
        stream = container.add_stream(codec, rate=FPS)
    stream.width, stream.height, stream.pix_fmt = W, H, "yuv420p"
    stream.options = {"crf": "18"} if codec == "libx264" else {}
    rgb_cache = [np.repeat(f[:, :, None], 3, axis=2) for f in frames]
    for arr in rgb_cache:
        frm = av.VideoFrame.from_ndarray(arr, format="rgb24")
        for pkt in stream.encode(frm):
            container.mux(pkt)
    for pkt in stream.encode():
        container.mux(pkt)
    container.close()
    print(f"已生成合成片 {out}  ({len(frames)} 帧 @ {FPS}fps, {codec})")
    print("已知 ground truth：")
    print("  1.00–1.25s  交叉淡化 + 上滑 12px  → 期望 250ms 档 / 减速类")
    print("  1.60–1.767s 浮层缩放淡入 8px      → 期望 167ms 档")
    print("  2.40s       瞬变（无过渡）        → 期望被标为「瞬变」")
    print("  2.60–3.10s  stagger 三段 0/83/166 → 期望被测出错峰")


# ---------------------------------------------------------------- extract

def cmd_extract(args):
    """导出采样静帧供人眼查看（不是量测用；量测在解码循环里直接算）。"""
    if Image is None:
        die("缺少 Pillow：pip install pillow")
    work = work_dir(args)
    frames_dir = work / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob("*.png"):
        old.unlink()

    rows = []
    step = max(1, args.every) if args.all else None
    idx = 0
    for t, arr in iter_gray(Path(args.video), gray=False):
        keep = True
        if step is not None:
            keep = (idx % step == 0)
        else:
            keep = False    # 非 --all 时先收集再均匀抽样（见下）
        if keep:
            name = f"f{idx:05d}.png"
            Image.fromarray(arr).save(frames_dir / name)
            rows.append({"idx": idx, "pts_ms": round(t, 2), "file": name})
        idx += 1

    if step is None:        # 均匀抽样 args.count 帧
        total = idx
        want = max(1, args.count)
        picks = sorted({int(round(i * (total - 1) / max(1, want - 1))) for i in range(want)})
        idx = 0
        pickset = set(picks)
        for t, arr in iter_gray(Path(args.video), gray=False):
            if idx in pickset:
                name = f"f{idx:05d}.png"
                Image.fromarray(arr).save(frames_dir / name)
                rows.append({"idx": idx, "pts_ms": round(t, 2), "file": name})
            idx += 1

    rows.sort(key=lambda r: r["idx"])
    with (work / "frames.csv").open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=["idx", "pts_ms", "file"])
        wr.writeheader()
        wr.writerows(rows)
    print(f"已导出 {len(rows)} 帧 → {frames_dir}")


# ---------------------------------------------------------------- segments

def cmd_segments(args):
    work = work_dir(args)
    work.mkdir(parents=True, exist_ok=True)
    probe = load_probe(work)
    fps = probe["fps"] or 30.0

    prev = None
    series = []
    for t, arr in iter_gray(Path(args.video), width=ANALYSIS_WIDTH):
        a = arr.astype(np.float32)
        lum = float(a.mean())
        mass = float(np.abs(a - np.median(a)).mean())
        if prev is None:
            ch, mad = 0.0, 0.0
        else:
            d = np.abs(a - prev)
            ch = float((d > DIFF_THR).mean())
            mad = float(d.mean())
        series.append({"t": round(t, 2), "lum": round(lum, 2),
                       "mass": round(mass, 2), "changed": round(ch, 6),
                       "mean_abs": round(mad, 3)})
        prev = a

    thr = args.threshold if args.threshold is not None else ACTIVE_RATIO
    active = [False] + [s["changed"] > thr for s in series[1:]]

    # 合并活动帧（允许中间夹 1 帧静止，防压缩噪声把一段切成两段）
    segs = []
    i = 1
    n = len(series)
    while i < n:
        if not active[i]:
            i += 1
            continue
        start = i
        end = i
        gap = 0
        j = i + 1
        while j < n:
            if active[j]:
                end = j
                gap = 0
            else:
                gap += 1
                if gap > args.gap:
                    break
            j += 1
        segs.append((start - 1, end))
        i = end + 1

    out = []
    k = 0
    for s, e in segs:
        length = e - s
        if length < args.min_frames:
            continue
        k += 1
        peak = round(max(series[x]["changed"] for x in range(s, e + 1)), 6)
        instant = length <= 1
        out.append({
            "id": f"s{k}",
            "start_idx": s,
            "end_idx": e,
            "t0_ms": round(series[s]["t"], 1),
            "t1_ms": round(series[e]["t"], 1),
            "active_frames": length,
            "duration_ms": round(series[e]["t"] - series[s]["t"], 1),
            "instant": instant,
            "noise": peak < SEG_NOISE_PEAK and not instant,
            "tier_guess": None if instant else nearest_tier(series[e]["t"] - series[s]["t"], fps),
            "peak_changed": peak,
        })

    timeline = {
        "fps": fps,
        "frame_interval_ms": round(1000.0 / fps, 2),
        "threshold": thr,
        "frame_count": len(series),
        "duration_ms": round(series[-1]["t"], 1) if series else 0,
        "series": series,
        "segments": out,
    }
    (work / "timeline.json").write_text(
        json.dumps(timeline, ensure_ascii=False, indent=1), encoding="utf-8")

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    print(f"共 {len(series)} 帧，{timeline['duration_ms']:.0f}ms，切出 {len(out)} 段动效")
    print(f"{'段':<4}{'起(ms)':>9}{'止(ms)':>9}{'时长':>8}{'活动帧':>7}  {'档位猜测':<30}峰值变化")
    for s in out:
        tier = s["tier_guess"]
        if s["instant"]:
            tname = "瞬变（单帧完成，无过渡）"
        elif s.get("noise"):
            tname = "幅度极小（<1%，可忽略）"
        else:
            tname = f"{tier['tier']}ms {tier['label']}" if tier else "—"
        print(f"{s['id']:<4}{s['t0_ms']:>9.0f}{s['t1_ms']:>9.0f}"
              f"{s['duration_ms']:>8.0f}{s['active_frames']:>7}  {tname:<30}{s['peak_changed']:.4f}")


def nearest_tier(ms: float, fps: float):
    if ms <= 0:
        return None
    fi = 1000.0 / fps if fps else 33.3
    lo, hi = ms - fi / 2, ms + fi / 2
    cands = [t for t in TIERS if lo - 1e-9 <= t <= hi + 1e-9]
    inside = bool(cands)
    tier = min(cands, key=lambda t: abs(t - ms)) if inside else min(TIERS, key=lambda t: abs(t - ms))
    ambiguous = fps < 45 and tier == 83
    if ambiguous:
        conf = "低（档位不可分辨）"
    elif inside and abs(ms - tier) <= fi / 2 + 1e-6:
        conf = "高"
    elif inside:
        conf = "中"
    else:
        conf = "低"
    note = ("命中官方档位" if inside else
            "测量值落在官方档位之间（%.0f–%.0fms），需看帧条确认" % (lo, hi))
    return {
        "measured_ms": round(ms, 1),
        "tier": tier,
        "label": TIER_NAMES[tier],
        "error_ms": round(ms - tier, 1),
        "frames_at_tier": round(tier / fi, 2),
        "confidence": conf,
        "in_tier": inside,
        "range_ms": [round(lo, 1), round(hi, 1)],
        "note": note,
        "ambiguous": ambiguous,
    }


# ---------------------------------------------------------------- motion

def resolve_window(args, timeline):
    if getattr(args, "seg", None):
        seg = next((s for s in timeline["segments"] if s["id"] == args.seg), None)
        if not seg:
            die(f"timeline 里没有段 {args.seg}")
        return seg["t0_ms"], seg["t1_ms"], f"seg_{args.seg}"
    a, b = getattr(args, "from_ms", None), getattr(args, "to_ms", None)
    if a is None or b is None:
        die("需要 --seg，或同时给 --from 与 --to（毫秒）")
    return float(a), float(b), getattr(args, "name", None) or f"w{int(a)}_{int(b)}"


def shift_improvement(prev: np.ndarray, cur: np.ndarray, dy: int, dx: int) -> float:
    """按 (dy,dx) 平移后残差下降多少（1.0 = 完全吻合，<=0.25 = 伪位移）。

    大面积纯色填充/整块换页时，互相关也会找出一个「一致但无意义」的峰；
    只有把 prev 真的平移过去能让残差明显下降，才说明是刚体平移。
    """
    h, w = prev.shape
    pad = max(8, abs(dy) + 2, abs(dx) + 2)
    if h - 2 * pad < 8 or w - 2 * pad < 8:
        pad = 4
        if h - 2 * pad < 8 or w - 2 * pad < 8:
            return 0.0
    a = prev[pad:h - pad, pad:w - pad]
    b = cur[pad:h - pad, pad:w - pad]
    r0 = float(np.mean(np.abs(a - b))) + 1e-6
    sh = np.roll(prev, (dy, dx), axis=(0, 1))[pad:h - pad, pad:w - pad]
    r1 = float(np.mean(np.abs(sh - b)))
    return 1.0 - r1 / r0


def measure_window(video, t0, t1, rois, probe):
    """流式解码窗口，逐帧算每个 ROI 的指标 + 逐帧全局平移（相位相关）。"""
    series = {name: [] for name, _ in rois}
    times = []
    w_full, h_full = probe["width"], probe["height"]
    state = {name: {"prev": None, "ref": None} for name, _ in rois}
    for t, gray in iter_gray(Path(video), t0_ms=t0, t1_ms=t1):
        times.append(round(t, 2))
        for name, roi in rois:
            box = (0, 0, w_full, h_full) if roi == "full" else roi
            crop = crop_gray(gray, box)
            st = state[name]
            m = roi_metrics(crop)
            if crop is not None:
                if st["prev"] is not None and st["prev"].shape == crop.shape:
                    dy, dx, peak = phase_shift(st["prev"], crop)
                    m["sdx"], m["sdy"], m["speak"] = int(dx), int(dy), round(peak, 2)
                    m["simp"] = round(shift_improvement(st["prev"], crop, dy, dx), 3)
                else:
                    m["sdx"], m["sdy"], m["speak"], m["simp"] = 0, 0, 0.0, 0.0
                if st["ref"] is None:
                    st["ref"] = crop
                m.update(change_bbox(crop, st["ref"]))
                st["prev"] = crop
            else:
                m["sdx"], m["sdy"], m["speak"], m["simp"] = 0, 0, 0.0, 0.0
                m.update({"cbx": 0, "cby": 0, "cbw": 0, "cbh": 0, "cfill": 0.0})
            series[name].append(m)
    return times, series


def fade_direction(d_lum: float, d_mass: float) -> str:
    """亮度与结构能量同向才敢断言「出现/消失」，否则只描述现象。"""
    if d_lum > 0 and d_mass > 0:
        return "→淡入/出现（更亮且结构变多）"
    if d_lum < 0 and d_mass < 0:
        return "→淡出/消失（更暗且结构变少）"
    if d_lum > 0 > d_mass:
        return "→亮度升高但结构变少（区域被填满或元素变大，出现/消失需看帧确认）"
    if d_lum < 0 < d_mass:
        return "→亮度降低但结构变多（元素拆细或底色变暗，需看帧确认）"
    return "→明暗变化（方向需看帧确认）"


def transition_span(step, lum, mass):
    """过渡区间：画面「首次明显偏离起始态」到「末次仍不同于终止态」的帧跨度。

    比「数超过噪声阈值的帧」稳得多 —— 缓出尾段的逐帧增量必然趋近于 0，
    数帧法会系统性少算（实测把 250ms 算成 167ms）。
    """
    n = len(step)
    if n < 3:
        return 0, 0, 0
    l0, l1 = lum[0], lum[-1]
    m0, m1 = mass[0], mass[-1]

    def differs(i, l_ref, m_ref):
        if step[i] > 0.5:
            return True
        if abs(lum[i] - l_ref) > 0.35:
            return True
        if m_ref and abs(mass[i] - m_ref) / m_ref > 0.02:
            return True
        return False

    s = 0
    for i in range(1, n):
        if differs(i, l0, m0):
            s = i
            break
    e = s
    for i in range(n - 1, -1, -1):
        if differs(i, l1, m1):
            e = i
            break
    return s, e, max(0, e - s)


def shift_is_rigid(step, sdx, sdy, simp):
    """判断逐帧位移是否构成「刚体平移」。

    三条门槛（顺序放松，逐条兜住不同场景）：
      1. 必须跨 ≥2 帧 —— 单帧大跳是「内容整块换掉」，不是平移；
      2. 方向必须一致；
      3. 大步位移必须有残差证据（平移后残差下降）——整块填色会给出
         「一致但无意义」的大位移；小步位移（缓动转场的典型形态）
         在交叉淡化下残差不可能下降，只靠方向一致性放行。
    """
    n = len(step)
    moved = [i for i in range(1, n) if step[i] >= 1.0]
    if not moved:
        return False, "窗口内没有可测平移"
    if len(moved) == 1:
        return False, "仅单帧出现位移尖峰（内容是整块换掉的，不是平移）"
    sx = [np.sign(sdx[i]) for i in moved if abs(sdx[i]) >= 1]
    sy = [np.sign(sdy[i]) for i in moved if abs(sdy[i]) >= 1]
    for axis, arr in (("x", sx), ("y", sy)):
        if len(arr) >= 2 and min(arr) != max(arr):
            return False, f"{axis} 方向不一致，位移不构成刚体平移"
    per = [step[i] for i in moved]
    med = float(np.median(per))
    med_imp = float(np.median([simp[i] for i in moved]))
    if med_imp >= 0.08:
        return True, f"{len(moved)} 帧同向位移，平移使残差下降 {med_imp:.0%}"
    if med <= 6.0:
        return True, (f"{len(moved)} 帧同向小步位移（中位 {med:.1f}px/帧）；"
                      f"交叉淡化下残差判据不适用，按方向一致性采信")
    return False, (f"位移幅度大（中位 {med:.1f}px/帧）但平移没能降低残差"
                   f"（{med_imp:+.0%}），判为整块填色/换页而非平移")


def analyze_series(times, series, fps, rois):
    out = {}
    fi = 1000.0 / fps if fps else 33.3
    for name, _ in rois:
        rows = series[name]
        n = len(rows)
        if n < 3:
            out[name] = {"error": "窗口内帧数不足（<3），无法量测"}
            continue
        simp = [r.get("simp", 0.0) for r in rows]
        sdx = [r["sdx"] for r in rows]
        sdy = [r["sdy"] for r in rows]
        cum_x = np.cumsum(sdx)
        cum_y = np.cumsum(sdy)
        total_dx = float(cum_x[-1])
        total_dy = float(cum_y[-1])
        total_shift = math.hypot(total_dx, total_dy)
        step = [math.hypot(sdx[i], sdy[i]) for i in range(n)]
        lum = [r["lum"] for r in rows]
        mass = [r["mass"] for r in rows]
        bh = [r["bh"] for r in rows]
        bw = [r["bw"] for r in rows]
        cbh = [r["cbh"] for r in rows]
        cbw = [r["cbw"] for r in rows]

        # 活动强度：位移为主，亮度/能量为辅
        act = []
        for i in range(1, n):
            act.append(max(step[i],
                           abs(lum[i] - lum[i - 1]) * 0.5,
                           abs(mass[i] - mass[i - 1]) * 0.15))
        noise = max(0.4, float(np.median(act)) * 0.15)

        # 时长用「首次偏离起始态 → 末次偏离终止态」的跨度来量
        first_act, last_act, intervals = transition_span(step, lum, mass)
        dur_frames = intervals + 1
        rigid, rigid_note = shift_is_rigid(step, sdx, sdy, simp)
        if not rigid:
            total_dx, total_dy = 0.0, 0.0
            total_shift = 0.0
            step = [0.0] * n      # 清掉伪位移，避免后续把它误报成抖动或位移

        d_lum = lum[-1] - lum[0]
        d_mass = (mass[-1] - mass[0]) / mass[0] if mass[0] else 0.0
        # 变化区面积增长（判「展开/尺寸变化」）
        cfills = [r["cfill"] for r in rows]
        peak_fill = max(cfills) if cfills else 0.0
        grow = 0.0
        nz = [c for c in cfills if c > 0.0005]
        if len(nz) >= 3:
            grow = nz[-1] / nz[0] if nz[0] else 0.0

        kind, detail = "fade", "无显著位移，仅明暗变化"
        if total_shift >= 2.0:
            if abs(total_dy) >= abs(total_dx):
                kind = "slide-vertical"
                detail = (f"垂直位移 {total_dy:+.1f}px"
                          f"（{'内容上移→入场 / 上滑转场' if total_dy < 0 else '内容下移→离场 / 下滑转场'}）")
            else:
                kind = "slide-horizontal"
                detail = (f"水平位移 {total_dx:+.1f}px"
                          f"（{'左移' if total_dx < 0 else '右移'}→Drill-in / Drill-out）")
            if abs(d_mass) >= 0.35:
                detail += f"；同时内容量变化 {d_mass * 100:+.0f}%（位移+淡入淡出叠加）"
        elif intervals == 0:
            kind = "instant"
            detail = "单帧完成，未捕捉到过渡（瞬变缺陷，或 83ms 档被帧率吞掉）"
        elif grow >= 1.15 and abs(d_lum) < 6:
            kind = "expand"
            detail = f"变化区域持续扩大 {grow:.2f}×（展开 / 尺寸变化）"
        elif abs(d_lum) >= 2.0 or abs(d_mass) >= 0.25:
            kind = "fade"
            detail = (f"仅明暗/填充变化（亮度 {d_lum:+.1f}，结构能量 {d_mass * 100:+.0f}%，"
                      f"变化区占比 {peak_fill * 100:.1f}%）{fade_direction(d_lum, d_mass)}")
        if not rigid:
            detail += f"｜位移判据：{rigid_note}"

        quality = quality_of(step, sdx, sdy, cum_x, cum_y, bh, mass, act, noise, fi, total_shift)

        # 缓动：优先用真实位移的累计进度，位移不足时退回亮度曲线
        # 只取活动区间，窗口前后留白会造成零速段、把减速曲线误判成「对称」
        easing_src = "位移累计曲线"
        if total_shift >= 3.0:
            cum_shift = list(np.hypot(cum_x, cum_y))
            seg = cum_shift[first_act:last_act + 1]
            easing = easing_shape(seg if len(seg) >= 4 else cum_shift)
        else:
            easing_src = "亮度曲线"
            seg = lum[first_act:last_act + 1]
            easing = easing_shape(seg if len(seg) >= 4 else lum)

        measured = (intervals + 1) * fi if intervals > 0 else 0.0
        if intervals == 0:
            easing = "不可判（单帧完成，没有可拟合的过渡曲线）"
            easing_src = "—"
        out[name] = {
            "frames": n,
            "duration_ms": round(times[-1] - times[0], 1),
            "active_frames": dur_frames,
            "active_span": [first_act, last_act],
            "measured_ms": round(measured, 1),
            "tier": nearest_tier(measured, fps) if measured > 0 else None,
            "kind": kind,
            "detail": detail,
            "rigid_shift": rigid,
            "rigid_note": rigid_note,
            "shift_px": {"dx": round(total_dx, 1), "dy": round(total_dy, 1),
                         "total": round(total_shift, 1)},
            "delta_lum": round(d_lum, 2),
            "delta_mass_pct": round(d_mass * 100, 1),
            "change_fill_peak": round(peak_fill, 4),
            "easing_shape": easing,
            "easing_source": easing_src,
            "quality": quality,
            "series": {"cum_dx": round_list(cum_x), "cum_dy": round_list(cum_y),
                       "step": round_list(step), "lum": round_list(lum),
                       "mass": round_list(mass), "bh": bh, "bw": bw,
                       "cbh": cbh, "cbw": cbw, "cfill": round_list(cfills, 4)},
        }
    return out


def quality_of(step, sdx, sdy, cum_x, cum_y, bh, mass, act, noise, fi, total_shift):
    """整屏动效质量体检：布局跳变、堆叠撑高、卡顿、重叠方式。"""
    q = {}

    # 1) 抖动 / 布局跳变：某一帧位移远超中位数，且与前后方向不一致
    jumps = []
    pos = [v for v in step[1:] if v > 0.3]
    med = float(np.median(pos)) if pos else 0.0
    thr = max(3.5 * med, 2.5)
    for i in range(2, len(step)):
        if step[i] > thr:
            prev = (sdx[i - 1], sdy[i - 1])
            cur = (sdx[i], sdy[i])
            rev = (prev[0] * cur[0] + prev[1] * cur[1]) < 0
            incoherent = (cur[0] * sdx[1] if len(sdx) > 1 else 0) < 0
            jumps.append({"at_ms": round(i * fi, 1), "delta_px": round(step[i], 2),
                          "vs_median": round(step[i] / med, 1) if med else None,
                          "reversed": bool(rev), "incoherent": bool(incoherent)})
    q["step_jumps"] = jumps
    if not jumps:
        q["jitter"] = "无位移阶跃"
    else:
        hard = [j for j in jumps if j["reversed"] or (j["vs_median"] or 0) >= 5]
        q["jitter"] = ("检测到 %d 处位移阶跃，其中 %d 处方向反转/超 5 倍中位 → 疑似抖动或布局跳变"
                       % (len(jumps), len(hard))) if hard else \
                      ("检测到 %d 处位移阶跃（幅度偏大但方向连续，可能只是入场首帧）" % len(jumps))

    # 2) 堆叠撑高：内容高度出现「涨起来又落回去」的峰
    if bh and len(bh) >= 5:
        ends = max(bh[0], bh[-1], 1)
        inner = bh[1:-1]
        hump = (max(inner) / ends) if inner else 1.0
        q["bbox_height_hump"] = round(hump, 3)
        q["stacking"] = (("内容区高度出现涨落 %.0f%%（%.0f→%.0f），疑似两态在纵向并存导致撑高"
                          % ((hump - 1) * 100, ends, max(inner)))
                         if hump > 1.08 else "无堆叠撑高（内容高度单调，未出现涨落）")
    else:
        q["bbox_height_hump"] = 1.0
        q["stacking"] = "不可判（帧数不足）"

    # 3) 卡顿：活动区间内出现 ≥2 帧完全静止后又继续
    stut = []
    k, n = 0, len(act)
    while k < n:
        if act[k] <= noise:
            j = k
            while j < n and act[j] <= noise:
                j += 1
            if 2 <= (j - k) < n and k > 0 and j < n:
                stut.append({"from_ms": round(k * fi, 1), "still_frames": j - k})
            k = j
        else:
            k += 1
    q["stutter"] = stut
    q["smoothness"] = ("活动区间内有 %d 处静止空档（疑似掉帧/卡顿）" % len(stut)) if stut else "连续无空档"

    # 4) 重叠方式：结构能量低洼 → 先后播放；持平 → 交叉淡化
    if len(mass) >= 5:
        trim = max(1, len(mass) // 10)
        ends = (float(np.mean(mass[:trim])) + float(np.mean(mass[-trim:]))) / 2.0
        dip = min(mass) / ends if ends > 1e-6 else 1.0
        q["mass_dip_ratio"] = round(dip, 3)
        if dip >= 0.65:
            q["overlap"] = "交叉淡化（同区域两态并存，中段能量保留 %.0f%%）" % (dip * 100)
        elif dip >= 0.45:
            q["overlap"] = ("介于两者之间（中段能量保留 %.0f%%，接近阈值）——"
                            "两页内容量差异大时会被低估，建议看帧条确认" % (dip * 100))
        else:
            q["overlap"] = "先后播放（中段能量落底至 %.0f%%，旧态先退场）" % (dip * 100)
    else:
        q["mass_dip_ratio"] = None
        q["overlap"] = "不可判"

    q["ok"] = (not jumps) and q.get("stacking", "").startswith("无")
    return q


def easing_shape(series):
    """由位移/亮度曲线的一阶差分判断缓动形状。"""
    if not series or len(series) < 4:
        return "不可判（帧数不足）"
    p = np.asarray(series, dtype=float)
    span = p[-1] - p[0]
    if abs(span) < 1e-6:
        return "不可判（总位移为 0）"
    prog = (p - p[0]) / span
    vel = np.diff(prog)
    # 去掉首尾零速段（窗口留白），否则减速曲线会被误判成「先加速后减速」
    nz = np.nonzero(np.abs(vel) > 1e-6)[0]
    if len(nz) >= 3:
        vel = vel[nz[0]:nz[-1] + 1]
    if len(vel) < 3:
        return "不可判（帧数不足）"
    mean_v = float(np.mean(vel))
    if mean_v <= 0:
        return "不可判（曲线非单调）"
    pk = int(np.argmax(vel))
    rel = pk / max(1, len(vel) - 1)
    mono = all(vel[i + 1] <= vel[i] * 1.25 + 1e-6 for i in range(len(vel) - 1))
    spread = (float(np.max(vel)) - float(np.min(vel))) / mean_v if mean_v else 0
    if spread < 0.5:
        return "近线性（linear）"
    if mono:
        return "减速类（decelerate → 对应官方 standard / point-to-point）"
    if 0.25 <= rel <= 0.78:
        return "对称类（缓入缓出 → ease-in-out / soft）"
    return "混合（先加速后减速，峰值偏前 → strong 弹性）"


def cmd_motion(args):
    work = work_dir(args)
    timeline = load_timeline(work)
    probe = load_probe(work)
    t0, t1, name = resolve_window(args, timeline)
    t0, t1 = pad_window(t0, t1, probe, args.pad)
    rois = [parse_roi(s) for s in (args.roi or [])] or [("screen", (0, 0, probe["width"], probe["height"]))]

    times, series = measure_window(args.video, t0, t1, rois, probe)
    if len(times) < 3:
        die(f"窗口 {t0}-{t1}ms 内解码到 {len(times)} 帧，不足 3 帧；请扩大窗口或检查时间码")
    res = analyze_series(times, series, probe["fps"], rois)

    payload = {
        "window": {"t0_ms": t0, "t1_ms": t1, "frames": len(times), "times_ms": times},
        "fps": probe["fps"],
        "rois": [{"name": n, "box": list(b)} for n, b in rois],
        "analysis": res,
        "stagger": stagger_of(res, probe["fps"]),
    }
    (work / "motion").mkdir(exist_ok=True)
    path = work / "motion" / (slug(name) + ".json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(f"窗口 {t0:.0f}–{t1:.0f}ms，{len(times)} 帧 @ {probe['fps']:.1f}fps → {path.name}")
    for n, r in res.items():
        if "error" in r:
            print(f"\n[{n}] {r['error']}")
            continue
        tier = r["tier"] or {}
        if tier and not tier.get("in_tier"):
            tier_txt = f"**无对应档位** — {tier.get('note')}"
        else:
            tier_txt = (f"档位 {tier.get('tier')}ms（{tier.get('label')}）"
                        f"  误差 {tier.get('error_ms')}ms  可信度 {tier.get('confidence')}")
        print(f"\n[{n}]  形状={r['kind']}  {r['detail']}")
        print(f"  活动帧 {r['active_frames']} → 实测约 {r['measured_ms']}ms  {tier_txt}")
        sp = r["shift_px"]
        print(f"  位移 {sp['total']}px (dx {sp['dx']}, dy {sp['dy']})"
              f"  亮度Δ {r['delta_lum']}  内容量Δ {r['delta_mass_pct']}%")
        print(f"  缓动 {r['easing_shape']}（源：{r['easing_source']}）")
        q = r["quality"]
        print(f"  质量: {q['jitter']} / {q['stacking']} / {q['smoothness']} / {q['overlap']}")
    if payload["stagger"]:
        print(f"\n错峰（stagger）: {payload['stagger']['summary']}")
    elif len(rois) > 1:
        print(f"\n错峰（stagger）: 未测到 —— {len(rois)} 个 ROI 的活动起点相差不足 1 帧（同步入场）")
    else:
        print("\n错峰（stagger）: 未测 —— 需要 ≥2 个 ROI 才能判错峰，用 --roi 指定各元素位置")


def stagger_of(res, fps=None):
    """多个 ROI 的「活动起点」错开 → 判为 stagger 编排。

    用统一的过渡起点（active_span[0]）而不是位移起始帧：错峰入场的元素
    常常只是变亮没有位移，用位移找会漏检。
    """
    onsets = {n: r["active_span"][0] for n, r in res.items()
              if "active_span" in r}
    if len(onsets) < 2:
        return None
    base = min(onsets.values())
    offs = sorted(onsets.items(), key=lambda kv: kv[1])
    steps = [offs[i + 1][1] - offs[i][1] for i in range(len(offs) - 1)]
    if not steps or max(steps) < 1:
        return None
    fi = 1000.0 / fps if fps else 0.0
    parts = []
    for k, v in offs:
        lag = v - base
        parts.append(f"{k} 滞后 {lag} 帧" + (f"（≈{lag * fi:.0f}ms）" if lag and fi else ""))
    gaps = [steps[i] * fi for i in range(len(steps))] if fi else []
    gap_txt = (f"；相邻间隔 {', '.join(f'{g:.0f}ms' for g in gaps)}" if gaps else "")
    return {
        "onsets_frames": {k: v - base for k, v in onsets.items()},
        "offsets": [k for k, _ in offs],
        "onset_ms": {k: round((v - base) * fi, 1) for k, v in onsets.items()} if fi else {},
        "summary": "、".join(parts) + f"{gap_txt}"
                   f"（共 {len(offs)} 个 ROI 错峰起步，判为 stagger 编排）",
    }


def pad_window(t0, t1, probe, pad_ms):
    """把窗口向两侧各扩一点，避免动效的首尾缓入缓出被切掉（切掉会系统性少算时长）。"""
    if pad_ms is None:
        pad_ms = 2.0 * (probe.get("frame_interval_ms") or 33.3)
    return max(0.0, t0 - pad_ms), t1 + pad_ms


def cmd_quality(args):
    work = work_dir(args)
    timeline = load_timeline(work)
    probe = load_probe(work)
    t0, t1, name = resolve_window(args, timeline)
    t0, t1 = pad_window(t0, t1, probe, args.pad)
    rois = [parse_roi(s) for s in (args.roi or [])] or [("screen", (0, 0, probe["width"], probe["height"]))]
    times, series = measure_window(args.video, t0, t1, rois, probe)
    if len(times) < 3:
        die("窗口内帧数不足")
    res = analyze_series(times, series, probe["fps"], rois)
    only = {n: r.get("quality") for n, r in res.items()}
    if args.json:
        print(json.dumps(only, ensure_ascii=False, indent=2))
        return
    print(f"质量体检 {t0:.0f}–{t1:.0f}ms（{len(times)} 帧）")
    for n, q in only.items():
        print(f"\n[{n}] {'通过' if q and q.get('ok') else '有问题'}")
        if not q:
            continue
        print(f"  抖动      {q['jitter']}")
        print(f"  堆叠      {q['stacking']}（高度峰 {q['bbox_height_hump']:.2f}×）")
        print(f"  连续性    {q['smoothness']}")
        print(f"  重叠方式  {q['overlap']}")
        for j in q["step_jumps"][:5]:
            print(f"    ! {j['at_ms']}ms 阶跃 {j['delta_px']}px"
                  f"{'（方向反转）' if j['reversed'] else ''}")


# ---------------------------------------------------------------- micro

def cmd_micro(args):
    work = work_dir(args)
    timeline = load_timeline(work)
    probe = load_probe(work)
    t0, t1, name = resolve_window(args, timeline)
    t0, t1 = pad_window(t0, t1, probe, args.pad)
    if args.roi:
        name2, roi = parse_roi(args.roi[0])
        name = args.name or name2
    else:
        roi = (0, 0, probe["width"], probe["height"])
    times, series = measure_window(args.video, t0, t1, [(name, roi)], probe)
    if len(times) < 2:
        die("窗口内帧数不足（<2）")
    rows = series[name]
    sdx = [r["sdx"] for r in rows]
    sdy = [r["sdy"] for r in rows]
    simp = [r.get("simp", 0.0) for r in rows]
    step = [math.hypot(sdx[i], sdy[i]) for i in range(len(rows))]
    total_dx, total_dy = float(np.sum(sdx)), float(np.sum(sdy))
    total_shift = math.hypot(total_dx, total_dy)
    lum = [r["lum"] for r in rows]
    mass = [r["mass"] for r in rows]
    cfills = [r["cfill"] for r in rows]
    peak_fill = max(cfills) if cfills else 0.0
    cbw = [r["cbw"] for r in rows]
    cbh = [r["cbh"] for r in rows]

    act = []
    for i in range(1, len(rows)):
        act.append(max(step[i], abs(lum[i] - lum[i - 1]) * 0.5,
                       abs(mass[i] - mass[i - 1]) * 0.5))
    noise = max(0.35, float(np.median(act)) * 0.15) if act else 0.35
    d_lum = lum[-1] - lum[0]
    d_mass = (mass[-1] - mass[0]) / mass[0] if mass[0] else 0.0
    nz = [c for c in cfills if c > 0.0005]
    grow = (nz[-1] / nz[0]) if len(nz) >= 3 and nz[0] else 0.0
    grow_h = (cbh[-1] / cbh[0]) if cbh[0] else 1.0
    grow_w = (cbw[-1] / cbw[0]) if cbw[0] else 1.0

    # 与 motion 同口径：起点/终点端点比对求过渡跨度
    _s, _e, intervals = transition_span(step, lum, mass)
    act_frames = intervals + 1 if (intervals or abs(d_lum) > 0.8 or abs(d_mass) > 0.02) else 0
    # 控件级放宽：ROI 只框住一个控件，83ms 的快档在 30fps 下常常一帧就位，
    # 用整屏那套「跨多帧且方向一致」会误判成没动。但也要防「填色被误认成位移」：
    # 单帧位移必须够大（≥8px，真实 knob/thumb 的典型行程），或有多帧同向支撑。
    peak_step = max(step) if step else 0.0
    moved_at = [i for i in range(1, len(step)) if step[i] >= 1.0]
    sign_ok = False
    if len(moved_at) >= 2:
        sg = [np.sign(sdx[i]) if abs(sdx[i]) >= abs(sdy[i]) else np.sign(sdy[i])
              for i in moved_at]
        sign_ok = (min(sg) == max(sg))
    moved = ((peak_step >= 8.0 and total_shift >= 5.0)
             or (sign_ok and total_shift >= 3.0))

    form, why = "无变化", "选区在窗口内没有可测变化"
    if act_frames == 0:
        if peak_fill > 0.02:
            form = "信号过弱(weak)"
            why = (f"选区里确实有变化（占 {peak_fill * 100:.1f}%），但被大面积静止背景稀释到阈值以下；"
                   f"请把 ROI 收紧到控件本身")
        elif short_side and short_side < 40:
            form = "无变化"
            why = "所有指标都在噪声内，且选区过小（<40px），边缘效应可能吃掉信号"
        else:
            form = "无变化"
            why = "所有指标都在噪声内"
    elif moved:
        axis = "水平" if abs(total_dx) >= abs(total_dy) else "垂直"
        big = abs(d_lum) >= 3.0 or abs(d_mass) >= 0.2
        form = "位移+淡变(move-fade)" if big else "位移(move)"
        why = (f"{axis}位移 {total_shift:.1f}px（最大单步 {peak_step:.1f}px）"
               + (f"，同时亮度Δ {d_lum:+.1f}（knob 滑动 + 轨道/底色过渡）" if big else
                  "（switch knob / slider thumb / 指示条滑动）"))
    elif intervals == 0:
        form, why = "瞬变(instant)", "状态在一帧内完成（违规：应有过渡）"
    elif grow >= 1.15 and max(grow_h, grow_w) >= 1.08:
        if grow_h >= 1.08 and grow_w < 1.08:
            form, why = "高度展开(expand)", f"变化区高度扩展 {grow_h:.2f}×，宽度基本不变"
        else:
            form, why = "缩放(scale)", f"变化区扩展 {grow_w:.2f}× / {grow_h:.2f}×"
    elif abs(d_lum) >= 1.2 or abs(d_mass) >= 0.12:
        form, why = "填充淡变(fill-fade)", (f"亮度Δ {d_lum:+.1f}，结构能量Δ {d_mass * 100:+.0f}%"
                                           f"（hover / checked 的底色或描边过渡）")
    else:
        form, why = "描边/阴影变化(stroke)", "几何不变，仅边缘能量变化（焦点环 / 描边出现）"

    measured = (intervals + 1) * (1000.0 / (probe["fps"] or 30)) if intervals > 0 else 0.0
    short_side = min(roi[2], roi[3]) if roi[2] and roi[3] else 0
    if peak_fill and peak_fill < 0.05:
        conf = (f"低（变化只占选区 {peak_fill * 100:.1f}%，选区过大导致信号被稀释；"
                f"请收紧 ROI 到控件本身）")
    elif short_side and short_side < 40:
        conf = f"中（选区短边 {short_side}px，偏小，边缘效应会干扰位移估计）"
    elif act_frames >= 2:
        conf = "高"
    else:
        conf = "中"
    payload = {
        "window": {"t0_ms": t0, "t1_ms": t1, "frames": len(times)},
        "roi": {"name": name, "box": list(roi)},
        "form": form, "reason": why,
        "form_confidence": conf,
        "roi_short_side": short_side,
        "active_frames": act_frames,
        "measured_ms": round(measured, 1),
        "tier": nearest_tier(measured, probe["fps"]) if measured > 0 else None,
        "noise_floor": round(noise, 3),
        "shift_px": {"dx": round(total_dx, 1), "dy": round(total_dy, 1),
                     "total": round(total_shift, 1)},
        "delta_lum": round(d_lum, 2),
        "series": {"step": round_list(step), "lum": round_list(lum),
                   "mass": round_list(mass), "cbw": cbw, "cbh": cbh,
                   "cfill": round_list(cfills, 4)},
    }
    (work / "micro").mkdir(exist_ok=True)
    (work / "micro" / (slug(name) + ".json")).write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    tier = payload["tier"] or {}
    print(f"[{name}] 形式判定：{form}")
    print(f"  依据      {why}")
    print(f"  判定可信度 {conf}")
    print(f"  活动帧 {act_frames} → 约 {payload['measured_ms']}ms"
          f"（{tier.get('tier')}ms 档，可信度 {tier.get('confidence')}）")


# ---------------------------------------------------------------- measure

def cmd_measure(args):
    work = work_dir(args)
    probe = load_probe(work)
    if args.frame:
        pass
    scale = 1.0
    calib_note = "未标定（假定录屏像素 = CSS px，即 100% 缩放且未缩放录制）"
    t0 = args.at_ms
    t1 = args.at_ms + 1 if args.at_ms is not None else None

    rois = [parse_roi(s) for s in (args.roi or [])]
    if not rois:
        die("至少给一个 --roi name:x,y,w,h")

    calib = None
    if args.calib:
        cname, croi, known = parse_calib(args.calib)
        calib = (cname, croi, known)
        need = rois + [(cname, croi)]
    else:
        need = rois

    times, series = measure_window(args.video, 0 if t0 is None else t0,
                                   (probe["duration_ms"] if t1 is None else t1), need, probe)
    if not times:
        die("解码不到帧")
    mid = len(times) // 2

    if calib:
        cname, croi, known = calib
        m = series[cname][mid]
        observed = m["bh"]
        if observed > 0:
            scale = known / observed
            calib_note = (f"以 {cname} 标定：已知 {known}px / 帧内 {observed}px"
                          f" → 缩放系数 {scale:.3f}")

    out = {"scale": round(scale, 4), "calibration": calib_note, "frame_ms": times[mid], "controls": []}
    print(f"标定：{calib_note}")
    print(f"{'控件':<16}{'帧内宽(px)':>12}{'换算宽(px)':>12}{'换算高(px)':>12}")
    for name, roi in rois:
        m = series[name][mid]
        w_px, h_px = m["bw"] * scale, m["bh"] * scale
        out["controls"].append({
            "name": name, "box": list(roi),
            "raw_w": m["bw"], "raw_h": m["bh"],
            "css_w": round(w_px, 1), "css_h": round(h_px, 1),
        })
        print(f"{name:<16}{m['bw']:>12}{w_px:>12.1f}{h_px:>12.1f}")
    (work / "measure.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    print("\n提示：圆角半径在压缩录屏里不可靠，报告只写「有/无 + 相对大小」，"
          "精确值以 official-values.md 的 4px/8px 为准。")


def parse_calib(s: str):
    """name:x,y,w,h:known_px"""
    parts = s.split(":")
    if len(parts) != 3:
        die(f"--calib 格式应为 name:x,y,w,h:known_px，收到：{s}")
    name, body, known = parts
    x, y, w, h = (int(float(p)) for p in body.split(","))
    return name, (x, y, w, h), float(known)


# ---------------------------------------------------------------- sheet

def cmd_sheet(args):
    if Image is None:
        die("缺少 Pillow")
    work = work_dir(args)
    frames_dir = work / "frames"
    files = sorted(frames_dir.glob("*.png"))
    if not files:
        die("frames/ 为空，先跑 extract")
    timeline = None
    if (work / "timeline.json").exists():
        timeline = load_timeline(work)

    # contact sheet
    cols = args.cols
    pick = files if len(files) <= args.max_frames else [
        files[int(round(i * (len(files) - 1) / (args.max_frames - 1)))]
        for i in range(args.max_frames)]
    thumbs = []
    for p in pick:
        im = Image.open(p).convert("RGB")
        w = args.thumb_width
        im = im.resize((w, max(2, int(im.height * w / im.width))), Image.LANCZOS)
        canvas = Image.new("RGB", (im.width, im.height + 16), (18, 18, 18))
        canvas.paste(im, (0, 16))
        ImageDraw.Draw(canvas).text((3, 2), p.stem, fill=(210, 210, 210))
        thumbs.append(canvas)
    rows = math.ceil(len(thumbs) / cols)
    cw = max(t.width for t in thumbs)
    ch = max(t.height for t in thumbs)
    sheet = Image.new("RGB", (cw * cols, ch * rows), (10, 10, 10))
    for i, t in enumerate(thumbs):
        sheet.paste(t, ((i % cols) * cw, (i // cols) * ch))
    out = work / "contact-sheet.png"
    sheet.save(out)
    print(f"contact sheet → {out} ({len(thumbs)} 帧)")

    # motion strips：直接从视频按段窗口逐帧解码（不能用 frames/ 的抽样帧，
    # 一个 250ms 的转场在均匀抽样里往往只剩 1~2 帧，看不出运动）
    if timeline and args.video:
        sdir = work / "motion-strips"
        sdir.mkdir(exist_ok=True)
        for seg in timeline["segments"]:
            ims = []
            for ms, arr in iter_gray(Path(args.video),
                                     t0_ms=max(0.0, seg["t0_ms"] - 40),
                                     t1_ms=seg["t1_ms"] + 40, gray=False):
                im = Image.fromarray(arr)
                w = args.thumb_width
                im = im.resize((w, max(2, int(im.height * w / im.width))), Image.LANCZOS)
                cv = Image.new("RGB", (im.width, im.height + 14), (18, 18, 18))
                cv.paste(im, (0, 14))
                ImageDraw.Draw(cv).text((2, 1), f"{ms:.0f}ms", fill=(235, 235, 235))
                ims.append(cv)
            if not ims:
                continue
            if len(ims) > 14:
                ims = [ims[int(round(i * (len(ims) - 1) / 13))] for i in range(14)]
            strip = Image.new("RGB", (sum(i.width for i in ims), max(i.height for i in ims)),
                              (10, 10, 10))
            x = 0
            for i in ims:
                strip.paste(i, (x, 0))
                x += i.width
            strip.save(sdir / f"{seg['id']}.png")
            print(f"帧条 → {sdir / (seg['id'] + '.png')} ({len(ims)} 帧)")


def cmd_compare(args):
    if Image is None:
        die("缺少 Pillow")
    work = work_dir(args)
    video_img = work / "frames" / f"f{args.frame:05d}.png"
    if not video_img.exists():
        cand = sorted((work / "frames").glob("*.png"))
        if not cand:
            die("frames/ 为空，先跑 extract")
        video_img = min(cand, key=lambda p: abs(int(p.stem[1:]) - args.frame))
    name, roi = parse_roi(args.roi)
    shot = Path(args.template_shot).expanduser().resolve()
    if not shot.exists():
        die(f"模板截图不存在：{shot}")
    a = Image.open(video_img).convert("RGB").crop(
        (roi[0], roi[1], roi[0] + roi[2], roi[1] + roi[3]))
    b = Image.open(shot).convert("RGB")
    target_h = max(a.height, b.height) * 2
    a = a.resize((max(1, int(a.width * target_h / a.height * 0.5)), target_h // 1), Image.LANCZOS)
    b = b.resize((max(1, int(b.width * target_h / b.height * 0.5)), target_h // 1), Image.LANCZOS)
    gap = 16
    canvas = Image.new("RGB", (a.width + b.width + gap, a.height + 22), (14, 14, 14))
    canvas.paste(a, (0, 22))
    canvas.paste(b, (a.width + gap, 22))
    d = ImageDraw.Draw(canvas)
    d.text((4, 5), f"VIDEO {video_img.stem}", fill=(240, 240, 240))
    d.text((a.width + gap + 4, 5), "TEMPLATE", fill=(240, 240, 240))
    d.text((4, 22 + a.height - 14), f"{roi[2]}x{roi[3]}", fill=(160, 160, 160))
    outdir = work / "forms"
    outdir.mkdir(exist_ok=True)
    out = outdir / (slug(name) + ".png")
    canvas.save(out)
    print(f"并排图 → {out}（左=视频，右=模板；统一高度对齐）")


# ---------------------------------------------------------------- report

REPORT_TEMPLATE = """# 视频对齐分析报告 · {stem}

> 生成时间 {now} ｜ 工具 `analyze_video.py`
> **范围约定**：本报告只分析**整屏动效**、**控件形态及其动效**；**颜色不作参考**（一律沿用官方 `--fl-*` token）。

## 1. 元信息与可信度

| 项 | 值 |
|---|---|
| 文件 | `{video_name}` |
| 编码 / 像素格式 | {codec} / {pix_fmt} |
| 尺寸 | {width} × {height} |
| 帧率 | **{fps:.2f} fps**（帧间隔 {frame_interval_ms}ms） |
| 时长 / 帧数 | {duration_ms:.0f}ms / {frame_count} |
| 码率 | {bitrate_kbps:.0f} kbps（{bpp} bit/px/帧） |
| 关键帧间隔 | {gop_seconds}s |

**本次结论的精度上限**

{resolvable}

{probe_warnings}

## 2. 整屏动效清单与类型判定（核心）

{segments_table}

{stagger_block}

## 3. 整屏动效质量体检（核心）

{quality_block}

## 4. 编排与节奏

{rhythm_block}

## 5. 浮层与遮罩动效

{overlay_block}

## 6. 控件形态清单

<!-- 由人工/代理填写：逐控件结构、高度、圆角、描边、内部部件、部件间距，对照模板类；
     差异指向 forms/ 下并排图。自动量测结果见 measure.json。 -->

| 控件 | 视频形态 | 模板实现 | 差异 | 并排图 |
|---|---|---|---|---|
|  |  |  |  |  |

## 7. 控件动效矩阵

{control_motion}

<!-- 行=控件，列=状态转换；每格写：形式 + 幅度 + 档位 + 置信度 + 时间码 -->

| 控件 | hover | pressed | focus | checked | expanded | selected |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

## 8. 差异清单与改动建议

<!-- 每条指向具体文件/选择器/属性，并标注会触发的校验器规则号 -->

| 优先级 | 差异 | 落点 | 规则风险 |
|---|---|---|---|
| P0 |  |  |  |

## 9. 偏离登记表

<!-- 视频里有、但官方规范没有的做法；不擅自跟，等用户裁决 -->

| 做法 | 时间码 | 官方是否有对应 | 建议 |
|---|---|---|---|
|  |  |  |  |

## 10. 附录

- contact sheet：`contact-sheet.png`
- 动效帧条：`motion-strips/`
- 控件并排图：`forms/`
- 原始指标：`timeline.json`、`motion/*.json`、`micro/*.json`、`measure.json`

**颜色未作参考**：本报告不含任何取色结论，界面颜色一律以 `official-values.md` 的官方 token 为准。
"""


def cmd_report(args):
    work = work_dir(args)
    probe = load_probe(work)
    timeline = load_timeline(work)
    motions = []
    for p in sorted((work / "motion").glob("*.json")) if (work / "motion").exists() else []:
        motions.append(json.loads(p.read_text(encoding="utf-8")))
    micros = []
    for p in sorted((work / "micro").glob("*.json")) if (work / "micro").exists() else []:
        micros.append(json.loads(p.read_text(encoding="utf-8")))

    fps = probe["fps"] or 30.0
    fi = 1000.0 / fps

    resolvable = ["| 官方档位 | 该档位帧数 | 结论 |", "|---|---|---|"]
    for t in TIERS:
        n = t / fi
        resolvable.append(f"| {t}ms（{TIER_NAMES[t]}） | {n:.1f} 帧 | "
                          f"{'可测' if n >= 4 else ('勉强' if n >= 3 else '**不可分辨**')} |")

    seg_rows = ["| 段 | 起止(ms) | 时长 | 活动帧 | 档位判定 |", "|---|---|---|---|---|"]
    noise_n = 0
    for s in timeline["segments"]:
        if s.get("noise"):
            noise_n += 1
            continue
        tg = s.get("tier_guess") or {}
        tier_txt = ("**瞬变**（单帧完成）" if s.get("instant")
                    else f"{tg.get('tier', '—')}ms（{tg.get('confidence', '—')}）")
        seg_rows.append(f"| {s['id']} | {s['t0_ms']:.0f} – {s['t1_ms']:.0f} | "
                        f"{s['duration_ms']:.0f}ms | {s['active_frames']} | {tier_txt} |")
    if noise_n:
        seg_rows.append(f"\n> 另有 {noise_n} 段变化面积 <1%（压缩噪声级），已忽略。")

    detail = []
    for m in motions:
        w = m["window"]
        for name, r in m["analysis"].items():
            if "error" in r:
                detail.append(f"- `{name}`: {r['error']}")
                continue
            q = r["quality"]
            t_obj = r["tier"] or {}
            tier_txt = (f"档位 **{t_obj['tier']}ms**，可信度 {t_obj.get('confidence')}"
                        if t_obj else "不给档位（单帧完成，无过渡）")
            detail.append(
                f"**{name}**（窗口 {w['t0_ms']:.0f}–{w['t1_ms']:.0f}ms）\n"
                f"- 类型：`{r['kind']}` — {r['detail']}\n"
                f"- 时长：活动 {r['active_frames']} 帧 ≈ {r['measured_ms']}ms → {tier_txt}\n"
                f"- 位移：{r['shift_px']['total']}px "
                f"(dx {r['shift_px']['dx']}, dy {r['shift_px']['dy']})；"
                f"内容量变化 {r['delta_mass_pct']:+.0f}%\n"
                f"- 缓动形状：{r['easing_shape']}（源：{r['easing_source']}）\n"
                f"- 质量：{q['jitter']}；{q['stacking']}；{q['smoothness']}；{q['overlap']}\n")
    segments_table = "\n".join(seg_rows)
    if detail:
        segments_table += "\n\n### 逐段量测明细\n\n" + "\n".join(detail)

    stag = [m["stagger"]["summary"] for m in motions if m.get("stagger")]
    stagger_block = ("**错峰编排**：" + "；".join(stag)) if stag else "本次未测到多 ROI 错峰。"

    # 质量汇总
    qlines = []
    bad = 0
    for m in motions:
        for name, r in m["analysis"].items():
            if "error" in r or "quality" not in r:
                continue
            q = r["quality"]
            flag = "通过" if q.get("ok") else "**存在问题**"
            if not q.get("ok"):
                bad += 1
            qlines.append(f"- `{name}`（{m['window']['t0_ms']:.0f}–{m['window']['t1_ms']:.0f}ms）："
                          f"{flag} — {q['jitter']}；{q['stacking']}；{q['smoothness']}；{q['overlap']}")
    quality_block = "\n".join(qlines) if qlines else "尚无 motion 数据，先跑 `motion`。"
    if bad:
        quality_block += f"\n\n合计 **{bad}** 处需要处理（对应「抖 / 跳 / 生硬」三类症状）。"

    micro_block = []
    for mm in micros:
        micro_block.append(
            f"- `{mm['roi']['name']}`：**{mm['form']}** — {mm['reason']}"
            f"（活动 {mm['active_frames']} 帧 ≈ {mm['measured_ms']}ms，"
            f"档位 {(mm['tier'] or {}).get('tier')}ms，"
            f"可信度 {(mm['tier'] or {}).get('confidence')}）")
    control_motion = "\n".join(micro_block) if micro_block else \
        "尚无 micro 数据（用 `micro --roi name:x,y,w,h --from/--to` 量控件级微动效）。"

    rhythm_lines = []
    if stag:
        rhythm_lines.append("**错峰编排（stagger）**：" + "；".join(stag))
    else:
        rhythm_lines.append("**错峰编排**：未测到（要么是同步入场，要么没给 ≥2 个 ROI）。")
    rhythm_lines.append("")
    rhythm_lines.append("**连续操作与中断**（需人工看帧或用 `quality` 复测）："
                        "快速连点是否残留、离场是否可中断、被打断后是否有元素卡在半途。")
    rhythm_block = "\n".join(rhythm_lines)
    overlay_block = ("浮层段见第 2 节对应时间码；重点看入场方向、scale 幅度、"
                     "Scrim/Smoke 是否参与过渡（第 3 节 overlap 字段）。")

    text = REPORT_TEMPLATE.format(
        stem=Path(args.video).stem,
        now=__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
        video_name=Path(args.video).name,
        codec=probe["codec"], pix_fmt=probe["pix_fmt"],
        width=probe["width"], height=probe["height"],
        fps=fps, frame_interval_ms=probe["frame_interval_ms"],
        duration_ms=probe["duration_ms"], frame_count=probe["frame_count"],
        bitrate_kbps=probe["bitrate_kbps"], bpp=probe["bits_per_pixel_frame"],
        gop_seconds=probe["gop_seconds"],
        resolvable="\n".join(resolvable),
        probe_warnings=("\n".join("- ⚠️ " + w for w in probe["warnings"])
                        if probe["warnings"] else "- 无素材质量告警"),
        segments_table=segments_table,
        stagger_block=stagger_block,
        quality_block=quality_block,
        rhythm_block=rhythm_block,
        control_motion=control_motion,
        overlay_block=overlay_block,
    )
    out = work / "report.md"
    out.write_text(text, encoding="utf-8")
    print(f"报告 → {out}")
    print("第 6/7/8/9 节是结构化骨架，需按本片内容填写（自动量测数据已放在附录与第 2/3 节）。")


# ---------------------------------------------------------------- CLI

def build_parser():
    p = argparse.ArgumentParser(
        description="从录屏反解 Win11 Fluent 的整屏动效与控件形态（颜色不参考）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="典型流程：probe → segments → motion --seg s1 → quality → micro → extract → sheet → report")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, need_video=True):
        if need_video:
            sp.add_argument("video", help="视频文件路径")
        sp.add_argument("--work", help="工作目录（默认 video-analysis/<视频名>）")
        sp.add_argument("--json", action="store_true", help="输出 JSON")

    sp = sub.add_parser("probe", help="元信息与素材质量")
    common(sp)
    sp.set_defaults(func=cmd_probe)

    sp = sub.add_parser("demo", help="生成带已知动效的合成片用于自检")
    sp.add_argument("--out", default="demo-motion.mp4")
    sp.set_defaults(func=cmd_demo)

    sp = sub.add_parser("encode", help="把帧序列编码成 CFR mp4")
    sp.add_argument("frames", help="帧目录（f00000.png ...）")
    sp.add_argument("--out", required=True, help="输出 mp4 路径")
    sp.add_argument("--fps", type=float, default=30.0)
    sp.set_defaults(func=cmd_encode)

    sp = sub.add_parser("extract", help="导出采样静帧供人眼查看")
    common(sp)
    sp.add_argument("--count", type=int, default=60, help="均匀抽样帧数（默认 60）")
    sp.add_argument("--all", action="store_true", help="导出全部帧")
    sp.add_argument("--every", type=int, default=1, help="配合 --all 时的步长")
    sp.set_defaults(func=cmd_extract)

    sp = sub.add_parser("segments", help="切分静态段/动效段")
    common(sp)
    sp.add_argument("--threshold", type=float, help="变化像素占比阈值（默认 0.0015）")
    sp.add_argument("--gap", type=int, default=1, help="段内允许夹的静止帧数")
    sp.add_argument("--min-frames", type=int, default=1,
                    help="最短活动帧数（默认 1，保留单帧瞬变，正是要抓的「瞬变」缺陷）")
    sp.set_defaults(func=cmd_segments)

    for cmd, fn, helptext in (("motion", cmd_motion, "多 ROI 整屏级量测"),
                              ("quality", cmd_quality, "整屏动效质量体检")):
        sp = sub.add_parser(cmd, help=helptext)
        common(sp)
        sp.add_argument("--seg", help="用 timeline 里的段 id（如 s1）")
        sp.add_argument("--from", dest="from_ms", type=float, help="窗口起点 ms")
        sp.add_argument("--to", dest="to_ms", type=float, help="窗口终点 ms")
        sp.add_argument("--name", help="本次量测名称（决定输出文件名）")
        sp.add_argument("--pad", type=float,
                        help="窗口两侧各扩多少 ms（默认 2 帧，防首尾缓动被切）")
        sp.add_argument("--roi", action="append",
                        help="ROI：name:x,y,w,h（可多次）；motion 默认整屏")
        sp.set_defaults(func=fn)

    sp = sub.add_parser("micro", help="控件级微动效形式判定")
    common(sp)
    sp.add_argument("--seg")
    sp.add_argument("--from", dest="from_ms", type=float)
    sp.add_argument("--to", dest="to_ms", type=float)
    sp.add_argument("--name")
    sp.add_argument("--pad", type=float)
    sp.add_argument("--roi", action="append", help="控件选区 name:x,y,w,h")
    sp.set_defaults(func=cmd_micro)

    sp = sub.add_parser("measure", help="标定尺度并量控件几何")
    common(sp)
    sp.add_argument("--roi", action="append", help="name:x,y,w,h（可多次）")
    sp.add_argument("--calib", help="标定：name:x,y,w,h:known_px")
    sp.add_argument("--at-ms", type=float, help="取哪一时刻的帧（默认整段中位帧）")
    sp.add_argument("--frame", type=int)
    sp.set_defaults(func=cmd_measure)

    sp = sub.add_parser("sheet", help="contact sheet 与动效帧条")
    common(sp)
    sp.add_argument("--cols", type=int, default=6)
    sp.add_argument("--thumb-width", type=int, default=320)
    sp.add_argument("--max-frames", type=int, default=36)
    sp.set_defaults(func=cmd_sheet)

    sp = sub.add_parser("compare", help="视频控件区域 × 模板控件截图 并排图")
    common(sp)
    sp.add_argument("--frame", type=int, default=0, help="用哪一帧（帧序号）")
    sp.add_argument("--roi", required=True, help="视频里控件的 name:x,y,w,h")
    sp.add_argument("--template-shot", required=True, help="模板控件截图 PNG 路径")
    sp.set_defaults(func=cmd_compare)

    sp = sub.add_parser("report", help="汇总 report.md")
    common(sp)
    sp.set_defaults(func=cmd_report)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
