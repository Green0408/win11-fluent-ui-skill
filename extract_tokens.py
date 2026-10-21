#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_tokens.py —— 从 raw/ 官方源提取数值 → official-values.json / official-values.md / fluent2-tokens.css

数据源（均为官方，缓存于 raw/，MIT 许可）：
- GitHub microsoft-ui-xaml controls/dev/CommonStyles/*.xaml（颜色/几何/字号，commit 见 official-values.json meta）
- Microsoft Learn 文档页快照 raw/doc_*.md（动效/字阶/间距/海拔/断点，出处见 DOC_VALUE 每条 source）

可复现：改 raw/ 后重跑  python extract_tokens.py  即可重建全部三个产物。
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

THEME_MAP = {"Default": "dark", "Light": "light"}  # HighContrast 不用于网页
# XAML 主题无关资源与控制文件（数值以 Common 为准，控件文件只补充不覆盖）
PARSE_FILES = [
    "xaml_Common_themeresources_any.xaml",
    "xaml_Common_themeresources.xaml",
    "xaml_CornerRadius_themeresources.xaml",
    "xaml_TextBlock_themeresources.xaml",
    "xaml_TextControlsCommon_themeresources.xaml",
    "xaml_Button_themeresources.xaml",
    "xaml_TextBox_themeresources.xaml",
    "xaml_PasswordBox_themeresources.xaml",
    "xaml_ListViewItem_themeresources.xaml",
    "xaml_GridViewItem_themeresources.xaml",
    "xaml_ContentDialog_themeresources.xaml",
    "xaml_ToggleSwitch_themeresources.xaml",
    "xaml_CheckBox_themeresources.xaml",
    "xaml_ComboBox_themeresources.xaml",
    "xaml_NavigationView_themeresources.xaml",
    "xaml_InfoBar_themeresources.xaml",
    "xaml_ToolTip_themeresources.xaml",
    "xaml_FlyoutPresenter_themeresources.xaml",
    "xaml_MenuFlyout_themeresources.xaml",
    "xaml_CommandBar_themeresources.xaml",
    "xaml_HyperlinkButton_themeresources.xaml",
    "xaml_RadioButton_themeresources.xaml",
    "xaml_NumberBox_themeresources.xaml",
    "xaml_Slider_themeresources.xaml",
    "xaml_ToggleButton_themeresources.xaml",
    "xaml_RepeatButton_themeresources.xaml",
]

ENTRY_PATTERNS = [
    ("Color", re.compile(r'<Color\s+x:Key="([^"]+)">([^<]+)</Color>')),
    ("Double", re.compile(r'<x:Double\s+x:Key="([^"]+)">([^<]+)</x:Double>')),
    ("Thickness", re.compile(r'<Thickness\s+x:Key="([^"]+)">([^<]+)</Thickness>')),
    ("CornerRadius", re.compile(r'<CornerRadius\s+x:Key="([^"]+)">([^<]+)</CornerRadius>')),
    ("FontFamily", re.compile(r'<FontFamily\s+x:Key="([^"]+)">([^<]+)</FontFamily>')),
]


def parse_xaml_file(path: Path):
    """返回 {"dark": {...}, "light": {...}, "common": {...}}，值为 {key: {"value": v, "type": t}}"""
    out = {"dark": {}, "light": {}, "common": {}}
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    m = re.search(
        r"<ResourceDictionary\.ThemeDictionaries>(.*?)</ResourceDictionary\.ThemeDictionaries>",
        text, re.S)
    blocks = []
    if m:
        blocks.append((m.group(1), True))
        text = text[:m.start()] + text[m.end():]
    blocks.append((text, False))
    for body, in_theme in blocks:
        if in_theme:
            for dm in re.finditer(r'<ResourceDictionary\s+x:Key="(\w+)">(.*?)</ResourceDictionary>', body, re.S):
                theme = THEME_MAP.get(dm.group(1))
                if not theme:
                    continue
                for typ, pat in ENTRY_PATTERNS:
                    for km in pat.finditer(dm.group(2)):
                        out[theme][km.group(1)] = {"value": km.group(2).strip(), "type": typ}
        else:
            for typ, pat in ENTRY_PATTERNS:
                for km in pat.finditer(body):
                    out["common"][km.group(1)] = {"value": km.group(2).strip(), "type": typ}
    return out


def merge_resources():
    """合并全部文件：Common 优先，其余文件只补充不覆盖。"""
    merged = {"dark": {}, "light": {}, "common": {}}
    src = {"dark": {}, "light": {}, "common": {}}
    for name in PARSE_FILES:
        p = RAW / name
        if not p.exists():
            print(f"[warn] 缺少 {name}，跳过", file=sys.stderr)
            continue
        data = parse_xaml_file(p)
        for theme in ("dark", "light", "common"):
            for k, v in data[theme].items():
                if k not in merged[theme]:
                    merged[theme][k] = v
                    src[theme][k] = name
    return merged, src


# ---------------------------------------------------------------------------
# tokens.css 的颜色映射：css 变量名 ← XAML key（缺 key 自动跳过并在控制台提示）
# ---------------------------------------------------------------------------
COLOR_MAP = [
    ("--fl-text-primary", "TextFillColorPrimary"),
    ("--fl-text-secondary", "TextFillColorSecondary"),
    ("--fl-text-tertiary", "TextFillColorTertiary"),
    ("--fl-text-disabled", "TextFillColorDisabled"),
    ("--fl-text-on-accent-primary", "TextOnAccentFillColorPrimary"),
    ("--fl-text-on-accent-secondary", "TextOnAccentFillColorSecondary"),
    ("--fl-text-on-accent-disabled", "TextOnAccentFillColorDisabled"),
    ("--fl-control-fill-default", "ControlFillColorDefault"),
    ("--fl-control-fill-secondary", "ControlFillColorSecondary"),
    ("--fl-control-fill-tertiary", "ControlFillColorTertiary"),
    ("--fl-control-fill-disabled", "ControlFillColorDisabled"),
    ("--fl-control-fill-input-active", "ControlFillColorInputActive"),
    ("--fl-control-strong-fill", "ControlStrongFillColorDefault"),
    ("--fl-control-strong-fill-disabled", "ControlStrongFillColorDisabled"),
    ("--fl-control-solid-fill", "ControlSolidFillColorDefault"),
    ("--fl-control-stroke", "ControlStrokeColorDefault"),
    ("--fl-control-stroke-secondary", "ControlStrokeColorSecondary"),
    ("--fl-control-stroke-on-accent", "ControlStrokeColorOnAccentDefault"),
    ("--fl-control-stroke-on-accent-secondary", "ControlStrokeColorOnAccentSecondary"),
    ("--fl-subtle-fill-hover", "SubtleFillColorSecondary"),
    ("--fl-subtle-fill-pressed", "SubtleFillColorTertiary"),
    ("--fl-subtle-fill-disabled", "SubtleFillColorDisabled"),
    ("--fl-card-bg", "CardBackgroundFillColorDefault"),
    ("--fl-card-bg-secondary", "CardBackgroundFillColorSecondary"),
    ("--fl-card-stroke", "CardStrokeColorDefault"),
    ("--fl-layer-fill", "LayerFillColorDefault"),
    ("--fl-smoke", "SmokeFillColorDefault"),
    ("--fl-solid-bg-base", "SolidBackgroundFillColorBase"),
    ("--fl-solid-bg-base-alt", "SolidBackgroundFillColorBaseAlt"),
    ("--fl-solid-bg-secondary", "SolidBackgroundFillColorSecondary"),
    ("--fl-solid-bg-tertiary", "SolidBackgroundFillColorTertiary"),
    ("--fl-solid-bg-quarternary", "SolidBackgroundFillColorQuarternary"),
    ("--fl-divider-stroke", "DividerStrokeColorDefault"),
    ("--fl-focus-stroke-outer", "FocusStrokeColorOuter"),
    ("--fl-focus-stroke-inner", "FocusStrokeColorInner"),
    ("--fl-success", "SystemFillColorSuccess"),
    ("--fl-caution", "SystemFillColorCaution"),
    ("--fl-critical", "SystemFillColorCritical"),
    ("--fl-success-bg", "SystemFillColorSuccessBackground"),
    ("--fl-caution-bg", "SystemFillColorCautionBackground"),
    ("--fl-critical-bg", "SystemFillColorCriticalBackground"),
    ("--fl-accent-fill-disabled", "AccentFillColorDisabled"),
]

# accent 为系统色（用户可选），XAML 引用 SystemAccentColor[Light1-3/Dark1-3]；
# 网页默认取 Windows 11 默认系统强调色 #0078D4，用户可整体替换。
#
# **主题映射以 XAML 为准（raw/xaml_Common_themeresources_any.xaml）**：
#   暗主题（dark 字典，约 L125）AccentFillColorDefaultBrush = SystemAccentColor**Light2**
#   亮主题（light 字典，约 L329）AccentFillColorDefaultBrush = SystemAccentColor**Dark1**
# 即暗色用**浅**蓝、亮色用**深**蓝。这与 TextOnAccentFillColorPrimary 正好互证：
#   暗主题=#000000（浅底配黑字）、亮主题=#FFFFFF（深底配白字）。
# 早期版本把两档写反（暗=Dark1 深蓝、亮=Light2 的深色近似），导致暗色主题的强调色发闷。
ACCENT = {
    "value": "#0078D4",
    "dark_fill": "#60CDFF",    # SystemAccentColorLight2 → 暗主题 AccentFillColorDefault
    "light_fill": "#005FB8",   # SystemAccentColorDark1  → 亮主题 AccentFillColorDefault
    "secondary_opacity": 0.9,  # AccentFillColorSecondaryBrush = Default @Opacity 0.9（hover）
    "tertiary_opacity": 0.8,   # AccentFillColorTertiaryBrush = Default @Opacity 0.8（pressed）
    "note": ("XAML 引用 SystemAccentColor（系统用户色）；此处取 Win11 默认强调色 #0078D4 的调色板："
             "暗主题填充用 Light2 档 #60CDFF（配黑字）、亮主题填充用 Dark1 档 #005FB8（配白字），可整体替换"),
}

# 官方几何（XAML 提取，主题无关）→ css 变量
GEOMETRY_MAP = [
    ("--fl-radius-control", "ControlCornerRadius"),
    ("--fl-radius-overlay", "OverlayCornerRadius"),
]

# 官方动效（doc_signature-experiences.md，learn.microsoft.com/.../signature-experiences/motion）
MOTION = {
    "durations": {
        "fast": {"ms": 83, "use": "Fade（In+Out，仅 Opacity）", "source": "learn.../motion Fade"},
        "normal": {"ms": 167, "use": "Direct Entrance/Exit、Point to Point、Gentle Exit、Strong Entrance 关键帧 1/2", "source": "learn.../motion"},
        "gentle": {"ms": 250, "use": "Direct Entrance、Point to Point（中档）", "source": "learn.../motion"},
        "slow": {"ms": 333, "use": "Direct Entrance、Point to Point（大位移）、Strong Entrance 关键帧 3", "source": "learn.../motion"},
    },
    # 控件级时长档：XAML *._themeresources 里以 ControlFaster/Fast/NormalAnimationDuration 命名，
    # 与上面「动效四档」是两套命名（83/167/250 数值相同但语义不同），故单列，避免引用时混淆。
    "control_durations": {
        "faster": {"ms": 83, "use": "控件状态色变、开关旋钮尺寸/位移（ControlFasterAnimationDuration）",
                   "source": "raw/xaml_ToggleSwitch_themeresources.xaml 等：ControlFasterAnimationDuration=00:00:00.083"},
        "fast": {"ms": 167, "use": "控件中等反馈（ControlFastAnimationDuration）",
                 "source": "raw/*_themeresources.xaml：ControlFastAnimationDuration=00:00:00.167"},
        "normal": {"ms": 250, "use": "控件较大位移/尺寸变化、勾号描绘（ControlNormalAnimationDuration）",
                   "source": "raw/xaml_Slider_themeresources.xaml、xaml_RadioButton_themeresources.xaml：ControlNormalAnimationDuration=00:00:00.250"},
    },
    "easings": {
        "standard": {"css": "cubic-bezier(0,0,0,1)", "use": "Direct Entrance / Direct Exit（Fast-In / Fast-Out）"},
        "point": {"css": "cubic-bezier(0.55,0.55,0,1)", "use": "Point to Point（位移类）"},
        "soft": {"css": "cubic-bezier(1,0,1,1)", "use": "Gentle Exit（Soft-Out）"},
        "strong-1": {"css": "cubic-bezier(0.85,0,0,1)", "use": "Strong Entrance 关键帧 1（167ms）与 3（333ms）"},
        "strong-2": {"css": "cubic-bezier(0.85,0,0.75,1)", "use": "Strong Entrance 关键帧 2（167ms）"},
        "linear": {"css": "linear", "use": "Fade 83ms"},
    },
    "rules": [
        "Direct Exit 必须与 fade out 组合（官方硬性要求）",
        "Strong Entrance 为 Elastic In 三关键帧：167ms(0.85,0,0,1) → 167ms(0.85,0,0.75,1) → 333ms(0.85,0,0,1)",
        "同一入口的表面以相同方式开合（Consistent）",
        "优先用现成控件转场（Resourceful），网页对应=直接用本 KIT 的 motion 类",
        "页面转场默认参数见 learn.../page-transitions（Entrance 250-300ms 档佐证）",
    ],
    "source": "https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/motion",
}

# 实测派生动效（**非官方档位**）：Win11 官方应用 60fps 录屏逐帧反解，方法与原始数字见 VIDEO-ALIGN.md §9
# 与 MOTION 严格分离：official-values.md 的「官方动效表」不引用本字典，避免给实测值伪造官方出处
DERIVED_MOTION = {
    "durations": {
        "page": {"value": "283ms", "use": "页面转场（二级下钻水平 / 一级导航垂直共用同一节奏）",
                 "source": "录屏《设置》10-21：下钻逐帧位移 2,4,6,8,12,16,22,34,70|66,38,24,16,10,8,6，17 帧 ≈283ms"},
        "tick": {"value": "1s", "use": "连续型：秒针跳秒周期（每秒一次 83ms 小变化）",
                 "source": "录屏《时钟》10-21：每秒出现一次 83ms、变化面积 0.6% 的位移"},
        "sweep": {"value": "60s", "use": "连续型：秒针整圈（分针/时针用 calc 倍乘）",
                  "source": "连续型动效的物理周期，非测量值"},
    },
    "easings": {
        "page": {"css": "cubic-bezier(0.1,0.9,0.2,1)",
                 "use": "页面转场·进场：强减速（起手就快、一路收尾；前 3 帧走完约 60%）",
                 "source": "拟合自录屏《设置》10-21 下钻逐帧进度 0.36/0.57/0.70/0.78/0.84/0.89/0.92…"},
        "page-out": {"css": "cubic-bezier(0.7,0,1,0.5)",
                     "use": "页面转场·退场：原地淡出后加速离开（速度峰在退场末尾，与进场的快起手衔接）",
                     "source": "录屏旧页逐帧增量 25,8,12,16（递增）→ ease-in；"
                               "试过近线性 (0.3,0.3,0.6,1)：退场末尾减速、紧接着进场猛起，速度突变反而更「顿」"},
        "steps-60": {"css": "steps(60, end)", "use": "跳秒：一秒 60 步",
                     "source": "录屏《时钟》秒针每秒一跳"},
    },
    "shifts": {
        "drill": {"px": 264, "use": "二级下钻单层行程（水平）",
                  "source": "录屏实测 176（350 视频 px @2x）→ 观感校准 ×1.5 = 264，4 的倍数；"
                            "录屏里内容区较窄，176 在宽内容区上显得位移太短"},
        "nav": {"px": 108, "use": "一级导航单层行程（垂直）",
                "source": "录屏实测 72（127–144 视频 px @2x 的上界）→ 观感校准 ×1.5 = 108，4 的倍数"},
    },
    "provenance": "measured-2026-10-21",
}

# Windows 11 Type ramp（learn.../typography；字号与 XAML TextBlock_themeresources 交叉一致）
TYPE_RAMP = [
    {"name": "Caption", "css": "caption", "size": 12, "line": 16, "weight": 400},
    {"name": "Body", "css": "body", "size": 14, "line": 20, "weight": 400},
    {"name": "Body Strong", "css": "body-strong", "size": 14, "line": 20, "weight": 600},
    {"name": "Body Large", "css": "body-large", "size": 18, "line": 24, "weight": 400},
    {"name": "Body Large Strong", "css": "body-large-strong", "size": 18, "line": 24, "weight": 600},
    {"name": "Subtitle", "css": "subtitle", "size": 20, "line": 28, "weight": 600},
    {"name": "Title", "css": "title", "size": 28, "line": 36, "weight": 600},
    {"name": "Title Large", "css": "title-large", "size": 40, "line": 52, "weight": 600},
    {"name": "Display", "css": "display", "size": 68, "line": 92, "weight": 600},
]
FONT_STACK = ('"Segoe UI Variable Display","Segoe UI Variable","Segoe UI",'
              'system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif')

# 间距（learn.../design/basics/content-basics，epx；4 的倍数规则见断点页）
SPACING = [
    {"px": 8, "use": "按钮之间"},
    {"px": 8, "use": "按钮与 flyout 之间"},
    {"px": 8, "use": "控件与标题(header)之间"},
    {"px": 12, "use": "控件与标签(label)之间"},
    {"px": 12, "use": "内容区之间"},
    {"px": 16, "use": "表面与边缘文字之间"},
    {"px": 16, "use": "控件与 expander 按钮之间（右对齐）"},
    {"px": 48, "use": "expander 内控件缩进"},
]
SPACING_SOURCE = "https://learn.microsoft.com/en-us/windows/apps/design/basics/content-basics"

# 海拔（learn.../signature-experiences/layering；官方只给 elevation 值，CSS 阴影为换算近似）
ELEVATION = [
    {"name": "Window/Dialog", "value": 128},
    {"name": "Flyout", "value": 32},
    {"name": "Tooltip", "value": 16},
    {"name": "Card", "value": 8},
    {"name": "Control", "value": 2},
    {"name": "Layer", "value": 1},
]
ELEVATION_STATES = {"rest": 2, "hover": 2, "pressed": 1}
STROKE_WIDTH = 1
ELEVATION_SOURCE = "https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/layering"
# elevation → CSS box-shadow 换算（KIT 自定，非官方 CSS 定义）：blur≈elevation*0.5px，两层投影，透明度随海拔增大
SHADOW_MAP = {
    "1": "0 0 1px rgba(0,0,0,.10)",
    "2": "0 1px 1px rgba(0,0,0,.07)",
    "8": "0 2px 4px rgba(0,0,0,.08), 0 0 1px rgba(0,0,0,.08)",
    "16": "0 4px 8px rgba(0,0,0,.10), 0 0 1px rgba(0,0,0,.08)",
    "32": "0 8px 16px rgba(0,0,0,.12), 0 0 1px rgba(0,0,0,.08)",
    "128": "0 32px 64px rgba(0,0,0,.19), 0 2px 21px rgba(0,0,0,.15)",
}

BREAKPOINTS = {"small_max": 640, "medium_max": 1007, "large_min": 1008,
               "source": "https://learn.microsoft.com/en-us/windows/apps/design/layout/screen-sizes-and-breakpoints-for-responsive-design"}
RULES_4PX = "所有 UI 尺寸/边距/位置为 4 epx 的倍数（文本除外）——learn.../breakpoints#multiples-of-four"

# 官方控件几何（XAML 提取 + 佐证源）
CONTROL_GEOMETRY = [
    {"key": "ButtonPadding", "value": None, "type": "Thickness"},   # 运行时从解析结果取
    {"key": "TextControlThemePadding", "value": None, "type": "Thickness"},
    {"key": "ContentDialogPadding", "value": None, "type": "Thickness"},
    {"key": "ContentDialogMaxWidth", "value": None, "type": "Double"},
    {"key": "ContentDialogMinHeight", "value": None, "type": "Double"},
    {"key": "ListViewItemMinHeight", "value": None, "type": "Double"},
    {"key": "ListViewItemMinWidth", "value": None, "type": "Double"},
    {"key": "ListViewItemCornerRadius", "value": None, "type": "CornerRadius"},
    {"key": "ListViewItemSelectionIndicatorCornerRadius", "value": None, "type": "CornerRadius"},
    {"key": "ListViewItemCheckBoxCornerRadius", "value": None, "type": "CornerRadius"},
    {"key": "ListViewItemContentOffsetX", "value": None, "type": "Double"},
    {"key": "ListViewItemDisabledThemeOpacity", "value": None, "type": "Double"},
    # CheckBox / RadioButton（raw/xaml_CheckBox_themeresources.xaml、xaml_RadioButton_themeresources.xaml）
    {"key": "CheckBoxSize", "value": None, "type": "Double"},
    {"key": "CheckBoxGlyphSize", "value": None, "type": "Double"},
    {"key": "CheckBoxBorderThickness", "value": None, "type": "Double"},
    {"key": "CheckBoxHeight", "value": None, "type": "Double"},
    {"key": "CheckBoxMinWidth", "value": None, "type": "Double"},
    {"key": "RadioButtonCheckGlyphSize", "value": None, "type": "Double"},
    # NavigationView（raw/xaml_NavigationView_themeresources.xaml）
    {"key": "NavigationViewItemOnLeftMinHeight", "value": None, "type": "Double"},
    {"key": "NavigationViewSelectionIndicatorWidth", "value": None, "type": "Double"},
    {"key": "NavigationViewSelectionIndicatorHeight", "value": None, "type": "Double"},
    {"key": "NavigationViewSelectionIndicatorRadius", "value": None, "type": "Double"},
    # ComboBox（raw/xaml_ComboBox_themeresources.xaml；注意 XAML 原键名拼写 Higlight 少一个 h）
    {"key": "ComboBoxThemeMinWidth", "value": None, "type": "Double"},
    {"key": "ComboBoxPopupThemeMinWidth", "value": None, "type": "Double"},
    {"key": "ComboBoxPopupBorderThemeThickness", "value": None, "type": "Thickness"},
    {"key": "ComboBoxHiglightBorderCornerRadius", "value": None, "type": "CornerRadius"},
    {"key": "ComboBoxItemCornerRadius", "value": None, "type": "CornerRadius"},
    {"key": "ComboBoxItemPillCornerRadius", "value": None, "type": "CornerRadius"},
]
CONTROL_GEOMETRY_EXTRA = [
    {"key": "TextControlThemeMinHeight", "value": "32", "type": "Double",
     "source": "WinUI DefaultTextBoxStyle MinHeight=TextControlThemeMinHeight，默认 32（stackover­flow.com/questions/78760996 引 generic.xaml；与 WinUI 3 Gallery 视觉一致）"},
    {"key": "ControlHeight", "value": "32", "type": "Double",
     "source": "Win11 常驻控件标准高度 32px（Button/TextBox/ComboBox/Slider 实际渲染高度；官方文档未单列数值，按 XAML 默认渲染确认）"},
    {"key": "SliderTrackThemeHeight", "value": "4", "type": "Double",
     "source": "raw/xaml_Slider_themeresources.xaml：SliderTrackThemeHeight=4（轨道粗）"},
    {"key": "SliderInnerThumbWidth", "value": "12", "type": "Double",
     "source": "raw/xaml_Slider_themeresources.xaml：SliderInnerThumbWidth=12（内圆直径，外环 20 由描边近似）"},
    {"key": "SliderThumbCornerRadius", "value": "10", "type": "CornerRadius",
     "source": "raw/xaml_Slider_themeresources.xaml：SliderThumbCornerRadius=10（圆形 thumb）"},
    {"key": "ComboBoxDropDownGlyphSize", "value": "12", "type": "Double",
     "source": "raw/xaml_ComboBox_themeresources.xaml：DropDownGlyph Width/Height=12、Margin=0,0,14,0（下拉箭头字形与右内边距）"},
    {"key": "ComboBoxDropDownGlyphGap", "value": "14", "type": "Double",
     "source": "raw/xaml_ComboBox_themeresources.xaml：DropDownGlyph Margin 右值 14（箭头距控件右缘）"},
    {"key": "ListViewItemMaxDropDownHeight", "value": "504", "type": "Double",
     "source": "raw/xaml_ComboBox_themeresources.xaml：ComboBox MaxDropDownHeight=504（下拉面板最大高，按 15 项一屏）"},
    {"key": "CheckGlyphStrokeThickness", "value": "2.5", "type": "Double",
     "source": "raw/xaml_ListViewItem_themeresources.xaml：CheckGlyph Path StrokeThickness=2.5（18.5x17 视箱，Stretch=Fill）"},
    {"key": "ListItemHeightTwoLine", "value": "64", "type": "Double",
     "source": "KIT 自定（官方只给 ListViewItemMinHeight=40）：图标+主副两行文本的行高，4 的倍数，与 Win11 设置页实测观感一致"},
    {"key": "IconSize", "value": "20", "type": "Double",
     "source": "Fluent 图标族 16/20/24 三档的中档（列表项图标）；4 的倍数，与 raw/xaml_ListViewItem 里 MultiSelectCheckBox 的 20px 槽位一致"},
    {"key": "SettingsRowHeight", "value": "56", "type": "Double",
     "source": "实测派生（设置类应用录屏，2026-10-21）：图标 20 + 主 14/20 + 副 12/16 两行 + 上下各 2 padding ≈ 56；"
               "行距实测 39 屏幕 px（渲染宽 1100 / 录制宽 2400，约合 56 CSS px），4 的倍数"},
]


def css_color(v: str) -> str:
    """XAML 颜色 #AARRGGBB（alpha 在前）→ CSS #RRGGBBAA（alpha 在后）；6 位/其他原样返回。"""
    v = v.strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{8}", v):
        return "#" + v[3:] + v[1:3]
    return v


def alpha(hex_color: str, opacity: float) -> str:
    """给 CSS 颜色加 alpha 后缀：#RRGGBB + opacity(0-1) → #RRGGBBAA。

    依据 XAML brush 的 Opacity 语义：AccentFillColorSecondaryBrush = Default @Opacity 0.9、
    TertiaryBrush = Default @Opacity 0.8（raw/xaml_Common_themeresources_any.xaml 主题字典）。
    网页用同色加 alpha 近似该 brush，不另取 hex。
    """
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    return "#" + h.upper() + format(round(opacity * 255), "02X")


def build():
    merged, src = merge_resources()
    common = merged["common"]

    def getval(key):
        for theme in ("common", "dark", "light"):
            if key in merged[theme]:
                return merged[theme][key]["value"], merged[theme][key]["type"], src[theme][key]
        return None, None, None

    # ---- 收集官方几何 ----
    geometry = {}
    for css_name, xaml_key in GEOMETRY_MAP:
        v, t, s = getval(xaml_key)
        if v is not None:
            if t == "CornerRadius":  # "4,4,4,4" → 取首分量
                v = v.split(",")[0].strip()
            geometry[css_name] = {"value": v, "xaml_key": xaml_key, "source": f"raw/{s}"}
    for item in CONTROL_GEOMETRY:
        v, t, s = getval(item["key"])
        if v is not None:
            geometry[f"xaml:{item['key']}"] = {"value": v, "type": t, "source": f"raw/{s}"}
    for item in CONTROL_GEOMETRY_EXTRA:
        geometry[f"extra:{item['key']}"] = {"value": item["value"], "type": item["type"], "source": item["source"]}

    # ---- 颜色（全量库存 + 精选映射） ----
    colors_all = {}
    for key in merged["dark"]:
        colors_all[key] = {
            "dark": merged["dark"][key]["value"],
            "light": merged["light"].get(key, {}).get("value"),
            "type": merged["dark"][key]["type"],
            "source": f"raw/{src['dark'][key]}",
        }
    selected_colors = {}
    missing = []
    for css_name, xaml_key in COLOR_MAP:
        if key_data := colors_all.get(xaml_key):
            selected_colors[css_name] = {"xaml_key": xaml_key, **key_data}
        else:
            missing.append((css_name, xaml_key))

    # ---- 写 official-values.json ----
    payload = {
        "_meta": {
            "generated_by": "extract_tokens.py",
            "xaml_source": "https://github.com/microsoft/microsoft-ui-xaml/tree/main/controls/dev/CommonStyles",
            "xaml_commit": "09cfc8ff3fbf (main, 2026-10-20)",
            "fetch_date": "2026-10-20",
            "license": "MIT (microsoft-ui-xaml)",
            "note": "颜色/几何取自官方 XAML 主题资源；动效/字阶/间距/海拔取自 Microsoft Learn 文档（出处逐条标注）",
        },
        "accent": ACCENT,
        "colors_selected": selected_colors,
        "colors_count": len(colors_all),
        "geometry": geometry,
        "motion": MOTION,
        "motion_derived": DERIVED_MOTION,
        "type_ramp": TYPE_RAMP,
        "font_stack": FONT_STACK,
        "spacing": SPACING,
        "spacing_source": SPACING_SOURCE,
        "elevation": ELEVATION,
        "elevation_states": ELEVATION_STATES,
        "elevation_stroke_width": STROKE_WIDTH,
        "elevation_source": ELEVATION_SOURCE,
        "shadow_map_approx": SHADOW_MAP,
        "breakpoints": BREAKPOINTS,
        "rule_4px": RULES_4PX,
    }
    (HERE / "official-values.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- 写 fluent2-tokens.css ----
    css = []
    css.append("/* fluent2-tokens.css —— 由 extract_tokens.py 从官方源生成，勿手改；"
               "重新生成：python extract_tokens.py")
    css.append("   颜色出处：microsoft-ui-xaml Common_themeresources_any.xaml (MIT)；"
               "动效/字阶/间距/海拔出处：learn.microsoft.com，详见 official-values.md */")
    css.append("")
    css.append(':root {')
    css.append(f'  --fl-accent: {ACCENT["value"]}; /* {ACCENT["note"]} */')
    for dur, d in MOTION["durations"].items():
        css.append(f'  --fl-dur-{dur}: {d["ms"]}ms;')
    for name, e in MOTION["easings"].items():
        css.append(f'  --fl-ease-{name}: {e["css"]};')
    css.append('')
    css.append('  /* 控件级时长档：XAML 用 ControlFaster/Fast/NormalAnimationDuration 命名，'
               '与上面动效四档数值相同但语义不同，勿混用 */')
    for name, d in MOTION["control_durations"].items():
        css.append(f'  --fl-dur-control-{name}: {d["ms"]}ms; /* {d["use"]} */')
    css.append('')
    css.append('  /* 实测派生（非官方档位）：Win11 官方应用 60fps 录屏反解，方法与原始数字见 VIDEO-ALIGN.md §9 */')
    css.append(f'  --fl-dur-page: {DERIVED_MOTION["durations"]["page"]["value"]};'
               f'  /* {DERIVED_MOTION["durations"]["page"]["use"]} */')
    css.append(f'  --fl-dur-tick: {DERIVED_MOTION["durations"]["tick"]["value"]};'
               f'  --fl-dur-sweep: {DERIVED_MOTION["durations"]["sweep"]["value"]};')
    css.append(f'  --fl-ease-page: {DERIVED_MOTION["easings"]["page"]["css"]};'
               f'  --fl-ease-page-out: {DERIVED_MOTION["easings"]["page-out"]["css"]};'
               f'  --fl-ease-steps-60: {DERIVED_MOTION["easings"]["steps-60"]["css"]};')
    css.append(f'  --fl-page-shift-drill: {DERIVED_MOTION["shifts"]["drill"]["px"]}px;'
               f'  --fl-page-shift-nav: {DERIVED_MOTION["shifts"]["nav"]["px"]}px;')
    css.append('  --fl-page-shift-x: var(--fl-page-shift-drill);'
               '  --fl-page-shift-y: var(--fl-page-shift-nav);'
               f'  /* 按轴取行程：drill=水平 {DERIVED_MOTION["shifts"]["drill"]["px"]} / '
               f'nav=垂直 {DERIVED_MOTION["shifts"]["nav"]["px"]}，供 motion.js 按方向选轴时引用 */')
    css.append('')
    css.append('  /* 字体栈（Segoe UI Variable → fallback） */')
    css.append(f'  --fl-font: {FONT_STACK};')
    css.append('')
    css.append('  /* 字阶（Type ramp：size/line 出自 learn.../typography，与 XAML TextBlock 字号交叉一致） */')
    for t in TYPE_RAMP:
        css.append(f'  --fl-font-size-{t["css"]}: {t["size"]}px;  --fl-line-{t["css"]}: {t["line"]}px;')
    css.append('  --fl-weight-regular: 400;  --fl-weight-semibold: 600; /* wght 轴 Regular/Semibold */')
    bp, _, _ = getval("ButtonPadding")
    if bp:  # 官方 ButtonPadding "11,5,11,6"
        p = [x.strip() for x in bp.split(",")]
        css.append(f'  --fl-btn-pad-h: {p[0]}px;  --fl-btn-pad-t: {p[1]}px;  --fl-btn-pad-b: {p[3]}px; /* ButtonPadding */')
    tp, _, _ = getval("TextControlThemePadding")
    if tp:  # 官方 TextControlThemePadding "10,5,6,6"
        p = [x.strip() for x in tp.split(",")]
        css.append(f'  --fl-text-pad-l: {p[0]}px; --fl-text-pad-t: {p[1]}px; --fl-text-pad-r: {p[2]}px; --fl-text-pad-b: {p[3]}px; /* TextControlThemePadding */')
    css.append('  --fl-control-fill-transparent: transparent;')
    css.append('  --fl-nav-width: 240px; /* KIT 自定：NavigationView 收起态之外的常用宽度，官方未单列 */')
    css.append('')
    css.append('  /* 圆角（XAML ControlCornerRadius / OverlayCornerRadius） */')
    for css_name, g in geometry.items():
        if css_name.startswith("--fl-radius"):
            css.append(f'  {css_name}: {g["value"]}px;')
    css.append('  --fl-stroke: 1px; /* 官方描边宽一律 1px */')
    css.append('  --fl-control-height: 32px; /* 官方控件标准高度 */')
    css.append('  --fl-list-item-height: 40px; /* ListViewItemMinHeight */')
    css.append('  --fl-slider-track: 4px;   /* SliderTrackThemeHeight */')
    css.append('  --fl-slider-inner: 12px;  /* SliderInnerThumbWidth */')
    css.append('  --fl-slider-radius: 10px; /* SliderThumbCornerRadius */')

    def gx(key, fallback="0"):
        it = geometry.get(f"xaml:{key}")
        return it["value"] if it else fallback

    css.append('')
    css.append('  /* 控件专属几何（逐一取自 raw/xaml_*_themeresources.xaml，勿凭空改写） */')
    css.append(f'  --fl-check-size: {gx("CheckBoxSize", "20")}px;      /* CheckBoxSize */')
    css.append(f'  --fl-check-glyph: {gx("CheckBoxGlyphSize", "12")}px;     /* CheckBoxGlyphSize */')
    css.append(f'  --fl-check-height: {gx("CheckBoxHeight", "32")}px;     /* CheckBoxHeight */')
    css.append(f'  --fl-check-min-width: {gx("CheckBoxMinWidth", "120")}px; /* CheckBoxMinWidth */')
    css.append(f'  --fl-check-stroke: {gx("CheckBoxBorderThickness", "1")}px;     /* CheckBoxBorderThickness */')
    css.append(f'  --fl-radio-glyph: {gx("RadioButtonCheckGlyphSize", "12")}px;     /* RadioButtonCheckGlyphSize */')
    css.append(f'  --fl-glyph-stroke: {gx("CheckGlyphStrokeThickness", "2.5")}px;    /* ListViewItem CheckGlyph StrokeThickness */')
    css.append(f'  --fl-radius-checkbox: {gx("ListViewItemCheckBoxCornerRadius", "4")}px;   /* ListViewItemCheckBoxCornerRadius；CheckBox 本体用 --fl-radius-control */')
    css.append(f'  --fl-radius-indicator: {gx("NavigationViewSelectionIndicatorRadius", "2")}px;  /* NavigationViewSelectionIndicatorRadius */')
    css.append(f'  --fl-radius-list-indicator: {gx("ListViewItemSelectionIndicatorCornerRadius", "1.5")}px; /* ListViewItemSelectionIndicatorCornerRadius */')
    css.append(f'  --fl-radius-combo-highlight: {gx("ComboBoxHiglightBorderCornerRadius", "7")}px; /* ComboBoxHiglightBorderCornerRadius（XAML 原键名少一个 h） */')
    css.append(f'  --fl-radius-combo-item: {gx("ComboBoxItemCornerRadius", "3")}px;      /* ComboBoxItemCornerRadius */')
    css.append(f'  --fl-radius-combo-pill: {gx("ComboBoxItemPillCornerRadius", "1.5")}px;  /* ComboBoxItemPillCornerRadius */')
    css.append(f'  --fl-nav-item-height: {gx("NavigationViewItemOnLeftMinHeight", "36")}px; /* NavigationViewItemOnLeftMinHeight */')
    css.append(f'  --fl-nav-indicator-w: {gx("NavigationViewSelectionIndicatorWidth", "3")}px;  /* NavigationViewSelectionIndicatorWidth */')
    css.append(f'  --fl-nav-indicator-h: {gx("NavigationViewSelectionIndicatorHeight", "16")}px; /* NavigationViewSelectionIndicatorHeight */')
    css.append(f'  --fl-list-min-width: {gx("ListViewItemMinWidth", "88")}px; /* ListViewItemMinWidth */')
    css.append(f'  --fl-list-check-offset: {gx("ListViewItemContentOffsetX", "-40.5").lstrip("-")}px;'
               f' /* = -ListViewItemContentOffsetX（XAML 为 -40.5，负号表示内容右移；此处取正值使用） */')
    css.append(f'  --fl-list-item-height-two-line: {gx("ListItemHeightTwoLine", "64")}px; /* KIT 自定：图标+主副两行，官方未单列 */')
    css.append(f'  --fl-icon-size: {gx("IconSize", "20")}px; /* 列表项图标 20（Fluent 图标族 16/20/24 中档） */')
    css.append(f'  --fl-settings-row-h: {gx("SettingsRowHeight", "56")}px;'
               f' /* 设置行最小高（实测派生：图标 20 + 主副两行 + 上下各 2） */')
    css.append(f'  --fl-combo-min-width: {gx("ComboBoxThemeMinWidth", "64")}px; /* ComboBoxThemeMinWidth */')
    css.append(f'  --fl-combo-popup-min-width: {gx("ComboBoxPopupThemeMinWidth", "80")}px; /* ComboBoxPopupThemeMinWidth */')
    css.append(f'  --fl-combo-popup-stroke: {gx("ComboBoxPopupBorderThemeThickness", "2")}px; /* ComboBoxPopupBorderThemeThickness */')
    css.append(f'  --fl-combo-max-h: {gx("ListViewItemMaxDropDownHeight", "504")}px; /* MaxDropDownHeight，15 项一屏 */')
    css.append(f'  --fl-combo-glyph: {gx("ComboBoxDropDownGlyphSize", "12")}px;  /* DropDownGlyph 12x12 */')
    css.append(f'  --fl-combo-glyph-gap: {gx("ComboBoxDropDownGlyphGap", "14")}px; /* DropDownGlyph Margin 右值 */')
    css.append('')
    css.append('  /* 间距（content-basics） */')
    css.append('  --fl-space-1: 4px;  --fl-space-2: 8px;  --fl-space-3: 12px;')
    css.append('  --fl-space-4: 16px; --fl-space-6: 24px; --fl-space-8: 32px; --fl-space-12: 48px;')
    css.append('')
    css.append('  /* 海拔阴影：官方只给 elevation 值，CSS 阴影为 KIT 换算近似（blur≈elevation*0.5px，非官方 CSS 定义） */')
    for ev, sh in SHADOW_MAP.items():
        css.append(f'  --fl-shadow-e{ev}: {sh}; /* elevation {ev} */')
    css.append('  --fl-shadow-card: var(--fl-shadow-e8);')
    css.append('  --fl-shadow-flyout: var(--fl-shadow-e32);')
    css.append('  --fl-shadow-dialog: var(--fl-shadow-e128);')
    css.append('}')
    css.append('')
    for theme in ("dark", "light"):
        sel = ':root, [data-theme="dark"]' if theme == "dark" else '[data-theme="light"]'
        css.append(f'{sel} {{ /* {theme}（XAML {("Default" if theme=="dark" else "Light")} 主题字典） */')
        slot = ("暗主题=SystemAccentColorLight2 档（浅，配黑字）" if theme == "dark"
                else "亮主题=SystemAccentColorDark1 档（深，配白字）")
        css.append(f'  --fl-accent-fill: {ACCENT["dark_fill"] if theme == "dark" else ACCENT["light_fill"]}; '
                   f'/* AccentFillColorDefault：{slot} */')
        accent_base = ACCENT["dark_fill"] if theme == "dark" else ACCENT["light_fill"]
        css.append(f'  --fl-accent-fill-hover: {alpha(accent_base, ACCENT["secondary_opacity"])}; '
                   f'/* AccentFillColorSecondaryBrush = AccentFillColorDefault @Opacity {ACCENT["secondary_opacity"]} */')
        css.append(f'  --fl-accent-fill-pressed: {alpha(accent_base, ACCENT["tertiary_opacity"])}; '
                   f'/* AccentFillColorTertiaryBrush = AccentFillColorDefault @Opacity {ACCENT["tertiary_opacity"]} */')
        for css_name, c in selected_colors.items():
            v = c.get(theme)
            if v:
                css.append(f'  {css_name}: {css_color(v)}; /* {c["xaml_key"]} */')
        css.append(f'  --fl-acrylic-bg: var(--fl-solid-bg-secondary); /* Acrylic 网页近似：纯色 + backdrop-filter blur(60px) saturate(125%)，见 fluent2-controls.css */')
        css.append('}')
        css.append('')
    (HERE / "fluent2-tokens.css").write_text("\n".join(css) + "\n", encoding="utf-8")

    # ---- 写 official-values.md ----
    md = []
    md.append("# official-values —— WinUI 3 / Fluent 官方数值（全部带出处）")
    md.append("")
    md.append(f"> 提取脚本 `extract_tokens.py`；XAML 源：microsoft-ui-xaml `controls/dev/CommonStyles` "
              f"（commit `09cfc8ff3fbf`，2026-10-20，MIT）；文档源：learn.microsoft.com（快照见 `raw/doc_*.md`）。")
    md.append(f"> 完整颜色库存共 **{len(colors_all)}** 个 token（暗/亮双主题），精选映射进 `fluent2-tokens.css`；"
              f"全量见 `official-values.json` 的 `colors_selected` 与 `raw/`。")
    md.append("")
    md.append("## 强调色（系统色）")
    md.append(f"- 默认 `{ACCENT['value']}`（Windows 11 默认系统强调色）。{ACCENT['note']}。")
    md.append("- 变体规则（XAML）：暗主题填充用 SystemAccentColorDark1，亮主题用 SystemAccentColorLight2；")
    md.append("  文本色 Dark2/Light3；共 Light1-3 / Dark1-3 六档。用户可整体替换 accent。")
    md.append(f"- 状态档位（按 XAML brush 的 Opacity 派生，不另取 hex）："
              f"`--fl-accent-fill-hover` = Default @Opacity {ACCENT['secondary_opacity']}（AccentFillColorSecondaryBrush）、"
              f"`--fl-accent-fill-pressed` = Default @Opacity {ACCENT['tertiary_opacity']}（AccentFillColorTertiaryBrush）。")
    md.append("")
    md.append("## 精选颜色 token（暗/亮）")
    md.append("")
    md.append("> 注意：下表 dark/light 列为 **XAML 原始格式 `#AARRGGBB`**（alpha 在前）；")
    md.append("> `fluent2-tokens.css` 中已转换为 **CSS 格式 `#RRGGBBAA`**（alpha 在后）。")
    md.append("")
    md.append("| CSS 变量 | XAML key | dark | light |")
    md.append("|---|---|---|---|")
    for css_name, c in selected_colors.items():
        md.append(f"| `{css_name}` | {c['xaml_key']} | {c.get('dark','—')} | {c.get('light','—')} |")
    md.append("")
    md.append("## 动效（motion）")
    md.append(f"出处：<{MOTION['source']}>")
    md.append("")
    md.append("| 名称 | 曲线 | 时长 | 用途 |")
    md.append("|---|---|---|---|")
    rows = [
        ("Direct Entrance", "cubic-bezier(0,0,0,1)", "167/250/333ms", "Position, Scale, Rotation（已有元素入场，Fast-In）"),
        ("Point to Point", "cubic-bezier(0.55,0.55,0,1)", "167/250/333ms", "位置/缩放/旋转的点对点位移"),
        ("Direct Exit", "cubic-bezier(0,0,0,1)", "167ms", "离场（**必须**配 fade out）"),
        ("Gentle Exit", "cubic-bezier(1,0,1,1)", "167ms", "最简离场（Position, Scale）"),
        ("Fade", "linear", "83ms", "仅 Opacity"),
        ("Strong Entrance", "三关键帧 Elastic In", "167+167+333ms", "Position, Scale（弹性入场）"),
    ]
    for r in rows:
        md.append("| " + " | ".join(r) + " |")
    md.append("")
    md.append("### 控件级时长档（XAML `Control*AnimationDuration`，与上面四档同数值、不同语义）")
    md.append("出处：`raw/xaml_Common_themeresources_any.xaml`。")
    md.append("")
    md.append("| CSS 变量 | 时长 | XAML key | 用途 |")
    md.append("|---|---|---|---|")
    for name, d in MOTION["control_durations"].items():
        key = "Control%sAnimationDuration" % name.capitalize()
        md.append(f"| `--fl-dur-control-{name}` | {d['ms']}ms | {key} | {d['use']} |")
    md.append("")
    md.append("规则：" + "；".join(MOTION["rules"][:4]) + "。")
    md.append("")
    md.append("## 动效：实测派生（**非官方档位**）")
    md.append("来源：Win11 官方应用 60fps 录屏逐帧反解（2026-10-21），方法与原始数字见 `VIDEO-ALIGN.md` §9。")
    md.append("这些值**不属于**官方 83 / 167 / 250 / 333ms 四档，检索官方规范时不要引用本节。")
    md.append("")
    md.append("| CSS 变量 | 值 | 用途 | 依据 |")
    md.append("|---|---|---|---|")
    for name, d in DERIVED_MOTION["durations"].items():
        md.append(f"| `--fl-dur-{name}` | {d['value']} | {d['use']} | {d['source']} |")
    for name, e in DERIVED_MOTION["easings"].items():
        md.append(f"| `--fl-ease-{name}` | `{e['css']}` | {e['use']} | {e['source']} |")
    for name, s in DERIVED_MOTION["shifts"].items():
        md.append(f"| `--fl-page-shift-{name}` | {s['px']}px | {s['use']} | {s['source']} |")
    md.append("")
    md.append("## 字阶（Type ramp，Segoe UI Variable）")
    md.append("出处：<https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/typography>；"
              "字号与 `xaml_TextBlock_themeresources.xaml` 交叉一致。")
    md.append("")
    md.append("| 样式 | 字号/行高 | 字重 | CSS 类 |")
    md.append("|---|---|---|---|")
    for t in TYPE_RAMP:
        md.append(f"| {t['name']} | {t['size']}/{t['line']} | {t['weight']} | `.fl-{t['css']}` |")
    md.append("")
    md.append("字重轴：Light 300 / Semilight 350 / Regular 400 / Semibold 600 / Bold 700；强调用 Semibold 不用 Bold；不用斜体。")
    md.append("最小可读：14px Semibold、12px Regular。每行 50–60 字符。")
    md.append("")
    md.append("## 间距（spacing & gutters）")
    md.append(f"出处：<{SPACING_SOURCE}>；{RULES_4PX}")
    md.append("")
    md.append("| 间距 | 用途 |")
    md.append("|---|---|")
    for s in SPACING:
        md.append(f"| {s['px']} epx | {s['use']} |")
    md.append("")
    md.append("## 海拔与描边（layering & elevation）")
    md.append(f"出处：<{ELEVATION_SOURCE}>")
    md.append("")
    md.append("| 元素 | Elevation | 描边 |")
    md.append("|---|---|---|")
    for e in ELEVATION:
        md.append(f"| {e['name']} | {e['value']} | {STROKE_WIDTH}px |")
    md.append("")
    md.append(f"控件状态：Rest={ELEVATION_STATES['rest']} / Hover={ELEVATION_STATES['hover']} / Pressed={ELEVATION_STATES['pressed']}。")
    md.append("双层系统：Base layer（导航/命令）+ Content layer（核心内容，卡片化）。")
    md.append("**CSS 阴影换算（KIT 自定，非官方 CSS 值）**：`blur ≈ elevation×0.5px`，两层投影，透明度随海拔增大，见 `fluent2-tokens.css` 注释。")
    md.append("")
    md.append("## 圆角（geometry）")
    md.append("出处：<https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/geometry>；"
              "与 `xaml_CornerRadius_themeresources.xaml` 交叉一致。")
    md.append("")
    md.append("| 圆角 | 用途 |")
    md.append("|---|---|")
    md.append("| 8px | 顶层容器：窗口、flyout、dialog、menuflyout、teaching tip |")
    md.append("| 4px | 页内元素：button、checkbox、textbox、combobox、listview、progressbar/slider/scrollbar 条形；ToolTip 例外也是 4px |")
    md.append("| 0px | 直边相接处；flyout 与唤起方相连一侧；snap/maximized 窗口 |")
    md.append("")
    md.append("## 控件几何（XAML 默认值）")
    md.append("| 资源 | 值 | 出处 |")
    md.append("|---|---|---|")
    label = {"ButtonPadding": "Button 内边距", "TextControlThemePadding": "TextBox/ComboBox 内边距",
             "TextControlThemeMinHeight": "文本控件最小高", "ControlHeight": "控件标准高",
             "ContentDialogPadding": "ContentDialog 内边距", "ContentDialogMaxWidth": "ContentDialog 最大宽",
             "ContentDialogMinHeight": "ContentDialog 最小高", "ListViewItemMinHeight": "列表项最小高",
             "ListViewItemCornerRadius": "列表项圆角", "ListViewItemSelectionIndicatorCornerRadius": "选中指示条圆角",
             "ListViewItemDisabledThemeOpacity": "列表项禁用透明度",
             "ListViewItemMinWidth": "列表项最小宽", "ListViewItemCheckBoxCornerRadius": "列表项内复选框圆角",
             "ListViewItemContentOffsetX": "多选时内容偏移（负值=右移）",
             "CheckBoxSize": "CheckBox 方框尺寸", "CheckBoxGlyphSize": "CheckBox 勾号字号",
             "CheckBoxBorderThickness": "CheckBox 描边宽", "CheckBoxHeight": "CheckBox 行高",
             "CheckBoxMinWidth": "CheckBox 最小宽", "RadioButtonCheckGlyphSize": "RadioButton 内点直径",
             "NavigationViewItemOnLeftMinHeight": "左侧导航项最小高",
             "NavigationViewSelectionIndicatorWidth": "导航选中条宽",
             "NavigationViewSelectionIndicatorHeight": "导航选中条高",
             "NavigationViewSelectionIndicatorRadius": "导航选中条圆角",
             "ComboBoxThemeMinWidth": "ComboBox 最小宽", "ComboBoxPopupThemeMinWidth": "ComboBox 下拉面板最小宽",
             "ComboBoxPopupBorderThemeThickness": "ComboBox 下拉面板描边宽",
             "ComboBoxHiglightBorderCornerRadius": "ComboBox 高亮边框圆角",
             "ComboBoxItemCornerRadius": "ComboBox 选项圆角",
             "ComboBoxItemPillCornerRadius": "ComboBox 选项选中条圆角",
             "ComboBoxDropDownGlyphSize": "ComboBox 下拉箭头尺寸",
             "ComboBoxDropDownGlyphGap": "ComboBox 下拉箭头右间距",
             "ListViewItemMaxDropDownHeight": "下拉面板最大高（15 项一屏）",
             "CheckGlyphStrokeThickness": "勾号描边宽（ListViewItem CheckGlyph）",
             "ListItemHeightTwoLine": "两行列表项行高（KIT 自定）",
             "SettingsRowHeight": "设置行最小高（实测派生）",
             "IconSize": "列表项图标尺寸"}
    for item in CONTROL_GEOMETRY:
        v, _t, s = getval(item["key"])
        if v is not None:
            md.append(f"| {label.get(item['key'], item['key'])} | `{v}` | raw/{s} |")
    for item in CONTROL_GEOMETRY_EXTRA:
        md.append(f"| {label.get(item['key'], item['key'])} | `{item['value']}` | {item['source']} |")
    md.append("")
    md.append("## 断点与单位")
    md.append(f"出处：<{BREAKPOINTS['source']}>")
    md.append("")
    md.append("| 档位 | 范围 |")
    md.append("|---|---|")
    md.append(f"| Small | ≤{BREAKPOINTS['small_max']}px |")
    md.append(f"| Medium | {BREAKPOINTS['small_max']+1}–{BREAKPOINTS['medium_max']}px |")
    md.append(f"| Large | ≥{BREAKPOINTS['large_min']}px |")
    md.append("")
    md.append("单位为 effective pixels（epx，网页直接当 CSS px 用）；**4 的倍数规则**：" + RULES_4PX)
    md.append("")
    md.append("## 材质（网页近似方案，官方无数值页）")
    md.append("出处：<https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/materials>（只有原则）")
    md.append("")
    md.append("| 材质 | 官方规则 | 网页落地（标注近似） |")
    md.append("|---|---|---|")
    md.append("| Mica | 不透明基底，染桌面壁纸色；应用基底 | `--fl-solid-bg-base` 纯色（网页无壁纸来源，近似=纯色基底层） |")
    md.append("| Acrylic | 半透明磨砂，只用于瞬态轻触消失表面（flyout/菜单） | 纯色 + `backdrop-filter: blur(60px) saturate(125%)` |")
    md.append("| Smoke | 模态遮罩，恒为半透明黑（不分主题） | `--fl-smoke`（XAML SmokeFillColorDefault=#4D000000） |")
    md.append("")
    md.append("## 导航与命令（原则，无数值）")
    md.append("- 左导航（NavigationView）：顶层页、导航项 >5、不频繁切换；顶部导航：要全展示/省空间/图标不够表意。")
    md.append("- 超过 2 层用 BreadcrumbBar；扁平 ≤8 页 / 层级 >7 页；避免 pogo-sticking。")
    md.append("- 命令：能直接操作就不加命令；高频放画布，其余 CommandBar/菜单；确认仅用于不可撤销且后果重大操作。")
    md.append("出处：navigation-basics / commanding-basics（快照 raw/doc_basics-and-layout.md）。")
    (HERE / "official-values.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"OK: colors_all={len(colors_all)} selected={len(selected_colors)} geometry={len(geometry)}")
    if missing:
        print(f"[warn] 未找到（跳过）：{missing}", file=sys.stderr)


if __name__ == "__main__":
    build()
