/* fluent2-motion.js —— 动效编排 API（数值全部来自官方，定义见 fluent2-tokens.css）
   规则：页面转场必须走 M.transitionTo()，禁直接切类（检查器规则 6）；
         flyout/dialog 隐藏态自动带 visibility/pointer-events（规则 7，由 .fl-overlay CSS 承担）；
         stagger 步进 83ms（官方 Fade 档）、上限 333ms，走 --fl-stagger-delay 自定义属性（不写 transition-delay）；
         尊重 prefers-reduced-motion 且随系统设置实时切换。

   编排约定：一次性动效用 CSS keyframe animation，靠 animationend 结算（setTimeout 兜底），
             不再用 void offsetWidth + requestAnimationFrame + 层层 setTimeout 猜测时序。 */
(function (global) {
  "use strict";

  var mq = global.matchMedia ? global.matchMedia("(prefers-reduced-motion: reduce)") : null;
  var REDUCED = !!(mq && mq.matches);
  if (mq) {
    if (mq.addEventListener) mq.addEventListener("change", function (e) { REDUCED = e.matches; });
    else if (mq.addListener) mq.addListener(function (e) { REDUCED = e.matches; });
  }

  var STEP = 83;    // 官方 Fade 档（ms），stagger 步进
  var CAP = 333;    // 官方最大时长档（ms），stagger 上限
  var PAGE_MS = 250; // 页面转场·进场：官方档 ControlNormalAnimationDuration（tokens --fl-dur-page）
  var PAGE_GAP = 133; // 两拍间隔 = −20% 的重叠缓冲：旧页淡出 167ms，新页 133ms 起手（避免衔接处空一帧）
  var PAGE_ANIM = "fl-page-in-slide-kf"; // 结算只认位移那条，不认 83ms 的 fade
  var PAGE_ANIM_OUT = "fl-page-out-slide-kf";

  var M = {};
  var pageGen = 0;      // 转场代际：快速连点时丢弃上一轮的回调
  var pageStack = [];   // 页面栈：用于自动判断 forward / back
  var PAGE_VARS = ["--fl-page-from-x", "--fl-page-from-y", "--fl-page-to-x", "--fl-page-to-y"];

  /* 一次性动效结算：animationend 优先，setTimeout 兜底；代际过期则丢弃（不污染新一次转场）
     animName 非空时只认这条动画 —— 页面转场有「位移 + fade」两条，fade 先结束会提前清类造成闪回 */
  function onAnimEnd(el, gen, fallbackMs, fn, animName) {
    if (!el) return;
    var done = false;
    function fire() {
      if (done) return;
      done = true;
      el.removeEventListener("animationend", onEnd);
      if (gen !== pageGen) return;
      fn();
    }
    function onEnd(e) {
      if (e.target !== el) return; // 忽略子元素冒泡上来的 animationend（stagger 项）
      if (animName && e.animationName !== animName) return;
      fire();
    }
    el.addEventListener("animationend", onEnd);
    global.setTimeout(fire, fallbackMs + 80);
  }

  /* 同步结算上一轮转场残留的类与位移变量（连点安全） */
  function settlePages() {
    var pages = document.querySelectorAll(".fl-page");
    for (var i = 0; i < pages.length; i++) {
      pages[i].classList.remove("fl-exit", "fl-point-to-point", "fl-in",
                                "fl-page-leaving", "fl-page-in", "fl-page-out");
      for (var k = 0; k < PAGE_VARS.length; k++) pages[i].style.removeProperty(PAGE_VARS[k]);
    }
  }

  /* ---- 转场方向 -------------------------------------------------------------
     dir 的语义 = **新页的入场起点方位**（不是运动方向）：
       up    → 起点在上方（-108px），向下落到 0
       down  → 起点在下方（+108px），向上落到 0
       left  → 起点在左侧（-264px）
       right → 起点在右侧（+264px）
     forward / back 是逻辑方向，按轴映射（drill→right/left）；
     **竖向一律落到 down**（见下面 shiftOf 的注释），所以 nav 的 forward / back 观感一致。
     轴由方向决定，行程由轴决定，kind 只提供缺省轴 —— 所以 {dir:"up"} 不带 kind 也能用，
     而 {kind:"drill", dir:"up"} 表示"水平场景下改走垂直"，见 KIT 规则 15。 */
  var DIR = {
    forward: { axis: null, sign: 1 },
    back:    { axis: null, sign: -1 },
    up:      { axis: "y",  sign: -1 },
    down:    { axis: "y",  sign: 1 },
    left:    { axis: "x",  sign: -1 },
    right:   { axis: "x",  sign: 1 }
  };
  var DIR_NAMES = ["forward", "back", "up", "down", "left", "right"];

  function axisOfKind(kind) { return kind === "drill" ? "x" : "y"; }

  /* dir → {axis, sign}；非法值返回 null，由调用方退化 —— 绝不静默当成 forward
     （旧实现只判 dir === "back"，其余一律 +1，导致竖向永远"从下方进入"且 dir:'top' 无报错）

     竖向的铁律：**一级导航（kind="nav"）只准"自下方进入"**。
     Win11 设置类应用里点任意侧栏项，内容都是向上滑入；早期版本按"导航项在侧栏里的先后序"
     给符号（点上面那条就从上方压下），实测观感过重、且与官方应用不符，已废弃。
     `forward` / `back` 在竖向都归一到 down；要反向只能显式写 dir:"up"（保留逃生口）。 */
  function shiftOf(kind, dir) {
    var d = DIR[dir];
    if (!d) return null;
    var axis = d.axis || axisOfKind(kind);
    var sign = d.sign;
    if (axis === "y" && kind !== "drill" && !d.axis) sign = 1; // forward / back → 一律自下方
    return { axis: axis, sign: sign };
  }

  function shiftVar(axis) {
    return axis === "x" ? "var(--fl-page-shift-x)" : "var(--fl-page-shift-y)";
  }

  /* 写入本轮的入/出方向：入页起点 = +sign*mag，出页终点 = -sign*mag
     只接受 axis / sign，不再感知 kind / dir —— "方向只有一种符号"这类缺陷因此在结构上无法复现 */
  function applyShift(inEl, outEl, axis, sign) {
    var mag = shiftVar(axis);
    var pos = mag, neg = "calc(" + mag + " * -1)";
    var inV = sign > 0 ? pos : neg;
    var outV = sign > 0 ? neg : pos;
    var zero = "0px";
    var inX = axis === "x" ? inV : zero, inY = axis === "y" ? inV : zero;
    var outX = axis === "x" ? outV : zero, outY = axis === "y" ? outV : zero;
    if (inEl) {
      inEl.style.setProperty("--fl-page-from-x", inX);
      inEl.style.setProperty("--fl-page-from-y", inY);
    }
    if (outEl) {
      outEl.style.setProperty("--fl-page-to-x", outX);
      outEl.style.setProperty("--fl-page-to-y", outY);
    }
  }

  /* 方向解析，三级退化：显式 dir → 页面栈（目标是上一页=back）→ 缺省 forward
     返回 {axis, sign, dir, isBack}；isBack 只决定页面栈语义，与物理方向彻底解耦。
     注意 nav 不管 forward 还是 back，**物理方向都是 down**（自下方进入），
     所以这里不能拿 dir 反推符号，只能拿 shiftOf 的结果。 */
  function resolveShift(kind, explicit, pageId, curId) {
    var s = explicit ? shiftOf(kind, explicit) : null;
    if (explicit && !s && global.console && global.console.warn) {
      global.console.warn('[M.transitionTo] 未知方向 dir="' + explicit + '"，可选 ' +
        DIR_NAMES.join(" / ") + "；已回退为自动推断");
    }
    var backByStack = pageStack.length >= 2 && pageStack[pageStack.length - 2] === pageId;
    if (s) {
      return { axis: s.axis, sign: s.sign, dir: explicit,
               isBack: explicit === "back" || backByStack };
    }
    if (kind === "nav") {
      // 一级导航固定"自下方进入"，与点在侧栏的哪一项无关。
      // isBack 恒 false：Win11 的一级导航没有"返回"概念，点回上面的项是新导航而不是后退，
      // 若按页面栈判成 back，A→B→A 之后栈会被截断到 [A]，M.back() 就无路可退。
      s = shiftOf(kind, "down");
      return { axis: s.axis, sign: s.sign, dir: "down", isBack: false };
    }
    if (backByStack) {
      s = shiftOf(kind, "back");
      return { axis: s.axis, sign: s.sign, dir: "back", isBack: true };
    }
    s = shiftOf(kind, "forward");
    return { axis: s.axis, sign: s.sign, dir: "forward", isBack: false };
  }

  /* 主题切换：dark | light（tokens.css 以 [data-theme] 承载双主题） */
  M.theme = function (name) {
    document.documentElement.setAttribute("data-theme", name);
  };
  M.toggleTheme = function () {
    var cur = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
    M.theme(cur);
    return cur;
  };

  /* 页面转场：两轴（实测派生 283ms；drill 水平 176px / nav 垂直 72px，竖向恒自下方进入）
     kind: "nav"（一级导航，点侧栏）| "drill"（二级下钻，点内容区入口）
     dir : "forward" | "back" | "up" | "down" | "left" | "right"
           缺省时 nav 恒为 down（自下方进入）、drill 按页面栈推断 right/left
     两页由 CSS 放在同一网格单元里重叠（不上下堆叠），转场期锁内容区高度，全程无布局跳变。
     用法：M.transitionTo("page-detail", { kind: "drill" })
           M.transitionTo("page-b")                        // nav，恒自下方进入
           M.transitionTo("page-x", { dir: "up" })          // 显式指定入场方位 */
  M.transitionTo = function (pageId, opts) {
    var next = document.getElementById(pageId);
    if (!next) return null;
    if (next.classList.contains("fl-current") && !next.classList.contains("fl-page-leaving")) return next;

    opts = opts || {};
    var kind = opts.kind === "drill" ? "drill" : "nav";
    var cur = document.querySelector(".fl-page.fl-current");
    var gen = ++pageGen;

    if (!pageStack.length && cur && cur.id) pageStack = [cur.id];
    var shift = resolveShift(kind, opts.dir, pageId, cur ? cur.id : null);

    settlePages();                 // 先清上一轮残留（含位移变量），否则连点时符号会串
    applyShift(next, cur, shift.axis, shift.sign);
    void next.offsetWidth;         // 单次 reflow：让「移除类 → 添加类」真实发生，动画才会重播

    /* 侧栏选中指示条：先把当前项记下来（首次进入时用于"从无到有"），再移到目标项 */
    var navItem = kind === "nav" ? document.querySelector('.fl-nav-item[data-page="' + pageId + '"]') : null;
    if (navItem) moveIndicatorTo(navItem);

    if (REDUCED) {                 // 无障碍：瞬时切换，不做位移与淡入淡出
      if (cur) cur.classList.remove("fl-current");
      next.classList.add("fl-current");
      recordStack(pageId, shift.isBack);
      M.stagger(next);
      return next;
    }

    if (cur) {
      cur.classList.remove("fl-current");
      cur.classList.add("fl-page-leaving", "fl-page-out"); // 保留渲染，播离场动画
    }
    next.classList.add("fl-current", "fl-page-in");
    /* 不再锁容器高度：内容层现在是固定高度（1fr 网格行），每页各自滚动，
       旧页移除时容器不会收缩 —— 高度锁在这里反而会把容器撑出外壳。 */
    /* 入场元素必须等新页真正开始滑入再跑，否则它们会在「页面还不可见」的 83ms 里播完 */
    global.setTimeout(function () { if (gen === pageGen) M.stagger(next); }, PAGE_GAP);
    recordStack(pageId, shift.isBack);

    onAnimEnd(cur, gen, PAGE_MS, function () {
      if (cur) cur.classList.remove("fl-page-leaving", "fl-page-out");
    }, PAGE_ANIM_OUT);
    onAnimEnd(next, gen, PAGE_MS + PAGE_GAP, function () {
      next.classList.remove("fl-page-in");
    }, PAGE_ANIM);
    return next;
  };

  /* 页面栈：isBack 为真才截断到目标页（配合方向缺省推断）
     注意 isBack 只看「目标是不是上一页」，与位移方向无关 —— up/down 一律是 forward 语义，
     否则「点侧栏里更上面的一项」会被误判成返回，A→C→B 之后 M.back() 会跳到 A */
  function recordStack(pageId, isBack) {
    if (isBack) {
      var i = pageStack.lastIndexOf(pageId);
      pageStack = i >= 0 ? pageStack.slice(0, i + 1) : pageStack.concat([pageId]);
    } else if (pageStack[pageStack.length - 1] !== pageId) {
      pageStack.push(pageId);
    }
  }

  /* 返回上一页（不硬编码 id，模块被删也不会报错） */
  M.back = function (kind) {
    if (pageStack.length < 2) return null;
    return M.transitionTo(pageStack[pageStack.length - 2], { kind: kind || "nav", dir: "back" });
  };
  M.stack = function () { return pageStack.slice(); };

  /* ---- 侧栏选中指示条（NavigationView SelectionIndicator）-------------------------
     ⚠ 先看结论：指示条**从不离开所在的导航项**（从不跨过项间空隙）。
       它是"旧项里长出来 → 换项瞬间直接在新项上出现 → 新项里收回去"，
       两段拉伸都发生在各自项的内部，峰值高度固定，与跳了几格无关。

     一手依据：`时钟 2026-10-21 21-24-36.mp4`（1808×1408 @1.5x）逐帧半高边缘法实测
     （脚本见 video-analysis/ind_edges.py）：
       · 静止 23.8 设备px = 16 CSS；峰值 38.1 设备px = 25.4 CSS ≈ **16 × 1.6**，
         1 格跳转与 4 格跳转的峰值完全一样（38.06 / 38.20），确认是固定比例而非 |Δ| 派生
       · 旧项：锚在"尾部边"（往下的方向 = 顶边）**单向**往目标方向长，中心只挪 4.8px；
         拉满后 2~3 帧（≈33ms）朝头部边塌缩并淡出
       · 新项：直接以满高（1.6×）出现，锚在"头部边"（往下 = 底边），333ms 收缩回 16
       · 节奏：拉伸 167ms（ControlFast）→ 换项 → 收缩 333ms（ControlSlow），总 500ms
       · 曲线拟合（RMSE）：拉伸 (0.4,0,0.7,0.4)=0.046；收缩 (0.25,0.1,0.25,1)=0.036

     ⚠ 不要按 |Δ| 拉伸成"覆盖两项"（16+|Δ|）。早期版本就是这么写的，条会越过项间隙、
       看起来"跑出按钮"，与录屏不符 —— 校验器 R47 专门拦这个。
     实现用两层：ghost 停在旧项里长/塌，pill 落在新项里收。 */
  var IND_MS = 500, IND_PEAK = 1 / 3;
  var IND_PEAK_SCALE = 1.6;             // 实测峰值 25.4/16 ≈ 1.6（与距离无关）
  var IND_EDGE_MS = 83;                 // 旧条塌缩淡出（实测 33ms，取官方 83 档）
  var IND_EASE_GROW = "cubic-bezier(0.4,0,0.7,0.4)";
  var IND_EASE_SHRINK = "cubic-bezier(0.25,0.1,0.25,1)";

  function indSize(nav) {
    var cs = global.getComputedStyle(nav);
    var h = parseFloat(cs.getPropertyValue("--fl-nav-indicator-h")) || 16;
    var w = parseFloat(cs.getPropertyValue("--fl-nav-indicator-w")) || 3;
    return { h: h, w: w };
  }

  function itemCenter(nav, item) {
    /* offsetTop 相对 offsetParent（.fl-nav 是 position:relative），再加半行高 */
    var h = indSize(nav).h;
    return item.offsetTop + (item.offsetHeight - h) / 2;
  }

  function makeInd(nav, role) {
    var el = nav.querySelector('.fl-nav-ind[data-role="' + role + '"]');
    if (el) return el;
    el = document.createElement("i");
    el.className = "fl-nav-ind";
    el.setAttribute("data-role", role);
    el.setAttribute("aria-hidden", "true");
    nav.appendChild(el);
    return el;
  }

  /* 把指示条放到某项上；给了 fromItem 时播"旧项内拉伸 → 新项满高出现 → 收回"两段动画 */
  function placeIndicator(nav, toItem, fromItem) {
    if (!nav || !toItem) return;
    nav.setAttribute("data-fl-indicator", "on");
    var size = indSize(nav);
    var top = itemCenter(nav, toItem);
    var pill = makeInd(nav, "pill");
    var ghost = makeInd(nav, "ghost");

    /* 横向：对齐到行的左边缘（nav 有 padding，CSS 里写死 left:0 会偏出去）；
       RTL 下改贴右边缘 —— 用 insetInlineStart 语义由 CSS 变量控制更麻烦，这里直接算 */
    var rtl = global.getComputedStyle(nav).direction === "rtl";
    var lateral = rtl ? (nav.clientWidth - toItem.offsetLeft - toItem.offsetWidth) : toItem.offsetLeft;
    pill.style.height = size.h + "px";
    pill.style.width = size.w + "px";
    ghost.style.height = size.h + "px";
    ghost.style.width = size.w + "px";
    pill.style[rtl ? "right" : "left"] = lateral + "px";
    ghost.style[rtl ? "right" : "left"] = lateral + "px";
    pill.style[rtl ? "left" : "right"] = "auto";
    ghost.style[rtl ? "left" : "right"] = "auto";

    var canAnimate = !REDUCED && fromItem && fromItem !== toItem && pill.animate;
    if (!canAnimate) {
      if (pill.getAnimations) pill.getAnimations().forEach(function (a) { a.cancel(); });
      if (ghost.getAnimations) ghost.getAnimations().forEach(function (a) { a.cancel(); });
      pill.style.top = top + "px";
      pill.style.transform = "none";
      pill.style.opacity = "1";
      ghost.style.opacity = "0";
      return;
    }

    /* 连点保护：先掐掉上一轮，避免两个 WAAPI 动画叠加成"抖" */
    if (pill.getAnimations) pill.getAnimations().forEach(function (a) { a.cancel(); });
    if (ghost.getAnimations) ghost.getAnimations().forEach(function (a) { a.cancel(); });

    var fromTop = itemCenter(nav, fromItem);
    var down = top > fromTop;

    /* 峰值比例：固定 1.6（实测），再按"项内上下各留 2px"钳一次 ——
       这样即使有人把 --fl-nav-item-height 调到很小，条也不会长出按钮。 */
    var itemH = Math.min(
      toItem.offsetHeight || size.h,
      fromItem.offsetHeight || size.h
    );
    var cap = 1 + Math.max(0, itemH - size.h - 4) / size.h;
    var peak = Math.min(IND_PEAK_SCALE, cap);
    var h = size.h;

    /* ghost：留在旧位置，锚"尾部边"朝目标方向单向长到 peak；
       换项瞬间（peak 处）改用"头部边"不动、塌缩到 0.2 并淡出
       —— 用 translateY 补偿锚点切换，避免 origin 中途变化导致跳位。 */
    ghost.style.top = fromTop + "px";
    ghost.style.transformOrigin = down ? "50% 0" : "50% 100%";
    ghost.style.opacity = "1";
    var collapse = (peak - 0.2) * h;
    var collapseShift = "translateY(" + (down ? collapse : -collapse) + "px) scaleY(0.2)";
    var edgeAt = IND_PEAK + IND_EDGE_MS / IND_MS;
    ghost.animate([
      { transform: "scaleY(1)", opacity: 1, offset: 0, easing: IND_EASE_GROW },
      { transform: "scaleY(" + peak + ")", opacity: 1, offset: IND_PEAK, easing: "cubic-bezier(0.2,0.9,0.3,1)" },
      { transform: collapseShift, opacity: 0, offset: edgeAt },
      { transform: collapseShift, opacity: 0, offset: 1 }
    ], { duration: IND_MS, fill: "both" });

    /* pill：落在新项的最终位置，锚"头部边"。
       前 1/3 不可见（那一段是 ghost 在旧项里长），换项瞬间**直接以满高出现**（没有位移、
       没有滑过间隙），再用 2/3 时长收成 16。
       ⚠ 不能只靠 delay：WAAPI 在 delay 期间就会套用首个关键帧，
         pill 会从一开始就是拉伸态、把 ghost 的生长阶段整个盖住（实测过）。 */
    pill.style.top = top + "px";
    pill.style.transformOrigin = down ? "50% 100%" : "50% 0";
    var atFull = "scaleY(" + peak + ")";
    var anim = pill.animate([
      { transform: atFull, opacity: 0, offset: 0 },
      { transform: atFull, opacity: 0, offset: IND_PEAK - 0.002 },
      { transform: atFull, opacity: 1, offset: IND_PEAK, easing: IND_EASE_SHRINK },
      { transform: "scaleY(1)", opacity: 1, offset: 1 }
    ], { duration: IND_MS, fill: "both" });
    anim.onfinish = function () {
      pill.style.transform = "none";      // 结算后不留合成层，避免长期挂在 GPU 上
      pill.style.opacity = "1";
      pill.getAnimations().forEach(function (a) { a.cancel(); });
      ghost.style.opacity = "0";
    };
  }

  /* 公开 API：M.nav.indicator.sync() 按当前 aria-current 落位（不animate）；
     M.nav.indicator.to(item, { animate }) 用于自己接管导航的场景。 */
  M.nav = M.nav || {};
  M.nav.indicator = {
    nav: function (el) {
      return (typeof el === "string" ? document.querySelector(el) : el) ||
        document.querySelector(".fl-nav");
    },
    current: function (nav) {
      nav = M.nav.indicator.nav(nav);
      return nav ? nav.querySelector('.fl-nav-item[aria-current="page"]') : null;
    },
    to: function (toItem, opts) {
      opts = opts || {};
      var nav = opts.nav || (toItem && toItem.closest ? toItem.closest(".fl-nav") : null) ||
        M.nav.indicator.nav();
      if (!nav || !toItem) return;
      var prev = nav.__flIndItem || null;
      placeIndicator(nav, toItem, opts.animate === false ? null : prev);
      nav.__flIndItem = toItem;
    },
    sync: function (nav) {
      nav = M.nav.indicator.nav(nav);
      if (!nav) return;
      var item = M.nav.indicator.current(nav);
      if (item) {
        nav.__flIndItem = item;
        placeIndicator(nav, item, null);
      }
    }
  };

  /* transitionTo 内部用：更新 aria-current 并让指示条移动过去。
     先 sync 一次是为了让「首次进入页面」也有落位基准（否则第一跳会没有起点）。 */
  function moveIndicatorTo(item) {
    var nav = item.closest ? item.closest(".fl-nav") : null;
    if (!nav) return;
    if (!nav.__flIndReady) {
      M.nav.indicator.sync(nav);
      nav.__flIndReady = true;
    }
    var items = nav.querySelectorAll(".fl-nav-item");
    for (var i = 0; i < items.length; i++) {
      if (items[i] !== item) items[i].removeAttribute("aria-current");
    }
    item.setAttribute("aria-current", "page");
    M.nav.indicator.to(item, { nav: nav });
  }

  /* 首屏：按现有的 aria-current 落位（不播动画） */
  function initIndicator() {
    var nav = document.querySelector(".fl-nav");
    if (!nav) return;
    M.nav.indicator.sync(nav);
    nav.__flIndReady = true;
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initIndicator, { once: true });
  } else {
    global.setTimeout(initIndicator, 0);
  }

  /* ---- 导航响应式档位（对应 XAML NavigationView 的 PaneDisplayMode=Auto）----
       官方把「显示档位」和「pane 是否打开」当成两个正交状态（NavigationView.cpp
       UpdateAdaptiveLayout / OnPaneToggleButtonClick）：
        ≥ --fl-nav-expand-threshold(1008)  expanded —— 240 并排；关上 = 48 图标列（CompactInline）
        641~1007                           compact  —— 关：48 图标列；开：240 覆盖（CompactOverlay）
        < --fl-nav-compact-threshold(641)  minimal  —— 关：收在左侧外；开：240 覆盖（Overlay）
      阈值直接读 CSS 变量，不在 JS 里写第二份数字（XAML 侧对应 AdaptiveTrigger → VisualState）。

      换档（官方 UpdateAdaptiveLayout）：进入 expanded 且用户没手动关过 → 打开；
      进入 compact/minimal → 一律关闭。用户点汉堡手动关闭记 wasForceClosed（= 官方
      m_wasForceClosed），再变宽也不会自己弹开；选中导航项 / 点遮罩 / Esc 属于轻关闭，
      不改这个意图（官方 AttemptClosePaneLightly / ClosePaneIfNeccessaryAfterItemIsClicked）。

      覆盖层打开时（compact/minimal）选中导航项会自动收起 —— 对应
      NavigationView::OnNavigationViewItemInvoked → ClosePaneIfNeccessaryAfterItemIsClicked。 */
  (function () {
    function num(v, fb) {
      var n = parseFloat(v);
      return isFinite(n) ? n : fb;
    }

    function bind(nav) {
      if (nav.__flNav) return nav.__flNav;
      var cs = global.getComputedStyle(nav);
      var compactT = num(cs.getPropertyValue("--fl-nav-compact-threshold"), 641);
      var expandT = num(cs.getPropertyValue("--fl-nav-expand-threshold"), 1008);
      var shell = nav.parentElement;
      var scrim = shell ? shell.querySelector(".fl-nav-scrim") : null;
      var content = shell ? shell.querySelector(".fl-content-layer") : null;
      var floats = shell ? shell.querySelectorAll(".fl-nav-toggle-float") : [];
      var wasForceClosed = false;   /* 官方 m_wasForceClosed：手动关过，换档回 expanded 也不自动打开 */

      function modeFor(w) {
        if (w < compactT) return "minimal";
        if (w < expandT) return "compact";
        return "expanded";
      }
      /* 开合状态是唯一真相：aria-expanded 与按钮名称都从它派生（官方
         SetPaneToggleButtonAutomationName：开 = 关闭导航 / 关 = 打开导航）。 */
      function syncToggles() {
        var open = nav.dataset.navOpen === "1";
        var name = open ? "关闭导航" : "打开导航";
        var all = nav.querySelectorAll(".fl-nav-toggle");
        var i;
        for (i = 0; i < all.length; i++) {
          all[i].setAttribute("aria-expanded", open ? "true" : "false");
          all[i].setAttribute("aria-label", name);
        }
        for (i = 0; i < floats.length; i++) {
          floats[i].setAttribute("aria-expanded", open ? "true" : "false");
          floats[i].setAttribute("aria-label", name);
        }
      }
      function setOpen(open) {
        nav.dataset.navOpen = open ? "1" : "0";
        /* 遮罩只在覆盖层（compact/minimal）打开时出现：expanded 收起是并排的 48 列，不浮 */
        if (scrim) scrim.dataset.open = (open && nav.dataset.navMode !== "expanded") ? "1" : "0";
        syncToggles();
      }
      function apply() {
        var w = shell ? shell.clientWidth : global.innerWidth;
        var m = modeFor(w);
        if (nav.dataset.navMode === m) return;
        /* 档位切换是布局级瞬变（官方 AdaptiveTrigger 语义）：先掐掉过渡再改，
           否则从 compact 到 minimal 会先播一段 clip/位移，内容闪一下。
           inline transition 清空后会自动回落到样式表里的过渡。 */
        nav.style.transition = "none";
        if (scrim) scrim.style.transition = "none";
        if (content) content.style.transition = "none";
        nav.dataset.navMode = m;
        /* 官方 UpdateAdaptiveLayout：只有 expanded 按用户意图打开；compact/minimal 一律关闭 */
        setOpen(m === "expanded" && !wasForceClosed);
        void nav.offsetHeight;              /* 强制同步样式，让 none 立即生效 */
        nav.style.transition = "";
        if (scrim) scrim.style.transition = "";
        if (content) content.style.transition = "";
        if (M.nav.indicator) M.nav.indicator.sync(nav); /* 宽度变了，指示条要重新落位 */
      }
      function toggle() {
        var opening = nav.dataset.navOpen !== "1";
        /* 手动关 = 记住（官方 m_wasForceClosed=true）；手动开 = 清除 */
        wasForceClosed = !opening;
        setOpen(opening);
      }
      function closeOverlay() {
        if (nav.dataset.navOpen === "1" && nav.dataset.navMode !== "expanded") setOpen(false);
      }

      /* 收起档会让 .fl-nav-label display:none；把名称补到链接上，读屏仍有项名。
         官方 NavigationViewItem 的自动化名称也来自 Content，不随 label 收起而消失。 */
      var items = nav.querySelectorAll(".fl-nav-item");
      for (var k = 0; k < items.length; k++) {
        var label = items[k].querySelector(".fl-nav-label");
        if (label && !items[k].hasAttribute("aria-label")) {
          var text = (label.textContent || "").replace(/\s+/g, " ").trim();
          if (text) items[k].setAttribute("aria-label", text);
        }
      }

      var btns = nav.querySelectorAll(".fl-nav-toggle");
      for (var i = 0; i < btns.length; i++) btns[i].addEventListener("click", toggle);
      for (var j = 0; j < floats.length; j++) floats[j].addEventListener("click", toggle);
      if (scrim) scrim.addEventListener("click", function () { setOpen(false); });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") closeOverlay();
      });
      /* 覆盖层里选中导航项就收起（展开档不关）。用捕获阶段：即使业务自己的 click
         处理器先 stopPropagation，也能在页面转场前收起浮层。 */
      nav.addEventListener("click", function (e) {
        var t = e.target;
        var item = t && t.closest ? t.closest(".fl-nav-item") : null;
        if (item && item.getAttribute("aria-disabled") !== "true") closeOverlay();
      }, true);

      if (global.ResizeObserver && shell) {
        new global.ResizeObserver(apply).observe(shell);
      } else {
        global.addEventListener("resize", apply);
      }
      apply();          /* 首次：按当前宽度落档位；expanded 默认开，compact/minimal 默认关 */
      if (!nav.dataset.navMode) nav.dataset.navMode = modeFor(shell ? shell.clientWidth : global.innerWidth);
      if (nav.dataset.navOpen !== "0" && nav.dataset.navOpen !== "1") {
        setOpen(nav.dataset.navMode === "expanded" && !wasForceClosed);
      }
      syncToggles();
      nav.__flNav = { apply: apply, setOpen: setOpen, mode: function () { return nav.dataset.navMode; } };
      return nav.__flNav;
    }

    M.nav = M.nav || {};
    M.nav.responsive = {
      bind: bind,
      auto: function (root) {
        var scope = (typeof root === "string" ? document.querySelector(root) : root) || document;
        var list = scope.querySelectorAll(".fl-nav");
        for (var i = 0; i < list.length; i++) bind(list[i]);
        return list.length;
      }
    };
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function () { M.nav.responsive.auto(); }, { once: true });
    } else {
      global.setTimeout(function () { M.nav.responsive.auto(); }, 0);
    }
  })();

  /* 列表/卡片分批入场：.fl-entrance + 83ms 步进、上限 333ms
     延迟写进 --fl-stagger-delay（只影响本动画的 animation-delay），不污染 hover/active 过渡 */  M.stagger = function (container, stepMs) {
    var root = (typeof container === "string" ? document.querySelector(container) : container);
    if (!root) return 0;
    var items = root.querySelectorAll(".fl-entrance");
    var step = typeof stepMs === "number" ? stepMs : STEP;
    var i;
    for (i = 0; i < items.length; i++) {
      items[i].classList.remove("fl-in");
      items[i].style.setProperty("--fl-stagger-delay", REDUCED ? "0ms" : Math.min(i * step, CAP) + "ms");
    }
    void root.offsetWidth; // 单次 reflow：让隐藏态落定，下面统一加类时动画才会重播
    for (i = 0; i < items.length; i++) items[i].classList.add("fl-in");
    return items.length;
  };

  /* ---- ComboBox -------------------------------------------------------------
     焦点始终留在按钮上（aria-activedescendant 指向高亮项），这是 APG「select-only combobox」的做法：
     焦点进弹层后 Esc/Tab/outside-click 的处理会成倍变复杂。
     弹层必须 portal 到 body：.fl-content-layer 有 overflow:clip（校验器 R26 强制），留在页内会被裁。
     API：M.combo.auto() 绑定页面上所有 .fl-combo；M.combo.init(rootEl) 单个绑定并返回实例。 */
  var comboSeq = 0;

  function comboInit(root) {
    if (!root) return null;
    if (root.__flCombo) return root.__flCombo;
    var btn = root.querySelector(".fl-combo-btn");
    var popup = root.querySelector(".fl-combo-popup");
    if (!btn || !popup) return null;

    var valueEl = btn.querySelector(".fl-combo-value");
    var items = Array.prototype.slice.call(popup.querySelectorAll(".fl-combo-item"));
    var active = -1;
    var typed = "", typedAt = 0;
    var base = root.id || ("fl-combo-" + (++comboSeq));
    var portalDone = false;
    var rafId = 0;

    /* aria-activedescendant 依赖 id，缺了就不生效 —— 统一补齐，避免调用方手写漏掉 */
    items.forEach(function (it, i) { if (!it.id) it.id = base + "-o" + (i + 1); });
    btn.setAttribute("aria-controls", popup.id);

    function isDisabled(i) { return items[i].getAttribute("aria-disabled") === "true"; }
    function selectedIndex() {
      for (var i = 0; i < items.length; i++) {
        if (items[i].getAttribute("aria-selected") === "true") return i;
      }
      return -1;
    }
    function step(from, delta) {
      var n = items.length, i = from;
      for (var k = 0; k < n; k++) {
        i = (i + delta + n) % n;
        if (!isDisabled(i)) return i;
      }
      return from;
    }
    function setActive(i) {
      if (i < 0 || i >= items.length) return;
      if (active >= 0 && items[active]) items[active].removeAttribute("data-active");
      active = i;
      items[i].setAttribute("data-active", "true");
      btn.setAttribute("aria-activedescendant", items[i].id);
      /* 键盘移动时保证高亮项可见（弹层自身滚动，不滚动页面） */
      var it = items[i], top = it.offsetTop, bot = top + it.offsetHeight;
      if (top < popup.scrollTop) popup.scrollTop = top;
      else if (bot > popup.scrollTop + popup.clientHeight) popup.scrollTop = bot - popup.clientHeight;
    }

    /* 定位（录屏实测的 Win11 行为）：让**选中项那一行正好盖住按钮** ——
         弹层顶边 = 按钮顶边 − 选中项相对弹层顶边的偏移（= padding + 边框 + 选中项之前的行）
       所以弹层是"压在"按钮上、顶边露一小条，而不是挂在按钮下方留 4px 缝；
       选中项在第几项都不影响：先量偏移再回推，索引 2 时弹层自然往上顶。
       水平：与按钮左对齐、宽度不小于按钮宽度，左右各留 8px 视口钳制。
       只赋值 left/top（不做 transition）。 */
    function place() {
      var r = btn.getBoundingClientRect();
      /* 先清掉上一轮写进 style 的 maxHeight：否则量到的尺寸是「被钳过的值」，
         钳制会自我维持 —— 4 项短列表被永久压出 4px 溢出，凭空多一条滚动条 */
      popup.style.maxHeight = "";
      popup.style.bottom = "auto";
      popup.scrollTop = 0;
      /* 量偏移要一个稳定基准：先落到 top=0（此时还没 .fl-open，clip-path 不影响布局） */
      popup.style.top = "0px";

      popup.style.minWidth = Math.max(parseFloat(global.getComputedStyle(root).minWidth) || 0, r.width) + "px";
      /* 水平钳制：按钮贴着右边缘时，弹层比按钮宽就会伸到视口外，右侧滚动条直接被窗口裁掉
         （表现是"看不到滚动条 / 内容像溢出了"）。左右各留 8px。 */
      var w = popup.offsetWidth;
      var margin = 8;
      var left = Math.min(r.left, global.innerWidth - margin - w);
      popup.style.left = Math.max(margin, left) + "px";

      /* maxHeight 是 border-box 语义，而 scrollHeight 只含 padding —— 两者直接比会差一圈边框，
         短列表因此刚好溢出 4px（= 上下各 2px 边框）。所以量自然高度用 offsetHeight。 */
      var naturalH = popup.offsetHeight;
      var maxH = parseFloat(global.getComputedStyle(popup).maxHeight) || 504;
      var wantH = Math.min(naturalH, maxH);

      /* 选中项相对弹层顶边的偏移：用 rect 差 + scrollTop 还原"未滚动"的位置，
         不要自己算 padding / 行高（改了 padding 就会偏）*/
      var sel = items[selectedIndex()];
      var off = 0;
      if (sel) {
        off = (sel.getBoundingClientRect().top - popup.getBoundingClientRect().top) + popup.scrollTop;
      }
      var top = Math.round(r.top - off);

      /* 视口钳制，三步：
         ① 首选"选中行盖住按钮"（top = 按钮顶 − 偏移）；
         ② 下方放不下整份列表 → 整体上移到刚好装下（丢掉对齐，但不出滚动条）；
         ③ 列表比视口还高 → 贴顶 + 内部滚动。
         只判"下方"是因为弹层永远从选中项往下展开（顶边不可能低于按钮顶太多）。 */
      var minTop = margin;
      var maxBottom = global.innerHeight - margin;
      if (top < minTop) top = minTop;
      if (top + wantH > maxBottom) {
        var fit = maxBottom - wantH;
        top = fit >= minTop ? fit : minTop;
      }
      popup.style.top = top + "px";
      var maxH = Math.max(96, Math.min(wantH, maxBottom - top));
      popup.style.maxHeight = maxH + "px";

      /* 揭示方向：弹层整体落在按钮上方 → 从底边往上揭；否则从顶边往下揭 */
      popup.dataset.drop = (top + maxH <= r.top) ? "up" : "down";
    }
    function reflowOnScroll() {
      if (!popup.classList.contains("fl-open")) return;
      if (rafId) return;
      rafId = global.requestAnimationFrame(function () { rafId = 0; place(); });
    }

    function open() {
      if (popup.classList.contains("fl-open")) return;
      if (!portalDone) { document.body.appendChild(popup); portalDone = true; }
      place();
      /* 必须在加 .fl-open **之前**把"关闭态"刷成已解析样式，否则浏览器认为元素出生就是开着的，
         一条过渡都不会创建 —— 表现就是「动画没了」（首开尤其容易踩）。
         place() 里已经在读 offsetWidth/offsetHeight，这里再显式读一次，把这个前提写死。 */
      void popup.offsetHeight;
      popup.classList.add("fl-open");
      btn.setAttribute("aria-expanded", "true");
      root.setAttribute("data-open", "true");
      setActive(selectedIndex() >= 0 ? selectedIndex() : step(-1, 1));
      document.addEventListener("pointerdown", onOutside, true);
      global.addEventListener("resize", reflowOnScroll);
      global.addEventListener("scroll", reflowOnScroll, true);
    }
    function close(restoreFocus) {
      if (!popup.classList.contains("fl-open")) return;
      popup.classList.remove("fl-open");
      btn.setAttribute("aria-expanded", "false");
      root.setAttribute("data-open", "false");
      btn.removeAttribute("aria-activedescendant");
      if (active >= 0 && items[active]) items[active].removeAttribute("data-active");
      active = -1;
      document.removeEventListener("pointerdown", onOutside, true);
      global.removeEventListener("resize", reflowOnScroll);
      global.removeEventListener("scroll", reflowOnScroll, true);
      if (restoreFocus) btn.focus();
    }
    function onOutside(e) {
      if (!popup.contains(e.target) && !btn.contains(e.target)) close(false);
    }

    function choose(i) {
      if (i < 0 || isDisabled(i)) return;
      items.forEach(function (it, k) { it.setAttribute("aria-selected", k === i ? "true" : "false"); });
      if (valueEl) valueEl.textContent = items[i].textContent.trim();
      root.setAttribute("data-value", items[i].getAttribute("data-value") || "");
      close(true);
      /* 让业务侧能响应选择（原生 select 的 change 语义） */
      var Ctor = global.CustomEvent;
      var ev = Ctor ? new Ctor("fl-combo-change", {
        bubbles: true, detail: {
          index: i, value: items[i].getAttribute("data-value") || "", text: items[i].textContent.trim()
        }
      }) : null;
      if (ev) root.dispatchEvent(ev);
    }

    btn.addEventListener("click", function () {
      if (popup.classList.contains("fl-open")) close(true); else open();
    });

    btn.addEventListener("keydown", function (e) {
      var open_ = popup.classList.contains("fl-open");
      var key = e.key;
      if (!open_) {
        if (key === "ArrowDown" || key === "ArrowUp" || key === "Enter" || key === " ") {
          e.preventDefault(); open();
          if (key === "ArrowUp") setActive(step(items.length, -1));  // 未打开时 Alt/Ctrl+↑ 也落到末项
          return;
        }
        if (key === "Escape") return;
      } else {
        if (key === "Escape") { e.preventDefault(); close(true); return; }
        if (key === "Tab") { close(false); return; }   // 不吞 Tab：正常移出焦点
        if (key === "Enter" || key === " ") { e.preventDefault(); choose(active); return; }
        if (key === "ArrowDown") { e.preventDefault(); setActive(step(active, 1)); return; }
        if (key === "ArrowUp") { e.preventDefault(); setActive(step(active, -1)); return; }
        if (key === "Home") { e.preventDefault(); setActive(step(-1, 1)); return; }
        if (key === "End") { e.preventDefault(); setActive(step(items.length, -1)); return; }
      }
      /* type-ahead：200ms 内累加，跳到首个以该串开头的项 */
      if (key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
        var now = Date.now();
        typed = (now - typedAt < 200 ? typed : "") + key.toLowerCase();
        typedAt = now;
        for (var k = 0; k < items.length; k++) {
          var t = items[k].textContent.trim().toLowerCase();
          if (!isDisabled(k) && t.indexOf(typed) === 0) {
            if (!open_) open();
            setActive(k);
            break;
          }
        }
      }
    });

    items.forEach(function (it, i) {
      it.addEventListener("click", function () { choose(i); });
      it.addEventListener("pointermove", function () { if (!isDisabled(i)) setActive(i); });
    });

    var inst = {
      root: root, btn: btn, popup: popup, items: items,
      open: open, close: close, value: function () {
        var i = selectedIndex();
        return i < 0 ? "" : items[i].getAttribute("data-value") || items[i].textContent.trim();
      }
    };
    root.__flCombo = inst;
    return inst;
  }

  M.combo = {
    init: comboInit,
    auto: function (scope) {
      var nodes = (scope || document).querySelectorAll(".fl-combo");
      var out = [];
      for (var i = 0; i < nodes.length; i++) out.push(comboInit(nodes[i]));
      return out;
    }
  };

  /* 列表辅助：多选模式开关 + 父勾选框半选态同步 */
  M.list = {
    multiselect: function (root, on) {
      var el = typeof root === "string" ? document.querySelector(root) : root;
      if (!el) return null;
      if (on) el.setAttribute("data-multiselect", "");
      else el.removeAttribute("data-multiselect");
      return el;
    },
    /* parentInput：表头「全选」input；items：.fl-listitem 数组 */
    syncParent: function (parentInput, items) {
      if (!parentInput) return;
      var sel = 0;
      for (var i = 0; i < items.length; i++) {
        if (items[i].getAttribute("aria-selected") === "true") sel++;
      }
      parentInput.checked = items.length > 0 && sel === items.length;
      parentInput.indeterminate = sel > 0 && sel < items.length;  // 半选靠 JS 设置，纯属性写不出来
    }
  };

  /* 滑块辅助：把当前值折算成 0..1 的 --fl-slider-pct，供轨道「已填充段」渐变使用
     （纯 CSS 拿不到 range 的值；几何补偿在 CSS 侧，见 --fl-slider-fill）
     键盘与 aria 全部交给原生 input[type=range]，这里不接管 */
  function sliderSync(el) {
    var min = parseFloat(el.min), max = parseFloat(el.max), val = parseFloat(el.value);
    if (isNaN(min)) min = 0;
    if (isNaN(max)) max = 100;
    if (isNaN(val)) val = min;
    var pct = max > min ? (val - min) / (max - min) : 0;
    pct = pct < 0 ? 0 : (pct > 1 ? 1 : pct);
    el.style.setProperty("--fl-slider-pct", pct);   // 不四舍五入：长轨道上 2 位小数会有 1px 级锯齿
  }

  M.slider = {
    sync: sliderSync,
    /* 幂等：重复调用不会重复绑事件 */
    auto: function (scope) {
      var nodes = (scope || document).querySelectorAll(".fl-slider");
      var out = [];
      for (var i = 0; i < nodes.length; i++) {
        var el = nodes[i];
        out.push(el);
        sliderSync(el);
        if (el.getAttribute("data-fl-slider") === "ready") continue;
        el.setAttribute("data-fl-slider", "ready");
        el.addEventListener("input", function (e) { sliderSync(e.currentTarget); });
        el.addEventListener("change", function (e) { sliderSync(e.currentTarget); });
      }
      return out;
    }
  };

  /* 浮层（flyout / contextmenu）：**整个弹层滑入视野**（MenuPopupThemeTransition 的做法：
     行程 = 弹层自身高度 100%，不淡入），关闭反向滑出。
     依据 2026-10-22 16-34-16.mp4（Win11 资源管理器 … 菜单）：菜单从工具栏下边缘一路"长"出来，
     底边扫到底、内容整体下移一个菜单高；首帧文字对比度已满 = 没有淡入。
     滑入方向看放置关系：弹层在触发元素下方 → 从上方滑下来（dir -1），在上方 → 从下方升上来（dir +1）。
     显隐与延迟隐藏由 .fl-overlay 的 transition（含 visibility 0s 延迟）承担，这里只切状态类 */
  /* 把 .fl-flyout 摆到触发元素旁边：优先正下方、右对齐；下方放不下就翻到上方。
     顺带算出滑入方向（菜单在触发元素上方 → dir +1，从下方升上来）。 */
  function placeFlyout(el, anchor) {
    var a = anchor.getBoundingClientRect();
    var w = el.offsetWidth, h = el.offsetHeight, m = 8;
    var below = a.bottom + 4, above = a.top - h - 4;
    var top = (below + h > global.innerHeight - m && above > m) ? above : below;
    el.style.right = "auto";
    el.style.bottom = "auto";
    el.style.top = top + "px";
    el.style.left = Math.max(m, Math.min(a.right - w, global.innerWidth - m - w)) + "px";
    el.dataset.drop = (top + h / 2) < (a.top + a.height / 2) ? "up" : "down";
  }
  function setOverlay(el, open, anchor, opts) {
    if (!el) return el;
    if (open && anchor && anchor.getBoundingClientRect) {
      if (!opts || opts.place !== false) {
        placeFlyout(el, anchor);      // 自己定位（按钮触发的菜单）
      } else {
        /* 页面已经摆好了位置（右键菜单跟着鼠标走），这里只按相对高低定方向。
           注意：关态弹层被 translateY(-100%) 抬起（开合是"整个弹层滑入视野"），
           getBoundingClientRect 拿到的是**加了位移**的位置 —— 必须先把位移减回去再比，
           否则右键菜单会一直判成"在上方"、从下往上滑。 */
        var pr = el.getBoundingClientRect(), ar = anchor.getBoundingClientRect();
        var ty = 0, m = global.getComputedStyle(el).transform;
        if (m && m !== "none") {
          var MM = global.DOMMatrixReadOnly || global.DOMMatrix;
          if (MM) ty = new MM(m).m42 || 0;
        }
        var above = (pr.top - ty + pr.height / 2) < (ar.top + ar.height / 2);
        el.dataset.drop = above ? "up" : "down";
      }
    }
    /* 方向可能刚被改写（这次在按钮下方、上次在上方）：先把**新的关态**刷成已解析样式，
       否则过渡会从旧方向的位移起手（比如明明该从下方升上来，却从上方滑下去）。 */
    void el.offsetHeight;
    el.classList.toggle("fl-open", !!open);
    return el;
  }
  M.flyout = {
    show: function (id, anchor, opts) { return setOverlay(document.getElementById(id), true, anchor, opts); },
    hide: function (id) { return setOverlay(document.getElementById(id), false); },
    toggle: function (id, anchor, opts) {
      var el = document.getElementById(id);
      return el ? setOverlay(el, !el.classList.contains("fl-open"), anchor, opts) : el;
    }
  };

  /* ContentDialog + Smoke 遮罩 */
  var smoke = null;
  var smokeTimer = null;
  M.dialog = {
    show: function (id) {
      if (smokeTimer) { global.clearTimeout(smokeTimer); smokeTimer = null; }
      if (!smoke) {
        smoke = document.createElement("div");
        smoke.className = "fl-smoke-backdrop fl-smoke";
        document.body.appendChild(smoke);
      }
      if (!smoke.classList.contains("fl-open")) {
        var s = smoke;
        global.requestAnimationFrame(function () { s.classList.add("fl-open"); });
      }
      return setOverlay(document.getElementById(id), true);
    },
    hide: function (id) {
      var el = setOverlay(document.getElementById(id), false);
      if (smoke) {
        var s = smoke;
        smoke = null;
        s.classList.remove("fl-open");
        function drop() {
          s.removeEventListener("transitionend", onEnd);
          if (s.parentNode) s.parentNode.removeChild(s);
        }
        function onEnd(e) { if (e.target === s && e.propertyName === "opacity") drop(); }
        s.addEventListener("transitionend", onEnd);
        smokeTimer = global.setTimeout(drop, REDUCED ? 0 : 83 + 80); // 兜底：transitionend 不触发时也能移除
      }
      return el;
    }
  };

  /* 轻提示（toast）：83ms fade in / fade out，自动移除 */
  M.toast = function (text, durationMs) {
    var el = document.createElement("div");
    el.className = "fl-card fl-fade";
    el.style.position = "fixed";
    el.style.bottom = "24px";
    el.style.left = "50%";
    el.style.transform = "translateX(-50%)";
    el.style.zIndex = "60";
    el.style.opacity = "0";
    el.textContent = text;
    document.body.appendChild(el);
    global.requestAnimationFrame(function () { el.style.opacity = "1"; });
    global.setTimeout(function () { el.classList.add("fl-hidden"); }, durationMs || 2000);
    global.setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); },
      (durationMs || 2000) + (REDUCED ? 0 : 83 + 80));
    return el;
  };

  /* 自启：滑块的填充段依赖 --fl-slider-pct，缺省 0 会静默退回「整条轨道一个颜色」
     → 这里按 readyState 兜一次（幂等，作者再手动调 M.slider.auto() 也不会重复绑事件）
     动态插入的滑块仍需作者自己调 M.slider.auto(容器) */
  function sliderBoot() { M.slider.auto(); }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", sliderBoot);
  } else {
    sliderBoot();
  }

  global.M = M;
})(window);
