# KIT.md —— win11-fluent-ui 执行契约

**唯一权威是本 skill 资源目录里的官方源（`raw/*.xaml`，microsoft-ui-xaml，MIT）与文档快照
（`raw/doc_*.md`，learn.microsoft.com）。不要凭记忆写**颜色、字号、圆角、时长、缓动 ——
全部取自 `fluent2-tokens.css` 变量与 `official-values.md` 数值表。

## 资产清单（模板必须与资产同层，相对路径引用）

| 文件 | 职责 |
|---|---|
| `fluent2-tokens.css` | 全部 `--fl-*` 官方变量（颜色暗/亮双主题、动效时长/缓动、圆角、间距、阴影）。脚本生成，勿手改 |
| `fluent2-controls.css` | 控件样式：按钮/输入/开关/复选/单选/列表项/卡片/导航/浮层/对话框/InfoBar/字阶类 |
| `fluent2-motion.css` | 动效类：fl-entrance / fl-point-to-point / fl-exit / **fl-page-in / fl-page-out（页面转场两轴两向）** / fl-fade / fl-strong-entrance / **fl-continuous / fl-tick（连续型）** / fl-overlay / fl-smoke（一次性动效用 animation，状态切换用 transition） |
| `fluent2-motion.js` | 编排 API：`M.transitionTo(id,{kind,dir})` / `M.back(kind)` / `M.stack()` / `M.stagger()` / `M.flyout` / `M.dialog` / `M.toast` / `M.theme` |
| `fluent2-tool-starter.html` | 可拆装骨架（模块标记 `<!-- 模块：<名> -->`） |
| `selftest.html` | 自测页（校验器应 0 FAIL） |

## 硬性规则（校验器逐条强制，FAIL 不交付）

1. **颜色**只用 `var(--fl-*)`。禁手写 hex / rgb。accent 唯一入口：`--fl-accent`（默认 #0078D4，Win11 默认系统强调色），整体替换即可换主题色；主题内实际填充用 `--fl-accent-fill`（暗=Dark1 档、亮=Light2 档，XAML 规则）。
2. **动效**只用 `var(--fl-dur-*)` / `var(--fl-ease-*)` 与 motion.css 的类。禁字面 ms / cubic-bezier。页面转场必须走 `M.transitionTo()`（默认垂直；二级页用 `{kind:'drill'}`），禁直接切类。
   **三类表达不要混用**：① 一次性动效（入场/出场/页面转场/Strong Entrance）用 keyframe `animation`；② 可逆的状态切换（hover/active/开关/浮层开合）用 `transition`；③ 连续型（秒针/进度环）用 animation + `infinite` + linear/steps 且**禁 both/forwards**。混用会让控件的 `transition` 简写覆盖入场动画（曾导致卡片入场静默失效）。
3. **圆角**只用 `var(--fl-radius-control)`（4px，页内元素）/ `var(--fl-radius-overlay)`（8px，浮层级）；直边相接处不圆角（0px）。
4. **字号**只用 `.fl-caption/.fl-body/.fl-body-strong/.fl-body-large/.fl-subtitle/.fl-title/.fl-title-large/.fl-display` 字阶类。
5. **焦点**用 `:focus-visible` 双描边（controls.css 已内置）；`:focus`（非 visible）不画框。
6. **浮层**（flyout/dialog/contextmenu）隐藏态必须 visibility/pointer-events（motion.css `.fl-overlay` 已内置），只 opacity:0 会挡交互。隐藏所用的 `visibility` 必须**延迟**切换（`visibility 0s … var(--fl-dur-*)`），否则关闭瞬间就 hidden、出场动画看不见。
7. **海拔**语义（layering 文档）：dialog/window=128、flyout=32、tooltip=16、card=8、control=2、layer=1。CSS 阴影 `--fl-shadow-e*` 是 KIT 换算近似（官方只给 elevation 值，无 CSS 定义），勿改作他用。
8. **材质**：Mica≈`--fl-solid-bg-base` 纯色基底；Acrylic=浮层 `backdrop-filter: blur(60px) saturate(125%)`（只用于瞬态轻触消失表面）；Smoke=`--fl-smoke` 模态遮罩（恒半透明黑）。三者均为网页近似，已在 tokens 注释登记。
9. **明暗双主题**：`<html data-theme="dark|light">`，切换走 `M.toggleTheme()`。两主题都必须渲染正确。
10. **间距/尺寸为 4 的倍数**（官方规则）：用 `--fl-space-1/2/3/4/6/8/12`（4/8/12/16/24/32/48）。语义间距（官方 content-basics）：按钮间 8、按钮-flyout 8、控件-header 8、控件-label 12、内容区 12、边缘文字 16、expander 缩进 48。
11. **删除模块时**：HTML 里搜 `模块：<名>` 整块删，JS 接线全部做了存在性保护，无需改脚本。
12. **偏离官方要登记**：官方未定义的值（如 nav 宽度 240px）在 KIT 已登记；用户要求偏离官方时，在交付说明里注明。
13. **多页布局**：`.fl-content-layer` 是 `display:grid` + `overflow: clip`，所有 `.fl-page` 占同一格（`grid-area: 1 / 1`），转场期重叠而非上下堆叠；非当前页靠 `.fl-current` / `.fl-page-leaving` 控制显隐。转场期 JS 会锁 `min-height`。删除或新增页面时**不要**改这层布局，否则转场会顶出布局跳变。`overflow: clip` 不支持 `position: sticky`，需要时改用 `overflow: hidden` + `overflow-clip-margin`。
14. **stagger 延迟**只写 `--fl-stagger-delay` 自定义属性（`M.stagger` 已封装），**禁止** `transition-delay` / `transitionDelay`——它会影响该元素后续所有过渡，造成悬停/点击迟滞。
15. **页面转场分两轴两向**（实测自 Win11 官方应用录屏，见 VIDEO-ALIGN.md §9）：

