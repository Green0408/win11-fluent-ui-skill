#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""run_lint_tests.py —— 校验器自测：坏例必须命中、正常例必须 0 误报

用法： python tests/run_lint_tests.py
退出码：0=全部符合预期；1=有不符预期的用例

每个坏例在临时目录里复制一份真实资产（tokens/controls/motion.css/motion.js + 页面），
只注入一处违规，然后跑 ../check_ui_conventions.py，断言：
  1) 退出码 1
  2) stdout 里出现对应规则号（如 R20）
正常例（模板、自测页、四种处方拆装）断言退出码 0 且「合计未通过：0」。
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECK = ROOT / "check_ui_conventions.py"
ASSETS = ["fluent2-tokens.css", "fluent2-controls.css", "fluent2-motion.css", "fluent2-motion.js"]
PY = sys.executable

# 坏例：规则号 -> (要改的文件, 原文, 替换成)
BAD_CASES = {
    "R20": ("fluent2-motion.css",
            "from { transform: translate3d(var(--fl-page-from-x, 0px), var(--fl-page-from-y, 0px), 0); }",
            "from { transform: translate3d(176px, 0, 0); }"),
    "R21": ("fluent2-motion.js",
            'inEl.style.setProperty("--fl-page-from-y", inY);',
            'inEl.style.setProperty("--fl-page-unused", inY);'),
    "R22": ("fluent2-tool-starter.html",
            'data-kind="drill" data-page="page-detail"',
            'data-kind="drill" data-page="page-detail" data-dir="upward"'),
    "R23": ("fluent2-motion.css",
            "animation-timing-function: var(--fl-ease-steps-60);",
            "animation-timing-function: var(--fl-ease-standard);"),
    "R24": ("fluent2-motion.css",
            "  .fl-page-in {\n    animation: none !important;",
            "  .fl-page-unused {\n    animation: none !important;"),
    "R25": ("fluent2-controls.css",
            ".fl-btn:hover { background: var(--fl-control-fill-secondary); }",
            ".fl-btn:hover { transition: background var(--fl-dur-fast) var(--fl-ease-linear); }"),
    "R26": ("fluent2-controls.css",
            "background: var(--fl-solid-bg-base); overflow: clip;",
            "background: var(--fl-solid-bg-base);"),
    # ---- R27~R34：控件与方向的结构性规则（针对"只有一种符号 / 只有一半状态"类缺陷）----
    "R27": ("fluent2-motion.js",
            'up:      { axis: "y",  sign: -1 },',
            'upward:  { axis: "y",  sign: -1 },'),
    "R28": ("fluent2-motion.js",
            'up:      { axis: "y",  sign: -1 },',
            'up:      { axis: "y",  sign: 1 },'),
    "R29": ("fluent2-controls.css",
            '.fl-listitem[aria-selected="true"]:hover { background: var(--fl-subtle-fill-pressed); }',
            ""),
    "R30": ("fluent2-controls.css",
            "  grid-template-columns: var(--fl-check-col) minmax(0, 1fr);",
            "  display: flex;"),
    "R31": ("fluent2-controls.css",
            ".fl-list-sub { color: var(--fl-text-secondary); }",
            '.fl-list-sub { color: var(--fl-text-secondary); }\n.fl-check .fl-box::after { content: "✓"; }'),
    "R32": ("fluent2-motion.css",
            "  .fl-check-glyph path,",
            "  .fl-unused-glyph,"),
    "R33": ("fluent2-tool-starter.html",
            'aria-haspopup="listbox" aria-expanded="false" aria-controls="combo-view-list"',
            'aria-haspopup="listbox" aria-controls="combo-view-list"'),
    "R34": ("fluent2-controls.css",
            "  position: fixed; z-index: 40;",
            "  position: absolute; z-index: 40;"),
    # 图省事写成 100% × pct：两端会偏半个 thumb，肉眼几乎看不出来，靠这条规则锁
    "R35": ("fluent2-controls.css",
            "  --fl-slider-fill: calc(var(--fl-slider-inner) / 2\n"
            "                   + (100% - var(--fl-slider-inner)) * var(--fl-slider-pct));",
            "  --fl-slider-fill: calc(100% * var(--fl-slider-pct));"),
    "R36": ("fluent2-controls.css",
            "  --fl-slider-accent: color-mix(in srgb, var(--fl-accent-fill) 90%, var(--fl-text-primary));",
            "  --fl-slider-accent: var(--fl-accent-fill-hover);"),
    "R37": ("fluent2-controls.css",
            "  padding: var(--fl-space-1) var(--fl-btn-pad-h);",
            "  padding: var(--fl-space-3) var(--fl-btn-pad-h) var(--fl-space-2) var(--fl-btn-pad-h);"),
    # 暗主题的 accent 换成亮主题的深蓝 → 两档亮度相等，R38 应判"写反"
    "R38": ("fluent2-tokens.css",
            "  --fl-accent-fill: #60CDFF;",
            "  --fl-accent-fill: #005FB8;"),
    # 弹层去掉 fl-scroll → 出现原生滚动条
    "R39": ("fluent2-tool-starter.html",
            'class="fl-combo-popup fl-overlay fl-scroll"',
            'class="fl-combo-popup fl-overlay"'),
    # 设置行行高改成字面量 → 不再走 --fl-settings-row-h
    "R40": ("fluent2-controls.css",
            "  min-height: var(--fl-settings-row-h);",
            "  min-height: 56px;"),
    # 指示条挂上了独立层，但没关掉每项的 ::before → 同屏两条胶囊
    "R46a": ("fluent2-controls.css",
             '.fl-nav[data-fl-indicator="on"] .fl-nav-item[aria-current="page"]::before { content: none; }',
             '/* removed */'),
    # 容器没有定位基准 → 指示条会相对更外层定位
    "R46b": ("fluent2-controls.css",
             "  position: relative;          /* 指示条层的定位基准（.fl-nav-ind 的 offsetParent） */",
             ""),
    # 指示条峰值按 |Δ| 派生 → 会从旧项一路盖到新项、跨过项间隙（"跑出按钮"）
    "R47a": ("fluent2-motion.js",
             "    var peak = Math.min(IND_PEAK_SCALE, cap);",
             "    var peak = (size.h + Math.abs(d)) / size.h;"),
    # 峰值写死比例但删掉常量 → 相当于把"固定 1.6×"的结论丢了，改项高就会越界
    "R47b": ("fluent2-motion.js",
             "    var peak = Math.min(IND_PEAK_SCALE, cap);",
             "    var peak = Math.min(1.6, cap);"),
    # 缩放写死倍数 → 带不上环宽补偿，外框跟着一起变大（模板只缩内点）
    "R48a": ("fluent2-controls.css",
             '.fl-slider:not(:disabled):hover::-webkit-slider-thumb  {\n  --fl-slider-scale: 1.1667;                              /* 12 → 14 */\n  transition-duration: var(--fl-dur-control-normal);      /* 放大 250ms */\n}',
             ".fl-slider:not(:disabled):hover::-webkit-slider-thumb  { transform: scale(1.167); }"),
    # hover 改外框直径 → 外框尺寸不恒定
    "R48b": ("fluent2-controls.css",
             '.fl-slider:not(:disabled):hover::-webkit-slider-thumb  {\n  --fl-slider-scale: 1.1667;                              /* 12 → 14 */\n  transition-duration: var(--fl-dur-control-normal);      /* 放大 250ms */\n}',
             ".fl-slider:not(:disabled):hover::-webkit-slider-thumb  { --fl-slider-thumb: 24px; }"),
    # hover 没把时长抬到 250ms → 放大/缩小一个速率
    "R48d": ("fluent2-controls.css",
             '.fl-slider:not(:disabled):hover::-webkit-slider-thumb  {\n  --fl-slider-scale: 1.1667;                              /* 12 → 14 */\n  transition-duration: var(--fl-dur-control-normal);      /* 放大 250ms */\n}',
             ".fl-slider:not(:disabled):hover::-webkit-slider-thumb  { --fl-slider-scale: 1.1667; "
             "transition-duration: var(--fl-dur-control-fast); }"),
    # 环宽算在父级 .fl-slider 上 → 按静止态算死，hover 时外框变 22（真踩过的坑）
    "R48c": ("fluent2-controls.css",
             "  --fl-slider-ring: calc((var(--fl-slider-thumb) / var(--fl-slider-scale) - "
             "var(--fl-slider-inner)) / 2);\n  /* 盒子恒为静止内点（12），尺寸靠 transform 缩放 → "
             "合成器逐帧插值，不经过 layout 取整 */",
             "  /* 盒子恒为静止内点（12），尺寸靠 transform 缩放 → 合成器逐帧插值，不经过 layout 取整 */"),
    # 尺寸动效改回过渡 width → layout 取整成 3 级台阶（"跳一下"，不是曲线）
    "R48e": ("fluent2-controls.css",
             '  transition:\n    transform var(--fl-dur-control-fast) var(--fl-ease-standard),\n    box-shadow var(--fl-dur-control-fast) var(--fl-ease-standard);',
             "  transition://n    width var(--fl-dur-control-fast) var(--fl-ease-standard),\n"
             "    box-shadow var(--fl-dur-control-fast) var(--fl-ease-standard);"),
    # 下拉列表改回位移 → 应该是「揭示」
    "R49d": ("fluent2-motion.css",
             "  clip-path: inset(-24px);\n  transition: clip-path var(--fl-dur-popup) var(--fl-ease-popup),",
             "  transform: translateY(0);\n  transition: transform var(--fl-dur-popup) var(--fl-ease-popup),"),
    # 下拉列表缓动退回 ControlFastOutSlowIn(0,0,0,1) → 起手只到 45%，看起来"先顿一下再冲"
    "R49f": ("fluent2-motion.css",
             "  transition: clip-path var(--fl-dur-popup) var(--fl-ease-popup),",
             "  transition: clip-path var(--fl-dur-popup) var(--fl-ease-standard),"),
    # 位置退回"挂在按钮下方一条缝" → 选中项不在按钮上
    "R49g": ("fluent2-motion.js",
             "      var top = Math.round(r.top - off);",
             "      var top = Math.round(r.bottom + 4);"),
    # 下拉列表关闭加了退场动画 → 录屏里是单帧瞬变
    "R49e": ("fluent2-motion.css",
             "  /* 关闭瞬变：录屏里没有退场动画，硬切 */\n  transition: none;",
             "  transition: clip-path var(--fl-dur-control-fast) var(--fl-ease-soft);"),
    # 弹出层加回 scale → 不再是官方的 fade + 平移
    "R49a": ("fluent2-motion.css",
             "  transform: translateY(calc(var(--fl-popup-shift) * var(--fl-popup-dir)));",
             "  transform: translateY(calc(var(--fl-popup-shift) * var(--fl-popup-dir))) scale(0.98);"),
    # 位移写死 8px（旧实现）→ 与官方建议的 50px 不符
    "R49b": ("fluent2-motion.css",
             "  --fl-popup-shift: 50px;   /* 官方建议的移动距离 */",
             "  --fl-popup-shift: 8px;"),
    # 对话框也带上了位移 → 对话框只许淡入淡出
    "R49c": ("fluent2-motion.css",
             "  opacity: 1;\n  visibility: visible;\n  pointer-events: auto;",
             "  opacity: 1;\n  transform: translateY(50px);\n  visibility: visible;\n  pointer-events: auto;"),
    # 滚动条拖动态把透明边框收到 0 → thumb 画满 12px，太粗
    # 悬停态只写 border-width（没有 style）→ 等于没有边框，thumb 回弹成 12px
    "R43a": ("fluent2-controls.css",
             "    border: 2px solid transparent;          /* 12 - 2×2 = 视觉 8px */",
             "    border-width: 2px;"),
    # 悬停态把边框收成 0 → 同样画满命中区
    "R43b": ("fluent2-controls.css",
             "    border: 2px solid transparent;          /* 12 - 2×2 = 视觉 8px */",
             "    border: 0;"),
    # 悬停态漏掉 background-clip → 回退 border-box，画满命中区
    "R43c": ("fluent2-controls.css",
             "    background-clip: content-box;\n    border: 2px solid transparent;          /* 12 - 2×2 = 视觉 8px */",
             "    border: 2px solid transparent;          /* 12 - 2×2 = 视觉 8px */"),
    # 变粗条件挂到容器上 → .fl-page:hover 恒真，整页滚动条永远粗着
    "R45": ("fluent2-controls.css",
            "  :is(.fl-scroll, .fl-page, .fl-nav)::-webkit-scrollbar-thumb:hover,\n"
            "  :is(.fl-scroll, .fl-page, .fl-nav)::-webkit-scrollbar-thumb:active {",
            "  :is(.fl-scroll, .fl-page, .fl-nav):hover::-webkit-scrollbar-thumb {"),
    # 弹层去掉 max-width → nowrap 长选项把弹层撑到视口外，右侧滚动条被窗口裁掉
    "R44a": ("fluent2-controls.css",
             "  max-width: calc(100vw - var(--fl-space-4));\n",
             ""),
    # 选项去掉省略号 → 长文本撑宽弹层
    "R44b": ("fluent2-controls.css",
             "  overflow: hidden;\n  text-overflow: ellipsis;\n",
             ""),
    # place() 用 getBoundingClientRect 量宽 → 入场 scale(0.98) 让读数少 2%，钳制失效
    "R44c": ("fluent2-motion.js",
             "      var w = popup.offsetWidth;",
             "      var w = popup.getBoundingClientRect().width;"),
    # 页面不再是滚动容器 → 内容区无法独立滚动
    "R42": ("fluent2-controls.css",
            "  overflow-y: auto; overflow-x: hidden;   /* 每个页面各自滚，切页各记各的位置 */",
            "  overflow: visible;"),
    # 去掉入页延迟 → 两页同时进出，会重影
    "R41": ("fluent2-motion.css",
            "  animation-delay: calc(var(--fl-dur-normal) * 0.8);",
            ""),
}

