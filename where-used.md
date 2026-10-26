# where-used.md —— 反查表：界面元素 → 该用哪条官方数值/令牌

| 界面元素 | 用什么 | 官方出处 |
|---|---|---|
| 应用基底背景 | `--fl-solid-bg-base`（Mica 网页近似） | XAML SolidBackgroundFillColorBase |
| 正文/说明/标题文字 | `.fl-body` / `.fl-caption` / `.fl-subtitle`… 字阶类 | learn.../typography + XAML TextBlock 字号 |
| 次要/禁用文字 | `--fl-text-secondary` / `--fl-text-disabled` | XAML TextFillColorSecondary/Disabled |
| 按钮（常规） | `.fl-btn`（高 32、padding 11,5,11,6、圆角 4、rest 阴影 e2） | XAML ButtonPadding + layering Rest=2 |
| 按钮（强调） | `.fl-btn.fl-btn-accent`（`--fl-accent-fill`） | XAML AccentFillColorDefaultBrush 规则 |
| 按钮 hover / pressed | 内置：`--fl-control-fill-secondary/tertiary` | XAML ControlFillColor* |
| 文本框 | `.fl-input`（高 32、padding 10,5,6,6、底边加重、焦点 accent 底边） | XAML TextControlThemePadding + MinHeight 32 |
| 设置页列表 | `.fl-settings` + `.fl-settings-group` + `.fl-settings-row`（组标题/说明 + 行：图标 20 + 主副标题 + 右控件；行高 56；组默认不套卡片；`data-divided` 出左缩进分隔线；`data-card` 变卡片分组） | 实测派生（2026-10-21 录屏：语音包列表）+ ListViewItemMinHeight/IconSize |
| 下拉（首选） | `.fl-combo`（闭合态 32/箭头 12、Acrylic 弹层 radius 8/描边 2/最大高 504、项 32+胶囊 1.5、`M.combo.auto()` 接键盘；**弹层必须带 `.fl-scroll`**；弹层**压在按钮上**（选中项那一行盖住按钮）、从顶边往下 `clip-path` 揭示 167ms / `--fl-ease-popup`，关闭瞬变） | XAML ComboBox_themeresources（ComboBoxThemeMinWidth / PopupBorderThemeThickness / ItemCornerRadius / MaxDropDownHeight） |
| 细滚动条 | `.fl-scroll`（12 命中区 / 4 视觉 / hover 8 / 圆角 999 / 无箭头；Firefox 走标准属性 + `@supports` 互斥） | KIT 自定（Win11 滚动条形态；浏览器默认 17px 方块） |
| 下拉（无 JS 回退） | `.fl-select`（原生 `<select>` 套 TextBox 外观；面板由 OS 绘制，暗色会漏白） | 同上 |
| 开关 | `.fl-switch`（轨道 40×20、旋钮 12、开态位移 20px、hover 14 / pressed 17） | XAML ToggleSwitch（KnobTranslateTransform X=20、SplineDoubleKeyFrame 14/17） |
| 滑块 | `.fl-slider`（轨道 4、内点 12、外框恒 20、圆角 10；hover 内点 14 / pressed 10，外框不变，进 250ms / 出 167ms；左段 accent 已填充段 + thumb 同步四档色；`M.slider.auto()` 写入 `--fl-slider-pct`） | XAML Slider（SliderTrackThemeHeight / SliderInnerThumbWidth / SliderThumbCornerRadius / SliderOuterThumbBackground / **SliderTrackValueFill** / SliderThumbBackground 的 PointerOver·Pressed·Disabled 四档 + SliderThumbStyle 的 VisualState 只缩内点） |
| 复选/单选 | `.fl-check` / `.fl-radio`（20×20、圆角 4、描边 1；勾号为 SVG 描画 12px/描边 2.5、167ms；单选内点 12 + hover 1.167/pressed 0.833；含半选/禁用） | XAML CheckBoxSize/GlyphSize/BorderThickness + RadioButtonCheckGlyphSize + ListViewItem CheckGlyph StrokeThickness |
| 列表（结构） | `.fl-list` + `.fl-listitem` + `.fl-list-content`（勾选列 + 图标 20 + 主副标题 + 尾部区域；行高 40/64 两档；`minmax(0,1fr)` 保省略号） | XAML ListViewItemMinHeight/MinWidth/CornerRadius |
| 列表（状态） | 六档：rest / hover / pressed / selected / selected+hover / selected+pressed（后者比前者更淡，官方反色档）；选中条 3×16 圆角 1.5；禁用 0.3 | XAML ListViewItemPresenter 六组 Background brush + SelectionIndicatorCornerRadius |
| 列表（多选） | `.fl-list[data-multiselect]`（勾选列 40.5px，列宽过渡；勾选状态由行 aria-selected 驱动） | XAML ListViewItemContentOffsetX / CheckMode=Inline |
| 列表（分组线） | `.fl-list-sep`（1px，上下各 4px；独立兄弟元素，不被行背景覆盖） | XAML NavigationViewItemSeparatorHeight + DividerStrokeColorDefault |
| 卡片 | `.fl-card`（圆角 8、elevation 8、`--fl-card-bg/stroke`） | XAML Card* + layering Card=8 |
| 应用外壳（布局） | `.fl-shell` + `.fl-content-layer` + `.fl-page`：左导航固定、内容区独立滚动；每页各自滚（切页记住位置） | web-app-shell 常见做法（KIT 规则 24）；Win11 视觉依据见 navigation-basics |
| 左导航（选中指示条） | `.fl-nav-ind`（JS 自动挂；`M.nav.indicator.to/sync`，`M.transitionTo` 已接线） | XAML NavigationViewSelectionIndicator 系列 几何 + 录屏实测节奏（拉伸 167 / 收缩 333，峰值固定 1.6×，见 VIDEO-ALIGN §12） |
| 左导航 | `.fl-nav` + `.fl-nav-item`（项高 36、圆角 2、选中=subtle 填充 + 3×16 accent 胶囊；文字包 `.fl-nav-label`、图标用 `.fl-nav-icon`） | XAML NavigationViewItemOnLeftMinHeight / SelectionIndicatorWidth/Height/Radius |
| 左导航响应式 | `M.nav.responsive.auto()`：≥1008 展开 240 / 641–1007 收成 48 图标列 / ≤640 收起 + 汉堡浮层 + `--fl-smoke` 遮罩；`.fl-nav-toggle`(40×36) + `.fl-nav-scrim` 必须一起放 | NavigationView `PaneDisplayMode=Auto` 默认行为（CompactModeThresholdWidth=641 / ExpandedModeThresholdWidth=1008，与响应式断点同值）；KIT 规则 27 |
| 通知条 | `.fl-infobar[data-severity=success/caution/critical]`（`--fl-success/caution/critical`） | XAML SystemFillColor* |
| flyout / 右键菜单 | `.fl-flyout.fl-overlay`（Acrylic 近似 + 圆角 8 + 阴影 e32；开合 = **整个弹层滑入视野**，行程 = 自身高度，**clip-path 裁到自身矩形**（从触发元素那一侧长出来），250/167ms，不淡入） | materials + geometry + layering Flyout=32 + WinUI `MenuPopupThemeTransition`（录屏实测见 VIDEO-ALIGN §14） |
| 对话框 | `.fl-dialog.fl-overlay` + `M.dialog`（Smoke 遮罩、圆角 8、阴影 e128、padding 24、max-width 548） | XAML ContentDialogPadding/MaxWidth/MinHeight + materials Smoke |
| tooltip | 圆角 4（小尺寸例外）、阴影 e16 | geometry ToolTip 例外 + layering Tooltip=16 |
| 元素入场 | `.fl-entrance` + `M.stagger`（167ms standard，位移 8px；83ms 步进上限 333，延迟走 `--fl-stagger-delay`） | motion Direct Entrance + Fade 档；位移量实测自录屏 |
| 页面切换（一级导航） | `M.transitionTo(id)`（默认 `kind:'nav'`，垂直 108px，250ms；**方向恒为自下往上**（不按导航序反向），要反向须显式 `{dir:'up'}`） | 实测派生（见 KIT 规则 15） |
| 页面切换（二级下钻） | `M.transitionTo(id,{kind:'drill'})`（水平 264px，返回用 `M.back('drill')` 方向取反） | 实测派生（见 KIT 规则 15） |
| 连续型动效（秒针/进度环） | `.fl-dial` + `.fl-dial-hand.fl-tick`（每秒 6°）/ `.fl-continuous`（linear 倍乘） | 录屏《时钟》秒针；见 KIT 规则 16 |
| 弹性大入场 | `.fl-strong-entrance`（三关键帧 167+167+333） | motion Strong Entrance |
| 元素离场 | `.fl-exit`（必须配 fade out）；浮层出场用 `.fl-overlay:not(.fl-open)` 的 soft 曲线（Gentle Exit 语义），不再有单独的出场类 | motion（硬性要求） |
| accent 按钮状态 | `.fl-btn-accent:hover/:active` 用 `--fl-accent-fill-hover/pressed`（Default @0.9/@0.8） | XAML AccentFillColorSecondary/TertiaryBrush |
| 位移过渡（拖拽/排序） | `.fl-movable`（point 曲线） | motion Point to Point |
| 纯透明度切换 | `.fl-fade`（linear 83ms） | motion Fade |
| 焦点框 | `:focus-visible` 双描边 outer/inner | XAML FocusStrokeColor* |
| 触屏按下反馈 | KIT 已在 `:root` 关掉 `-webkit-tap-highlight-color`；可点类必须自带 `:active`（`.fl-btn` / `.fl-nav-item` / `.fl-listitem` / `.fl-settings-row` / `.fl-combo-item` / `.fl-flyout-item`），新加的可点类要自己补一条 —— 否则安卓上先闪一块半透明方块、按下又没反馈 | 浏览器 UA 行为（非官方值）；KIT 规则 28 / 校验器 R51 |
| 成功/警告/错误 | `--fl-success/caution/critical`(+`-bg`) | XAML SystemFillColor* |
| 分隔线 | `--fl-divider-stroke` | XAML DividerStrokeColorDefault |
| 间距 | `--fl-space-*`（4 的倍数）；语义 8/12/16/48 见 KIT 规则 10 | content-basics |
| 断点 | ≤640 / 641–1007 / ≥1008 | breakpoints 页 |
