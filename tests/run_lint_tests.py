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
            'M.back("drill")',
            'M.transitionTo("page-main")'),
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
            "display: grid; overflow: clip; }",
            "display: grid; }"),
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
            hit = rule in out
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

    print(f"\n坏例命中 {bad_ok}/{len(BAD_CASES)}，正常例通过 {pos_ok}/{2 + len(PRESCRIPTIONS)}")
    return 0 if (bad_fail == 0 and pos_fail == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
