# official-values —— WinUI 3 / Fluent 官方数值（全部带出处）

> 提取脚本 `extract_tokens.py`；XAML 源：microsoft-ui-xaml `controls/dev/CommonStyles` （commit `09cfc8ff3fbf`，2026-10-20，MIT）；文档源：learn.microsoft.com（快照见 `raw/doc_*.md`）。
> 完整颜色库存共 **152** 个 token（暗/亮双主题），精选映射进 `fluent2-tokens.css`；全量见 `official-values.json` 的 `colors_selected` 与 `raw/`。

## 强调色（系统色）
- 默认 `#0078D4`（Windows 11 默认系统强调色）。XAML 引用 SystemAccentColor（系统用户色）；此处取 Win11 默认强调色，暗色填充用 Dark1 档、亮色填充用 Light2 档，可整体替换。
- 变体规则（XAML）：暗主题填充用 SystemAccentColorDark1，亮主题用 SystemAccentColorLight2；
  文本色 Dark2/Light3；共 Light1-3 / Dark1-3 六档。用户可整体替换 accent。
- 状态档位（按 XAML brush 的 Opacity 派生，不另取 hex）：`--fl-accent-fill-hover` = Default @Opacity 0.9（AccentFillColorSecondaryBrush）、`--fl-accent-fill-pressed` = Default @Opacity 0.8（AccentFillColorTertiaryBrush）。

## 精选颜色 token（暗/亮）

> 注意：下表 dark/light 列为 **XAML 原始格式 `#AARRGGBB`**（alpha 在前）；
> `fluent2-tokens.css` 中已转换为 **CSS 格式 `#RRGGBBAA`**（alpha 在后）。

