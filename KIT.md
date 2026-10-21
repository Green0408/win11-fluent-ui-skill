# KIT.md —— win11-fluent-ui 执行契约

**唯一权威是本 skill 资源目录里的官方源（`raw/*.xaml`，microsoft-ui-xaml，MIT）与文档快照
（`raw/doc_*.md`，learn.microsoft.com）。不要凭记忆写**颜色、字号、圆角、时长、缓动 ——
全部取自 `fluent2-tokens.css` 变量与 `official-values.md` 数值表。

## 资产清单（模板必须与资产同层，相对路径引用）

| 文件 | 职责 |
|---|---|
| `fluent2-tokens.css` | 全部 `--fl-*` 官方变量（颜色暗/亮双主题、动效时长/缓动、圆角、间距、阴影）。脚本生成，勿手改 |
| `fluent2-controls.css` | 控件样式：按钮/输入/**列表（六档 + 行结构 + 多选列）**/**设置页列表（.fl-settings 组+行）**/**勾选·单选（SVG 勾号）**/**自绘 ComboBox**/**细滚动条 .fl-scroll**/开关/卡片/导航/浮层/对话框/InfoBar/字阶类 |
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
| 点左侧栏一级导航 | `nav`（默认） | 垂直 | `--fl-page-shift-y` 108px | `--fl-dur-page` 250ms | `--fl-ease-page` |
| 点内容区入口进入二级页 | `drill` | 水平 | `--fl-page-shift-x` 264px | `--fl-dur-page` 250ms | `--fl-ease-page` |
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
　位移由 JS 写入 `--fl-page-from-x/-y` 与 `--fl-page-to-x/-y` 四个带符号变量（keyframe 内**不写**位移字面量）。快速连点由 `pageGen` 代际 + `settlePages()` 保证无残留。
　**节奏是「两拍」，不是同时进出**（逐帧实测 2026-10-21，见 VIDEO-ALIGN §11）：

| 拍 | 时间 | 旧页 | 新页 |
|---|---|---|---|
| ① 退场 | 0 → 167ms（`--fl-dur-normal`） | **原地淡出 → 加速离开**，彻底消失 | 停在行程起点、`opacity: 0`（已 `display` 但不显形） |
| ② 进场 | 133 → 450ms（`--fl-dur-page`） | 已移除 | 从行程起点滑到 0，淡入 83ms |

　**两拍要略微搭接，不能严丝合缝**：延迟取退场时长的 0.8（≈133ms）。若延迟正好等于 167ms，
　旧页淡到 0 的那一帧新页还全透明 —— 中间空出一帧背景，快速转场里就是可见的"闪一下"。
　**两条曲线是一对**：退场 **加速**（`--fl-ease-page-out` = `0.7,0,1,0.5`，速度峰在末尾）、
　进场 **强减速**（`--fl-ease-page` = `0.1,0.9,0.2,1`，起手即峰值）。这样衔接处的速度是连续的。
　反面教材：退场用近线性 `0.3,0.3,0.6,1` —— 末尾减速、紧接着进场猛起，速度突变反而更"顿"。

　为什么不能同时：两页叠在同一网格格里（靠 `overflow: clip` 裁），同时淡入淡出会让新旧文字在中途各半透明地叠在一起（重影）；而给离场页涂不透明底又变成「整块面板压过去」的硬边擦除 —— 录屏里两种情况都不是。
　实现：`.fl-page-in { animation-delay: calc(var(--fl-dur-normal) * 0.8) }`、`.fl-page-out` 用 `--fl-dur-normal` 而非 `--fl-dur-page`，页面**保持透明**；`M.stagger` 同样延后 167ms，否则入场元素会在页面还不可见时播完。校验器 **R41** 锁结构，`tests/transition_shots.js`（截图）与 `tests/motion_trace.js`（rAF 采 60fps 轨迹）锁观感。
　两轴共用同一节奏（167ms 退场 + 250ms 进场、搭接 34ms = 约 400ms 全程）：§9 早期只测到竖向 250ms 的减速尾段，样本不足拆两套曲线，统一后与 drill 实测一致。
16. **连续型动效**用 `.fl-continuous` / `.fl-tick`（加在指针元素本身，绕自身 `transform-origin: 50% 100%` 旋转），宿主用 `.fl-dial` + `.fl-dial-hand` + `.fl-dial-hub`。必须 linear/steps、`infinite`、`fill: none`；`prefers-reduced-motion` 下直接停住（不要退化成播完一圈就停）。
17. **列表**必须用 `.fl-list` + `.fl-listitem` + `.fl-list-content` 三层：
    - `.fl-listitem` 只有两列（勾选列 / 内容），行内容一律放在 `.fl-list-content` 里，否则多选时内容无法整体右移；
    - 图标用 `.fl-list-lead`（20px），主副标题用 `.fl-list-text` + `.fl-list-sub`，尾部数值/开关/箭头放最后两列；
    - 两行档写 `data-lines="2"`（行高 64），单行档不写（行高 40）；分组线用独立的 `.fl-list-sep`（不要用 border，否则会被行背景盖住）；
    - **六档状态顺序即语义**（选中+hover 必须写在 `:hover` 之后），官方反色档「选中+hover 比仅选中更淡」不是 bug。
