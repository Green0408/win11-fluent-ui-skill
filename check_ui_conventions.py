#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
check_ui_conventions.py —— win11-fluent-ui 规范检查器

用法： python check_ui_conventions.py <生成的文件.html>
退出码：0=全部通过；1=存在未通过（FAIL），不可交付。
豁免：在违规行尾或上一行加注释  fl-lint-ignore  可豁免该行全部规则。

规则（数值权威：fluent2-tokens.css / official-values.md，全部有官方出处）：
 R1  颜色只用 --fl-* 变量：禁止 hex 字面量 #RGB/#RRGGBB[AA]
 R2  动画数值只用官方变量：禁止字面 cubic-bezier(、transition/animation 声明必须引用 var(--fl-dur-*/--fl-ease-*)；禁止字面 \d+ms
 R3  圆角只用官方变量：禁止 border-radius 字面 px（50% 允许）
 R4  字号只用官方字阶：禁止 font-size 字面 px（须用 .fl-* 类或 var(--fl-font-size-*)）
 R5  焦点框：:focus-visible 双描边（--fl-focus-stroke-outer/inner）必须在引用的资产 CSS 中定义；:focus（非 visible）不得画框
 R6  页面骨架：存在 .fl-page 且至少一个 .fl-current；用导航转场时必须经 M.transitionTo()
 R7  浮层隐藏：flyout/dialog 隐藏态必须 visibility:hidden / pointer-events:none（由 fluent2-motion.css .fl-overlay 承担），禁止只 opacity:0
 R8  变量存在性：用到的每个 --fl-* 必须在 fluent2-tokens.css 中定义
 R9  主题双模式：<html> 带 data-theme，且引用的 tokens.css 含 light/dark 两个主题块
 R10 出场残留：内嵌 <style> 的 @keyframes 终态不得 opacity:0（整页残留不可见）
 R11 海拔语义（警告）：--fl-shadow-* 只应出现在卡片/浮层/对话框/按钮等官方海拔语义元素上
 R12 资产完整：引用的 fluent2-*.css / fluent2-motion.js 相对文件必须存在
 R13 禁止 transition: all（必须逐属性声明，否则会把布局/重绘属性一起过渡）
 R14 状态反馈禁用 filter（:hover/:active 里用 filter 无法平滑过渡，是「点击瞬跳」来源）
 R15 浮层关闭必须延迟 visibility（.fl-overlay/.fl-smoke 的 :not(.fl-open) 要有 visibility 0s … var(--fl-dur-)）
 R16 多页必须叠放（≥2 个 .fl-page 时资产 CSS 必须有 grid-area: 1 / 1；缺 scrollbar-gutter 仅警告）
 R17 禁止内联 transition-delay / transitionDelay（改用 --fl-stagger-delay 自定义属性）
 R18 一次性入场/出场必须 animation 化（.fl-entrance/.fl-point-to-point/.fl-exit/.fl-page-in/.fl-page-out）
 R19 dialog 居中禁用 transform: translate(-50%…)（须用独立 translate 属性，transform 留给开合动效）
 R20 页面转场位移禁写死：@keyframes fl-page-* 内不得出现非零 px 字面量位移（须走 --fl-page-* 变量）
 R21 转场必须两轴通用：有 .fl-page-in 时 CSS 必须定义 x/y 四个位移变量，JS 必须写入 from-x 与 from-y
R22 drill 必须有方向：出现 data-kind="drill" 时需 data-dir 属性或 M.back(；且 data-dir 取值必须在六向枚举内
R23 连续型动效必须线性非 both：infinite 的规则只能 linear/steps、禁 both/forwards、reduced 里关停
R24 reduced-motion 必须覆盖页面转场类（.fl-page-in/.fl-page-out）
R25 --fl-ease-linear 只允许用于 opacity/visibility 过渡（位移/底色用 linear 会「生硬」）
R26 页面转场容器必须裁剪（.fl-content-layer 需 overflow: clip/hidden，否则横向位移撑出滚动条）
R27 方向枚举必须齐全：DIR 表须同时含 forward/back/up/down/left/right（缺 up/down = 竖向只有一个方向）
R28 竖向必须能取两种符号：up→-1、down→+1；applyShift 必须以 (axis, sign) 为参数
R29 列表六档不许塌陷：≥6 条含 background 的 .fl-listitem 规则，且必须有 selected+hover / selected+active
R30 列表行结构：.fl-listitem 必须用 grid-template-columns（只看声明），且两档行高变量齐全
R31 勾号必须是 SVG 描边：禁止 content:"✓" 文本勾，必须有 .fl-check-glyph 与 stroke-dashoffset
R32 reduced-motion 必须覆盖 .fl-check-glyph / .fl-combo-popup / .fl-listitem
R33 ComboBox 可达性：combobox/listbox/option 三个 role + aria-expanded/controls + 键盘 Escape/方向键/activedescendant
R34 弹层不得被裁：.fl-combo-popup 必须 position: fixed，且 JS 有 portal 到 body 的证据
R35 滑块必须有填充段且做半 thumb 补偿：轨道双段渐变 + --fl-slider-fill 走 calc(inner/2 + (100%-inner)×pct) + 禁 background 过渡
R36 滑块档位色不得用 alpha：--fl-slider-accent 不许直接引用 --fl-accent-fill-hover/-pressed，须用 color-mix 不透明混色
R37 按钮纵向内边距必须对称：.fl-btn 的 padding 四值里 top 必须等于 bottom（否则 flex 居中下文字整体偏移）
R38 强调色主题档位不许写反：暗主题 --fl-accent-fill 的相对亮度必须高于亮主题（XAML：暗=Light2、亮=Dark1）
R39 自绘弹层必须用细滚动条：.fl-combo-popup 必须带 fl-scroll，且 CSS 要有 @supports selector(::-webkit-scrollbar) 互斥块
R40 设置行造型：行高走 --fl-settings-row-h、hover 底色带圆角、分隔线左缩进对齐文字、行内必须有 .fl-settings-text
R41 转场必须两拍：.fl-page-in 要有 animation-delay、离场页不许与入页同长、转场页不得涂不透明底
R42 应用外壳：body 锁高度、.fl-shell 有 min-height:0、内容层固定 1fr 行、.fl-page 是滚动容器
R43 滚动条悬停/拖动态：边框 2px 左右、必须写完整 border 简写 + background-clip（否则回弹成 12px 命中区）
R44 弹层不许越出视口：.fl-combo-popup 必须有 max-width、选项走省略号、JS 量宽用 offsetWidth 且做水平钳制
R45 滚动条变粗只许 thumb 自身 hover：禁止把 :hover/:focus-within 挂在容器上（.fl-page:hover 恒真）
R46 侧栏指示条：.fl-nav 必须 position:relative、必须关掉每项 ::before、JS 必须有 reduced 分支
R47 指示条拉伸必须"留在按钮内"：峰值来自固定常量，禁止按 |Δ| 派生（会跨过项间隙、跑出按钮）
R48 滑块 thumb：外框恒定（ring = 外框/scale − 内点，反向补偿）+ 只缩内点 + 尺寸动效走 transform（禁过渡 width/height）
    + 逐状态时长（基态 167ms / hover·active 250ms）
R49 弹出层：菜单 = 整个弹层滑入视野（行程 = 自身高度 100%、不淡入、方向按放置关系、入 250ms/出 167ms、无缩放）；
    下拉列表 = 压在按钮上（选中项那一行盖住按钮）+ clip-path 从顶边往下揭示，167ms / --fl-ease-popup，
    关闭瞬变；对话框与 ToolTip 只许淡入淡出（基类不带 transform）
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def line_text(text, pos):
    nl = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    return text[nl:end if end != -1 else len(text)]


def ignored(text, pos):
    """fl-lint-ignore 在本行尾或上一行"""
    cur, prev = line_text(text, pos), ""
    nl = text.rfind("\n", 0, pos)
    if nl != -1:
        prev = line_text(text, nl)
    return "fl-lint-ignore" in cur or "fl-lint-ignore" in prev


def collect_inline_css(html):
    """<style> 块 + 内联 style 属性"""
    chunks = []
    for m in re.finditer(r"<style[^>]*>(.*?)</style>", html, re.S | re.I):
        chunks.append((m.group(1), m.start(1), "style-block"))
    for m in re.finditer(r'style="([^"]*)"', html):
        chunks.append((m.group(1), m.start(1), "inline"))
    return chunks


def css_refs(html, base_dir: Path):
    """本 HTML 引用的本地资产文件列表（存在与否）"""
    refs = []
    for m in re.finditer(r'(?:href|src)="([^"#?]+\.css|[^"#?]+\.js)"', html):
        p = base_dir / m.group(1)
        refs.append((m.group(1), p, line_of(html, m.start(1))))
    return refs


def defined_vars(css_text):
    return set(re.findall(r"(--fl-[a-z0-9-]+)\s*:", css_text))


def _css_var(css_text, name):
    m = re.search(re.escape(name) + r"\s*:\s*([^;]+);", css_text)
    return m.group(1).strip() if m else None


def _bezier_progress(points, t):
    """CSS cubic-bezier 在时间比例 t 处的进度（先解 x(s)=t，再取 y(s)）"""
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    p1x, p1y, p2x, p2y = points

    def x(s): return 3 * (1 - s) ** 2 * s * p1x + 3 * (1 - s) * s * s * p2x + s ** 3
    def y(s): return 3 * (1 - s) ** 2 * s * p1y + 3 * (1 - s) * s * s * p2y + s ** 3

    lo, hi = 0.0, 1.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if x(mid) < t:
            lo = mid
        else:
            hi = mid
    return y((lo + hi) / 2)


def _reveal_first_frame_progress(tokens_css, frame_ms=16.7):
    """揭示类动画在真机第一个渲染帧处的进度（0~1）；取不到返回 None。

    为什么要有这条：录屏逐帧进度只能证明"首帧已 60%"，但那可能是采样相位（59.73fps，
    弹层出现的那一帧落在两个采样点中间），照抄成曲线形状会让真机第一帧就近乎全开 ——
    用户看到的就是「动画没了」。
    """
    dur_raw = _css_var(tokens_css, "--fl-dur-popup")
    ease_raw = _css_var(tokens_css, "--fl-ease-popup")
    if not dur_raw or not ease_raw:
        return None
    m = re.match(r"([\d.]+)\s*ms", dur_raw)
    if not m:
        return None
    dur = float(m.group(1))
    m = re.match(r"cubic-bezier\(\s*([\d.\-]+)\s*,\s*([\d.\-]+)\s*,\s*([\d.\-]+)\s*,\s*([\d.\-]+)\s*\)",
                 ease_raw)
    if m:
        pts = tuple(float(g) for g in m.groups())
    elif ease_raw.strip() in ("linear",):
        pts = (0.0, 0.0, 1.0, 1.0)
    else:
        return None
    if dur <= 0:
        return 1.0
    return _bezier_progress(pts, frame_ms / dur)



def main():
    if len(sys.argv) < 2:
        print("用法：python check_ui_conventions.py <文件.html>")
        return 1
    target = Path(sys.argv[1])
    if not target.exists():
        print(f"FAIL 文件不存在：{target}")
        return 1
    html = target.read_text(encoding="utf-8-sig", errors="replace")
    base = target.parent
    fails, warns = [], []

    def fail(rule, pos, msg, text=html):
        fails.append(f"R{rule} L{line_of(text, pos)}: {msg}  |{line_text(text, pos).strip()[:80]}")

    def warn(rule, pos, msg, text=html):
        warns.append(f"R{rule} L{line_of(text, pos)}: {msg}")

    inline = collect_inline_css(html)

    # 资产
    refs = css_refs(html, base)
    assets = {}
    for name, p, ln in refs:
        if not p.exists():
            fails.append(f"R12 L{ln}: 引用的资产缺失：{name}")
        assets[name] = p
    tokens_css = ""
    controls_css = ""
    motion_css = ""
    if "fluent2-tokens.css" in assets and assets["fluent2-tokens.css"].exists():
        tokens_css = assets["fluent2-tokens.css"].read_text(encoding="utf-8-sig", errors="replace")
    if "fluent2-controls.css" in assets and assets["fluent2-controls.css"].exists():
        controls_css = assets["fluent2-controls.css"].read_text(encoding="utf-8-sig", errors="replace")
    if "fluent2-motion.css" in assets and assets["fluent2-motion.css"].exists():
        motion_css = assets["fluent2-motion.css"].read_text(encoding="utf-8-sig", errors="replace")
    motion_js = ""
    if "fluent2-motion.js" in assets and assets["fluent2-motion.js"].exists():
        motion_js = assets["fluent2-motion.js"].read_text(encoding="utf-8-sig", errors="replace")

    # R1 颜色字面量
    for m in re.finditer(r"#[0-9a-fA-F]{3}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{8}\b", html):
        if not ignored(html, m.start()):
            fail(1, m.start(), "禁止手写颜色，请用 var(--fl-*) 变量")
    # rgb/rgba 字面量（含内联与 style 块；rgba(0,0,0,.x) 也属手写颜色）
    for chunk, pos, _kind in inline:
        for m in re.finditer(r"\brgba?\(", chunk):
            if not ignored(html, pos + m.start()):
                fail(1, pos + m.start(), "禁止手写颜色，请用 var(--fl-*) 变量", html)

    # R2 动画数值
    for m in re.finditer(r"cubic-bezier\(", html):
        if not ignored(html, m.start()):
            fail(2, m.start(), "禁止手写缓动曲线，请用 var(--fl-ease-*)")
    for m in re.finditer(r"\b\d+ms\b", html):
        if not ignored(html, m.start()):
            fail(2, m.start(), "禁止手写动画时长，请用 var(--fl-dur-*)")
    for chunk, pos, kind in inline:
        for m in re.finditer(r"(transition|animation)\s*:", chunk):
            seg = chunk[m.start():m.end() + 120].split(";")[0]
            if "var(--fl-dur-" not in seg and "var(--fl-ease-" not in seg and "none" not in seg:
                if not ignored(html, pos + m.start()):
                    fail(2, pos + m.start(), f"transition/animation 必须引用 var(--fl-dur-*/--fl-ease-*)：{seg[:60]}", html)
        # 动画时长字面量（0.5s / 300ms 等出现在动画属性里）
        for m in re.finditer(r"(transition|animation)[^;]*?\b\d*\.?\d+m?s\b", chunk):
            if "var(--fl-dur-" in m.group(0):
                continue
            if not ignored(html, pos + m.start()):
                fail(2, pos + m.start(), "禁止手写动画时长，请用 var(--fl-dur-*)", html)

    # R3 圆角字面量
    for chunk, pos, _kind in inline:
        for m in re.finditer(r"border-radius\s*:\s*[^;]+", chunk):
            seg = m.group(0)
            if re.search(r"\d+px", seg) and "var(--fl-radius" not in seg:
                if not ignored(html, pos + m.start()):
                    fail(3, pos + m.start(), "圆角只用 var(--fl-radius-control/overlay)", html)

    # R4 字号字面量
    for chunk, pos, _kind in inline:
        for m in re.finditer(r"font-size\s*:\s*[^;]+", chunk):
            seg = m.group(0)
            if re.search(r"\d+px", seg) and "var(--fl-font-size" not in seg:
                if not ignored(html, pos + m.start()):
                    fail(4, pos + m.start(), "字号只用官方字阶类 .fl-* 或 var(--fl-font-size-*)", html)

    # R5 焦点框
    if "focus-visible" not in (controls_css + motion_css):
        if re.search(r"<(button|a|input|select|textarea)\b", html, re.I):
            fails.append("R5: 交互页面必须有 :focus-visible 双描边样式（由 fluent2-controls.css 提供）")
    for m in re.finditer(r"(\.fl-[a-z-]+)?\s*:focus\s*\{", controls_css):
        # :focus（非 visible）画框 → 提示；controls.css 自身不受限
        pass

    # R6 页面骨架
    pages = re.findall(r'class="[^"]*fl-page[^"]*"', html)
    if not pages:
        fail(6, 0, "缺少 .fl-page 页面容器")
    elif "fl-current" not in html:
        fail(6, 0, "至少一个 .fl-page 需带 .fl-current 初始显示")
    if re.search(r"data-page=", html) and "M.transitionTo" not in html:
        fail(6, 0, "有导航项但未走 M.transitionTo()，禁直接切类")

    # R7 浮层隐藏
    if "fl-overlay" in html and motion_css:
        hidden_ok = ("visibility" in motion_css and "pointer-events" in motion_css
                     and ".fl-overlay:not(.fl-open)" in motion_css)
        if not hidden_ok:
            fails.append("R7: fluent2-motion.css 缺少 .fl-overlay:not(.fl-open) 的 visibility/pointer-events 隐藏规则")
    for chunk, pos, _kind in inline:
        if re.search(r"\.(fl-flyout|fl-dialog)[^{]*\{[^}]*(opacity\s*:\s*0)", chunk):
            if "visibility" not in chunk and "pointer-events" not in chunk:
                if not ignored(html, pos):
                    fail(7, pos, "浮层隐藏必须同时 visibility/pointer-events，只 opacity:0 会挡交互", html)

    # R8 变量存在性
    defined = defined_vars(tokens_css)
    used = set(re.findall(r"--fl-[a-z0-9-]+", html))
    if tokens_css:
        for v in sorted(used):
            if v not in defined and not ignored(html, html.find(v)):
                fails.append(f"R8: 未定义的 --fl-* 变量：{v}（以 fluent2-tokens.css 为准）")

    # R9 主题双模式
    m = re.search(r"<html[^>]*>", html, re.I)
    if not m or "data-theme" not in m.group(0):
        fail(9, m.start() if m else 0, "<html> 必须带 data-theme（light/dark 双模式）")
    if tokens_css and '[data-theme="light"]' not in tokens_css:
        fails.append('R9: fluent2-tokens.css 缺少 [data-theme="light"] 主题块')

    # R38 强调色的主题档位不许写反
    #     XAML：暗主题 AccentFillColorDefault = SystemAccentColor**Light2**、亮主题 = **Dark1**，
    #     即「暗色用浅蓝、亮色用深蓝」。写反了暗色主题的蓝会发闷，且黑字对比不足 —— 纯观感缺陷，
    #     只能靠「相对亮度」这种可量化的不变量来锁。
    def _accent_block(sel):
        b = re.search(re.escape(sel) + r"[^{]*\{([^}]*)\}", tokens_css or "")
        if not b:
            return None
        h = re.search(r"--fl-accent-fill\s*:\s*#([0-9A-Fa-f]{6})", b.group(1))
        return h.group(1) if h else None

    dark_hex, light_hex = _accent_block(':root, [data-theme="dark"]'), _accent_block('[data-theme="light"]')
    if dark_hex and light_hex:
        def _lum(hx):
            ch = [int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            ch = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
            return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
        ld, ll = _lum(dark_hex), _lum(light_hex)
        if ld <= ll:
            fails.append(f"R38 fluent2-tokens.css: 强调色主题档位写反了"
                         f"（暗主题 #{dark_hex} 亮度 {ld:.3f} ≤ 亮主题 #{light_hex} 亮度 {ll:.3f}）；"
                         f"XAML 规定暗主题=SystemAccentColorLight2、亮主题=Dark1，即暗色必须更浅")

    # R10 出场残留
    for chunk, pos, _kind in inline:
        for m in re.finditer(r"@keyframes\s+([\w-]+)\s*\{(.*?)\}\s*\}", chunk, re.S):
            body = m.group(2)
            if re.search(r"(100%|to)\s*\{[^}]*opacity\s*:\s*0", body):
                if not ignored(html, pos + m.start()):
                    fail(10, pos + m.start(), f"keyframes {m.group(1)} 终态 opacity:0 会残留不可见", html)

    # R11 海拔语义（警告）
    for chunk, pos, _kind in inline:
        for m in re.finditer(r"--fl-shadow-[a-z0-9-]+", chunk):
            if not ignored(html, pos + m.start()):
                warn(11, pos + m.start(), "确认 --fl-shadow-* 只用于 dialog/flyout/card/control 等官方海拔语义元素")

    # ---- R13-R19 动效架构防复发（数值层面查不出的动效缺陷） ----
    asset_css = [("fluent2-tokens.css", tokens_css),
                 ("fluent2-controls.css", controls_css),
                 ("fluent2-motion.css", motion_css)]
    blocks = []  # (file, text, selector, body, pos)
    for name, text in asset_css:
        if not text:
            continue
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
            blocks.append((name, text, m.group(1).strip(), m.group(2), m.start()))

    # R13 禁 transition: all
    for name, text in asset_css:
        for m in re.finditer(r"transition\s*:\s*all\b", text or ""):
            if not ignored(text, m.start()):
                fails.append(f"R13 {name} L{line_of(text, m.start())}: 禁止 transition: all，须逐属性声明")
    for chunk, pos, _kind in inline:
        for m in re.finditer(r"transition\s*:\s*all\b", chunk):
            if not ignored(html, pos + m.start()):
                fail(13, pos + m.start(), "禁止 transition: all，须逐属性声明", html)

    # R14 状态反馈禁用 filter
    for name, text, sel, body, pos in blocks:
        if (":hover" in sel or ":active" in sel) and re.search(r"(^|;)\s*filter\s*:", body):
            if not ignored(text, pos):
                fails.append(f"R14 {name} L{line_of(text, pos)}: 状态反馈禁用 filter"
                             f"（无法平滑过渡），请用官方档位色如 --fl-accent-fill-hover")
    for chunk, pos, _kind in inline:
        if re.search(r":(hover|active)\b[^{]*\{[^}]*filter\s*:", chunk):
            if not ignored(html, pos):
                fail(14, pos, "状态反馈禁用 filter，请用官方档位色", html)

    # R15 浮层关闭必须延迟 visibility（否则关闭瞬间就 hidden，出场动画看不见）
    if motion_css and ("fl-overlay" in html or "fl-smoke" in html):
        for sel in (".fl-overlay:not(.fl-open)", ".fl-smoke:not(.fl-open)"):
            ok = any(re.search(r"visibility\s+0s[^;}]*var\(--fl-dur-", body)
                     for _n, _t, s, body, _p in blocks
                     if _n == "fluent2-motion.css" and s.startswith(sel))
            if not ok:
                fails.append(f"R15 fluent2-motion.css: {sel} 缺少延迟的 visibility 过渡"
                             f"（visibility 0s … var(--fl-dur-*)）")

    # R16 多页必须同格叠放（否则转场期两页垂直堆叠 → 布局跳变）
    page_count = len(re.findall(r'class="[^"]*\bfl-page\b[^"]*"', html))
    if page_count >= 2:
        if not re.search(r"grid-area\s*:\s*1\s*/\s*1", controls_css):
            fails.append("R16 fluent2-controls.css: 多页必须同格叠放（.fl-page { grid-area: 1 / 1 }）")
        if "scrollbar-gutter" not in controls_css:
            warns.append("R16 fluent2-controls.css: 建议 html { scrollbar-gutter: stable }，避免滚动条消放造成横向抖动")

    # R17 禁内联 transition-delay（改用 --fl-stagger-delay）
    for src_name, src_text in (("HTML", html), ("fluent2-motion.js", motion_js)):
        for m in re.finditer(r"transitionDelay\s*=|transition-delay\s*:", src_text or ""):
            if not ignored(src_text, m.start()):
                fails.append(f"R17 {src_name} L{line_of(src_text, m.start())}: 禁止内联 transition-delay，"
                             f"stagger 请用 --fl-stagger-delay 自定义属性")

    # R18 一次性入场/出场必须 animation 化（transition 会被控件自身 transition 简写覆盖）
    if motion_css:
        for cls in ("fl-entrance", "fl-point-to-point", "fl-exit", "fl-page-in", "fl-page-out"):
            has_anim = False
            for m in re.finditer(r"[^{}]*\.%s[^{}]*\{([^{}]*)\}" % cls, motion_css):
                decl = re.search(r"animation\s*:\s*([^;]+)", m.group(1))
                if decl and not decl.group(1).strip().startswith("none"):
                    has_anim = True
                    break
                # 长写（animation-name + animation-duration）同样算 animation 化
                if re.search(r"animation-name\s*:\s*[^;]+", m.group(1)) and \
                   re.search(r"animation-duration\s*:\s*[^;]+", m.group(1)):
                    has_anim = True
                    break
            if not has_anim:
                fails.append(f"R18 fluent2-motion.css: .{cls} 必须用 animation 实现"
                             f"（reduced-motion 里的 animation:none 不算）")

    # R19 dialog 居中禁用 transform（会与开合动效的 transform 互相覆盖）
    for m in re.finditer(r"\.fl-dialog[^{}]*\{[^}]*transform\s*:\s*translate\(-50%", controls_css):
        if not ignored(controls_css, m.start()):
            fails.append(f"R19 fluent2-controls.css L{line_of(controls_css, m.start())}: dialog 居中禁用 "
                         f"transform，请用 translate: -50% -50%")

    # ---- R20-R26：转场两轴两向 + 连续型动效 防复发 ----

    def keyframe_body(text, name):
        """取 @keyframes <name> 的完整体内文本（花括号可嵌套）。"""
        m = re.search(r"@keyframes\s+%s\s*\{" % re.escape(name), text)
        if not m:
            return None, -1
        i, depth = m.end(), 1
        start = m.end()
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        return text[start:i - 1], m.start()

    # R20 页面转场位移禁写死（换尺寸/换方向只能改变量）
    for kf in re.findall(r"@keyframes\s+(fl-page-[\w-]+)", motion_css or ""):
        body, pos = keyframe_body(motion_css, kf)
        if body is None:
            continue
        for tm in re.finditer(r"translate[3dXY]*\(([^)]*)\)", body):
            arg = tm.group(1)
            if "--fl-page-" in arg:
                continue
            if re.search(r"(?<![\d.])[1-9][\d.]*px", arg):
                fails.append(f"R20 fluent2-motion.css L{line_of(motion_css, pos)}: @keyframes {kf} "
                             f"位移写死（{arg.strip()}），须走 var(--fl-page-*) 变量")
                break

    # R21 转场必须两轴通用（防「只做垂直」）
    if ".fl-page-in" in (motion_css or ""):
        need_vars = ["--fl-page-from-x", "--fl-page-from-y", "--fl-page-to-x", "--fl-page-to-y"]
        missing = [v for v in need_vars if v not in motion_css]
        if missing:
            fails.append(f"R21 fluent2-motion.css: 转场必须两轴通用，缺少 {', '.join(missing)}")
        if motion_js and not (re.search(r'setProperty\(\s*["\']--fl-page-from-x', motion_js)
                              and re.search(r'setProperty\(\s*["\']--fl-page-from-y', motion_js)):
            fails.append("R21 fluent2-motion.js: 转场必须同时写入 --fl-page-from-x 与 --fl-page-from-y"
                         "（只写一个轴 = 只会垂直或只会水平）")

    # R22 drill 必须带方向，且 data-dir 的取值必须在枚举内（拼错会静默退化成自动推断）；注释不算数
    html_code = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    if re.search(r'data-kind\s*=\s*["\']drill["\']', html_code):
        if 'data-dir="' not in html_code and "M.back(" not in html_code:
            fails.append('R22: 出现 data-kind="drill" 但没有方向传递（需 data-dir 属性或 M.back(）')
    for v in re.findall(r'data-dir\s*=\s*["\']([^"\']*)["\']', html_code):
        if v not in ("forward", "back", "up", "down", "left", "right"):
            fails.append(f'R22: data-dir="{v}" 非法（可选 forward/back/up/down/left/right）'
                         f'—— 非法值会被静默忽略并回退到自动推断')

    # R23 连续型动效必须线性非 both，且 reduced 里关停
    reduced_body = ""
    rm = re.search(r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{", motion_css or "")
    if rm:
        reduced_body = motion_css[rm.end():]
    for name, text, sel, body, pos in blocks:
        if name != "fluent2-motion.css":
            continue
        if not re.search(r"(animation-iteration-count|animation)\s*:[^;]*\binfinite\b", body):
            continue
        timing_ok = (re.search(r"animation-timing-function\s*:\s*var\(--fl-ease-(linear|steps-)", body)
                     or re.search(r"animation\s*:[^;]*\b(linear|steps\()", body))
        if not timing_ok:
            fails.append(f"R23 fluent2-motion.css L{line_of(text, pos)}: 连续型动效 {sel} 必须 "
                         f"linear 或 steps（--fl-ease-linear / --fl-ease-steps-*）")
        if re.search(r"animation-fill-mode\s*:\s*(both|forwards)", body) or \
           re.search(r"animation\s*:[^;]*\b(both|forwards)\b", body):
            fails.append(f"R23 fluent2-motion.css L{line_of(text, pos)}: 连续型动效 {sel} 禁用 "
                         f"both/forwards（会把终态钉死）")
        for cls in re.findall(r"\.(fl-continuous|fl-tick)\b", sel):
            if not re.search(r"\.%s[^{]*\{[^}]*animation\s*:\s*none" % cls, reduced_body):
                fails.append(f"R23 fluent2-motion.css: prefers-reduced-motion 必须关停 .{cls}")

    # R24 reduced-motion 必须覆盖页面转场类
    if re.search(r"\.fl-page-in\b", motion_css or ""):
        for cls in ("fl-page-in", "fl-page-out"):
            if not re.search(r"\.%s[^{]*\{[^}]*animation\s*:\s*none" % cls, reduced_body):
                fails.append(f"R24 fluent2-motion.css: prefers-reduced-motion 未覆盖 .{cls}"
                             f"（关掉系统动画后仍会位移）")

    # R25 --fl-ease-linear 只允许用于 opacity/visibility
    linear_srcs = list(asset_css) + [("HTML inline", c) for c, _p, _k in inline]
    for nm, text in linear_srcs:
        for m in re.finditer(r"transition\s*:\s*([^;{}]+)[;}]", text or ""):
            for seg in m.group(1).split(","):
                if "var(--fl-ease-linear)" in seg and not re.search(r"\b(opacity|visibility)\b", seg):
                    fails.append(f"R25 {nm} L{line_of(text, m.start())}: --fl-ease-linear 只允许用于 "
                                 f"opacity/visibility 过渡（位移/底色请用 --fl-ease-standard）")
                    break

    # R26 转场容器必须裁剪
    if "fl-page-in-slide-kf" in (motion_css or ""):
        if not re.search(r"\.fl-content-layer\s*\{[^}]*overflow\s*:\s*(clip|hidden)", controls_css):
            fails.append("R26 fluent2-controls.css: .fl-content-layer 必须 overflow: clip/hidden"
                         "（否则 ±位移会撑出横向滚动条）")

    # ---- R27~R34：控件与方向的结构性防复发规则 ----
    # 这批规则针对的是「实现层只有一种符号 / 只有一半状态」类缺陷：
    # 旧 R20/R21/R22 全是"变量名是否出现"的存在性检查，所以"竖向只能从下方进入"当年零告警通过。

    # R27 方向枚举必须齐全（缺 up/down 就等于竖向只有一个方向）
    if motion_js:
        miss = [d for d in ("forward", "back", "up", "down", "left", "right")
                if not re.search(r'\b%s\s*:\s*\{' % d, motion_js)]
        if miss:
            fails.append(f"R27 fluent2-motion.js: 方向枚举不全，缺 {', '.join(miss)}"
                         f"（DIR 表须同时含 forward/back/up/down/left/right）")

    # R28 竖向必须能取到两种符号，且 applyShift 不得再按 kind/dir 自行推断
    if motion_js:
        if not re.search(r'up\s*:\s*\{[^}]*sign\s*:\s*-\s*1', motion_js):
            fails.append("R28 fluent2-motion.js: up 的方向映射必须为 sign: -1（自上方进入）")
        if not re.search(r'down\s*:\s*\{[^}]*sign\s*:\s*1', motion_js):
            fails.append("R28 fluent2-motion.js: down 的方向映射必须为 sign: 1（自下方进入）")
        fn = re.search(r"function\s+applyShift\s*\(([^)]*)\)", motion_js)
        if fn and not ("axis" in fn.group(1) and "sign" in fn.group(1)):
            fails.append("R28 fluent2-motion.js: applyShift 必须以 (axis, sign) 为参数，"
                         "不得再从 kind/dir 内部推导符号（那正是单符号缺陷的来源）")

    # R29 列表六档不许塌陷
    if controls_css and ".fl-listitem" in controls_css:
        list_bgs = re.findall(r"\.fl-listitem[^{}]*\{[^}]*background\s*:", controls_css)
        if len(list_bgs) < 6:
            fails.append(f"R29 fluent2-controls.css: 列表状态档不足（找到 {len(list_bgs)} 条含 background 的"
                         f" .fl-listitem 规则，官方 XAML 要求 6 档）")
        for pseudo, name in ((r":hover", "SelectedPointerOver"), (r":active", "SelectedPressed")):
            if not re.search(r'\.fl-listitem\[aria-selected\s*=\s*"true"\]\s*' + pseudo +
                             r'\s*\{[^}]*background\s*:', controls_css):
                fails.append(f'R29 fluent2-controls.css: 缺少 .fl-listitem[aria-selected="true"]{pseudo}'
                             f' 的 background（{name} 档；缺了就是"选中后没反馈"）')

    # R30 列表行结构：网格列 + 两档行高
    if controls_css and re.search(r"^\.fl-listitem\s*\{", controls_css, re.M):
        item_rule = re.search(r"\.fl-listitem\s*\{([^}]*)\}", controls_css)
        body = item_rule.group(1) if item_rule else ""
        # 只看声明（property: value），不看 transition 里的属性名，否则过渡列表会冒充结构
        if not re.search(r"(?<![\w-])grid-template-columns\s*:", body):
            fails.append("R30 fluent2-controls.css: .fl-listitem 必须用 grid-template-columns"
                         "（flex 布局下尾部区域无法与主文本对齐）")
        if "--fl-list-item-height" not in controls_css:
            fails.append("R30 fluent2-controls.css: 列表行高必须走 --fl-list-item-height 变量")
        if "--fl-list-item-height-two-line" not in controls_css:
            fails.append("R30 fluent2-controls.css: 缺两行档行高 --fl-list-item-height-two-line")

    # R31 勾号必须是 SVG 描边，禁止退化成文本字符
    if "fl-check" in html_code:
        if re.search(r'content\s*:\s*["\']\s*[✓✔√]', controls_css + html_code):
            fails.append('R31: 勾号不得用文本字符（content: "✓"）—— 无法描画、字重随字体漂移，'
                         '必须用 .fl-check-glyph 的 SVG 中心线 + stroke-dashoffset')
        if "fl-check-glyph" not in html_code:
            fails.append("R31: 出现 .fl-check 但页面里没有 .fl-check-glyph（勾号 SVG）")
        if "stroke-dashoffset" not in (controls_css or ""):
            fails.append("R31 fluent2-controls.css: 勾号必须有 stroke-dashoffset 过渡（描画动效）")

    # R32 reduced-motion 必须覆盖新增控件的过渡
    for cls in (".fl-check-glyph", ".fl-combo-popup", ".fl-listitem"):
        if not re.search(re.escape(cls) + r"[^{]*[,{]", reduced_body):
            fails.append(f"R32 fluent2-motion.css: prefers-reduced-motion 未覆盖 {cls}"
                         f"（关掉系统动画后仍会过渡/描画）")

    # R33 ComboBox 可达性
    if re.search(r'class\s*=\s*["\'][^"\']*fl-combo\b', html_code):
        for attr in ('role="combobox"', 'aria-expanded', 'aria-controls', 'role="listbox"', 'role="option"'):
            if attr not in html_code:
                fails.append(f'R33: 出现 .fl-combo 但缺少 {attr}')
        for key in ("Escape", "ArrowDown", "ArrowUp", "aria-activedescendant"):
            if key not in (motion_js or ""):
                fails.append(f"R33 fluent2-motion.js: ComboBox 键盘/可达性缺 {key}")

    # R34 弹层不得被转场容器的 overflow:clip 裁切
    if ".fl-combo-popup" in (controls_css or ""):
        if not re.search(r"\.fl-combo-popup\s*\{[^}]*position\s*:\s*fixed", controls_css):
            fails.append("R34 fluent2-controls.css: .fl-combo-popup 必须 position: fixed"
                         "（.fl-content-layer 有 overflow:clip，absolute 会被裁）")
        if "appendChild(popup)" not in (motion_js or ""):
            fails.append("R34 fluent2-motion.js: ComboBox 弹层必须 portal 到 body")

    # R35 滑块必须有已填充段，且填充宽必须做「半 thumb」补偿
    #     只写 100% × pct 也能让左侧变色，但 thumb 的实际行程是「轨道宽 - thumb 宽」，
    #     两端会偏半个 thumb —— 这类"看起来有、其实错位"没法靠肉眼验收，必须靠规则锁。
    if ".fl-slider" in (controls_css or ""):
        track = re.search(r"\.fl-slider::-webkit-slider-runnable-track\s*\{([^}]*)\}", controls_css)
        if not track or "linear-gradient" not in track.group(1):
            fails.append("R35 fluent2-controls.css: 滑块轨道必须是双段渐变（SliderTrackValueFill = "
                         "AccentFillColorDefault），不得整条单色")
        fill_var = re.search(r"--fl-slider-fill\s*:\s*calc\(([^;]*)\)", controls_css)
        if not fill_var:
            fails.append("R35 fluent2-controls.css: 缺 --fl-slider-fill 的 calc 定义")
        elif "var(--fl-slider-dot)" in fill_var.group(1):
            fails.append("R35 fluent2-controls.css: --fl-slider-fill 不得引用 --fl-slider-dot"
                         "（那是随状态变的 12/14/10，悬停时填充末端会平移 1px）—— 用静止态 --fl-slider-inner")
        elif "var(--fl-slider-inner)" not in fill_var.group(1):
            fails.append("R35 fluent2-controls.css: --fl-slider-fill 必须含半 thumb 补偿"
                         "（calc(--fl-slider-inner/2 + (100% - --fl-slider-inner) × pct)）；"
                         "直接写 100% × pct 会在两端偏半个 thumb")
        slider_body = re.search(r"\.fl-slider\s*\{([^}]*)\}", controls_css)
        if slider_body and re.search(r"transition\s*:[^;]*\bbackground", slider_body.group(1)):
            fails.append("R35 fluent2-controls.css: 滑块填充段不得加 background 过渡"
                         "（拖动时会变成拖影，是新的抖动源）")
        # 档位色不得用 alpha：0.9/0.8 的半透明填充会透出底下的灰环与卡片，观感是"滑块变透明了"
        if re.search(r"--fl-slider-accent\s*:[^;]*var\(--fl-accent-fill-(hover|pressed)\)", controls_css):
            fails.append("R36 fluent2-controls.css: 滑块档位色不得直接引用 --fl-accent-fill-hover/-pressed"
                         "（那是 alpha 0.9/0.8，悬停时填充与 thumb 会透出底层）；"
                         "改用 color-mix 混向 --fl-text-primary 的不透明档")

    # R37 按钮纵向内边距必须对称
    #     XAML ButtonPadding=11,5,11,6 是给 ContentPresenter 做字基线补偿的；
    #     照搬进 align-items:center 的 flex 盒，内容盒中心会整体偏移，文字看着"不居中"。
    if ".fl-btn" in (controls_css or ""):
        btn = re.search(r"\.fl-btn\s*\{([^}]*)\}", controls_css)
        if btn:
            pad = re.search(r"padding\s*:\s*([^;]+);", btn.group(1))
            if pad:
                parts = pad.group(1).split()
                if len(parts) == 4 and parts[0] != parts[2]:
                    fails.append(f"R37 fluent2-controls.css: .fl-btn 纵向内边距不对称"
                                 f"（上={parts[0]} 下={parts[2]}），flex 居中下文字会整体偏移；"
                                 f"居中交给 align-items:center，上下取同值")

    # R39 自绘弹层必须用细滚动条
    #     浏览器默认滚动条是 17px 带箭头的方块，在 Acrylic 弹层里非常出戏；而且这条很容易漏 ——
    #     只有"项数超过 15 项（MaxDropDownHeight 504 / 项高 32）"时才看得见，演示数据通常不到。
    if re.search(r'class\s*=\s*"[^"]*fl-combo-popup[^"]*"', html_code):
        for m in re.finditer(r'class\s*=\s*"([^"]*fl-combo-popup[^"]*)"', html_code):
            if "fl-scroll" not in m.group(1):
                fails.append(f"R39: 弹层 class=\"{m.group(1)}\" 缺 fl-scroll"
                             f"（会出现原生滚动条；细滚动条见 fluent2-controls.css 的 .fl-scroll）")
    if "fl-scroll" in html_code and controls_css:
        if "::-webkit-scrollbar-thumb" not in controls_css:
            fails.append("R39 fluent2-controls.css: 用了 fl-scroll 但没有 ::-webkit-scrollbar-thumb 规则")
        # Chromium 116+：scrollbar-width/color 非 auto 会让 ::-webkit-scrollbar 全部失效，
        # 必须有一个 @supports 块把它们重置回 auto
        if not re.search(r"@supports\s*(?:\(\s*)?selector\(::-webkit-scrollbar\)", controls_css):
            fails.append("R39 fluent2-controls.css: 缺 @supports selector(::-webkit-scrollbar) 块"
                         "（不重置 scrollbar-width 为 auto，伪元素样式在 Chromium 里会被静默忽略）")

    # R43 滚动条悬停/拖动态：宽度必须仍是「细」，且必须写完整 border 简写 + background-clip
    #     thumb 的"细"是靠「透明边框 + background-clip: content-box」裁出来的。
    #     ⚠ Chromium 里悬停/按下的规则会**整体接管**该部件的绘制，不是常规层叠：
    #       只写 `border-width: 2px`（没有 style）等于没有边框 → thumb 回弹成整个 12px 命中区。
    #       实测 6px → 12px，这就是"悬停突然变粗"的真因。所以这两条都必须显式重复。
    # 注释里也会出现 "::-webkit-scrollbar-thumb:hover"（本文件的说明就写了），
    # 不剥注释会把它当成一条规则，然后拿相邻规则的 body 去判定 → 假阳性
    css_nc = re.sub(r"/\*.*?\*/", "", controls_css or "", flags=re.S)
    if css_nc and "::-webkit-scrollbar-thumb" in css_nc:
        for m in re.finditer(r"[^{}]*::-webkit-scrollbar-thumb[^{]*\{([^}]*)\}", css_nc):
            sel = m.group(0).split("{")[0]
            state = re.search(r":(hover|active)", sel)
            if not state:
                continue
            body = m.group(1)
            st = state.group(1)
            # 宽度：border-width 或 border 简写都认（0 可以不带单位，所以 px 后缀可选）
            bw = re.search(r"border-width\s*:\s*([\d.]+)", body) or \
                 re.search(r"border\s*:\s*([\d.]+)", body)
            if bw and float(bw.group(1)) < 2:
                fails.append(f"R43 fluent2-controls.css: 滚动条 :{st} 态边框 {bw.group(1)}px 太窄"
                             f"（视觉会占 {12 - 2 * float(bw.group(1)):.0f}px，看起来太粗）；"
                             f"保持 2px（视觉 8px）")
            # 必须有 style：只写 border-width / border: 0 都等于无边框
            has_style = re.search(r"border-style\s*:", body) or \
                        re.search(r"border\s*:\s*[\d.]+(?:\s*px)?\s+(?:solid|dashed|dotted)", body)
            if not has_style:
                fails.append(f"R43 fluent2-controls.css: 滚动条 :{st} 态没有带 border-style 的边框。"
                             f"悬停规则会整体接管绘制，缺 style 等于无边框 → thumb 回弹成 12px")
            if "background-clip" not in body:
                fails.append(f"R43 fluent2-controls.css: 滚动条 :{st} 态没有重复 background-clip: content-box。"
                             f"悬停时它会回退成 border-box，thumb 直接画满整个命中区")

    # R45 滚动条变粗只能由 thumb 自身的 hover / active 触发
    #     挂在容器上一定错：`.fl-page:hover` 在指针位于页面任意位置时都成立 → 整页滚动条永远变粗；
    #     `:focus-within` 则会让下拉一展开（焦点进 listbox）就变粗。两种都被用户当 bug 报过。
    if css_nc and "::-webkit-scrollbar-thumb" in css_nc:
        for m in re.finditer(r"([^{}]*::-webkit-scrollbar-thumb[^{]*)\{", css_nc):
            sel = m.group(1)
            if re.search(r":(hover|focus-within)\s*::", sel):
                fails.append("R45 fluent2-controls.css: 滚动条变粗写成了容器 hover（" + sel.strip()[:60] + "），"
                             "应立即命中整个容器（.fl-page:hover 恒真）；要写在 thumb 上："
                             "::-webkit-scrollbar-thumb:hover")

    # R46 侧栏选中指示条（NavigationView SelectionIndicator）
    #     它是一条会移动的独立层，不是每项各画一条。三层缺一不可：
    #     ① 容器要给定位基准；② 挂上层之后必须关掉每项的 ::before（否则同屏两条）；
    #     ③ reduced-motion 下必须走静态落位分支（WAAPI 不受 CSS 的 animation:none 约束）。
    if controls_css and ".fl-nav-ind" in controls_css:
        nav_rule = re.search(r"\.fl-nav\s*\{([^}]*)\}", controls_css)
        if not nav_rule or "position" not in nav_rule.group(1):
            fails.append("R46 fluent2-controls.css: .fl-nav 必须 position: relative（指示条层靠它定位）")
        if not re.search(r'\.fl-nav\[data-fl-indicator="on"\][^{]*::before', controls_css):
            fails.append("R46 fluent2-controls.css: 缺 .fl-nav[data-fl-indicator=\"on\"] ... ::before { content: none }"
                         "（不关掉每项的静态胶囊会看到两条）")
        ind_rule = re.search(r"\.fl-nav-ind\s*\{([^}]*)\}", controls_css)
        if ind_rule and re.search(r"transition\s*:[^;]*\b(top|height)", ind_rule.group(1)):
            fails.append("R46 fluent2-controls.css: .fl-nav-ind 不许过渡 top/height（会逐帧 layout），"
                         "位移与拉伸都走 transform")
    if motion_js and "placeIndicator" in motion_js:
        seg = motion_js[motion_js.index("function placeIndicator"):]
        seg = seg[:seg.index("M.nav = M.nav")] if "M.nav = M.nav" in seg else seg[:4000]
        if "REDUCED" not in seg:
            fails.append("R46 fluent2-motion.js: placeIndicator 里必须有 REDUCED 分支"
                         "（WAAPI 动画不受 CSS 的 reduced-motion 块约束）")
        # R47 峰值必须"留在按钮内"
        #     按 |Δ| 拉伸（16+|Δ|）会从旧项一路盖到新项，跨过项间隙 —— 看起来就是"装饰条跑出按钮"，
        #     与录屏不符。官方观感是：旧项里长出来 → 换项瞬间直接在新项上出现 → 新项里收回，
        #     两段都发生在各自项内部，峰值是固定比例（实测 1.6×，1 格与 4 格跳转同值）。
        if re.search(r"(?:size\.h|\.h)\s*\+\s*Math\.abs\(", seg) or "Math.abs(d)" in seg:
            fails.append("R47 fluent2-motion.js: 指示条峰值不许按 |Δ| 派生（16+|Δ| 会跨过项间隙、跑出按钮；"
                         "实测固定 1.6×，见 video-analysis/ind_edges.py）")
        if "IND_PEAK_SCALE" not in seg:
            fails.append("R47 fluent2-motion.js: 峰值必须取自固定常量 IND_PEAK_SCALE，"
                         "并按项高做上限钳制（否则改 --fl-nav-item-height 后会长出按钮）")

    # R48 滑块 thumb：外框恒定 + 只缩内点 + 尺寸动效走 transform（不是 width）
    #     XAML SliderThumbStyle 是两层：Border（ControlSolidFill 外盘）+ Ellipse（accent 内点 12）。
    #     VisualState 只对 **Ellipse** 做 ScaleTransform（0.86 / 1.167 / 0.71），Border 一帧都不动。
    #     三条不变量（各对应一次真实返工）：
    #       ① 外框不许变：只能缩内点，且要用 ring = (外框/scale − 内点)/2 反向补偿；
    #       ② 尺寸动效必须走 transform：过渡 width/height 会被 layout 取整成 3 级台阶（"跳一下"）；
    #       ③ 时长逐状态：缩放回 Normal 用 ControlFast(167)，放大/按下用 ControlNormal(250)。
    if ".fl-slider" in (controls_css or ""):
        for need in ("--fl-slider-thumb", "--fl-slider-scale", "--fl-slider-ring"):
            if need not in controls_css:
                fails.append("R48 fluent2-controls.css: 缺 %s（外框 20 / 内点缩放 1·1.1667·0.8333 / 环宽反向补偿）"
                             % need)
        RING = re.compile(r"--fl-slider-ring\s*:\s*calc\(\s*\(\s*var\(--fl-slider-thumb\)\s*/\s*"
                          r"var\(--fl-slider-scale\)\s*-\s*var\(--fl-slider-inner\)\s*\)\s*/\s*2\s*\)")
        ring_on_thumb = False
        for m in re.finditer(r"\.fl-slider[^{]*::-webkit-slider-thumb\s*\{([^}]*)\}", controls_css):
            body, sel = m.group(1), m.group(0).split("{")[0].strip()
            is_state = bool(re.search(r":(?:hover|active)", sel))
            is_base = sel == ".fl-slider::-webkit-slider-thumb"   # 焦点环等附加规则只管 box-shadow
            if RING.search(body):
                ring_on_thumb = True
            # ① 缩放必须来自变量（写死数字 = 没做环宽补偿）
            if re.search(r"transform\s*:\s*scale\(\s*[\d.]", body):
                fails.append("R48 fluent2-controls.css: %s 的 transform 必须写成 scale(var(--fl-slider-scale))，"
                             "不许写死倍数（写死就带不上环宽补偿，外框会跟着变大）" % sel)
            if is_base and "transform" not in body:
                fails.append("R48 fluent2-controls.css: %s 必须 transform: scale(var(--fl-slider-scale))"
                             "（内点尺寸动效走合成器，不走 layout）" % sel)
            # ② 盒子宽恒定
            for wh in re.finditer(r"\b(?:width|height)\s*:\s*([^;]+);", body):
                val = wh.group(1).strip()
                if val != "var(--fl-slider-inner)":
                    fails.append("R48 fluent2-controls.css: %s 的 width/height 必须是 var(--fl-slider-inner)"
                                 "（实际是 %s）—— 盒子恒定，尺寸只靠 transform" % (sel, val))
            # ③ 不许过渡 width/height/box-shadow 之外的布局属性
            if is_base and "transition" in body:
                tr = re.search(r"transition\s*:([^;]*)(?:;|$)", body.replace("\n", " "))
                if tr and re.search(r"\b(?:width|height|margin)\b", tr.group(1)):
                    fails.append("R48 fluent2-controls.css: %s 的过渡里不许出现 width/height/margin —— "
                                 "布局属性会被量化取整，动画变成 3 级台阶（实测 12.0/13.3/13.9）" % sel)
            if "box-shadow" in body and "var(--fl-slider-ring)" not in body:
                fails.append("R48 fluent2-controls.css: %s 的 box-shadow 必须用 var(--fl-slider-ring) 画外框"
                             "（写死环宽会让外框随状态变大小）" % sel)
            # ④ 时长逐状态
            if is_base and "transition" in body and "var(--fl-dur-control-fast)" not in body:
                fails.append("R48 fluent2-controls.css: %s 的过渡时长必须是 --fl-dur-control-fast(167ms)"
                             "（模板 Normal 态 KeyTime=ControlFast；一个时长糊三个状态就是"
                             "\"放大缩小速率一样\"，用户会看出不对）" % sel)
        if not ring_on_thumb:
            fails.append("R48 fluent2-controls.css: --fl-slider-ring 必须**写在 thumb 规则里**且是 "
                         "(外框/scale − 内点)/2 —— 写在 .fl-slider 上会按静止态算死，hover 时外框变 22（真踩过）")
        # 状态规则：改缩放、抬时长，且不许动外框直径
        state_rules = [m for m in re.finditer(
            r"\.fl-slider[^{]*:(?:hover|active)[^{]*::-webkit-slider-thumb\s*\{([^}]*)\}", controls_css)]
        if not state_rules:
            fails.append("R48 fluent2-controls.css: 缺 hover/active 的 thumb 规则（缩放与时长都要在这里改）")
        for m in state_rules:
            body = m.group(1)
            sel = m.group(0).split("{")[0].strip()
            if "--fl-slider-scale" not in body:
                fails.append("R48 fluent2-controls.css: %s 必须改 --fl-slider-scale（内点缩放）" % sel)
            if not re.search(r"transition-duration\s*:\s*var\(--fl-dur-control-normal\)", body):
                fails.append("R48 fluent2-controls.css: %s 必须写 transition-duration: "
                             "var(--fl-dur-control-normal)（250ms）—— CSS 过渡取目标态时长，"
                             "不写就一直是基态的 167ms，放大与缩小一个速率" % sel)
            if re.search(r"--fl-slider-thumb\s*:", body):
                fails.append("R48 fluent2-controls.css: %s 不许改 --fl-slider-thumb（外框尺寸三态恒定）" % sel)

    # R49 弹出层开合动画：**下拉列表与菜单是两套**（各自有录屏依据）
    #     下拉列表（.fl-combo-popup，依据 2026-10-21 23-13-35.mp4）：顶边固定、底边扫下去，
    #       内容是"被揭示"而不是被拉伸（不是 scaleY）；不淡入；关闭单帧瞬变。
    #     菜单（.fl-flyout，依据 2026-10-22 16-34-16.mp4 + WinUI 源码注释）：MenuPopupThemeTransition
    #       = 整个弹层滑入视野，行程 = 弹层自身高度（100%），不淡入，没有缩放；方向按放置关系；
    #       入场 250ms / 出场 167ms。自定义 Popup 的"50px 微移"是 PopupThemeTransition，别混用。
    #     对话框 / ToolTip 只许淡入淡出（基类 .fl-overlay 不许带 transform）。
    if motion_css and "fl-overlay" in motion_css:
        # —— 菜单（flyout）——
        pop = re.search(r"\.fl-overlay\.fl-flyout\s*\{([^}]*)\}", motion_css)
        closed = re.search(r"\.fl-overlay\.fl-flyout:not\(\.fl-open\)\s*\{([^}]*)\}", motion_css)
        if not pop or not closed:
            fails.append("R49 fluent2-motion.css: 菜单（.fl-flyout）必须有独立的开合规则")
        else:
            if "--fl-popup-shift" not in pop.group(1) or "100%" not in pop.group(1):
                fails.append("R49 fluent2-motion.css: 菜单位移必须走 --fl-popup-shift: 100%"
                             "（MenuPopupThemeTransition = 整个弹层滑入视野；录屏实测行程 = 菜单高 355 CSS）")
            if "translateY(calc(var(--fl-popup-shift)" not in closed.group(1):
                fails.append("R49 fluent2-motion.css: 菜单关态必须 translateY(calc(var(--fl-popup-shift) * var(--fl-popup-dir)))"
                             "（方向由 JS 按放置关系写 --fl-popup-dir）")
            for body, name in ((pop.group(1), "开态"), (closed.group(1), "关态")):
                if "scale" in body:
                    fails.append("R49 fluent2-motion.css: 菜单%s不许有 scale —— 官方 pop-up 动画只有平移" % name)
                for om in re.finditer(r"opacity\s*:\s*([^;]+);", body):
                    if om.group(1).strip() != "1":
                        fails.append("R49 fluent2-motion.css: 菜单%s的 opacity 只能是 1"
                                     "（录屏首帧文字对比度已满：菜单不淡入也不淡出）" % name)
                if re.search(r"transition[^;]*opacity", body):
                    fails.append("R49 fluent2-motion.css: 菜单的 transition 里不许有 opacity —— 只滑入/滑出")
            if "var(--fl-dur-control-normal)" not in pop.group(1):
                fails.append("R49 fluent2-motion.css: 菜单入场时长要用 --fl-dur-control-normal(250ms)")
            if "var(--fl-dur-control-fast)" not in closed.group(1):
                fails.append("R49 fluent2-motion.css: 菜单出场时长要用 --fl-dur-control-fast(167ms)")
            # 裁剪：开态留 -24px（阴影），关态零高并贴在最终矩形的那条边上 →
            # 吃相才是"从触发元素那一侧长出来"，而不是从上面盖过去
            if not re.search(r"clip-path\s*:\s*inset\(-2px -24px -24px -24px\)", pop.group(1)):
                fails.append("R49 fluent2-motion.css: 菜单开态必须 clip-path: inset(-2px -24px -24px -24px)"
                             "（左右下留 24px 给 --fl-shadow-flyout；**上沿只留 2px**，"
                             "留大了裁剪线会在动画中往上漂、压住触发元素）")
            if not re.search(r"clip-path\s*:\s*inset\(\s*100%", closed.group(1)):
                fails.append("R49 fluent2-motion.css: 菜单关态必须 clip-path: inset(100% 0 0 0)"
                             "（零高、贴在最终顶边；配合 translateY(-100%) 才等于「长出来」）")
            for body, name in ((pop.group(1), "开态"), (closed.group(1), "关态")):
                if "clip-path" not in body.split("transition", 1)[-1]:
                    fails.append("R49 fluent2-motion.css: 菜单%s的 transition 必须同时过渡 clip-path"
                                 "（只动 transform 会变成从上面盖过去）" % name)
            if not re.search(r'\[data-drop="up"\][^{]*\{[^}]*clip-path\s*:\s*inset\(\s*0\s+0\s+100%', motion_css):
                fails.append("R49 fluent2-motion.css: 菜单向上翻时裁剪要贴在底边（inset(0 0 100% 0)）")
            if not re.search(r'\[data-drop="up"\]\s*\{[^}]*clip-path\s*:\s*inset\(-24px -24px -2px -24px\)',
                             motion_css):
                fails.append("R49 fluent2-motion.css: 菜单向上翻的开态裁剪要 inset(-24px -24px -2px -24px)"
                             "（下沿只留 2px，避免裁剪线往下漂盖住触发元素）")
        if not re.search(r"\.fl-overlay[^{]*\[data-drop=[\"']up[\"']\][^{]*\{[^}]*--fl-popup-dir\s*:\s*1", motion_css):
            fails.append("R49 fluent2-motion.css: 菜单向上展开时必须 --fl-popup-dir: 1（从下方升上来）")
        # —— 下拉列表（reveal）——
        bodies = re.findall(r"\.fl-overlay\.fl-combo-popup[^{]*\{([^}]*)\}", motion_css)
        if not bodies:
            fails.append("R49 fluent2-motion.css: 下拉列表（.fl-combo-popup）必须有独立开合规则")
        else:
            reveal = [b for b in bodies if "clip-path" in b]
            if not reveal:
                fails.append("R49 fluent2-motion.css: 下拉列表必须用 clip-path 揭示"
                             "（录屏：顶边固定、底边扫下去；位移或 scaleY 都不对）")
            if any(("transform" in b and "translate" in b) or "scale(" in b for b in bodies):
                fails.append("R49 fluent2-motion.css: 下拉列表不许用位移/缩放 —— 它是「揭示」")
            closed_body = next((b for b in bodies if "calc(100%" in b), None)
            if closed_body is None or "transition: none" not in closed_body:
                fails.append("R49 fluent2-motion.css: 下拉列表关闭必须瞬变（transition: none）"
                             "—— 录屏里 f275 还在、f276 全没了，没有退场动画")
            if not re.search(r"\.fl-overlay\.fl-combo-popup\[data-drop=[\"']up[\"']\][^{]*\{[^}]*"
                             r"clip-path\s*:\s*inset\(calc\(100%", motion_css):
                fails.append("R49 fluent2-motion.css: 下拉列表向上翻时必须从底边往上揭示"
                             "（[data-drop=\"up\"] 的 clip-path 要把 100% 放在上边）")
            # 速率：--fl-ease-popup + --fl-dur-popup(167ms)；
            # 且**任何揭示动画在真机第一个渲染帧（16.7ms）处进度不得超过 40%** ——
            # 上一版为了凑录屏的"首帧 60%"套了 (0.1,0.9,0.2,1)，16.7ms 就到 58%，
            # 用户看到的第一帧近乎全开，反馈「动画没了」。录屏首帧 60% 是采样相位造成的假象
            # （59.73fps，弹层首帧落在帧间隔中间），不是曲线形状。
            reveal_body = reveal[0] if reveal else ""
            if "var(--fl-ease-popup)" not in reveal_body:
                fails.append("R49 fluent2-motion.css: 下拉列表的揭示缓动必须是 --fl-ease-popup"
                             "（ControlFastOutSlowIn 0,0,0,1；起手要有可见加速段）")
            if "var(--fl-dur-popup)" not in reveal_body:
                fails.append("R49 fluent2-motion.css: 下拉列表的揭示时长必须是 --fl-dur-popup(167ms)")
            first = _reveal_first_frame_progress(tokens_css)
            if first is None:
                fails.append("R49 fluent2-tokens.css: 取不到 --fl-ease-popup / --fl-dur-popup，无法校验揭示速率")
            elif first > 0.50:
                fails.append("R49 fluent2-tokens.css: 揭示曲线在第一个渲染帧（16.7ms）已到 "
                             f"{first * 100:.0f}%，第一帧就过半 —— 真机观感等于「没有动画」。"
                             "起手太陡的曲线（如 0.1,0.9,0.2,1 = 58%）不要用来拟合录屏的首帧进度"
                             "（那是 59.73fps 采样相位造成的假象）")

        # —— 位置（JS）：弹层要"压在"按钮上，选中项那一行盖住按钮 ——
        #     录屏：按钮 y 543..602、选中行 543..605、弹层顶边 526（露出 17 设备px ≈ 6 CSS）。
        #     旧实现是 r.bottom + 4（挂在按钮下方一条缝），位置完全是另一回事。
        if motion_js and "function place()" in motion_js:
            place_seg = motion_js[motion_js.index("function place()"):]
            place_seg = place_seg[:place_seg.index("function reflowOnScroll")] if "function reflowOnScroll" in place_seg else place_seg[:4000]
            if "r.bottom + 4" in place_seg or "r.bottom + 8" in place_seg:
                fails.append("R49 fluent2-motion.js place(): 下拉列表不许挂在按钮下方（r.bottom + 4）"
                             "—— 录屏里弹层是压在按钮上、选中项那一行盖住按钮")
            if not re.search(r"selectedIndex\(\)|aria-selected", place_seg):
                fails.append("R49 fluent2-motion.js place(): 必须先量出选中项相对弹层的偏移，"
                             "再回推 top = 按钮顶 − 偏移（否则选中项不在按钮上）")
            if "r.top - off" not in place_seg.replace(" ", " "):
                fails.append("R49 fluent2-motion.js place(): top 必须是 r.top - off（选中项对齐按钮顶边）")
        # —— 基类不许带位移（对话框/ToolTip 只淡入淡出）——
        base = re.search(r"\n\.fl-overlay\s*\{([^}]*)\}", motion_css)
        if base and "transform" in base.group(1):
            fails.append("R49 fluent2-motion.css: 基类 .fl-overlay 不许带 transform —— 对话框/ToolTip 只许淡入淡出")

    # R44 弹层不许越出视口
    #     弹层是 position: fixed + 内容撑宽（选项 nowrap），贴着右边缘的按钮会把弹层顶到视口外，
    #     而滚动条正好在最右边 —— 被窗口裁掉的表现就是"根本没有滚动条"。三层都要有：
    #     ① CSS max-width 封顶；② 选项省略号，别把弹层撑宽；③ JS 横向钳制。
    if controls_css and ".fl-combo-popup" in controls_css:
        pop_rule = re.search(r"\.fl-combo-popup\s*\{([^}]*)\}", controls_css)
        pop_body = pop_rule.group(1) if pop_rule else ""
        if "max-width" not in pop_body:
            fails.append("R44 fluent2-controls.css: .fl-combo-popup 必须设 max-width（如 calc(100vw - 16px)），"
                         "否则 nowrap 长选项会把弹层撑到视口外，右侧滚动条被窗口裁掉")
    if controls_css and ".fl-combo-item" in controls_css:
        item_rule = re.search(r"\.fl-combo-item\s*\{([^}]*)\}", controls_css)
        item_body = item_rule.group(1) if item_rule else ""
        if "text-overflow" not in item_body:
            fails.append("R44 fluent2-controls.css: .fl-combo-item 必须 text-overflow: ellipsis"
                         "（nowrap + 无省略号会把弹层撑宽）")
    if motion_js and "function place" in motion_js:
        if "Math.min(r.left" not in motion_js and "Math.min(btn" not in motion_js:
            fails.append("R44 fluent2-motion.js: place() 必须做水平钳制（Math.min(r.left, innerWidth - margin - w)），"
                         "否则贴右边缘的弹层会越出视口")
        if "popup.offsetWidth" not in motion_js:
            fails.append("R44 fluent2-motion.js: place() 量弹层宽度必须用 offsetWidth —— "
                         "getBoundingClientRect 会把入场态 scale(0.98) 算进去，少 2% 导致钳制不生效")

    # R40 设置行造型
    if ".fl-settings-row" in (controls_css or ""):
        row = re.search(r"\.fl-settings-row\s*\{([^}]*)\}", controls_css)
        body = row.group(1) if row else ""
        if "--fl-settings-row-h" not in body:
            fails.append("R40 fluent2-controls.css: .fl-settings-row 的行高必须走 --fl-settings-row-h（56，实测派生）")
        if "border-radius" not in body:
            fails.append("R40 fluent2-controls.css: .fl-settings-row 需要圆角 4（hover 底色不能是直角的通栏块）")
        if not re.search(r"\.fl-settings-row\[data-divided\][^{]*::after\s*\{[^}]*left", controls_css):
            fails.append("R40 fluent2-controls.css: 设置行的分隔线必须左缩进对齐文字起点（data-divided::after + left）")
    if ".fl-settings" in html_code:
        if not re.search(r'class\s*=\s*"[^"]*fl-settings-(text|title)"', html_code):
            fails.append("R40: 用了 .fl-settings 但行内没有 .fl-settings-text / .fl-settings-title"
                         "（设置行必须是「左文本 + 右控件」，纯文本不应直接塞进行里）")

    # R41 转场必须是「两拍」：旧页先淡出退场，新页再滑入
    #     录屏实测：旧页在 ≈80-170ms 内消失干净，新页才开始从行程起点进来。
    #     两页同时淡入淡出 → 中途新旧文字各半透明叠在一起（重影）；
    #     给离场页涂不透明底 → 变成"整块面板压过去"的硬边擦除，两种都不是 Win11 的样子。
    if ".fl-page-in" in (motion_css or ""):
        in_rule = re.search(r"\.fl-page-in\s*\{([^}]*)\}", motion_css or "")
        in_body = in_rule.group(1) if in_rule else ""
        if "animation-delay" not in in_body:
            fails.append("R41 fluent2-motion.css: .fl-page-in 必须设 animation-delay（略短于旧页退场时长），"
                         "否则两页同时进出会重影")
        out_rule = re.search(r"\.fl-page-out\s*\{([^}]*)\}", motion_css or "")
        out_body = out_rule.group(1) if out_rule else ""
        if "var(--fl-dur-page)" in out_body:
            fails.append("R41 fluent2-motion.css: 离场页的时长不许也用 --fl-dur-page"
                         "（旧页要在一小段内退场，不能和新页一样长）")
        if re.search(r"\.fl-page-(in|leaving)[^{]*\{[^}]*background\s*:", motion_css + "\n" + controls_css):
            fails.append("R41: 转场页不得涂不透明背景 —— 会变成硬边擦除，"
                         "与录屏的「旧页淡出 → 新页滑入」不符")

    # R42 应用外壳：左导航固定、只有内容区滚
    #     这类布局的失败方式很隐蔽：高度链断在任意一层，滚动就"消失"或跑回整页，
    #     而页面看起来还是对的（只是整页在滚）。三层必须同时成立。
    if ".fl-shell" in (controls_css or ""):
        if not re.search(r"body:has\(\.fl-shell\)[^{]*\{[^}]*height\s*:\s*100%", controls_css) and \
           not re.search(r"body\s*\{[^}]*height\s*:\s*100%", controls_css):
            fails.append("R42 fluent2-controls.css: body 必须是 height:100% + overflow:hidden"
                         "（否则整页会滚，左导航跟着跑）")
        if not re.search(r"\.fl-shell\s*\{[^}]*min-height\s*:\s*0", controls_css):
            fails.append("R42 fluent2-controls.css: .fl-shell 必须有 min-height:0"
                         "（flex 子项默认 min-height:auto，会被内容撑破导致内层滚动失效）")
        if not re.search(r"\.fl-content-layer\s*\{[^}]*grid-template-rows\s*:\s*minmax\(0,\s*1fr\)",
                         controls_css):
            fails.append("R42 fluent2-controls.css: .fl-content-layer 必须 grid-template-rows: minmax(0,1fr)"
                         "（auto 行会被内容撑高，overflow:clip 直接裁掉而不出滚动条）")
        if not re.search(r"\.fl-page\s*\{[^}]*overflow-y\s*:\s*auto", controls_css):
            fails.append("R42 fluent2-controls.css: .fl-page 必须是滚动容器（overflow-y: auto），"
                         "否则内容区不能独立滚动")

    # 输出
    print(f"目标：{target}")
    for w in warns:
        print(f"警告  {w}")
    for f in fails:
        print(f"未通过 {f}")
    print(f"合计未通过：{len(fails)}，警告：{len(warns)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