| CSS 变量 | XAML key | dark | light |
|---|---|---|---|
| `--fl-text-primary` | TextFillColorPrimary | #FFFFFF | #E4000000 |
| `--fl-text-secondary` | TextFillColorSecondary | #C5FFFFFF | #9E000000 |
| `--fl-text-tertiary` | TextFillColorTertiary | #87FFFFFF | #72000000 |
| `--fl-text-disabled` | TextFillColorDisabled | #5DFFFFFF | #5C000000 |
| `--fl-text-on-accent-primary` | TextOnAccentFillColorPrimary | #000000 | #FFFFFF |
| `--fl-text-on-accent-secondary` | TextOnAccentFillColorSecondary | #80000000 | #B3FFFFFF |
| `--fl-text-on-accent-disabled` | TextOnAccentFillColorDisabled | #87FFFFFF | #FFFFFF |
| `--fl-control-fill-default` | ControlFillColorDefault | #0FFFFFFF | #B3FFFFFF |
| `--fl-control-fill-secondary` | ControlFillColorSecondary | #15FFFFFF | #80F9F9F9 |
| `--fl-control-fill-tertiary` | ControlFillColorTertiary | #08FFFFFF | #4DF9F9F9 |
| `--fl-control-fill-disabled` | ControlFillColorDisabled | #0BFFFFFF | #4DF9F9F9 |
| `--fl-control-fill-input-active` | ControlFillColorInputActive | #B31E1E1E | #FFFFFF |
| `--fl-control-strong-fill` | ControlStrongFillColorDefault | #8BFFFFFF | #72000000 |
| `--fl-control-strong-fill-disabled` | ControlStrongFillColorDisabled | #3FFFFFFF | #51000000 |
| `--fl-control-solid-fill` | ControlSolidFillColorDefault | #454545 | #FFFFFF |
| `--fl-control-stroke` | ControlStrokeColorDefault | #12FFFFFF | #0F000000 |
| `--fl-control-stroke-secondary` | ControlStrokeColorSecondary | #18FFFFFF | #29000000 |
| `--fl-control-stroke-on-accent` | ControlStrokeColorOnAccentDefault | #14FFFFFF | #14FFFFFF |
| `--fl-control-stroke-on-accent-secondary` | ControlStrokeColorOnAccentSecondary | #23000000 | #66000000 |
| `--fl-subtle-fill-hover` | SubtleFillColorSecondary | #0FFFFFFF | #09000000 |
| `--fl-subtle-fill-pressed` | SubtleFillColorTertiary | #0AFFFFFF | #06000000 |
| `--fl-subtle-fill-disabled` | SubtleFillColorDisabled | #00FFFFFF | #00FFFFFF |
| `--fl-card-bg` | CardBackgroundFillColorDefault | #0DFFFFFF | #B3FFFFFF |
| `--fl-card-bg-secondary` | CardBackgroundFillColorSecondary | #08FFFFFF | #80F6F6F6 |
| `--fl-card-stroke` | CardStrokeColorDefault | #19000000 | #0F000000 |
| `--fl-layer-fill` | LayerFillColorDefault | #4C3A3A3A | #80FFFFFF |
| `--fl-smoke` | SmokeFillColorDefault | #4D000000 | #4D000000 |
| `--fl-solid-bg-base` | SolidBackgroundFillColorBase | #202020 | #F3F3F3 |
| `--fl-solid-bg-base-alt` | SolidBackgroundFillColorBaseAlt | #0A0A0A | #DADADA |
| `--fl-solid-bg-secondary` | SolidBackgroundFillColorSecondary | #1C1C1C | #EEEEEE |
| `--fl-solid-bg-tertiary` | SolidBackgroundFillColorTertiary | #282828 | #F9F9F9 |
| `--fl-solid-bg-quarternary` | SolidBackgroundFillColorQuarternary | #2C2C2C | #FFFFFF |
| `--fl-divider-stroke` | DividerStrokeColorDefault | #15FFFFFF | #0F000000 |
| `--fl-focus-stroke-outer` | FocusStrokeColorOuter | #FFFFFF | #E4000000 |
| `--fl-focus-stroke-inner` | FocusStrokeColorInner | #B3000000 | #B3FFFFFF |
| `--fl-success` | SystemFillColorSuccess | #6CCB5F | #0F7B0F |
| `--fl-caution` | SystemFillColorCaution | #FCE100 | #9D5D00 |
| `--fl-critical` | SystemFillColorCritical | #FF99A4 | #C42B1C |
| `--fl-success-bg` | SystemFillColorSuccessBackground | #393D1B | #DFF6DD |
| `--fl-caution-bg` | SystemFillColorCautionBackground | #433519 | #FFF4CE |
| `--fl-critical-bg` | SystemFillColorCriticalBackground | #442726 | #FDE7E9 |
| `--fl-accent-fill-disabled` | AccentFillColorDisabled | #28FFFFFF | #37000000 |

## 动效（motion）
出处：<https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/motion>

| 名称 | 曲线 | 时长 | 用途 |
|---|---|---|---|
| Direct Entrance | cubic-bezier(0,0,0,1) | 167/250/333ms | Position, Scale, Rotation（已有元素入场，Fast-In） |
| Point to Point | cubic-bezier(0.55,0.55,0,1) | 167/250/333ms | 位置/缩放/旋转的点对点位移 |
| Direct Exit | cubic-bezier(0,0,0,1) | 167ms | 离场（**必须**配 fade out） |
| Gentle Exit | cubic-bezier(1,0,1,1) | 167ms | 最简离场（Position, Scale） |
| Fade | linear | 83ms | 仅 Opacity |
| Strong Entrance | 三关键帧 Elastic In | 167+167+333ms | Position, Scale（弹性入场） |

规则：Direct Exit 必须与 fade out 组合（官方硬性要求）；Strong Entrance 为 Elastic In 三关键帧：167ms(0.85,0,0,1) → 167ms(0.85,0,0.75,1) → 333ms(0.85,0,0,1)；同一入口的表面以相同方式开合（Consistent）；优先用现成控件转场（Resourceful），网页对应=直接用本 KIT 的 motion 类。

## 动效：实测派生（**非官方档位**）
来源：Win11 官方应用 60fps 录屏逐帧反解（2026-10-21），方法与原始数字见 `VIDEO-ALIGN.md` §9。
这些值**不属于**官方 83 / 167 / 250 / 333ms 四档，检索官方规范时不要引用本节。