18. **勾选框**的勾必须是 `.fl-check-glyph` 的 SVG（`pathLength="1"` + `stroke-dashoffset`），**禁止**用文本字符 "✓"。半选用原生 `:indeterminate`（由 JS 设 `input.indeterminate = true`），不要自造 `data-indeterminate`。
19. **下拉**首选 `.fl-combo`（自绘：有 Acrylic 弹层、项状态、开合动效、完整键盘）。`.fl-select` 只作无 JS 回退 —— 原生 `<option>` 面板由操作系统绘制，暗色主题会漏白底且无法承载项状态。自绘弹层必须 portal 到 `body` 且 `position: fixed`（内容区有 `overflow: clip`）。
20. **滑块**的已填充段（thumb 左侧、accent 色）靠 `--fl-slider-pct`（0–1）驱动，由 `M.slider.auto()` 在 `input` 时写入 —— **没有这个变量，轨道就是整条同色**（Win11 是左 accent 右灰）。
    - 填充宽 = `calc(12px / 2 + (100% - 12px) * var(--fl-slider-pct))`：减 12px 是因为 thumb 圆心行程比轨道短一个 thumb 宽，不补偿会让两端各溢出 6px。**必须用静止态 `--fl-slider-inner`**，不能跟着 hover 后的内点尺寸走（否则悬停时填充末端平移 1px）；
    - 填充段**禁止**加 `transition: background`（值跟随加过渡会变成拖影，是新的抖动源；校验器 R35 会拦）；
    - **thumb 是两层，外框尺寸三态恒定**（XAML `SliderThumbStyle`：Border 外盘 + Ellipse 内点，VisualState 只对 Ellipse 做 ScaleTransform）：

| 态 | 内点 | 环宽（反向补偿） | 外框 | 过渡时长（KeyTime） |
|---|---|---|---|---|
| Normal | 12 | 4 | 20 | **167ms**（ControlFast） |
| PointerOver | **14** | 3 | 20 | **250ms**（ControlNormal） |
| Pressed | **10** | 5 | 20 | **250ms**（ControlNormal） |
| Disabled | 14 | 3 | 20 | 167ms |

      **时长必须逐状态**（曲线三态都是 `cubic-bezier(0,0,0,1)` = `--fl-ease-standard`）：
      CSS 过渡取的是**目标态**的时长，所以基态写 `--fl-dur-control-fast`(167)、hover/active 各自
      用 `transition-duration: var(--fl-dur-control-normal)` 覆盖成 250 —— 放大比缩小慢 1.5 倍。
      一个时长糊三个状态就是"放大缩小一个速率"，观感立刻不对（R48 拦）。

      实现：盒子恒为静止内点 12，**收缩放走合成器**，外框用 `box-shadow` 环反向补偿：
      `transform: scale(var(--fl-slider-scale))`（1 / 1.1667 / 0.8333）
      `--fl-slider-ring: calc((外框 / scale − 内点) / 2)`（4 / 2.571 / 6）
      两者相乘恒等于 20 → 内点变大时环变窄、外框不动。
      **四个坑**（都踩过）：
      · **尺寸动效别改 width/height**：layout 会把伪元素盒宽量化取整，整段过渡只剩
        12.0 / 13.3 / 13.9 三级台阶，看起来像"跳一下"、完全没有曲线（R48 拦，坏例 R48e）；
        走 transform 实测能拿到 7 级连续值；
      · 但**也不能直接 scale 了事**：环会跟着放大（"整个滑块变大"，用户原话"外框从来不会变大小"），
        必须配 ring = (外框/scale − 内点)/2 反向补偿；
      · 别用"固定 20 盒子 + 背景图圆点 + `background-size` 过渡" —— `::-webkit-slider-thumb` 上
        `background-size` **不会过渡**（实测直接跳变）；
      · `--fl-slider-ring` 必须**写在 thumb 规则里**：写在 `.fl-slider` 上会按静止态算死，
        hover 时外框变 22（R48 拦，坏例 R48c）；
    - **档位色必须不透明**：`--fl-slider-accent` 不许直接引用 `--fl-accent-fill-hover/-pressed`（那是 alpha 0.9/0.8），必须 `color-mix(in srgb, var(--fl-accent-fill) 90%/80%, var(--fl-text-primary))`。alpha 档位叠在卡片上会透出底下的灰环，观感就是「悬停时滑块变透明」（校验器 R36 会拦）；
    - 填充色与 thumb 同步走四档（Default → hover → pressed → Disabled）；`[dir="rtl"]` 下渐变方向要翻转。
    - 验收：`node tests/slider_thumb_shots.js` → `python tests/slider_thumb_pixels.py`（量三态外框/内点直径，含慢放中间态）；
      速率与曲线：`node tests/slider_thumb_timing.js` → `python tests/slider_thumb_timing.py`（时长放大 4× 后逐帧量，
      判「80% 进度出现在 42% 时长处」「放大:缩小 = 1.5」「直径 ≥5 个不同取值」——
      实测 0.43 / 0.42、比值 1.52、7 级，与 cubic-bezier(0,0,0,1) 的 RMSE 5%）。
