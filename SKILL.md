---
name: win11-fluent-ui
description: 用 Windows 11 / WinUI 3 / Fluent 官方规格生成工具界面（HTML/CSS/JS 网页）：官方动效时长与缓动曲线（Direct Entrance/Point to Point/Strong Entrance）、页面转场两轴（一级导航垂直·恒自下方进入 / 二级下钻水平，283ms）、连续型动效（秒针/进度环）、Fluent 颜色 token（暗/亮双主题、Mica/Acrylic/Smoke 网页近似）、Segoe UI Variable 字阶、官方圆角（控件 4px/浮层 8px）与海拔阴影、可拆装界面模块（单页/列表详情/网格详情/设置型）。当用户要求「用 Win11 / Fluent / WinUI 风格做个界面」「Windows 11 风格工具」「照 KIT 做界面」，需要核对 Fluent 官方数值，或发来 Win11 应用录屏要反解整屏动效与控件形态时使用。含组合处方、可复制骨架、录屏动效反解工具与可执行规范检查器。
---

# Win11 / Fluent 工具界面 KIT

**唯一权威是本 skill 资源目录里的官方源**（`raw/` 内 microsoft-ui-xaml XAML 主题资源与
learn.microsoft.com 文档快照）。不要凭记忆写颜色、字号、圆角、时长、缓动 —— 全部取自
`fluent2-tokens.css` 变量与 `official-values.md` 数值表（逐条注明出处）。

## 用户最短一句话（其余按默认，不用描述排版）

```text
照 KIT 做一个「<工具名>」工具界面。
用途：<一句话>。列表项=<字段>，详情=<字段>，面板设置=<项>，工具栏命令=<项>。
```

| 用户写的 | 落到模板哪里 | 不写时 |
|---|---|---|
| 用途 | titlebar 下 / `<h1>` 说明行 | 保留占位文案 |
| 列表项 | 主区左侧列表行（标题 + 次要文字） | 保留 3 条示例 |
| 详情 | 右侧 `fl-card` 键值/段落 | 保留示例字段 |
| 设置列表 | `.fl-settings` 组+行（左标题副标题 / 右控件），行高 56 | 保留示例 |
| 工具栏命令 | `toolbar` 按钮 + 「⋯」flyout | 保留三条示例 |

只问业务内容：颜色/字号/圆角/动效都按官方。用户要偏离官方时照做，并在交付说明里登记。

## 工作流：先定模块，再写业务

1. **先按 `FLUENT-COMPOSE.md` 的 5 个问题定模块**，挑一套处方：
   - **A 单页**：内容区 + 工具栏（删 nav/列表详情/面板）
   - **B 列表 + 详情**：条目管理型
   - **C 网格 + 详情**：图库型
   - **D 设置型**：内容区 + 常驻面板
2. 把 `fluent2-tool-starter.html` **连同四个资产**（`fluent2-tokens.css`、`fluent2-controls.css`、`fluent2-motion.css`、`fluent2-motion.js`）复制到目标目录的**同一层**（模板用相对路径引用）。
3. **删掉不用的模块**：搜文件里的 `模块：<名>` 标记整块删。JS 接线全部有存在性保护，删完页面照常运行，不用手工改脚本。
4. 只改业务：标题/说明、数据、详情字段、工具栏命令、文案。
5. **不要改**：`--fl-*` 变量值、动效类、`M.transitionTo()` 的签名与默认参数、stagger 步进、浮层开合逻辑。
6. **交付前必须跑**（有 FAIL 返回 1，目标「合计未通过：0」，不达标不交付）：

   ```bash
   python3 "<本 skill 资源目录>/check_ui_conventions.py" <生成的文件.html>
   ```

## 硬性规则摘要（完整版见 KIT.md）