| CSS 变量 | 值 | 用途 | 依据 |
|---|---|---|---|
| `--fl-dur-page` | 283ms | 页面转场（二级下钻水平 / 一级导航垂直共用同一节奏） | 录屏《设置》10-21：下钻逐帧位移 2,4,6,8,12,16,22,34,70|66,38,24,16,10,8,6，17 帧 ≈283ms |
| `--fl-dur-tick` | 1s | 连续型：秒针跳秒周期（每秒一次 83ms 小变化） | 录屏《时钟》10-21：每秒出现一次 83ms、变化面积 0.6% 的位移 |
| `--fl-dur-sweep` | 60s | 连续型：秒针整圈（分针/时针用 calc 倍乘） | 连续型动效的物理周期，非测量值 |
| `--fl-ease-page` | `cubic-bezier(0.6,0,0.3,1)` | 页面转场：对称加减速（逐帧增量先增后减，峰在中段） | 拟合自录屏《设置》下钻的逐帧位移序列 |
| `--fl-ease-steps-60` | `steps(60, end)` | 跳秒：一秒 60 步 | 录屏《时钟》秒针每秒一跳 |
| `--fl-page-shift-drill` | 176px | 二级下钻单层行程（水平） | 录屏《设置》实测 350 视频 px @2x ≈175 CSS px，取 4 的倍数 176 |
| `--fl-page-shift-nav` | 72px | 一级导航单层行程（垂直） | 录屏《设置》实测 127–144 视频 px @2x ≈64–72 CSS px，取上界 72 |

## 字阶（Type ramp，Segoe UI Variable）
出处：<https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/typography>；字号与 `xaml_TextBlock_themeresources.xaml` 交叉一致。

| 样式 | 字号/行高 | 字重 | CSS 类 |
|---|---|---|---|
| Caption | 12/16 | 400 | `.fl-caption` |
| Body | 14/20 | 400 | `.fl-body` |
| Body Strong | 14/20 | 600 | `.fl-body-strong` |
| Body Large | 18/24 | 400 | `.fl-body-large` |
| Body Large Strong | 18/24 | 600 | `.fl-body-large-strong` |
| Subtitle | 20/28 | 600 | `.fl-subtitle` |
| Title | 28/36 | 600 | `.fl-title` |
| Title Large | 40/52 | 600 | `.fl-title-large` |
| Display | 68/92 | 600 | `.fl-display` |

字重轴：Light 300 / Semilight 350 / Regular 400 / Semibold 600 / Bold 700；强调用 Semibold 不用 Bold；不用斜体。
最小可读：14px Semibold、12px Regular。每行 50–60 字符。

## 间距（spacing & gutters）
出处：<https://learn.microsoft.com/en-us/windows/apps/design/basics/content-basics>；所有 UI 尺寸/边距/位置为 4 epx 的倍数（文本除外）——learn.../breakpoints#multiples-of-four

| 间距 | 用途 |
|---|---|
| 8 epx | 按钮之间 |
| 8 epx | 按钮与 flyout 之间 |
| 8 epx | 控件与标题(header)之间 |
| 12 epx | 控件与标签(label)之间 |
| 12 epx | 内容区之间 |
| 16 epx | 表面与边缘文字之间 |
| 16 epx | 控件与 expander 按钮之间（右对齐） |
| 48 epx | expander 内控件缩进 |

## 海拔与描边（layering & elevation）
出处：<https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/layering>

| 元素 | Elevation | 描边 |
|---|---|---|
| Window/Dialog | 128 | 1px |
| Flyout | 32 | 1px |
| Tooltip | 16 | 1px |
| Card | 8 | 1px |
| Control | 2 | 1px |
| Layer | 1 | 1px |

控件状态：Rest=2 / Hover=2 / Pressed=1。
双层系统：Base layer（导航/命令）+ Content layer（核心内容，卡片化）。
**CSS 阴影换算（KIT 自定，非官方 CSS 值）**：`blur ≈ elevation×0.5px`，两层投影，透明度随海拔增大，见 `fluent2-tokens.css` 注释。

## 圆角（geometry）
出处：<https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/geometry>；与 `xaml_CornerRadius_themeresources.xaml` 交叉一致。