21. **按钮居中交给 flex，不要抄 XAML 的 `ButtonPadding=11,5,11,6`**：那是 ContentPresenter 做字基线补偿用的 4 值，照搬进 `align-items:center` 的盒子会让内容整体下沉 2px（校验器 R37 会拦上下不对称）。正确写法是 `padding: var(--fl-space-1) var(--fl-btn-pad-h)` + `min-height: var(--fl-control-height)`，再用 CDP 量 `Range` 文本盒中心与按钮盒中心的偏差（应 ≤0.5px）。
22. **设置页列表用 `.fl-settings`，不要用卡片里堆控件**（这是"设置型工具"最容易做错的地方，堆出来像表单，不像 Windows 设置）：

    ```html
    <div class="fl-settings">
      <section>
        <h3 class="fl-settings-header">显示</h3>
        <p class="fl-settings-desc">这组设置是干什么的（可选）</p>
        <div class="fl-settings-group">           <!-- 需要卡片分区时写 data-card -->
          <div class="fl-settings-row" data-divided>
            <span class="fl-settings-icon">…20px 图标…</span>
            <span class="fl-settings-text">
              <span class="fl-settings-title">标题</span>
              <span class="fl-settings-sub">副标题</span>
            </span>
            <span class="fl-settings-action">…开关 / 下拉 / 数值 / chevron…</span>
          </div>
        </div>
      </section>
    </div>
    ```

    - 造型三条硬指标（实测自 2026-10-21 录屏）：**组默认不套卡片**（直接铺页面底色）、**行间默认没有分隔线**（要线才写 `data-divided`，线会自动左缩进对齐文字起点）、**行高 56**（`--fl-settings-row-h`，单行档自动回落到 40）；
    - hover 是整行浅填充 + 圆角 4，**不要给每行做胶囊**（那是 ListViewItem 的形态）；
    - 整行可点（跳转）时用 `button.fl-settings-row` + 尾部 `.fl-list-chevron`；只做展示时用 `div`；
    - 控件放在 `.fl-settings-action` 里，**不要**在行内重复写一遍标题文字（标题已经在左边）。