- 颜色只用 `var(--fl-*)`；动效只用 `var(--fl-dur-*/--fl-ease-*)` 与 motion 类；页面转场必须走 `M.transitionTo()`。
- **转场两轴**：点侧栏（一级）用默认 `nav`（垂直 72px），**恒自下往上进入** —— 点任意一项都一样，不按导航序反向；点内容区入口进二级页用 `{kind:'drill'}`（水平 176px），返回用 `M.back('drill')`。要反向只能显式写 `{dir:'up'}`。两者都是 283ms + 交叉淡化。
- **列表/勾选/下拉**：列表用 `.fl-list` + `.fl-list-content` 三层结构与六档状态；勾号是 SVG 描画（不是字符 ✓）；下拉首选自绘 `.fl-combo`（`.fl-select` 仅作无 JS 回退）。
- 一次性动效（入场/出场/转场）用 `animation`，状态切换（hover/active/浮层开合）用 `transition`，连续型（秒针/进度环）用 `animation + infinite + linear/steps（禁 both）` —— 三类别混用。
- 圆角两档：控件 4px / 浮层 8px（`--fl-radius-*`）；字号只用 `.fl-*` 字阶类；间距/尺寸 4 的倍数（`--fl-space-*`）。
- 浮层隐藏必须 visibility/pointer-events（`.fl-overlay` 已内置，且 visibility 延迟切换以保证出场动画可见）；对话框只用于不可撤销且后果重大的确认。
- 多页布局是 grid 同格叠放（`.fl-page { grid-area: 1 / 1 }`），转场期靠 `.fl-page-leaving` 保持离场页渲染，不要改成上下堆叠。
- 明暗双主题：`<html data-theme>` + `M.toggleTheme()`，两主题都要渲染正确。
- 海拔语义：dialog=128 / flyout=32 / tooltip=16 / card=8 / control=2 / layer=1；CSS 阴影为 KIT 换算近似（已在注释登记）。
- Mica/Acrylic/Smoke 网页落地均为近似方案（tokens.css 注释与 official-values.md 已标注）。

## 按需读取

| 需要什么 | 读哪个 |
|---|---|
| 某元素该用哪个类/变量 | `where-used.md` |
| 模块怎么拆/怎么组合 | `FLUENT-COMPOSE.md` |
| 全部官方数值与出处 | `official-values.md`（机读 `official-values.json`） |
| 完整规则与控件清单 | `KIT.md` |
| **用户发来录屏要「照着改」** | `VIDEO-ALIGN.md`（整屏动效反解流程、判定阈值、素材要求、已知限制） |
| 官方原文 | `raw/*.xaml`（XAML 源码）、`raw/doc_*.md`（文档快照） |

## 用户发来录屏时（先出报告，别直接改）

用同目录的 `analyze_video.py`（依赖 `av`/`pillow`/`numpy`，装隔离 venv）：

```bash
python analyze_video.py probe 录屏.mp4 --work video-analysis/<名字>   # 先看帧率能不能测
python analyze_video.py segments 录屏.mp4 --work ...                  # 切出 s1/s2..
python analyze_video.py motion 录屏.mp4 --work ... --seg s1           # 整屏动效（重点）
python analyze_video.py quality 录屏.mp4 --work ... --seg s1          # 抖/跳/生硬体检
python analyze_video.py micro  录屏.mp4 --work ... --from 1330 --to 1560 --roi "switch:268,398,52,30"
python analyze_video.py report 录屏.mp4 --work ...                    # 10 节 report.md
```

**范围**：只参考**整屏动效**、**整屏动效质量**、**控件形态与控件微动效**；**颜色一律不参考**
（继续用官方 token —— 录屏取色必然偏移，拿视频校准颜色只会把准确值改坏）。
30fps 下 83ms 档测不出、167/250 档可能互判，`VIDEO-ALIGN.md` 里有完整可测性表与素材要求。

## 最高频错误

1. 复制了模板却没带 4 个资产文件 → 校验器 R12 直接 FAIL。
2. 手写 hex 颜色/字面 px 圆角/字面 ms 时长 → R1/R2/R3/R4 FAIL。要换 accent 只改 `--fl-accent`。
3. 直接切类换页 → R6 FAIL，必须 `M.transitionTo()`。
4. 自己写 `opacity:0` 隐藏浮层 → 挡交互，用 `.fl-overlay` 的开合类（R7/R15）。
5. 忘了删页面上不存在的模块对应的接线（其实有保护，但模块功能要重新判断该不该存在，见 FLUENT-COMPOSE.md 第 5 问）。
6. 用 `transition-delay` 做 stagger、用 `filter: brightness()` 做按压反馈 → 分别被 R17 / R14 拦下（前者让 hover 迟滞，后者无法平滑过渡）。
7. 把入场动画写成 `transition` → 会被控件自身的 `transition` 简写覆盖（R18），表现为「动画根本没播」。
8. 把二级下钻也做成垂直转场（或只做垂直不做水平）→ 与官方应用观感不符，且 R21 会拦「只写一个轴」。
9. 连续型动效用 `both`/`forwards`，或拿 `--fl-ease-standard` 驱动秒针 → 终态被钉死/节奏不对，R23 会拦。
10. 用 `--fl-ease-linear` 做位移或底色过渡 → 「生硬」的来源之一，R25 只放行 opacity/visibility。
