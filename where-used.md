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
| 下拉 | `.fl-select` | 同上 |
| 开关 | `.fl-switch`（轨道 40×20、旋钮 12、开态位移 20px、hover 14 / pressed 17） | XAML ToggleSwitch（KnobTranslateTransform X=20、SplineDoubleKeyFrame 14/17） |
| 滑块 | `.fl-slider`（轨道 4、内圆 12、圆角 10；hover 1.167 / pressed 0.833，250ms） | XAML Slider（SliderTrackThemeHeight / SliderInnerThumbWidth / SliderThumbCornerRadius） |
| 复选/单选 | `.fl-check` / `.fl-radio`（20×20、圆角 4） | XAML CheckBox + geometry 4px |
| 列表项 | `.fl-listitem`（min-height 40、圆角 4、禁用透明 0.3、选中 accent 胶囊） | XAML ListViewItemMinHeight/CornerRadius/DisabledThemeOpacity |
| 卡片 | `.fl-card`（圆角 8、elevation 8、`--fl-card-bg/stroke`） | XAML Card* + layering Card=8 |
| 左导航 | `.fl-nav` + `.fl-nav-item`（选中=subtle 填充+3px accent 胶囊） | navigation-basics + NavigationView XAML |
| 通知条 | `.fl-infobar[data-severity=success/caution/critical]`（`--fl-success/caution/critical`） | XAML SystemFillColor* |
| flyout / 右键菜单 | `.fl-flyout.fl-overlay`（Acrylic 近似 + 圆角 8 + 阴影 e32） | materials + geometry + layering Flyout=32 |
| 对话框 | `.fl-dialog.fl-overlay` + `M.dialog`（Smoke 遮罩、圆角 8、阴影 e128、padding 24、max-width 548） | XAML ContentDialogPadding/MaxWidth/MinHeight + materials Smoke |
| tooltip | 圆角 4（小尺寸例外）、阴影 e16 | geometry ToolTip 例外 + layering Tooltip=16 |
| 元素入场 | `.fl-entrance` + `M.stagger`（167ms standard，位移 8px；83ms 步进上限 333，延迟走 `--fl-stagger-delay`） | motion Direct Entrance + Fade 档；位移量实测自录屏 |
| 页面切换（一级导航） | `M.transitionTo(id)`（默认 `kind:'nav'`，垂直 72px + 交叉淡化，283ms） | 实测派生（见 KIT 规则 15） |
| 页面切换（二级下钻） | `M.transitionTo(id,{kind:'drill'})`（水平 176px，返回用 `M.back('drill')` 方向取反） | 实测派生（见 KIT 规则 15） |
| 连续型动效（秒针/进度环） | `.fl-dial` + `.fl-dial-hand.fl-tick`（每秒 6°）/ `.fl-continuous`（linear 倍乘） | 录屏《时钟》秒针；见 KIT 规则 16 |
| 弹性大入场 | `.fl-strong-entrance`（三关键帧 167+167+333） | motion Strong Entrance |
| 元素离场 | `.fl-exit`（必须配 fade out）；浮层出场用 `.fl-overlay:not(.fl-open)` 的 soft 曲线（Gentle Exit 语义），不再有单独的出场类 | motion（硬性要求） |
| accent 按钮状态 | `.fl-btn-accent:hover/:active` 用 `--fl-accent-fill-hover/pressed`（Default @0.9/@0.8） | XAML AccentFillColorSecondary/TertiaryBrush |
| 位移过渡（拖拽/排序） | `.fl-movable`（point 曲线） | motion Point to Point |
| 纯透明度切换 | `.fl-fade`（linear 83ms） | motion Fade |
| 焦点框 | `:focus-visible` 双描边 outer/inner | XAML FocusStrokeColor* |
| 成功/警告/错误 | `--fl-success/caution/critical`(+`-bg`) | XAML SystemFillColor* |
| 分隔线 | `--fl-divider-stroke` | XAML DividerStrokeColorDefault |
| 间距 | `--fl-space-*`（4 的倍数）；语义 8/12/16/48 见 KIT 规则 10 | content-basics |
| 断点 | ≤640 / 641–1007 / ≥1008 | breakpoints 页 |
