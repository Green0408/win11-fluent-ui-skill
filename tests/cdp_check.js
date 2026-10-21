/* tests/cdp_check.js —— 零依赖 CDP 驱动：真开 Chrome、真点击、真截图、读运行时状态
   跑法：node tests/cdp_check.js
   为什么需要它：静态截图看不到 hover / 展开态 / 转场中的位移符号，只能靠真实交互验证。
   依赖：Node ≥ 22 的全局 WebSocket + fetch（不需要 npm 包）。 */
"use strict";
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const CHROME = process.env.CHROME_PATH ||
  "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9333;
const OUT = path.join(os.tmpdir(), "shots");
const PAGE = "file:///" + path.join(__dirname, "..", "fluent2-tool-starter.html").replace(/\\/g, "/");

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function getWsUrl() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      const j = await r.json();
      if (j.webSocketDebuggerUrl) return j.webSocketDebuggerUrl;
    } catch (_) { /* 还没起来 */ }
    await sleep(200);
  }
  throw new Error("Chrome DevTools 端口未就绪");
}

class CDP {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    ws.addEventListener("message", (e) => {
      const m = JSON.parse(e.data);
      if (m.id && this.pending.has(m.id)) {
        const { resolve, reject } = this.pending.get(m.id);
        this.pending.delete(m.id);
        m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result);
      }
    });
  }
  send(method, params, sessionId) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params: params || {}, sessionId }));
    });
  }
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const userDir = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-profile-"));
  const chrome = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio",
    /* file:// 下每个文件都是 opaque origin，不加这个标志读不到 CSSStyleSheet.cssRules */
    "--allow-file-access-from-files",
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${userDir}`,
    "--window-size=1100,900", "--force-device-scale-factor=2", "about:blank",
  ], { stdio: "ignore" });

  const wsUrl = await getWsUrl();
  const ws = new WebSocket(wsUrl);
  await new Promise((r) => ws.addEventListener("open", r));
  const cdp = new CDP(ws);

  const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
  const S = (m, p) => cdp.send(m, p, sessionId);

  await S("Page.enable");
  await S("Runtime.enable");
  await S("Page.navigate", { url: PAGE });
  await sleep(900);

  const results = [];
  const check = (label, ok, extra) => {
    results.push({ label, ok, extra });
    console.log(`${ok ? "PASS" : "FAIL"}  ${label}${extra ? "   " + extra : ""}`);
  };
  const evaluate = async (expr) => {
    const r = await S("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + " " + JSON.stringify(r.exceptionDetails.exception));
    return r.result.value;
  };
  const shot = async (name) => {
    const { data } = await S("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    const p = path.join(OUT, name + ".png");
    fs.writeFileSync(p, Buffer.from(data, "base64"));
    return p;
  };
  const mouse = (type, x, y, button) => S("Input.dispatchMouseEvent", {
    type, x, y, button: button || "none", clickCount: type === "mousePressed" || type === "mouseReleased" ? 1 : 0,
  });

  /* ---- 0) 外壳布局：整页不滚、只有内容区滚、左导航固定 ---- */
  const layout = await evaluate(`(function(){
    var doc = document.documentElement;
    var page = document.querySelector(".fl-page.fl-current");
    var nav = document.getElementById("nav");
    var navTop = nav.getBoundingClientRect().top;
    page.scrollTop = 240;                     // 只滚内容区
    var after = {
      pageScrollTop: page.scrollTop,
      navTop: nav.getBoundingClientRect().top,
      winScrollY: window.scrollY
    };
    var out = {
      docScrollable: doc.scrollHeight > window.innerHeight + 1,
      pageScrollable: page.scrollHeight > page.clientHeight + 1,
      navFixed: Math.abs(after.navTop - navTop) < 0.5 && after.winScrollY === 0,
      scrolled: after.pageScrollTop > 0,
      shellH: document.querySelector(".fl-shell").getBoundingClientRect().height,
      winH: window.innerHeight
    };
    page.scrollTop = 0;
    return out;
  })()`);
  check("整页不滚（文档没有溢出滚动）", layout.docScrollable === false, JSON.stringify(layout));
  check("内容区可以自己滚", layout.pageScrollable === true && layout.scrolled === true, JSON.stringify(layout));
  check("滚内容区时左侧栏不动、窗口不滚", layout.navFixed === true, JSON.stringify(layout));
  check("外壳高度 = 视口高度（不留整页滚动条）",
    Math.abs(layout.shellH - layout.winH + 32) < 2, `shell=${layout.shellH} win=${layout.winH}（差值为标题栏高度）`);

  /* ---- 1) 转场方向：点导航项上/下，读运行时写入的位移符号 ---- */
  const navBox = async (idx) => evaluate(`(function(){
    var a = document.querySelectorAll(".fl-nav-item[data-page]")[${idx}];
    var r = a.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  })()`);

  const clickAt = async (p) => {
    await mouse("mouseMoved", p.x, p.y);
    await mouse("mousePressed", p.x, p.y, "left");
    await mouse("mouseReleased", p.x, p.y, "left");
  };

  /* 当前在 page-main（导航第 0 项）→ 点第 2 项（设置，更靠下）应从下方进入 */
  await clickAt(await navBox(2));
  await sleep(110);
  await shot("x0-transition-down");   // 转场中段：两页叠放、新页偏下
  const down = await evaluate(`(function(){
    var p = document.getElementById("page-settings");
    return { fromY: p.style.getPropertyValue("--fl-page-from-y"),
             fromX: p.style.getPropertyValue("--fl-page-from-x") };
  })()`);
  await sleep(400);
  check("点下方导航项 → 自下方进入（+shift-y）", /^var\(--fl-page-shift-y\)$/.test(down.fromY), JSON.stringify(down));

  await shot("x1-page-settings");

  /* 再点回第 0 项（条目管理，更靠上）→ 仍必须自下方进入（用户口径：竖向只准从下往上） */
  await clickAt(await navBox(0));
  await sleep(110);
  await shot("x0-transition-up");     // 转场中段：新页仍偏下
  const up = await evaluate(`(function(){
    var p = document.getElementById("page-main");
    return { fromY: p.style.getPropertyValue("--fl-page-from-y") };
  })()`);
  await sleep(400);
  check("点上方导航项 → 仍自下方进入（+shift-y，不允许反向）",
    /^var\(--fl-page-shift-y\)$/.test(up.fromY), JSON.stringify(up));

  /* ---- 1.5) drill 转场是「两拍」：旧页先淡出退场，新页再滑入 ----
     录屏实测（设置应用逐帧）：旧页在 ≈80-170ms 内消失干净，此时新页才开始从行程起点进来。
     两页同时淡入淡出会让新旧文字在中途各半透明地叠在一起，观感是重影。 */
  const drillBtn = await evaluate(`(function(){
    var b = document.querySelector("[data-kind='drill'][data-page]");
    var r = b.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  })()`);
  await clickAt(drillBtn);
  const beat = await evaluate(`(function(){
    var inn = document.querySelector(".fl-page.fl-page-in");
    var out = document.querySelector(".fl-page.fl-page-leaving");
    if (!inn) return null;
    return {
      inOp: +getComputedStyle(inn).opacity,
      inX: +inn.getBoundingClientRect().left.toFixed(1),
      outBg: out ? getComputedStyle(out).backgroundColor : null,
      inDelay: getComputedStyle(inn).animationDelay
    };
  })()`);
  check("drill 第 1 拍：新页还没出现（opacity 0），旧页仍在",
    beat && beat.inOp === 0 && beat.outBg === "rgba(0, 0, 0, 0)",
    JSON.stringify(beat));
  check("drill 入页有 ≈133ms 延迟（0.8×退场时长，两拍略微搭接）",
    beat && parseFloat(beat.inDelay) > 0, beat && beat.inDelay);

  /* 第 1 拍内（≈100ms）：旧页必须在动且在淡出 —— 起手就顿住是「卡顿」的直接来源 */
  await sleep(100);
  const moving = await evaluate(`(function(){
    var out = document.querySelector(".fl-page.fl-page-leaving");
    if (!out) return null;
    return { x: +out.getBoundingClientRect().left.toFixed(1),
             op: +getComputedStyle(out).opacity };
  })()`);
  check("drill 第 1 拍：≈100ms 时旧页已在移动且正在淡出（不许起手顿住）",
    moving && moving.x <= 254 && moving.op > 0.2 && moving.op < 0.9,
    JSON.stringify(moving));

  await sleep(140);
  const beat2 = await evaluate(`(function(){
    var inn = document.querySelector(".fl-page.fl-page-in");
    var out = document.querySelector(".fl-page.fl-page-leaving");
    if (!inn) return null;
    return { outGone: !out, inOp: +getComputedStyle(inn).opacity,
             inX: +inn.getBoundingClientRect().left.toFixed(1) };
  })()`);
  check("drill 第 2 拍：≈240ms 时旧页已退场、新页已在滑（尚未落位）",
    beat2 && beat2.outGone === true && beat2.inOp > 0.2 && beat2.inX > 244,
    JSON.stringify(beat2));
  await sleep(450);
  const settledX = await evaluate(
    `+document.getElementById("page-detail").getBoundingClientRect().left.toFixed(1)`);
  check("drill 结束：新页落位（无残留位移）", Math.abs(settledX - 240) <= 1, String(settledX));
  await evaluate(`(function(){ document.getElementById("btn-back").click(); })()`);
  await sleep(600);

  /* ---- 1.8) 每个页面各自记滚动位置：切走再回来要回到原处 ---- */
  await evaluate(`document.getElementById("page-main").scrollTop = 180`);
  await sleep(120);
  await clickAt(await navBox(2));                 // 去设置页
  await sleep(600);
  const settingsScroll = await evaluate(`document.getElementById("page-settings").scrollTop`);
  await clickAt(await navBox(0));                 // 回到条目管理
  await sleep(600);
  const backScroll = await evaluate(
    `[document.getElementById("page-main").scrollTop, window.scrollY]`);
  check("滚到 180 后切走、再回来仍在 180（每页各记各的）",
    Math.abs(backScroll[0] - 180) <= 2 && backScroll[1] === 0, JSON.stringify(backScroll));
  check("新进的页面从顶部开始（不继承上一页的滚动位置）", settingsScroll === 0, String(settingsScroll));
  await evaluate(`document.getElementById("page-main").scrollTop = 0`);
  await sleep(150);

  /* ---- 2) 列表六档：hover / 选中+hover 的 computed background ---- */
  const rowBox = await evaluate(`(function(){
    var it = document.querySelectorAll("#list .fl-listitem")[1];
    var r = it.getBoundingClientRect();
    return { x: r.left + r.width * 0.5, y: r.top + r.height / 2 };
  })()`);
  const bgOf = (idx) => evaluate(`getComputedStyle(document.querySelectorAll("#list .fl-listitem")[${idx}]).backgroundColor`);
  const restBg = await bgOf(1);
  await mouse("mouseMoved", rowBox.x, rowBox.y);
  await sleep(260);
  const hoverBg = await bgOf(1);
  check("列表 hover 改变底色", restBg !== hoverBg, `${restBg} → ${hoverBg}`);
  await shot("x2-list-hover");

  await clickAt(rowBox);
  await sleep(260);
  const selHoverBg = await bgOf(1);
  check("选中+hover 与仅选中不同（官方反色档）", selHoverBg !== hoverBg, `${hoverBg} → ${selHoverBg}`);
  await mouse("mouseMoved", 5, 5);
  await sleep(260);
  const selBg = await bgOf(1);
  check("选中态底色 = Secondary", selBg !== restBg, `${restBg} → ${selBg}`);

  /* ---- 3) ComboBox：点开、看弹层是否 portal 出去且未被裁、键盘可选中 ---- */
  const comboBox = await evaluate(`(function(){
    var b = document.getElementById("combo-view-btn");
    var r = b.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  })()`);
  await clickAt(comboBox);
  await sleep(300);
  const openState = await evaluate(`(function(){
    var b = document.getElementById("combo-view-btn");
    var p = document.getElementById("combo-view-list");
    var r = p.getBoundingClientRect();
    return { expanded: b.getAttribute("aria-expanded"),
             parent: p.parentElement.tagName,
             pos: getComputedStyle(p).position,
             w: Math.round(r.width), h: Math.round(r.height),
             open: p.classList.contains("fl-open"),
             active: b.getAttribute("aria-activedescendant") };
  })()`);
  check("ComboBox 展开：aria-expanded=true", openState.expanded === "true", openState.expanded);
  check("弹层已 portal 到 body（避免被 overflow:clip 裁切）", openState.parent === "BODY", openState.parent);
  check("弹层 position:fixed", openState.pos === "fixed", openState.pos);
  check("弹层有实际尺寸（未塌陷/未被裁）", openState.w > 60 && openState.h > 60, `${openState.w}×${openState.h}`);

  /* 弹层不许伸到视口外：右侧一旦被窗口裁掉，滚动条正好在裁掉那一侧 —— 表现是"没有滚动条" */
  const bounds = await evaluate(`(function(){
    var p = document.getElementById("combo-view-list");
    var r = p.getBoundingClientRect();
    return { left: Math.round(r.left), right: Math.round(r.right),
             vw: window.innerWidth, vh: window.innerHeight,
             bottom: Math.round(r.bottom) };
  })()`);
  check("弹层不越出视口左右边界（否则右侧滚动条会被窗口裁掉）",
    bounds.left >= 7 && bounds.right <= bounds.vw - 7,
    JSON.stringify(bounds));
  check("弹层不越出视口下边界", bounds.bottom <= bounds.vh - 3, JSON.stringify(bounds));

  /* 4 项的短弹层不该有滚动条：项文字一旦折行、或 maxHeight 与 border-box 语义不匹配，
     弹层都会凭空长出一条滚动条（而那条"没用的滚动条"最扎眼） */
  const shortList = await evaluate(`(function(){
    var pop = document.getElementById("combo-view-list");
    var wrapped = [].some.call(pop.children, function (c) { return c.getBoundingClientRect().height > 40; });
    return { scroll: pop.scrollHeight - pop.clientHeight, h: pop.clientHeight, wrapped: wrapped };
  })()`);
  check("短弹层恰好装下 4 项（不溢出、不出滚动条）",
    shortList.wrapped === false && shortList.scroll <= 1, JSON.stringify(shortList));

  /* 超长选项：弹层被 max-width 挡住、文字走省略号，而不是把弹层撑到屏幕外 */
  const longText = await evaluate(`(function(){
    var pop = document.getElementById("combo-view-list");
    var d = document.createElement("div");
    d.className = "fl-combo-item";
    d.setAttribute("role", "option");
    d.setAttribute("data-tmp", "long");
    d.textContent = "超长选项：" + "这条文字故意写得非常非常长，用来把弹层宽度顶到 max-width 上，".repeat(4) + "然后必须出现省略号";
    pop.appendChild(d);
    window.dispatchEvent(new Event("resize"));       // 触发 re-place
    return new Promise(function (res) {
      requestAnimationFrame(function () {
        var r = pop.getBoundingClientRect();
        var cs = getComputedStyle(d);
        var out = { right: Math.round(r.right), vw: window.innerWidth,
                    overflow: cs.textOverflow, itemScrollW: d.scrollWidth, itemW: d.clientWidth,
                    popClientW: pop.clientWidth, hScroll: pop.scrollWidth - pop.clientWidth };
        d.remove();
        window.dispatchEvent(new Event("resize"));
        res(out);
      });
    });
  })()`);
  check("超长选项被省略号截断（不横向溢出、弹层不出横条）",
    longText.overflow === "ellipsis" && longText.itemScrollW > longText.itemW && longText.hScroll <= 1,
    JSON.stringify(longText));
  check("超长选项下弹层仍不越出视口右边界",
    longText.right <= longText.vw - 7, JSON.stringify(longText));

  /* 滚动条：塞 20 项到弹层里，看它是不是自定义的细滚动条（原生约 15-17px 且带箭头） */
  const comboScroll = await evaluate(`(function(){
    var pop = document.getElementById("combo-view-list");
    var n = 0;
    while (pop.children.length < 20) {
      var d = document.createElement("div");
      d.className = "fl-combo-item";
      d.setAttribute("role", "option");
      d.textContent = "选项 " + (++n + 4);
      pop.appendChild(d);
    }
    var cs = getComputedStyle(pop);
    /* offset-client 同时含左右边框（弹层 2px×2），不扣掉会把滚动条量宽 4px */
    var w = pop.offsetWidth - pop.clientWidth - parseFloat(cs.borderLeftWidth) - parseFloat(cs.borderRightWidth);
    var out = {
      hasScroll: pop.scrollHeight > pop.clientHeight + 2,
      sbw: w,
      cls: pop.className,
      ff: getComputedStyle(pop).scrollbarColor || "",
      maxH: getComputedStyle(pop).maxHeight
    };
    while (pop.children.length > 4) pop.removeChild(pop.lastElementChild);
    return out;
  })()`);
  check("弹层超长时出现滚动", comboScroll.hasScroll === true, `scrollHeight>clientHeight ${comboScroll.hasScroll} maxH=${comboScroll.maxH}`);
  /* headless 默认用 overlay 滚动条（不占布局宽），所以"占宽"这条在 CI 里恒为边框宽、证明力弱；
     改从 CSSOM 里核对规则本身：.fl-scroll 的 ::-webkit-scrollbar 必须设宽 ≤12px，
     thumb 必须有圆角与透明边框（两者缺一，滚动条就退化成原生方块）。 */
  const sbRules = await evaluate(`(function(){
    var out = { width: null, thumbRadius: null, thumbBorder: null, buttons: false };
    /* 规则写在 @supports 里，必须递归进去找（CSSSupportsRule 自己有 cssRules） */
    function walk(rules) {
      for (var j = 0; j < rules.length; j++) {
        var r = rules[j];
        if (r.cssRules && !r.selectorText) { walk(r.cssRules); continue; }
        if (!r.selectorText || r.selectorText.indexOf("fl-scroll") < 0) continue;
        if (/::-webkit-scrollbar$/.test(r.selectorText)) out.width = r.style.width;
        if (/::-webkit-scrollbar-thumb/.test(r.selectorText)) {
          /* 多条规则命中同一伪元素（静止/hover/active），静止态只取第一次给出的值 */
          out.thumbRadius = out.thumbRadius || r.style.borderRadius;
          out.thumbBorder = out.thumbBorder || r.style.borderWidth || r.style.border;
          if (/:hover|:active/.test(r.selectorText)) {
            var bw = r.style.borderWidth;
            if (/:hover/.test(r.selectorText)) out.hoverBorder = bw;
            else out.activeBorder = bw;
          }
        }
        if (/::-webkit-scrollbar-button/.test(r.selectorText)) out.buttons = true;
      }
    }
    for (var i = 0; i < document.styleSheets.length; i++) {
      walk(document.styleSheets[i].cssRules || []);
    }
    return out;
  })()`);
  /* 注意：cdp_check 以 --hide-scrollbars 启动，占宽恒为 0，所以这里只能断言上界；
     真实宽度由 CSSOM 规则那条（width:12px）与 tests/combo_probe.js 的实测量保证 */
  check("滚动条占宽不超过 12px（自定义细条）",
    comboScroll.sbw <= 12, `实际占宽 ${comboScroll.sbw}px`);
  check("滚动条是自定义细条（规则宽度 ≤12px 且去掉箭头按钮）",
    !!sbRules.width && parseFloat(sbRules.width) <= 12 && sbRules.buttons === true,
    `::-webkit-scrollbar{width:${sbRules.width}} button 规则=${sbRules.buttons}`);
  check("滚动条 thumb 是圆头内缩（圆角 + 透明边框做出「细」的视觉）",
    !!sbRules.thumbRadius && !!sbRules.thumbBorder,
    `border-radius:${sbRules.thumbRadius} border:${sbRules.thumbBorder}`);
  /* hover 与拖动态的透明度边框不能收到 <2px，否则 thumb 画满 12px 命中区（"激活后太粗"的来源） */
  const bwNum = (v) => parseFloat(String(v || "0"));
  check("滚动条 hover/拖动态不变粗（透明边框仍 ≥2px，视觉 ≤8px）",
    bwNum(sbRules.hoverBorder) >= 2 && bwNum(sbRules.activeBorder) >= 2,
    `hover:${sbRules.hoverBorder} active:${sbRules.activeBorder}`);
  check("弹层带 fl-scroll 类且设了 Firefox 的 scrollbar-color", /fl-scroll/.test(comboScroll.cls) && !!comboScroll.ff,
    `${comboScroll.cls} | scrollbar-color: ${comboScroll.ff}`);
  /* Chromium 116+ 里标准属性（scrollbar-width/color 非 auto）会让 ::-webkit-scrollbar 全部失效。
     我们靠 @supports selector(::-webkit-scrollbar) 把它们重置回 auto；若哪天被删掉，
     这里会立刻变成 thin，说明伪元素样式已经悄悄失效。 */
  const sbStd = await evaluate(
    `getComputedStyle(document.getElementById("combo-view-list")).scrollbarWidth`);
  check("Chromium 里 scrollbar-width 必须被重置为 auto（否则 webkit 伪元素样式失效）",
    sbStd === "auto", String(sbStd));
  check("键盘高亮项已设置 aria-activedescendant", !!openState.active, String(openState.active));
  await shot("x3-combo-open");

  /* 键盘：↓ 两次 + Enter 选中第三项 */
  for (const key of ["ArrowDown", "ArrowDown"]) {
    await S("Input.dispatchKeyEvent", { type: "keyDown", key, code: "ArrowDown", windowsVirtualKeyCode: 40 });
    await S("Input.dispatchKeyEvent", { type: "keyUp", key, code: "ArrowDown", windowsVirtualKeyCode: 40 });
    await sleep(60);
  }
  await S("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
  await S("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
  await sleep(260);
  const afterKey = await evaluate(`(function(){
    var b = document.getElementById("combo-view-btn");
    return { text: b.querySelector(".fl-combo-value").textContent.trim(),
             expanded: b.getAttribute("aria-expanded"),
             selected: document.querySelectorAll("#combo-view-list .fl-combo-item[aria-selected='true']").length };
  })()`);
  check("键盘 ↑↓ + Enter 能改变选中值", afterKey.text === "紧凑", afterKey.text);
  check("选择后弹层关闭", afterKey.expanded === "false", afterKey.expanded);
  check("选中项唯一", afterKey.selected === 1, String(afterKey.selected));

  /* ---- 4) 勾号是 SVG 描画而非文本字符 ---- */
  const glyph = await evaluate(`(function(){
    var svg = document.querySelector(".fl-check-glyph");
    var cs = getComputedStyle(svg.querySelector("path"));
    return { tag: svg.tagName, dash: cs.strokeDasharray, dur: cs.transitionDuration };
  })()`);
  check("勾号是 <svg> 且带 dash 过渡", glyph.tag.toLowerCase() === "svg" && glyph.dash !== "none", JSON.stringify(glyph));

  /* ---- 4.4) 强调色的主题档位：暗主题必须比亮主题浅（XAML 暗=Light2 / 亮=Dark1）---- */
  const themeAccent = await evaluate(`(function(){
    var root = document.documentElement;
    var prev = root.getAttribute("data-theme");
    function lum(h){
      h = (h || "").trim().replace("#", "");
      var c = [0, 2, 4].map(function (i) {
        var v = parseInt(h.substr(i, 2), 16) / 255;
        return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
    }
    function val(){ return getComputedStyle(root).getPropertyValue("--fl-accent-fill").trim(); }
    root.setAttribute("data-theme", "dark");  var d = val();
    root.setAttribute("data-theme", "light"); var l = val();
    root.setAttribute("data-theme", prev || "dark");
    return { dark: d, light: l, ld: +lum(d).toFixed(3), ll: +lum(l).toFixed(3) };
  })()`);
  check("强调色：暗主题比亮主题更浅（XAML 暗=Light2 / 亮=Dark1，不是写反）",
    themeAccent.ld > themeAccent.ll + 0.05, JSON.stringify(themeAccent));

  /* ---- 4.5) 按钮文字必须居中：用 Range 量文本盒，和按钮盒比中心 ----
     曾经的 padding 是「上 12 / 下 8」（误把 XAML ButtonPadding 11,5,11,6 的语义套进 flex 盒），
     文字整体下沉 2px。这类偏移肉眼"觉得怪"但说不清，必须用数值锁。 */
  const btnBox = await evaluate(`(function(){
    var ids = ["btn-refresh", "btn-open-detail", "btn-dialog-cancel"];
    var out = [];
    for (var i = 0; i < ids.length; i++) {
      var b = document.getElementById(ids[i]);
      if (!b) continue;
      var r = b.getBoundingClientRect();
      if (!r.width) continue;                       // 隐藏页里的按钮跳过
      var rg = document.createRange(); rg.selectNodeContents(b);
      var t = rg.getBoundingClientRect();
      out.push({ id: ids[i],
                 dx: +((t.left + t.width / 2) - (r.left + r.width / 2)).toFixed(2),
                 dy: +((t.top + t.height / 2) - (r.top + r.height / 2)).toFixed(2),
                 h: +r.height.toFixed(1) });
    }
    return out;
  })()`);
  check("按钮文字居（|dx|,|dy| ≤ 0.5px）",
    btnBox.length > 0 && btnBox.every((b) => Math.abs(b.dx) <= 0.5 && Math.abs(b.dy) <= 0.5),
    JSON.stringify(btnBox));

  /* ---- 5) 滑块已填充段：--fl-slider-pct 跟随值、轨道是双段渐变、hover/pressed/禁用四档配色 ---- */
  await clickAt(await navBox(2));   // 滑块在设置页
  await sleep(420);
  const sl = await evaluate(`(function(){
    var el = document.getElementById("set-slider");
    function pct() { return getComputedStyle(el).getPropertyValue("--fl-slider-pct").trim(); }
    function set(v) { el.value = v; el.dispatchEvent(new Event("input", { bubbles: true })); }
    var out = {};
    set(0);   out.p0   = pct();
    set(40);  out.p40  = pct();
    out.fill40 = getComputedStyle(el).getPropertyValue("--fl-slider-fill").replace(/\\s+/g, " ").trim();
    set(100); out.p100 = pct();
    var track = [];
    for (var i = 0; i < document.styleSheets.length; i++) {
      var rules = document.styleSheets[i].cssRules || [];
      for (var j = 0; j < rules.length; j++) {
        var r = rules[j];
        if (r.selectorText && r.selectorText.indexOf("::-webkit-slider-runnable-track") >= 0 &&
            r.style && r.style.backgroundImage) track.push(r.style.backgroundImage);
      }
    }
    out.track = track;
    set(40);
    return out;
  })()`);
  const trackAll = (sl.track || []).join(" ");
  check("滑块 pct 跟随值（0/40/100 → 0/0.4/1）",
    sl.p0 === "0" && sl.p40 === "0.4" && sl.p100 === "1", JSON.stringify([sl.p0, sl.p40, sl.p100]));
  check("轨道是双段渐变，且 LTR/RTL 两个方向都在（不是整条单色）",
    /to right/.test(trackAll) && /to left/.test(trackAll) && /var\(--fl-slider-fill\)/.test(trackAll),
    String(trackAll).replace(/\s+/g, " ").slice(0, 80));
  check("填充宽走半 thumb 补偿 calc（含 100% 与 thumb 宽）",
    /100%/.test(sl.fill40) && /12px/.test(sl.fill40), sl.fill40);

  /* 像素判不出「填充宽到底多宽」（被 4px 外环遮住），所以在这里读渐变解析后的 px 停点：
     把同一条 calc 挂到一个等宽探针 div 上，浏览器会把 var() 代进去并算出 px。 */
  const probe = await evaluate(`(function(){
    var src = document.getElementById("set-slider");
    var w = src.getBoundingClientRect().width;
    var wrap = document.createElement("div");
    wrap.className = "fl-slider";
    wrap.style.cssText = "--fl-slider-pct:0.3;display:block;height:4px;width:" + w + "px";
    var inner = document.createElement("div");
    /* 把同一个 calc 当成宽度用，浏览器会把它算成 px（放在 background 停点里只会剩 calc(30% + 2.4px)） */
    inner.style.cssText = "width:var(--fl-slider-fill);height:1px";
    wrap.appendChild(inner);
    document.body.appendChild(wrap);
    var fw = inner.getBoundingClientRect().width;
    var pct = getComputedStyle(inner).getPropertyValue("--fl-slider-pct").trim();
    wrap.remove();
    return { w: w, fill: fw, pct: pct };
  })()`);
  const want = 6 + 0.3 * (probe.w - 12);
  check("填充宽 = 半 thumb + 0.3×(轨道宽-12)（实测解析后的宽度）",
    Math.abs(probe.fill - want) <= 0.6,
    `实测=${probe.fill.toFixed(1)} 期望=${want.toFixed(1)} 轨道宽=${probe.w} pct=${probe.pct}`);

  const sb = await evaluate(`(function(){
    var r = document.getElementById("set-slider").getBoundingClientRect();
    return { x: r.left + r.width * 0.5, y: r.top + r.height / 2 };
  })()`);
  const accent = () => evaluate(`getComputedStyle(document.getElementById("set-slider")).getPropertyValue("--fl-slider-accent").trim()`);
  /* 把当前档位色真实解析成 rgb()，用来判断"有没有 alpha" —— 光看变量字符串看不出透不透明 */
  const accentRGB = () => evaluate(`(function(){
    var v = getComputedStyle(document.getElementById("set-slider"))
              .getPropertyValue("--fl-slider-accent").trim();
    var d = document.createElement("div");
    d.style.backgroundColor = v;
    document.body.appendChild(d);
    var c = getComputedStyle(d).backgroundColor;
    d.remove();
    return c;
  })()`);
  /* color-mix 解析出来是 color(srgb r g b) 这种无 alpha 形式，不能只看是否以 rgb( 开头 */
  const opaque = (c) =>
    !/rgba\([^)]*,\s*0?\.\d+\s*\)/.test(c) && !/\/\s*0?\.\d+\s*\)/.test(c);
  const restAccent = await accent();
  const restRGB = await accentRGB();
  await mouse("mouseMoved", sb.x, sb.y);
  await sleep(140);
  const hoverAccent = await accent();
  const hoverRGB = await accentRGB();
  await mouse("mousePressed", sb.x, sb.y, "left");
  await sleep(140);
  const pressAccent = await accent();
  const pressRGB = await accentRGB();
  await mouse("mouseReleased", sb.x, sb.y, "left");
  await mouse("mouseMoved", 5, 5);
  await sleep(340);
  check("滑块填充段 hover/pressed 逐档变色（Default→Secondary→Tertiary）",
    restAccent !== hoverAccent && hoverAccent !== pressAccent && restAccent !== pressAccent,
    [restAccent, hoverAccent, pressAccent].join(" / "));
  /* 用户反馈："悬停时滑块变透明了" —— 根因是档位色用了 alpha(0.9/0.8)，透出底下的灰环/卡片。
     修法改成不透明混色，这里锁死三态都必须 alpha=1。 */
  check("滑块三态都是不透明色（不靠 alpha 变淡）",
    opaque(restRGB) && opaque(hoverRGB) && opaque(pressRGB),
    [restRGB, hoverRGB, pressRGB].join(" / "));
  await shot("x5-slider");

  const dis = await evaluate(`(function(){
    var el = document.getElementById("set-slider");
    el.disabled = true;
    var cs = getComputedStyle(el);
    var out = { accent: cs.getPropertyValue("--fl-slider-accent").trim(),
                rest: cs.getPropertyValue("--fl-slider-rest").trim() };
    el.disabled = false;
    return out;
  })()`);
  check("滑块禁用改用 Disabled 档配色", dis.accent !== restAccent && !!dis.rest, JSON.stringify(dis));

  /* ---- 6) reduced-motion 下终态正确 ---- */
  await S("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
  await sleep(200);
  const rm = await evaluate(`(function(){
    var on = document.querySelector("#set-check");
    var off = document.querySelector("#set-check-off");
    var g = function (i) { return getComputedStyle(i.parentElement.querySelector(".fl-check-glyph path")).strokeDashoffset; };
    return { on: g(on), off: g(off), box: getComputedStyle(on.parentElement.querySelector(".fl-box")).backgroundColor };
  })()`);
  check("reduced-motion 下已勾选勾号到位", parseFloat(rm.on) === 0, rm.on);
  check("reduced-motion 下未勾选勾号仍隐藏", parseFloat(rm.off) > 0, rm.off);
  await shot("x4-reduced");

  /* ---- 汇总 ---- */
  const failed = results.filter((r) => !r.ok);
  console.log(`\n结果：${results.length - failed.length}/${results.length} 通过`);
  ws.close();
  chrome.kill();
  if (failed.length) {
    console.log("失败项：" + failed.map((f) => f.label).join("；"));
    process.exit(1);
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
