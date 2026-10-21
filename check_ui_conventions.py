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
 R18 一次性入场/出场必须 animation 化（.fl-entrance/.fl-point-to-point/.fl-exit 块内须有 animation）
 R19 dialog 居中禁用 transform: translate(-50%…)（须用独立 translate 属性，transform 留给开合动效）
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
        for cls in ("fl-entrance", "fl-point-to-point", "fl-exit"):
            has_anim = False
            for m in re.finditer(r"[^{}]*\.%s[^{}]*\{([^{}]*)\}" % cls, motion_css):
                decl = re.search(r"animation\s*:\s*([^;]+)", m.group(1))
                if decl and not decl.group(1).strip().startswith("none"):
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