23. **任何可滚动的浮层都必须加 `.fl-scroll`**（ComboBox 弹层、长菜单、长对话框）。浏览器默认滚动条是 17px 带上下箭头的方块，在 Acrylic 弹层里非常出戏。
    - 两套写法**互斥**：Chromium 116+ 里 `scrollbar-width` / `scrollbar-color` 只要是 non-auto，`::-webkit-scrollbar-*` 全部失效。所以默认给 Firefox 写标准属性，再用 `@supports selector(::-webkit-scrollbar)` 块把它们重置回 `auto`，然后写伪元素样式（校验器 R39 会拦缺 `@supports` 块）；
    - 视觉：命中区 12px、静止画 **6px**（3px 透明 border + `background-clip: content-box` 裁出）、hover / 拖动收到 2px border → 视觉 **8px**、thumb 圆角 999、`min-height` 28、**去掉 `::-webkit-scrollbar-button`**；
    - **颜色直接用 `--fl-control-strong-fill`**（= ControlStrongFillColorDefault，暗 55% 白 / 亮 45% 黑），hover 用 `--fl-text-secondary`。**不要再套 `color-mix(..., 85%, transparent)`** —— 这个 token 本身已经是半透明色，再混透明等于把对比度稀释掉，Acrylic 底上直接消失（2px + 55% alpha 那版就是这么"看不见"的）；
    - **变粗必须挂在 thumb 上**（`::-webkit-scrollbar-thumb:hover`）。挂在容器上就是 bug：`.fl-page:hover` 在指针位于页面任意位置时都成立 → 整页滚动条永远粗着（校验器 **R45** 会拦）；`:focus-within` 同理，下拉一展开焦点进 listbox 就变粗；
    - **悬停/拖动规则必须写完整的 `border` 简写并重复 `background-clip`**：
      ```css
      …::-webkit-scrollbar-thumb:hover,
      …::-webkit-scrollbar-thumb:active {
        background: var(--fl-text-secondary);
        background-clip: content-box;      /* 必须重复 */
        border: 2px solid transparent;     /* 必须是简写，含 style */
      }
      ```
      这两个部件状态**不是常规层叠**，悬停规则会整体接管绘制：只写 `border-width: 2px`
      （没有 style）等于没有边框，`background-clip` 也会回退成 border-box —— 两种都会让
      thumb 直接画满 12px 命中区。实测就是 6px → 12px 的突变，这是「一悬停就变粗」的真因（R43 会拦）；
    - **宽度只能靠截图量**：`getComputedStyle(el, '::-webkit-scrollbar-thumb')` 在 Chromium 里拿不到东西，
      `cdp_check` 又是 `--hide-scrollbars` 起的（占宽恒为 0）。用 `tests/scrollbar_pixels.py`：
      `python tests/scrollbar_pixels.py shot.png --y 300 --window 60 --expect-width 6 --expect-min 60`；
    - 这条容易漏：只有"超过 15 项（MaxDropDownHeight 504 ÷ 项高 32）"才看得见滚动条，演示数据通常到不了这个量。
    - **下拉项必须 `white-space: nowrap` + `text-overflow: ellipsis`**：折行会把弹层撑高，凭空长出一条滚动条；而不折行又不截断则会把弹层**撑到视口外**（见规则 25）。

24. **布局：左导航固定、只有右侧内容区滚**（不是整页滚）。三层缺一不可，任何一层断掉都会退回"整页滚动"：

    ```css
    html:has(.fl-shell) { height: 100%; }
    body:has(.fl-shell) { height: 100%; overflow: hidden; display: flex; flex-direction: column; }
    .fl-shell    { flex: 1; min-height: 0; display: flex; overflow: hidden; }
    .fl-content-layer { flex: 1; display: grid;
                        grid-template-rows: minmax(0, 1fr);   /* 页面必须拿到确定高度 */
                        overflow: clip; }                     /* 转场横向位移仍要裁 */
    .fl-page     { align-self: stretch; min-height: 0;
                   overflow-y: auto; scrollbar-gutter: stable; padding: var(--fl-space-4); }
    ```

    - `min-height: 0` 有两层含义：`.fl-shell` 上防 flex 子项被内容撑破；`.fl-page` 上防 grid 项撑破行高；
    - 内边距放在 `.fl-page` 而不是 `.fl-content-layer`：否则滚动条会缩进到 padding 里面，看着像"悬浮的条"；
    - **每页各自滚**（不是内容层统一滚）→ 切页时各页自己记住滚动位置，返回还在原处，且新页天然从顶部开始；
    - 一旦改成统一滚动容器，就必须自己存/取每个页的 `scrollTop`，还要处理转场期间"旧页还在淡出但滚动位置被改"的问题；
    - `scrollbar-gutter: stable` 让长短页切换时不横移 12px；
    - 用了 `:has()` 守卫：没用到 `.fl-shell` 的普通长页面照旧整页滚动。校验器 **R42** 锁这四层。