# 处方：按模块名整块删除（与 FLUENT-COMPOSE.md 的四种处方一致）
PRESCRIPTIONS = {
    "A-单页": ["nav", "list-detail", "settings-panel", "flyout", "dialog", "infobar"],
    "B-列表详情": ["grid", "settings-panel", "flyout", "dialog"],
    "C-网格详情": ["toolbar", "list-detail", "settings-panel", "dialog", "infobar"],
    "D-设置": ["nav", "toolbar", "list-detail", "flyout", "dialog", "infobar"],
}


def run(target, cwd):
    r = subprocess.run([PY, str(CHECK), target.name], cwd=str(cwd),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def stage(case_dir):
    for a in ASSETS:
        shutil.copy(ROOT / a, case_dir / a)
    shutil.copy(ROOT / "fluent2-tool-starter.html", case_dir / "fluent2-tool-starter.html")
    shutil.copy(ROOT / "selftest.html", case_dir / "selftest.html")


def remove_module(html, name):
    m = re.search(r"<!-- 模块：%s -->" % re.escape(name), html)
    if not m:
        return html
    nxt = re.search(r"<!-- 模块：", html[m.end():])
    end = m.end() + nxt.start() if nxt else len(html)
    return html[:m.start()] + html[end:]


def check_tokens_in_sync():
    """资产一致性：在临时目录重跑 extract_tokens.py，断言产物与仓库内的完全一致。

    这是「tokens 是脚本生成的，勿手改」这条纪律的唯一机械保障 ——
    手改 fluent2-tokens.css 能过所有 lint，却会在下次重生成时被静默抹掉。
    """
    print("== 资产一致性（tokens 必须由脚本生成）==")
    import filecmp
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        shutil.copy(ROOT / "extract_tokens.py", td / "extract_tokens.py")
        shutil.copytree(ROOT / "raw", td / "raw")
        r = subprocess.run([PY, "extract_tokens.py"], cwd=str(td),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(f"  ✗ extract_tokens.py 执行失败\n    {r.stderr.strip()[:300]}")
            return 1
        bad = 0
        for name in ("fluent2-tokens.css", "official-values.json", "official-values.md"):
            same = filecmp.cmp(ROOT / name, td / name, shallow=False)
            print(f"  {name}  {'✓ 与脚本产物一致' if same else '✗ 与脚本产物不一致（被手改过？）'}")
            if not same:
                bad += 1
        return bad


def main():
    bad_ok = bad_fail = 0
    print("== 坏例（应命中）==")
    for rule, (fname, old, new) in BAD_CASES.items():
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            stage(td)
            p = td / fname
            text = p.read_text(encoding="utf-8")
            if old not in text:
                print(f"  {rule}  ✗ 夹具失效：{fname} 里找不到待替换片段")
                bad_fail += 1
                continue
            p.write_text(text.replace(old, new, 1), encoding="utf-8")
            code, out = run(td / "fluent2-tool-starter.html", td)
            base = re.match(r"R\d+", rule).group(0)   # R44a → R44：一个规则可以有多份坏例
            hit = base in out
            ok = code == 1 and hit
            print(f"  {rule}  {'✓' if ok else '✗'}  exit={code} hit={hit}")
            if not ok:
                print("    " + "\n    ".join(out.strip().splitlines()[:6]))
                bad_fail += 1
            else:
                bad_ok += 1

    print("== 正常例（应 0 误报）==")
    pos_ok = pos_fail = 0
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        stage(td)
        for name in ("fluent2-tool-starter.html", "selftest.html"):
            code, out = run(td / name, td)
            ok = code == 0 and "合计未通过：0" in out
            print(f"  {name}  {'✓' if ok else '✗'}  exit={code}")
            if not ok:
                print("    " + "\n    ".join(out.strip().splitlines()[:8]))
                pos_fail += 1
            else:
                pos_ok += 1

        src = (ROOT / "fluent2-tool-starter.html").read_text(encoding="utf-8")
        for label, mods in PRESCRIPTIONS.items():
            h = src
            for m in mods:
                h = remove_module(h, m)
            p = td / f"presc_{label}.html"
            p.write_text(h, encoding="utf-8")
            code, out = run(p, td)
            ok = code == 0 and "合计未通过：0" in out
            print(f"  处方 {label}  {'✓' if ok else '✗'}  exit={code}")
            if not ok:
                print("    " + "\n    ".join(out.strip().splitlines()[:8]))
                pos_fail += 1
            else:
                pos_ok += 1

    bad_sync = check_tokens_in_sync()

    print(f"\n坏例命中 {bad_ok}/{len(BAD_CASES)}，正常例通过 {pos_ok}/{2 + len(PRESCRIPTIONS)}，"
          f"资产一致性不符 {bad_sync}")
    return 0 if (bad_fail == 0 and pos_fail == 0 and bad_sync == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
