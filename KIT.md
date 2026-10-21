# KIT.md —— win11-fluent-ui 执行契约

**唯一权威是本 skill 资源目录里的官方源（`raw/*.xaml`，microsoft-ui-xaml，MIT）与文档快照
（`raw/doc_*.md`，learn.microsoft.com）。不要凭记忆写**颜色、字号、圆角、时长、缓动 ——
全部取自 `fluent2-tokens.css` 变量与 `official-values.md` 数值表。

## 资产清单（模板必须与资产同层，相对路径引用）

| 文件 | 职责 |
|---|---|
| `fluent2-tokens.css` | 全部 `--fl-*` 官方变量（颜色暗/亮双主题、动效时长/缓动、圆角、间距、阴影）。脚本生成，勿手改 |
| `fluent2-controls.css` | 控件样式：按钮/输入/**列表（六档 + 行结构 + 多选列）**/**勾选·单选（SVG 勾号）**/**自绘 ComboBox**/开关/卡片/导航/浮层/对话框/InfoBar/字阶类 |
| `fluent2-motion.css` | 动效类：fl-entrance / fl-point-to-point / fl-exit / **fl-page-in / fl-page-out（页面转场两轴）** / fl-fade / fl-strong-entrance / **fl-continuous / fl-tick（连续型）** / fl-overlay / fl-smoke（一次性动效用 animation，状态切换用 transition） |
| `fluent2-motion.js` | 编排 API：`M.transitionTo(id,{kind,dir})` / `M.back(kind)` / `M.stack()` / `M.stagger()` / **`M.combo.init/auto`** / **`M.list.multiselect/syncParent`** / **`M.slider.init/auto`** / `M.flyout` / `M.dialog` / `M.toast` / `M.theme` |
| `fluent2-tool-starter.html` | 可拆装骨架（模块标记 `<!-- 模块：<名> -->`） |
| `selftest.html` | 自测页（校验器应 0 FAIL） |

## 硬性规则（校验器逐条强制，FAIL 不交付）

1. **颜色**只用 `var(--fl-*)`。禁手写 hex / rgb。accent 唯一入口：`--fl-accent`（默认 #0078D4，Win11 默认系统强调色），整体替换即可换主题色；主题内实际填充用 `--fl-accent-fill`（暗=Dark1 档、亮=Light2 档，XAML 规则）。
2. **动效**只用 `var(--fl-dur-*)` / `var(--fl-ease-*)` 与 motion.css 的类。禁字面 ms / cubic-bezier。页面转场必须走 `M.transitionTo()`（默认垂直；二级页用 `{kind:'drill'}`），禁直接切类。
   **三类表达不要混用**：① 一次性动效（入场/出场/页面转场/Strong Entrance）用 keyframe `animation`；② 可逆的状态切换（hover/active/开关/浮层开合）用 `transition`；③ 连续型（秒针/进度环）用 animation + `infinite` + linear/steps 且**禁 both/forwards**。混用会让控件的 `transition` 简写覆盖入场动画（曾导致卡片入场静默失效）。**第三类例外**：跟着指针逐帧变形的（滑块已填充段、拖拽预览）**一律不加过渡** —— 它属于「值跟随」，加 250ms 会把拖动变成拖影，是新的抖动源（校验器 R35 会拦住 `transition: background`）。
3. **圆角**只用 `var(--fl-radius-control)`（4px，页内元素）/ `var(--fl-radius-overlay)`（8px，浮层级）；直边相接处不圆角（0px）。
   控件内部另有官方小圆角 token，**不属于 4/8 两档**、按 XAML 原值使用：`--fl-radius-checkbox` 3（列表内复选框）、`--fl-radius-indicator` 2（导航选中条）、`--fl-radius-list-indicator` 1.5（列表选中条）、`--fl-radius-combo-item` 3 / `--fl-radius-combo-pill` 1.5 / `--fl-radius-combo-highlight` 7（下拉项与高亮框）。