25. **自绘弹层必须做「视口钳制」**——否则贴右边缘的下拉会把弹层顶出窗口，而滚动条正好在最右边被裁掉，
    表现就是「没有滚动条 / 内容溢出到外面」。四件事缺一不可（校验器 R44 拦前三件）：

    ```css
    .fl-combo-popup { position: fixed; max-width: calc(100vw - 16px); }   /* ① 封顶 */
    .fl-combo-item  { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }  /* ② 截断 */
    ```
    ```js
    var w = popup.offsetWidth;                              // ③ 必须 offsetWidth
    var left = Math.min(r.left, innerWidth - 8 - w);         // ④ 水平钳制
    popup.style.left = Math.max(8, left) + "px";
    ```

    - **量宽度不能用 `getBoundingClientRect()`**：`place()` 跑在加 `.fl-open` 之前，此时入场态带
      `transform: scale(0.98)`，rect 会少算 2%（337→330），钳制就差这几像素不生效 —— 这个坑极难看出来；
    - 高度钳制同理必须用 `offsetHeight` 取自然高度：`max-height` 是 border-box 语义，而 `scrollHeight`
      只含 padding，两者直接比会差一圈边框，4 项短列表被永久压出 4px 溢出、凭空多一条滚动条；
    - `overscroll-behavior: contain`：滚到弹层尽头不要穿透到页面。

26. **侧栏选中指示条（NavigationView SelectionIndicator）是一条会「拉伸」的独立层**，不是每项各画一条。
    **条永远不出自己的按钮**：在旧项里长出来 → 换项瞬间直接在新项上出现 → 在新项里收回，
    靠两端**相向的有限拉伸**做呼应（值取自录屏逐帧半高边缘法，见 `VIDEO-ALIGN.md` §12）：

| 项 | 值 |
|---|---|
| 几何 | 3 × 16，圆角 2，`AccentFillColorDefault`（`NavigationViewSelectionIndicatorWidth/Height/Radius`） |
| 拉伸峰值 | **固定 1.6×**（16 → 25.6），与跳几格无关（跨 1 项/跨 4 项实测同为 38.1 设备 px） |
| 拉伸方向 | **单向**：旧条锚"尾部边"朝目标长（往下走 = 顶边），中心只挪 4.8px |
| 拉伸范围 | 只在所属项内：25.6 vs 项高 36，两端各留 0.4px（`--fl-nav-item-height` 改小要同步钳制） |
| 换项 | 旧条朝"头部边"塌缩+淡出 83ms；新条在目标项上**直接以满高出现**（不滑过间隙、不从 16 长起） |
| 节奏 | 拉伸 **167ms**（ControlFast）+ 收缩 **333ms**（ControlSlow）= 500ms |
| 缓动 | 拉伸 `cubic-bezier(0.4,0,0.7,0.4)`；收缩 `cubic-bezier(0.25,0.1,0.25,1)` |

    用法：把 `.fl-nav` 里带 `aria-current="page"` 的项交给 `M.transitionTo()` 即可，
    JS 会自动挂 `.fl-nav-ind` 层并维护 aria-current（首次进入走 `sync()` 静态落位）。

    - ⚠ **不要按 `|Δ|/16+1` 拉伸**（XAML 源码的写法）：会拉到 16+行距、跨过项间隙，
      看起来就是"装饰条跑出按钮"，与录屏不符 —— 第一版照抄踩过，校验器 R47 现在拦这个；
    - **每项的 `::before` 必须关掉**：`.fl-nav[data-fl-indicator="on"] .fl-nav-item[aria-current="page"]::before { content: none }`
      —— 不关就是同屏两条胶囊（R46 会拦）；
    - **两层的分工**：`ghost` 停在旧项里往目标长（origin = 尾部边），`pill` 落在新项里往回缩
      （origin = 头部边）；往上移动时两者的 origin 对调，塌缩用 translateY 补偿，不许中途换 origin；
    - **别用 `delay` 藏首个关键帧**：WAAPI 在 delay 期间就会套用第一帧，`pill` 会从一开始就是拉伸态，
      把 ghost 的生长阶段整个盖住（实测过，表现为"没有生长过程、直接跳"）；
    - 位移与拉伸只走 `transform`，不要过渡 `top`/`height`；
    - **WAAPI 不受 CSS 的 `prefers-reduced-motion` 块约束**，必须在 JS 里判 `REDUCED` 走静态落位（R46）。

## 官方关键数值速查（详见 official-values.md）

