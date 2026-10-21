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
  var PAGE_MS = 283; // 页面转场：实测派生档（tokens --fl-dur-page），非官方 83/167/250/333
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
       up    → 起点在上方（-72px），向下落到 0
       down  → 起点在下方（+72px），向上落到 0
       left  → 起点在左侧（-176px）
       right → 起点在右侧（+176px）
     forward / back 是逻辑方向，按轴映射（drill→right/left，nav→down/up），
     与本文件旧调用点、M.back() 完全兼容。
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
     （旧实现只判 dir === "back"，其余一律 +1，导致竖向永远"从下方进入"且 dir:'top' 无报错） */
  function shiftOf(kind, dir) {
    var d = DIR[dir];
    if (!d) return null;
    return { axis: d.axis || axisOfKind(kind), sign: d.sign };
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

  /* 导航项在侧栏中的先后序：给竖向转场定符号（点更靠上的项 → 新页自上方进入） */
  function navOrder() {
    var els = document.querySelectorAll(".fl-nav-item[data-page]");
    var map = {}, i;
    for (i = 0; i < els.length; i++) map[els[i].getAttribute("data-page")] = i;
    return map;
  }

  function has(map, key) {
    return key != null && Object.prototype.hasOwnProperty.call(map, key);
  }

  /* 方向解析，四级退化：显式 dir → 导航项先后序 → 页面栈（目标是上一页=back）→ 缺省 forward
     返回 {axis, sign, dir, isBack}；isBack 只决定页面栈语义，与物理方向彻底解耦 */
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
      var order = navOrder();
      if (has(order, pageId) && has(order, curId) && order[pageId] !== order[curId]) {
        var d = order[pageId] < order[curId] ? "up" : "down"; // 点靠上的项 → 自上方进入
        s = shiftOf(kind, d);
        return { axis: s.axis, sign: s.sign, dir: d, isBack: false };
      }
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

  /* 页面转场：两轴 × 四向（实测派生 283ms；drill 水平 176px / nav 垂直 72px）
     kind: "nav"（一级导航，点侧栏）| "drill"（二级下钻，点内容区入口）
     dir : "forward" | "back" | "up" | "down" | "left" | "right"
           缺省时按「导航项先后序 → 页面栈」自动推断（点上面那条 → 内容从上方进入）
     两页由 CSS 放在同一网格单元里重叠（不上下堆叠），转场期锁内容区高度，全程无布局跳变。
     用法：M.transitionTo("page-detail", { kind: "drill" })
           M.transitionTo("page-b")                        // nav + 自动定符号
           M.transitionTo("page-x", { dir: "up" })          // 显式指定入场方位 */
  M.transitionTo = function (pageId, opts) {
    var next = document.getElementById(pageId);
    if (!next) return null;
    if (next.classList.contains("fl-current") && !next.classList.contains("fl-page-leaving")) return next;

    opts = opts || {};
    var kind = opts.kind === "drill" ? "drill" : "nav";
    var cur = document.querySelector(".fl-page.fl-current");
    var host = next.parentElement;
    var gen = ++pageGen;

    if (!pageStack.length && cur && cur.id) pageStack = [cur.id];
    var shift = resolveShift(kind, opts.dir, pageId, cur ? cur.id : null);

    settlePages();                 // 先清上一轮残留（含位移变量），否则连点时符号会串
    applyShift(next, cur, shift.axis, shift.sign);
    void next.offsetWidth;         // 单次 reflow：让「移除类 → 添加类」真实发生，动画才会重播

    if (REDUCED) {                 // 无障碍：瞬时切换，不做位移与淡入淡出
      if (cur) cur.classList.remove("fl-current");
      if (host) host.style.minHeight = "";
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
    if (host) { // 锁高度 = max(旧页, 新页)：旧页移除的瞬间容器不收缩，避免二次跳变
      host.style.minHeight = Math.max(cur ? cur.offsetHeight : 0, next.offsetHeight) + "px";
    }
    M.stagger(next); // 入场页的元素分批入场与页面入场同步启动（否则隐藏页里的 .fl-entrance 永不显形）
    recordStack(pageId, shift.isBack);

    onAnimEnd(cur, gen, PAGE_MS, function () {
      if (cur) cur.classList.remove("fl-page-leaving", "fl-page-out");
    }, PAGE_ANIM_OUT);
    onAnimEnd(next, gen, PAGE_MS, function () {
      next.classList.remove("fl-page-in");
      if (host) host.style.minHeight = "";
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

  /* 列表/卡片分批入场：.fl-entrance + 83ms 步进、上限 333ms
     延迟写进 --fl-stagger-delay（只影响本动画的 animation-delay），不污染 hover/active 过渡 */
  M.stagger = function (container, stepMs) {
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

  /* 浮层（flyout / contextmenu）：开 = point 入、关 = soft 出（官方 Consistent：同入口同方式开合）
     显隐与延迟隐藏由 .fl-overlay 的 transition（含 visibility 0s 延迟）承担，这里只切状态类 */
  function setOverlay(el, open) {
    if (!el) return el;
    el.classList.toggle("fl-open", !!open);
    return el;
  }
  M.flyout = {
    show: function (id) { return setOverlay(document.getElementById(id), true); },
    hide: function (id) { return setOverlay(document.getElementById(id), false); },
    toggle: function (id) {
      var el = document.getElementById(id);
      return el ? setOverlay(el, !el.classList.contains("fl-open")) : el;
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

  global.M = M;
})(window);
