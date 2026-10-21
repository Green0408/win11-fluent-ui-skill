# 官方文档快照：设计基础与布局（抓取日期 2026-10-20，来源 learn.microsoft.com/en-us/windows/apps/design/）

## 响应式断点（/design/layout/screen-sizes-and-breakpoints-for-responsive-design）
| Size class | Breakpoint | 典型设备 | 典型窗口 |
|---|---|---|---|
| Small | ≤640px | TVs（观看距离远） | 480x854, 540x960 |
| Medium | 641–1007px | 7–12" 平板 | 960x540 |
| Large | ≥1008px | PC / 笔记本 / Surface Hub | 1024x640, 1366x768, 1920x1080 |

**4 的倍数规则**：UI 元素的尺寸、边距、位置必须是 4 epx 的倍数（文本除外，可任意）。缩放平台 100%–400%，4px 在所有平台取整。
设计单位为 effective pixels (epx/ep/px 通用)。按窗口可用空间设计，不按物理屏幕。

## 间距与 gutter（/design/basics/content-basics）
| 间距值 | 用途 |
|---|---|
| 8 epx | 按钮之间 |
| 8 epx | 按钮与 flyout 之间 |
| 8 epx | 控件与标题(header)之间 |
| 12 epx | 控件与标签(label)之间 |
| 12 epx | 内容区之间 |
| 16 epx | 表面与边缘文字之间 |
| 16 epx | 控件与 expander 按钮之间（控件右对齐时） |
| 48 epx | expander 内控件缩进 |

文字层级：Title/Subtitle/Body 配 12 epx 间距；紧凑空间标题用 Body Strong（不加间距）；命令按钮文字用 Caption。
列表：多行列表用 Body + Caption，图标 32 epx；区块标题用 Body Strong；网格项图标下 Caption 居中。

## 导航基础（/design/basics/navigation-basics）
原则：Consistency / Simplicity / Clarity。
- 扁平结构：页面无先后顺序、彼此独立、少于 8 页。
- 层级结构：有明确父子关系、超过 7 页。
- 超过两层导航提供 BreadcrumbBar；避免 pogo-sticking（先上后下）。
- **Left navigation**（NavigationView）：页在顶层、导航项多于 5 个、不频繁切换。
- **Top navigation**：需展示全部导航项、要更多内容空间、图标不足以表意。
- **Tabs**（TabView）：动态开关/重排标签页。
- **List/details**：频繁在子项间切换、需对条目做删除/排序等操作（邮箱、联系人、数据录入）。
- Back 规则：跨 peer group 计入历史；同 peer group 且有屏幕导航元素则视情况；瞬态 UI（对话框/键盘）不计入，back 先关闭它。

## 命令基础（/design/basics/commanding-basics）
- 命令元素：Buttons（即时动作）、Lists、选择控件（CheckBox/RadioButton/ToggleSwitch）、日期时间选择器、AutoSuggestBox。
- 命令表面优先级：**能直接操作内容就不加命令**（如拖拽排序）；核心高频命令放画布（靠近其作用对象）；其余放 CommandBar / MenuBar / 菜单与上下文菜单（CommandBarFlyout）。
- 反馈：优先自然融入 UI；CommandBar 内容区可显示状态；flyout 轻量提示；对话框有打断性，慎用。
- 需确认（不可撤销且后果重大）：覆盖/未保存关闭/永久删除/购买/提交表单。
- 提供 undo 即可（可撤销）：删除（非永久）/编辑/重命名。

## 控件与模式清单（/develop/ui/controls/，WinUI 独有控件加粗）
AutoSuggestBox, Button, **Animated Icon**, CalendarDatePicker, CalendarView, CheckBox, **ColorPicker**, ComboBox, **CommandBarFlyout**, CommandBar, **ContactCard**, ContentDialog, **DropDownButton**, **Expander**, Flyout, **InfoBar**, **MenuBar**, **MenuFlyout**, **Navigation View**, **Number box**, **PipsPager**, **Person picture**, **RatingControl**, **RichEditBox**, RichTextBlock, Progress, ScrollViewer, SemanticZoom, **SplitButton**, SwipeControl, **Teaching tip**, **TreeView**, **TabView**, **TwoPaneView** 等 45+。