- 动效：Direct Entrance/Exit 167ms（exit 必须配 fade out）、Point to Point 167/250/333、Gentle Exit 167、Fade 83、Strong Entrance 三关键帧 167+167+333。
- **实测派生（非官方档，来自 60fps 录屏反解）**：页面转场 = 退场 167ms + 进场 250ms（全程 400ms；250 取官方 ControlNormal 档，见 WINUI-MOTION-SPEC.md）、drill 264px、nav 108px（= 录屏实测 176/72 的 1.5 倍，观感校准）、`--fl-ease-page` = cubic-bezier(0.1,0.9,0.2,1)（进场强减速）、`--fl-ease-page-out` = cubic-bezier(0.7,0,1,0.5)（退场加速）、连续型 `--fl-dur-sweep` 60s / `--fl-dur-tick` 1s。官方四档仍是 83/167/250/333，检索官方规范时不要引用这一行。
- 强调色（系统色，可整体替换）：`--fl-accent-fill` **暗主题 `#60CDFF`（SystemAccentColorLight2，配黑字）/ 亮主题 `#005FB8`（SystemAccentColorDark1，配白字）** —— 暗色用浅蓝、亮色用深蓝，由 `TextOnAccentFillColorPrimary`（暗=#000000 / 亮=#FFFFFF）反证。改色只动 `extract_tokens.py` 的 `ACCENT`，不要手改 `fluent2-tokens.css`。
- accent 状态档位（XAML brush Opacity）：`--fl-accent-fill-hover` = Default @0.9、`--fl-accent-fill-pressed` = Default @0.8。状态反馈用档位色过渡，禁用 `filter: brightness()`。**例外：滑块**的轨道填充与 thumb 不许用这两个 alpha 档（会透出底层，见规则 20）。
- 字阶：Caption 12/16、Body 14/20、Body Strong 14/20 Semibold、Body Large 18/24、Subtitle 20/28、Title 28/36、Title Large 40/52、Display 68/92。
- 控件：高 32px；Button padding 11,5,11,6；TextBox padding 10,5,6,6；列表项 min-height 40；ContentDialog padding 24 / max-width 548 / min-height 184；Switch 轨道 40×20、旋钮 12（hover 14 / pressed 17）、开态位移 **20px**（XAML `KnobTranslateTransform X=20`）；Slider 轨道 4 / 内圆 12 / 圆角 10（hover 1.167、pressed 0.833，250ms）；轨道**左段为 accent 已填充段**（`SliderTrackValueFill`，宽 = 半 thumb + 比例×(轨道宽-12)，由 `M.slider.auto()` 写 `--fl-slider-pct`），填充与 thumb 同步四档变色（Default→Secondary 0.9→Tertiary 0.8→Disabled）。
- 列表：行高单行 40 / 两行 64（后者 KIT 自定）；圆角 4；选中条 3×16 圆角 1.5；多选列宽 40.5；禁用透明度 0.3；图标 20；行内间距 12。
- 设置页列表：行高 **56**（实测派生）；组默认不套卡片；分隔线左缩进 = 行内边距 12 + 图标 20 + 列间距 12 = 44；组间 24。
- 滚动条（.fl-scroll）：命中区 12 / 静止视觉 **6** / hover·拖动视觉 **8** / 圆角 999 / 无箭头按钮；变粗只认 `::-webkit-scrollbar-thumb:hover`（不挂容器、不用 `:focus-within`）；Firefox 走 scrollbar-width:thin 回退。
- 勾选/单选：方框 20×20、圆角 4、描边 1；勾号字形 12 / 描边 2.5；单选内点 12（hover 1.167 / pressed 0.833）；控件行高 32。
- 下拉（自绘）：闭合态高 32、最小宽 64、箭头 12×12 距右缘 14；弹层最小宽 80、最大高 504（15 项）、圆角 8、描边 2、项高 32、项圆角 3、选中胶囊 3×16 圆角 1.5。
- 控件级时长：`--fl-dur-control-faster` 83ms（状态色变）/ `-fast` 167ms（勾号描绘）/ `-normal` 250ms（滑块、单选缩放）。
- 状态过渡曲线：一律 `--fl-ease-standard`（XAML `ControlFastOutSlowInKeySpline = 0,0,0,1`）；`--fl-ease-linear` **只允许**用于 opacity/visibility。
- 断点：≤640 Small / 641–1007 Medium / ≥1008 Large。