4. **字号**只用 `.fl-caption/.fl-body/.fl-body-strong/.fl-body-large/.fl-subtitle/.fl-title/.fl-title-large/.fl-display` 字阶类。
5. **焦点**用 `:focus-visible` 双描边（controls.css 已内置）；`:focus`（非 visible）不画框。
6. **浮层**（flyout/dialog/contextmenu）隐藏态必须 visibility/pointer-events（motion.css `.fl-overlay` 已内置），只 opacity:0 会挡交互。隐藏所用的 `visibility` 必须**延迟**切换（`visibility 0s … var(--fl-dur-*)`），否则关闭瞬间就 hidden、出场动画看不见。
7. **海拔**语义（layering 文档）：dialog/window=128、flyout=32、tooltip=16、card=8、control=2、layer=1。CSS 阴影 `--fl-shadow-e*` 是 KIT 换算近似（官方只给 elevation 值，无 CSS 定义），勿改作他用。
8. **材质**：Mica≈`--fl-solid-bg-base` 纯色基底；Acrylic=浮层 `backdrop-filter: blur(60px) saturate(125%)`（只用于瞬态轻触消失表面）；Smoke=`--fl-smoke` 模态遮罩（恒半透明黑）。三者均为网页近似，已在 tokens 注释登记。
9. **明暗双主题**：`<html data-theme="dark|light">`，切换走 `M.toggleTheme()`。两主题都必须渲染正确。
10. **间距/尺寸为 4 的倍数**（官方规则）：用 `--fl-space-1/2/3/4/6/8/12`（4/8/12/16/24/32/48）。语义间距（官方 content-basics）：按钮间 8、按钮-flyout 8、控件-header 8、控件-label 12、内容区 12、边缘文字 16、expander 缩进 48。
    **已登记的官方例外**（不要"顺手取整"）：`--fl-list-check-offset` 40.5px（ListViewItemContentOffsetX，多选列宽）、`--fl-glyph-stroke` 2.5px（勾号描边）、以及规则 3 列出的 1.5/2/3/7px 控件圆角。
11. **删除模块时**：HTML 里搜 `模块：<名>` 整块删，JS 接线全部做了存在性保护，无需改脚本。
12. **偏离官方要登记**：官方未定义的值（如 nav 宽度 240px）在 KIT 已登记；用户要求偏离官方时，在交付说明里注明。
13. **多页布局**：`.fl-content-layer` 是 `display:grid` + `overflow: clip`，所有 `.fl-page` 占同一格（`grid-area: 1 / 1`），转场期重叠而非上下堆叠；非当前页靠 `.fl-current` / `.fl-page-leaving` 控制显隐。转场期 JS 会锁 `min-height`。删除或新增页面时**不要**改这层布局，否则转场会顶出布局跳变。`overflow: clip` 不支持 `position: sticky`，需要时改用 `overflow: hidden` + `overflow-clip-margin`。
14. **stagger 延迟**只写 `--fl-stagger-delay` 自定义属性（`M.stagger` 已封装），**禁止** `transition-delay` / `transitionDelay`——它会影响该元素后续所有过渡，造成悬停/点击迟滞。
15. **页面转场两轴**（实测自 Win11 官方应用录屏，见 VIDEO-ALIGN.md §9/§10）：

| 触发 | kind | 轴向 | 单层行程 | 时长 | 曲线 |
|---|---|---|---|---|---|
| 点左侧栏一级导航 | `nav`（默认） | 垂直 | `--fl-page-shift-y` 72px | `--fl-dur-page` 283ms | `--fl-ease-page` |
| 点内容区入口进入二级页 | `drill` | 水平 | `--fl-page-shift-x` 176px | `--fl-dur-page` 283ms | `--fl-ease-page` |
| 返回上一级 | `M.back(kind)` | 同上 | 同上，方向取反 | 同 | 同 |

　**方向（`dir`）= 新页的入场起点方位**，六个取值：

| dir | 含义 | 起点偏移 |
|---|---|---|
| `forward` / `back` | 逻辑方向，按轴映射（drill→右/左；nav **两个都归一到 down**） | ±行程 |
| `up` | 新页**自上方**进入（仅显式指定时使用） | −行程 |
| `down` | 新页**自下方**进入（nav 的唯一缺省） | +行程 |
| `left` / `right` | 自左 / 自右进入 | ∓行程 |