| 圆角 | 用途 |
|---|---|
| 8px | 顶层容器：窗口、flyout、dialog、menuflyout、teaching tip |
| 4px | 页内元素：button、checkbox、textbox、combobox、listview、progressbar/slider/scrollbar 条形；ToolTip 例外也是 4px |
| 0px | 直边相接处；flyout 与唤起方相连一侧；snap/maximized 窗口 |

## 控件几何（XAML 默认值）
| 资源 | 值 | 出处 |
|---|---|---|
| Button 内边距 | `11,5,11,6` | raw/xaml_Button_themeresources.xaml |
| TextBox/ComboBox 内边距 | `10,5,6,6` | raw/xaml_Common_themeresources.xaml |
| ContentDialog 内边距 | `24` | raw/xaml_ContentDialog_themeresources.xaml |
| ContentDialog 最大宽 | `548` | raw/xaml_ContentDialog_themeresources.xaml |
| ContentDialog 最小高 | `184` | raw/xaml_ContentDialog_themeresources.xaml |
| 列表项最小高 | `40` | raw/xaml_ListViewItem_themeresources.xaml |
| 列表项圆角 | `4` | raw/xaml_ListViewItem_themeresources.xaml |
| 选中指示条圆角 | `1.5` | raw/xaml_ListViewItem_themeresources.xaml |
| 列表项禁用透明度 | `0.3` | raw/xaml_ListViewItem_themeresources.xaml |
| 文本控件最小高 | `32` | WinUI DefaultTextBoxStyle MinHeight=TextControlThemeMinHeight，默认 32（stackover­flow.com/questions/78760996 引 generic.xaml；与 WinUI 3 Gallery 视觉一致） |
| 控件标准高 | `32` | Win11 常驻控件标准高度 32px（Button/TextBox/ComboBox/Slider 实际渲染高度；官方文档未单列数值，按 XAML 默认渲染确认） |
| SliderTrackThemeHeight | `4` | raw/xaml_Slider_themeresources.xaml：SliderTrackThemeHeight=4（轨道粗） |
| SliderInnerThumbWidth | `12` | raw/xaml_Slider_themeresources.xaml：SliderInnerThumbWidth=12（内圆直径，外环 20 由描边近似） |
| SliderThumbCornerRadius | `10` | raw/xaml_Slider_themeresources.xaml：SliderThumbCornerRadius=10（圆形 thumb） |

## 断点与单位
出处：<https://learn.microsoft.com/en-us/windows/apps/design/layout/screen-sizes-and-breakpoints-for-responsive-design>

| 档位 | 范围 |
|---|---|
| Small | ≤640px |
| Medium | 641–1007px |
| Large | ≥1008px |

单位为 effective pixels（epx，网页直接当 CSS px 用）；**4 的倍数规则**：所有 UI 尺寸/边距/位置为 4 epx 的倍数（文本除外）——learn.../breakpoints#multiples-of-four

## 材质（网页近似方案，官方无数值页）
出处：<https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/materials>（只有原则）

| 材质 | 官方规则 | 网页落地（标注近似） |
|---|---|---|
| Mica | 不透明基底，染桌面壁纸色；应用基底 | `--fl-solid-bg-base` 纯色（网页无壁纸来源，近似=纯色基底层） |
| Acrylic | 半透明磨砂，只用于瞬态轻触消失表面（flyout/菜单） | 纯色 + `backdrop-filter: blur(60px) saturate(125%)` |
| Smoke | 模态遮罩，恒为半透明黑（不分主题） | `--fl-smoke`（XAML SmokeFillColorDefault=#4D000000） |

## 导航与命令（原则，无数值）
- 左导航（NavigationView）：顶层页、导航项 >5、不频繁切换；顶部导航：要全展示/省空间/图标不够表意。
- 超过 2 层用 BreadcrumbBar；扁平 ≤8 页 / 层级 >7 页；避免 pogo-sticking。
- 命令：能直接操作就不加命令；高频放画布，其余 CommandBar/菜单；确认仅用于不可撤销且后果重大操作。
出处：navigation-basics / commanding-basics（快照 raw/doc_basics-and-layout.md）。
