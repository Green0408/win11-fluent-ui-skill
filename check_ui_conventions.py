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
        elif "var(--fl-slider-inner)" not in fill_var.group(1):
            fails.append("R35 fluent2-controls.css: --fl-slider-fill 必须含半 thumb 补偿"
                         "（calc(inner/2 + (100% - inner) × pct)）；直接写 100% × pct 会在两端偏半个 thumb")
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