　**竖向铁律：一级导航只准「自下往上进入」**。点侧栏里任意一项（无论更靠上还是更靠下），内容都从下方滑入、向上归位；`forward` / `back` 在 nav 上观感完全一致。规则：`shiftOf()` 里只要 `kind !== "drill"` 且方向没显式给轴，符号恒为 `+1`。
　早期版本按「导航项在侧栏里的先后序」定符号（点上面那条 → 内容从上方压下），**已废弃**：观感过重，且与 Win11 设置类应用不符。要反向只能显式写 `dir:"up"`（保留逃生口）。
　缺省解析顺序：**显式 `dir` → nav 恒 `down` / drill 按页面栈（目标是上一页=右→左反转）**。非法 `dir` 会 `console.warn` 并回退缺省（**不会**静默当成 forward）。
　`nav` 的 `isBack` 恒为 false（一级导航没有"返回"概念）：否则 A→B→A 之后页面栈会被截断成 `[A]`，`M.back()` 无路可退。只有 `drill` 或显式 `back` 才截断栈。
　位移由 JS 写入 `--fl-page-from-x/-y` 与 `--fl-page-to-x/-y` 四个带符号变量（keyframe 内**不写**位移字面量）；淡入淡出单独 83ms linear，两条 animation 并行。快速连点由 `pageGen` 代际 + `settlePages()` 保证无残留。
　两轴共用同一节奏（283ms / `--fl-ease-page`）：§9 早期只测到竖向 250ms 的减速尾段，样本不足拆两套曲线，统一后与 drill 实测一致。
16. **连续型动效**用 `.fl-continuous` / `.fl-tick`（加在指针元素本身，绕自身 `transform-origin: 50% 100%` 旋转），宿主用 `.fl-dial` + `.fl-dial-hand` + `.fl-dial-hub`。必须 linear/steps、`infinite`、`fill: none`；`prefers-reduced-motion` 下直接停住（不要退化成播完一圈就停）。
17. **列表**必须用 `.fl-list` + `.fl-listitem` + `.fl-list-content` 三层：
    - `.fl-listitem` 只有两列（勾选列 / 内容），行内容一律放在 `.fl-list-content` 里，否则多选时内容无法整体右移；
    - 图标用 `.fl-list-lead`（20px），主副标题用 `.fl-list-text` + `.fl-list-sub`，尾部数值/开关/箭头放最后两列；
    - 两行档写 `data-lines="2"`（行高 64），单行档不写（行高 40）；分组线用独立的 `.fl-list-sep`（不要用 border，否则会被行背景盖住）；
    - **六档状态顺序即语义**（选中+hover 必须写在 `:hover` 之后），官方反色档「选中+hover 比仅选中更淡」不是 bug。
18. **勾选框**的勾必须是 `.fl-check-glyph` 的 SVG（`pathLength="1"` + `stroke-dashoffset`），**禁止**用文本字符 "✓"。半选用原生 `:indeterminate`（由 JS 设 `input.indeterminate = true`），不要自造 `data-indeterminate`。
19. **下拉**首选 `.fl-combo`（自绘：有 Acrylic 弹层、项状态、开合动效、完整键盘）。`.fl-select` 只作无 JS 回退 —— 原生 `<option>` 面板由操作系统绘制，暗色主题会漏白底且无法承载项状态。自绘弹层必须 portal 到 `body` 且 `position: fixed`（内容区有 `overflow: clip`）。
20. **滑块**的已填充段（thumb 左侧、accent 色）靠 `--fl-slider-pct`（0–1）驱动，由 `M.slider.auto()` 在 `input` 时写入 —— **没有这个变量，轨道就是整条同色**（Win11 是左 accent 右灰）。
    - 填充宽 = `calc(12px / 2 + (100% - 12px) * var(--fl-slider-pct))`：减 12px 是因为 thumb 圆心行程比轨道短一个 thumb 宽，不补偿会让两端各溢出 6px；
    - 填充段**禁止**加 `transition: background`（值跟随加过渡会变成拖影，是新的抖动源；校验器 R35 会拦）；thumb 的 `transform` 缩放保留 250ms；
    - **档位色必须不透明**：`--fl-slider-accent` 不许直接引用 `--fl-accent-fill-hover/-pressed`（那是 alpha 0.9/0.8），必须 `color-mix(in srgb, var(--fl-accent-fill) 90%/80%, var(--fl-text-primary))`。alpha 档位叠在卡片上会透出底下的灰环，观感就是「悬停时滑块变透明」（校验器 R36 会拦）；
    - 填充色与 thumb 同步走四档（Default → hover → pressed → Disabled）；`[dir="rtl"]` 下渐变方向要翻转。