| 触发 | kind | 轴向 | 单层行程 | 时长 | 曲线 |
|---|---|---|---|---|---|
| 点左侧栏一级导航 | `nav`（默认） | 垂直 | `--fl-page-shift-nav` 72px | `--fl-dur-page` 283ms | `--fl-ease-standard` |
| 点内容区入口进入二级页 | `drill` | 水平 | `--fl-page-shift-drill` 176px | `--fl-dur-page` 283ms | `--fl-ease-page` |
| 返回上一级 | `drill` + `M.back()` | 同上，方向取反 | 同 | 同 | 同 |

　位移方向由 JS 写入 `--fl-page-from-x/-y` 与 `--fl-page-to-x/-y` 四个带符号变量（keyframe 内**不写**位移字面量）；淡入淡出单独 83ms linear，两条 animation 并行。快速连点由 `pageGen` 代际 + `settlePages()` 保证无残留。
16. **连续型动效**用 `.fl-continuous` / `.fl-tick`（加在指针元素本身，绕自身 `transform-origin: 50% 100%` 旋转），宿主用 `.fl-dial` + `.fl-dial-hand` + `.fl-dial-hub`。必须 linear/steps、`infinite`、`fill: none`；`prefers-reduced-motion` 下直接停住（不要退化成播完一圈就停）。

## 官方关键数值速查（详见 official-values.md）

- 动效：Direct Entrance/Exit 167ms（exit 必须配 fade out）、Point to Point 167/250/333、Gentle Exit 167、Fade 83、Strong Entrance 三关键帧 167+167+333。
- **实测派生（非官方档，来自 60fps 录屏反解）**：页面转场 283ms（`--fl-dur-page`）、drill 176px、nav 72px、`--fl-ease-page` = cubic-bezier(0.6,0,0.3,1)、连续型 `--fl-dur-sweep` 60s / `--fl-dur-tick` 1s。官方四档仍是 83/167/250/333，检索官方规范时不要引用这一行。
- accent 状态档位（XAML brush Opacity）：`--fl-accent-fill-hover` = Default @0.9、`--fl-accent-fill-pressed` = Default @0.8。状态反馈用档位色过渡，禁用 `filter: brightness()`。
- 字阶：Caption 12/16、Body 14/20、Body Strong 14/20 Semibold、Body Large 18/24、Subtitle 20/28、Title 28/36、Title Large 40/52、Display 68/92。
- 控件：高 32px；Button padding 11,5,11,6；TextBox padding 10,5,6,6；列表项 min-height 40；ContentDialog padding 24 / max-width 548 / min-height 184；Switch 轨道 40×20、旋钮 12（hover 14 / pressed 17）、开态位移 **20px**（XAML `KnobTranslateTransform X=20`）；Slider 轨道 4 / 内圆 12 / 圆角 10（hover 1.167、pressed 0.833）。
- 状态过渡曲线：一律 `--fl-ease-standard`（XAML `ControlFastOutSlowInKeySpline = 0,0,0,1`）；`--fl-ease-linear` **只允许**用于 opacity/visibility。
- 断点：≤640 Small / 641–1007 Medium / ≥1008 Large。
