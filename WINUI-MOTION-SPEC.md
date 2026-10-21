# WinUI 3 动效规范核查（2026-10-21）

目的：给 `win11-fluent-ui` 的转场参数找到**可引用的官方依据**，并标出我们偏离在哪、偏离是否成立。

---

## 1. 规范分三层，数字来源不同

| 层 | 出处 | 有哪些数字 | 强度 |
|---|---|---|---|
| 设计指导 | Learn：`/windows/apps/design/signature-experiences/motion` | 6 类动效的曲线 + 时长档（167/250/333/83） | 强 |
| 转场示例 | Learn：`/windows/apps/design/motion/motion-in-practice` | 转场四向的具体数值（150px / 300ms / 150ms） | 强（但是"示例"口径） |
| API 语义 | Learn：`/design/motion/page-transitions`、`NavigationTransitionInfo` | 只规定**用哪种转场**，不给时长/距离 | 强（语义）／无（数值） |
| 实现 | WinUI 源码 `microsoft-ui-xaml`（dxaml 原生层） | 具体毫秒数**未公开** | 无 |

结论：**"用哪种转场"有硬规范；"具体多少毫秒"只有档位与示例，没有逐转场的定值。**
所以录屏实测（我们做的 176px/283ms）在这套体系里是合法的一手依据。

---

## 2. 转场类型：官方只认三种 + 一种关闭

原文（Page transitions）：

| 类型 | API | 效果 | 官方指定场景 |
|---|---|---|---|
| **Page refresh** | `EntranceNavigationTransitionInfo` | 上滑 + 淡入 | **顶部导航**：标签页、**左侧导航** |
| **Drill** | `DrillInNavigationTransitionInfo` | "深入层级"（动画细节未公开） | 列表 → 详情 |
| **Horizontal slide** | `SlideNavigationTransitionInfo`（FromLeft/FromRight/FromBottom） | 水平滑动 | **同级页**；NavigationView 的**顶部导航**自动用它 |
| Suppress | `SuppressNavigationTransitionInfo` | 无动画 | 自建转场时 |

`Frame` 默认挂 `NavigationThemeTransition`，其默认动效 = Page refresh。

**对我们的意义**

- 左侧栏切页 → 官方就是 **Page refresh（上滑 + 淡入）**：我们的 `nav` 方向正确 ✓
- 点内容区入口进详情 → 官方叫 **Drill**，但**没有公开它到底怎么动**。
  我们做的是「水平滑动」，语义上更接近 `SlideNavigation`（同级页）。
  这是**已知的取舍**：录屏实测 Settings 的下钻就是水平位移，属于"跟随实机"而非"跟随 API 语义"。
- 顺带发现：**Fluent 2（Web）** 建议顶层导航用 **quick fade**、不要滑动（`fluent2.microsoft.design/motion`）。
  那是 Web 组件层的口径，与 Windows 应用（page refresh 上滑）相反，本 kit 不采用，但可解释"为什么有人觉得滑动多余"。

---

## 3. 数值：官方给到的全部

### 3.1 标准时长档（`Timing and easing`）

`ControlFasterAnimationDuration` **83ms** / `ControlFastAnimationDuration` **167ms** / `ControlNormalAnimationDuration` **250ms**
（另：主题资源里还有 `ControlSlowAnimationDuration` 333ms，早期文档列过）

### 3.2 六类动效（`Motion in Windows` 表格，原文值）

| 用途 | 曲线 | 时长 | 适用属性 |
|---|---|---|---|
| Direct Entrance | `cubic-bezier(0,0,0,1)` | 167 / 250 / 333 | 位置、缩放、旋转 |
| Point to Point（已存在元素） | `cubic-bezier(0.55,0.55,0,1)` | 167 / 250 / 333 | 位置、缩放、旋转 |
| Direct Exit | `cubic-bezier(0,0,0,1)` | 167 | 位置、缩放、旋转（**必须配淡出**） |
| Gentle Exit | `cubic-bezier(1,0,1,1)` | 167 | 位置、缩放 |
| Bare Minimum（淡入淡出） | `linear` | 83 | 不透明度 |
| Strong Entrance | 3 关键帧 `(0.85,0,0,1)` / `(0.85,0,0.75,1)` / `(0.85,0,0,1)` | 167 / 167 / 333 | 位置、缩放 |

**注意**：时长选择是**按距离分档**（167 近、333 远），不是按场景定死。

### 3.3 转场示例（`motion-in-practice`，唯一给"页面转场"具体值的地方）

| 方向 | 官方值 |
|---|---|
| Forward Out | 淡出 **150ms**，accelerate |
| **Forward In** | **上滑 150px / 300ms / decelerate** |
| Backward Out | 下滑 150px / **150ms** / accelerate |
| Backward In | 淡入 **300ms** / decelerate |

### 3.4 官方自身的一处不一致（值得记录）

同一个"进场"：§3.2 的档位是 **167/250/333**，§3.3 的转场示例却写 **300ms**。
300 不在 333/250 任一档上。说明"页面转场时长"是**指导性**的，不是可校验常量。
→ 我们没有理由为了"凑 300"而改；反过来，凑到 **250**（三档之一）在体系内更自洽。

### 3.5 旧版（UWP）文档的等价曲线

`decelerate = cubic-bezier(0.1,0.9,0.2,1)`、`accelerate = cubic-bezier(0.7,0,1,0.5)`。
本 kit 目前用的就是这一对——**来源合法，但属于上一代命名**（当前表格里对应 Direct Entrance / Gentle Exit 的不同数值）。

---

