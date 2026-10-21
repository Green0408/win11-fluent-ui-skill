# 官方文档快照：Signature Experiences（抓取日期 2026-10-20，来源 learn.microsoft.com/en-us/windows/apps/design/signature-experiences/）

## Motion（/motion）
| Purpose | Ease | Timing(ms) | Used For |
|---|---|---|---|
| Direct Entrance | cubic-bezier(0,0,0,1) | 167, 250, 333 | Position, Scale, Rotation（Existing Elements） |
| Point to Point | cubic-bezier(0.55,0.55,0,1) | 167, 250, 333ms | Position, Scale, Rotation |
| Direct Exit | cubic-bezier(0,0,0,1) | 167ms | Position, Scale, Rotation（**必须**与 fade out 组合） |
| Gentle Exit | cubic-bezier(1,0,1,1) | 167ms | Position, Scale（Bare Minimum） |
| Fade – In + Out | Linear | 83ms | Opacity |
| Strong Entrance | Elastic In（3 关键帧） | 见下 | Position, Scale |

Strong Entrance 关键帧：
1. cubic-bezier(0.85, 0, 0, 1) — 167ms
2. cubic-bezier(0.85, 0, 0.75, 1) — 167ms
3. cubic-bezier(0.85, 0, 0, 1) — 333ms

原则：Connected / Consistent（同一入口同一开合方式）/ Responsive / Delightful / Resourceful（优先用现成控件动画，避免自定义）。
推荐控件化动效：Page transitions、Connected animation、Animated Icon。

## Typography（/typography）
Type ramp（Windows 11；页面显示名 ↔ 惯用名，单位 epx）：
| 惯用名 | 页面显示名 | Size/line-height | Weight |
|---|---|---|---|
| Caption | Small | 12/16 | Regular |
| Body | Text | 14/20 | Regular |
| Body Strong | Text semibold | 14/20 | Semibold |
| Body Large | Text（large） | 18/24 | Regular |
| Body Large Strong | Text semibold（large） | 18/24 | Semibold |
| Subtitle | — | 20/28 | Semibold |
| Title | — | 28/36 | Semibold |
| Title Large | — | 40/52 | Semibold |
| Display | — | 68/92 | Semibold |

Weight 轴（Segoe UI Variable `wght`）：Light 300 / Semilight 350 / Regular 400 / Semibold 600 / Bold 700。
Opsz 轴：8pt–36pt 自动光学缩放。
最小可读：**14px Semibold、12px Regular**（更小即不可读）。
强调用 Semibold 不用 Bold；不用斜体。每行 50–60 字符，不少于 20、不多于 60。默认左对齐。

## Layering / Elevation（/layering）
海拔值（阴影+描边 contour 表达；描边宽一律 1）：
| 元素 | Elevation | Stroke width |
|---|---|---|
| Window | 128 | 1 |
| Dialog | 128 | 1 |
| Flyout | 32 | 1 |
| Tooltip | 16 | 1 |
| Card | 8 | 1 |
| Control | 2 | 1 |
| Layer | 1 | 1 |

控件状态：Rest=2 / Hover=2 / Pressed=1（描边均 1）。海拔越高阴影越大越柔。
双层系统：**Base layer**（菜单/命令/导航所在最底层）+ **Content layer**（核心内容，可为连续面或卡片）。

## Materials（/materials）
- **Acrylic**：半透明磨砂玻璃；**只用于瞬态轻触消失表面**（flyout、context menu）；明暗模式均支持。
- **Mica**：不透明材质，染用户桌面背景色；用于应用基底；明暗模式均支持；带 active/inactive 焦点态。
- **Smoke**：模态遮罩，压暗下层以突出模态 UI（如 dialog）；**不分模式，恒为半透明黑**。

## Color（/color）
- 双主题 light/dark；深色=次要背景表面，重要表面更亮更突出（两模式同理）。
- Accent 强调色：节制使用、表交互状态、自动按对比度生成（文档无固定 hex）。
- 对比度：无具体数值要求（原文无 WCAG 数值）。
- 色盲：约 8% 男性、0.5% 女性红绿色盲，勿以红绿对比作唯一区分。

## Geometry（/geometry）
圆角三级：
| 圆角 | 用途 |
|---|---|
| **8px** | 顶层容器：app windows、flyouts、dialogs |
| **4px** | 页内元素：buttons、list backplates；ProgressBar/ScrollBar/Slider 等条形元素 |
| **0px** | 直边相接处（如 SplitButton 两半相触处）；flyout 与唤起它的 UI 相连的一侧；窗口 snap/maximized 时 |

- 常驻控件（Button、CheckBox、ComboBox、TextBox、ListView）= 4px。
- 瞬态覆盖元素（ContentDialog、Flyout、MenuFlyout、TeachingTip）= 8px；**ToolTip 例外 = 4px**（因尺寸小）。
- 全局资源：`ControlCornerRadius`=4px、`OverlayCornerRadius`=8px。
