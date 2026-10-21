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
       up    → 起点在上方（-72px），向下落到 0
       down  → 起点在下方（+72px），向上落到 0
       left  → 起点在左侧（-176px）
       right → 起点在右侧（+176px）
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

    /* 定位：优先向下展开，下方不够且上方更宽裕则翻转；只赋值 left/top（不做 transition） */
    function place() {
      var r = btn.getBoundingClientRect();
      var maxH = parseFloat(global.getComputedStyle(popup).maxHeight) || 504;
      var wantH = Math.min(popup.scrollHeight, maxH);
      var below = global.innerHeight - r.bottom - 8;
      var above = r.top - 8;
      var up = below < wantH && above > below;
      popup.dataset.drop = up ? "up" : "down";
      popup.style.minWidth = Math.max(parseFloat(global.getComputedStyle(root).minWidth) || 0, r.width) + "px";
      popup.style.left = r.left + "px";
      popup.style.maxHeight = Math.min(wantH, up ? above : below) + "px";
      if (up) {
        popup.style.top = "auto";
        popup.style.bottom = (global.innerHeight - r.top + 4) + "px";
      } else {
        popup.style.bottom = "auto";
        popup.style.top = (r.bottom + 4) + "px";
      }
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