## 4. 现状 vs 官方（逐项）

| 项 | 官方 | 本 kit | 判定 |
|---|---|---|---|
| 左导航转场类型 | Page refresh（上滑+淡入） | 垂直上滑 108px + 淡入 83ms | ✓ 类型对 |
| 内容区入口转场类型 | Drill（细节未公开） | 水平滑动 264px | △ 语义偏 Slide，跟实测 |
| 进场时长 | 250 / 300 / 333 | **283** | ✗ 不在任何档位上 |
| 退场时长 | 150 / 167 | 167 | ✓ |
| 进场曲线 | `(0,0,0,1)` 或旧 `(0.1,0.9,0.2,1)` | `(0.1,0.9,0.2,1)` | ✓（旧版值） |
| 退场曲线 | `(1,0,1,1)` 或旧 `(0.7,0,1,0.5)` | `(0.7,0,1,0.5)` | ✓（旧版值） |
| 行程 | 150px（示例） | 264px（观感校准） | △ 有意偏离，已记录 |
| 两拍（退场→进场） | 官方未描述 | 有 | △ 来自实测，保留 |
| 元素 stagger | 官方只说"短偏移"，Bare Minimum 83 / Strong Entrance 333 | step 83、cap 333，从 133ms 起 | △ 尾巴最长 ≈800ms |

---

## 5. 结论与建议（按证据强度排序）

### 已实施

1. ~~进场 283 → 250ms~~ **已改（2026-10-21）**：250 是官方三档之一，总时长 450 → 400ms（退场 167 不动）。
   cdp_check 新增断言：`--fl-dur-page` 必须是 167/250/333 之一。

### 已否决（有实测数据）

2. ~~进场曲线 `(0.1,0.9,0.2,1)` → `(0,0,0,1)`~~ **不采用**。
   我原以为官方新曲线"起手更快"，实测反了：`(0,0,0,1)` 的 x(u)=u³，**前段比现用曲线慢一倍**。
   同一行程 264px、同时长 250ms 下的剩余位移（`tests/enter-easing-ab.html` 定格实测）：

   | t (ms) | A 现用 (0.1,0.9,0.2,1) | B 官方 (0,0,0,1) |
   |---|---|---|
   | 160 | 103px | **141px** |
   | 190 | 45px | **89px** |
   | 230 | 17px | **47px** |
   | 280 | 5px | **19px** |

   换成 B 会让"感觉更久"，与"嫌稍长"的诉求相反。现用曲线是旧版文档的 decelerate 值，
   语义同为"进场强减速"，**保留**。

### 中等证据、可选

3. **退场曲线 `(0.7,0,1,0.5)` → `(1,0,1,1)`**（Gentle Exit，同为 167ms）。
   两者都是"加速离开"，新版曲线更陡；录屏拟合值更接近 `(0.7,0,1,0.5)`，所以**建议不动**，只记录候选。
4. **stagger 尾巴**：把 `CAP` 从 333 收到 250，让整页在 ≈550ms 内彻底安静（当前 ≈800ms）。
   官方没有 stagger 具体值，这一条属于"体感优化"，不是规范要求。

### 不建议改

5. **行程 264 → 150**：官方示例值会让位移重新变短（用户已否决过 176）。
6. **drill 改成真正的 DrillIn**：官方没公开 Drill 的动画参数，改了就是纯猜；现有实测算唯一漂移依据。

---

## 6. 来源

- https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/motion （六类动效表）
- https://learn.microsoft.com/en-us/windows/apps/design/motion/timing-and-easing （标准时长档、缓动定义）
- https://learn.microsoft.com/en-us/windows/apps/design/motion/motion-in-practice （转场四向示例）
- https://learn.microsoft.com/en-us/windows/apps/design/motion/page-transitions （转场类型与适用场景）
- https://learn.microsoft.com/en-us/windows/windows-app-sdk/api/winrt/microsoft.ui.xaml.media.animation.entrancenavigationtransitioninfo
- https://learn.microsoft.com/en-us/windows/windows-app-sdk/api/winrt/microsoft.ui.xaml.media.animation.drillinnavigationtransitioninfo
- https://fluent2.microsoft.design/motion （Web 层口径，与本 kit 不同层）

---

## 7. A/B 工具

`tests/enter-easing-ab.html`：左右两栏同参数（264px / 250ms / 133ms 起手）只换缓动，
点击「播放一次」双侧同步；带 1/4 慢放、实时行程读数、以及两条曲线的解析进度表。
`tests/` 下还有定格脚本思路：用 `document.getAnimations()` 暂停后设 `currentTime`，可抓任意时刻的确定帧。

---

## 8. 侧栏选中指示条（源码级规范）

`microsoft-ui-xaml` → `controls/dev/NavigationView/NavigationView.cpp` → `PlayIndicatorAnimations()`：

| 关键帧 | 值 |
|---|---|
| posAnim | 0% = from；33.3% = to（`singleStep`：前段不动，到点直接跳） |
| scaleAnim | 0% = 1；33.3% = `|to-from|/dimension + 1`；100% = 1 |
| centerAnim | 0% = 0；100% = dimension（200ms，`singleStep` → 缩放中心在 200ms 处切边） |
| duration | 600ms（opacity 同） |
| easing | 拉伸 `cubic-bezier(0.9,0.1,1,0.2)`；收缩 `cubic-bezier(0.1,0.9,0.2,1)` |

模板实现见 KIT 规则 26；录屏实测见 `VIDEO-ALIGN.md` §12（拉伸峰值 = 16 + 行距，与公式一致）。

