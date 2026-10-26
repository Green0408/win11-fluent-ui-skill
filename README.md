# Win11 / Fluent UI KIT

**这是一个 Agent Skill。** 装上之后，对 AI 说「照 KIT 做一个 XX 工具界面」，它就会用 Win11 / WinUI 3 / Fluent
的**官方**规格生成 HTML 界面——官方动效时长与缓动曲线（Direct Entrance / Point to Point / Strong Entrance）、
页面转场两轴（一级导航垂直、二级下钻水平，250ms）、Fluent 颜色 token（暗/亮双主题、Mica/Acrylic/Smoke 网页近似）、
Segoe UI Variable 字阶、官方圆角（控件 4px / 浮层 8px）与海拔阴影——而不是凭记忆瞎编数值。

还有一个少见的能力：**录屏反解**。发一段 Win11 应用的录屏进来，逐帧把动效参数对齐到官方数值——
把「看起来像」变成「和官方一致」。量测工具已拆成独立技能
**[video-motion-analyzer](https://github.com/Green0408/video-motion-analyzer-skill)**，
本仓库保留 Win11 侧的全部实测记录与结论落点（`VIDEO-ALIGN.md`）。

- **类型**：Agent Skill —— 根目录 `SKILL.md` 带 `name` / `description` 头信息，属于「一个目录即一个技能」的约定
- **触发**：说「用 Win11 / Fluent / WinUI 风格做个界面」「照 KIT 做界面」，或要把录屏反解的结论落成 Fluent 实现
- **安装**：克隆到 skills 目录，无依赖、无需构建（见下）
- **许可**：MIT，见 `LICENSE`；`raw/` 为微软官方源快照，保留原许可与出处

## 安装

```bash
git clone https://github.com/Green0408/win11-fluent-ui-skill.git ~/.workbuddy/skills/win11-fluent-ui
```

| 工具 | skills 目录 |
|---|---|
| WorkBuddy | `~/.workbuddy/skills/` |
| Claude Code | `~/.claude/skills/` |
| 其他支持 `SKILL.md` 的 Agent | 放进该工具约定的 skills 目录，保证 `SKILL.md` 在目录根 |

放进去后**新开一个会话**生效——`SKILL.md` 头部的 `description` 就是触发条件，不需要额外注册。

## 一句话使用

```text
照 KIT 做一个「<工具名>」工具界面。
用途：<一句话>。列表项=<字段>，详情=<字段>，面板设置=<项>，工具栏命令=<项>。
```

交付前跑 `python3 check_ui_conventions.py <生成的文件.html>`，要求 0 FAIL。

## 目录里都是什么

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 技能入口（frontmatter 定义 name / description） |
| `KIT.md` | 给 AI 的执行契约：骨架、动效接线、控件清单、交付自检 |
| `FLUENT-COMPOSE.md` | 动手前先定模块：单页 / 列表详情 / 网格详情 / 设置型 |
| `fluent2-tool-starter.html` | 可拆装的界面模板（复制它改业务） |
| `fluent2-tokens.css` / `fluent2-motion.css` / `fluent2-motion.js` | 三个必需资产：颜色 token、动效 CSS、动效 JS |
| `WINUI-MOTION-SPEC.md` | WinUI 动效规格汇总（时长 / 缓动 / 关键帧，逐条注明出处） |
| `official-values.md` / `.json` | 官方数值表（152 个颜色 token 等），程序可读 |
| `where-used.md` | 反查表：这个界面元素该用哪条动效 |
| `check_ui_conventions.py` | 规范检查器：把 KIT 规则可执行化，交付前必跑 |
| `VIDEO-ALIGN.md` | Win11 录屏实测记录与结论落点表（量测工具在 `video-motion-analyzer` 技能） |
| `extract_tokens.py` | 从 `raw/` 的 XAML 提取并换算 token（重生成数值表用） |
| `selftest.html` | 自检页，打开应全 PASS（可在线看） |
| `tests/` | 检查器与动效回归测试 |
| `raw/` | 微软官方源快照：microsoft-ui-xaml 主题资源（MIT，commit 见 `raw/commit.json`）与 learn.microsoft.com 文档快照 |

## 数值来源与许可

- `raw/xaml_*.xaml`：来自 [microsoft/microsoft-ui-xaml](https://github.com/microsoft/microsoft-ui-xaml)，
  MIT 许可，快照 commit `09cfc8ff3fbf`（记录在 `raw/commit.json`）
- `raw/doc_*.md`：learn.microsoft.com 页面快照，版权归 Microsoft，仅作为数值出处留档
- 本仓库其余内容 MIT，见 `LICENSE`

## 在线看效果

- 自检页：https://green0408.github.io/win11-fluent-ui-skill/selftest.html
- 界面模板：https://green0408.github.io/win11-fluent-ui-skill/fluent2-tool-starter.html

## 姊妹项目

同一套方法论的上一代 —— **[win8-metro-ui-skill](https://github.com/Green0408/win8-metro-ui-skill)**：
Windows 8 / Metro 官方 WinJS 动画参数（51 个 API、61 条命名动画 + 102 条过渡）、磁贴与列表控件几何。
两代规格的差异本身就有参考价值——Win8 的入场是「从下方滑入」，Win11 改成了更克制的 Direct Entrance。

在线看：https://green0408.github.io/win8-metro-ui-skill/win8-animation-demo.html

## 配套技能

**[video-motion-analyzer-skill](https://github.com/Green0408/video-motion-analyzer-skill)** —— 录屏动效反解工具，
从这里拆出去的。给它一段录屏，它输出转场类型/方向/时长/档位/缓动/错峰与「抖·跳·生硬」体检报告；
`--profile win11` 用的就是本 KIT 的 83 / 167 / 250 / 333 档。**先在那里出报告，再回来改实现。**