21. **按钮居中交给 flex，不要抄 XAML 的 `ButtonPadding=11,5,11,6`**：那是 ContentPresenter 做字基线补偿用的 4 值，照搬进 `align-items:center` 的盒子会让内容整体下沉 2px（校验器 R37 会拦上下不对称）。正确写法是 `padding: var(--fl-space-1) var(--fl-btn-pad-h)` + `min-height: var(--fl-control-height)`，再用 CDP 量 `Range` 文本盒中心与按钮盒中心的偏差（应 ≤0.5px）。

## 官方关键数值速查（详见 official-values.md）

- 动效：Direct Entrance/Exit 167ms（exit 必须配 fade out）、Point to Point 167/250/333、Gentle Exit 167、Fade 83、Strong Entrance 三关键帧 167+167+333。
- **实测派生（非官方档，来自 60fps 录屏反解）**：页面转场 283ms（`--fl-dur-page`）、drill 176px、nav 72px、`--fl-ease-page` = cubic-bezier(0.6,0,0.3,1)、连续型 `--fl-dur-sweep` 60s / `--fl-dur-tick` 1s。官方四档仍是 83/167/250/333，检索官方规范时不要引用这一行。
- 强调色（系统色，可整体替换）：`--fl-accent-fill` **暗主题 `#60CDFF`（SystemAccentColorLight2，配黑字）/ 亮主题 `#005FB8`（SystemAccentColorDark1，配白字）** —— 暗色用浅蓝、亮色用深蓝，由 `TextOnAccentFillColorPrimary`（暗=#000000 / 亮=#FFFFFF）反证。改色只动 `extract_tokens.py` 的 `ACCENT`，不要手改 `fluent2-tokens.css`。
- accent 状态档位（XAML brush Opacity）：`--fl-accent-fill-hover` = Default @0.9、`--fl-accent-fill-pressed` = Default @0.8。状态反馈用档位色过渡，禁用 `filter: brightness()`。**例外：滑块**的轨道填充与 thumb 不许用这两个 alpha 档（会透出底层，见规则 20）。
- 字阶：Caption 12/16、Body 14/20、Body Strong 14/20 Semibold、Body Large 18/24、Subtitle 20/28、Title 28/36、Title Large 40/52、Display 68/92。
- 控件：高 32px；Button padding 11,5,11,6；TextBox padding 10,5,6,6；列表项 min-height 40；ContentDialog padding 24 / max-width 548 / min-height 184；Switch 轨道 40×20、旋钮 12（hover 14 / pressed 17）、开态位移 **20px**（XAML `KnobTranslateTransform X=20`）；Slider 轨道 4 / 内圆 12 / 圆角 10（hover 1.167、pressed 0.833，250ms）；轨道**左段为 accent 已填充段**（`SliderTrackValueFill`，宽 = 半 thumb + 比例×(轨道宽-12)，由 `M.slider.auto()` 写 `--fl-slider-pct`），填充与 thumb 同步四档变色（Default→Secondary 0.9→Tertiary 0.8→Disabled）。
- 列表：行高单行 40 / 两行 64（后者 KIT 自定）；圆角 4；选中条 3×16 圆角 1.5；多选列宽 40.5；禁用透明度 0.3；图标 20；行内间距 12。
- 勾选/单选：方框 20×20、圆角 4、描边 1；勾号字形 12 / 描边 2.5；单选内点 12（hover 1.167 / pressed 0.833）；控件行高 32。
- 下拉（自绘）：闭合态高 32、最小宽 64、箭头 12×12 距右缘 14；弹层最小宽 80、最大高 504（15 项）、圆角 8、描边 2、项高 32、项圆角 3、选中胶囊 3×16 圆角 1.5。
- 控件级时长：`--fl-dur-control-faster` 83ms（状态色变）/ `-fast` 167ms（勾号描绘）/ `-normal` 250ms（滑块、单选缩放）。
- 状态过渡曲线：一律 `--fl-ease-standard`（XAML `ControlFastOutSlowInKeySpline = 0,0,0,1`）；`--fl-ease-linear` **只允许**用于 opacity/visibility。
- 断点：≤640 Small / 641–1007 Medium / ≥1008 Large。
