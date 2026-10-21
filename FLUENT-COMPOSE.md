# FLUENT-COMPOSE.md —— 组合处方（按工具形态挑模块，不整套照搬）

**模板是可拆装的骨架。** 先回答 5 个问题再挑处方：

1. 有 ≥2 个页面/视图吗？（→ nav 或 topnav）
2. 是不是「选中看详情」？（→ list-detail）
3. 有**持续生效**的设置吗？（→ settings：`.fl-settings` 组+行，**不要**用卡片堆控件）
4. 有全局命令吗？（→ toolbar，高频的放画布、其余收进「⋯」flyout）
5. 有次要/上下文动作吗？（→ flyout / contextmenu）
6. 页面有层级吗？一级（侧栏切换）用 `nav` 垂直转场；从内容区入口进入的二级页用 `{kind:'drill'}` 水平转场 —— 两者不要混成一种。

## 四种处方

### A 单页工具
保留：`titlebar`(可选) + `toolbar` + 一块内容区。
删除：nav、infobar(无通知时)、list-detail 的详情列、settings、dialog(无可撤销操作时)。
动效：进场 `.fl-entrance` + `M.stagger`。

### B 列表 + 详情（条目管理型）
保留：`titlebar` + `nav` + `toolbar` + `list-detail` + `dialog`（删除确认，仅当不可撤销）+ `contextmenu`。
删除：grid、settings（或并入详情卡片）。
动效：列表 `M.stagger`；选择详情用 `.fl-fade`（83ms，轻量切换）；页面切换走 `M.transitionTo()` ——
点侧栏用默认（垂直 108px），点内容区里的入口进二级页用 `M.transitionTo(id,{kind:'drill'})`（水平 264px，250ms），返回用 `M.back('drill')`。

### C 网格 + 详情（图库型）
保留：`titlebar` + `nav` + `grid`。
删除：toolbar(或精简)、list-detail、settings。
动效：卡片 `M.stagger`；hover 用 `.fl-card.fl-hoverable` 内置过渡；点卡片进详情页用 `M.transitionTo(id,{kind:'drill'})`（水平钻入，返回自动反向）；要「原地放大」观感时可用 `.fl-strong-entrance`（弹性入场）。

### D 设置型
保留：`titlebar` + `settings`（`.fl-settings` 组+行：左标题副标题、右控件；或 `topnav` 分组）。
删除：nav、toolbar、list-detail、grid。
造型：设置行默认**不套卡片、行间默认没有分隔线**，组与组之间用 `.fl-settings-header` + 24px 间距分隔；行高 56，图标 20，hover 整行浅填充 + 圆角 4（不要给每行做胶囊）；需要分隔线时才写 `data-divided`（自动左缩进对齐文字）。
动效：分组 `.fl-entrance`；控件均带官方微动效：开关旋钮 12→hover 14→pressed 17、开态位移 20px、83ms FastOutSlowIn；滑块 hover 1.167 / pressed 0.833、250ms，左段 accent 已填充段随值伸缩（`M.slider.auto()` 自动接，档位色用不透明混色，悬停不会透出底层）；勾选框为 SVG 勾号描画 167ms（含半选/禁用）；下拉用自绘 `.fl-combo`（83ms 开合 + 上下翻转）；有实时数值（进度/秒表）时用 `.fl-dial` + `.fl-tick` / `.fl-continuous`。

## 官方结构规则依据

- 导航：左导航（NavigationView）用于顶层页、>5 项、不频繁切换；顶部导航用于要全展示/省空间；>2 层加面包屑；扁平 ≤8 页 / 层级 >7 页（navigation-basics）。
- 命令：能直接操作内容就不加命令；核心高频命令放画布靠近作用对象；其余 CommandBar；菜单/上下文菜单收纳次要命令（commanding-basics）。
- 对话框只用于**不可撤销且后果重大**的操作确认（永久删除、覆盖、提交、购买）；可撤销的给 toast/undo 即可（commanding-basics）。
- 断点：≤640px 收起 nav 为汉堡/顶部；≥1008px 完整布局（breakpoints）。
