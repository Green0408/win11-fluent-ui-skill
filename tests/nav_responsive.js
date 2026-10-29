/* tests/nav_responsive.js —— 导航响应式三档 × 开合状态（对应 XAML NavigationView PaneDisplayMode=Auto）

官方规范（learn.../design/controls/navigationview + NavigationView.cpp UpdateAdaptiveLayout）：
  · Auto：≥1008px  Expanded（240 并排）；641~1007 Compact；≤640 Minimal
  · Compact 关闭 = 48 图标列（CompactPaneLength），打开 = 240 覆盖内容（CompactOverlay）
  · Expanded 关闭 = 48 图标列（CompactInline，clip 只露 48），打开 = 240 并排；
    展开/收起 = clip 48↔240 与内容 margin 48↔240 同步 250ms（推挤），不是 width 过渡
  · Minimal 关闭 = 收在左侧外，打开 = 240 覆盖 + Smoke
  · 换档：进入 Expanded 按用户意图打开（手动关过则不打开）；Compact/Minimal 一律关闭
  · 覆盖层里选中项 / 点遮罩 / Esc 关闭

判据：
  ① 三档 + 每种开合的可见宽度、内容让位、文字显隐
  ② 图标中心在展开/紧凑两档一致（官方图标盒 40 → 中心 24）
  ③ Compact 打开是覆盖层：pane 240、内容左边界仍 48（不重排）、遮罩出现
  ④ Expanded 收起是 48 图标列（clip，不是 0），浮动汉堡不出现；展开/收起有 clip + margin 动画
  ⑤ Minimal 打开/关闭内容左边界都不动（40）
  ⑥ 选中项/遮罩/Esc 关闭覆盖层；手动关的意图跨档保留
  ⑦ 指示条在换档后仍贴当前项

跑法：node tests/nav_responsive.js     （退出码 0 = 通过） */
"use strict";
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const CHROME = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9375;
const PAGE = "file:///" + path.join(__dirname, "..", "fluent2-tool-starter.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let pass = 0, fail = 0;
function check(name, ok, detail) {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}   ${detail === undefined ? "" : detail}`);
  ok ? pass++ : fail++;
}

async function wsUrl() {
  for (let i = 0; i < 60; i++) {
    try {
      const j = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json();
      if (j.webSocketDebuggerUrl) return j.webSocketDebuggerUrl;
    } catch (_) {}
    await sleep(200);
  }
  throw new Error("DevTools 端口未就绪");
}

class CDP {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.pending = new Map();
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

(async () => {
  const userDir = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-nav-"));
  const chrome = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--mute-audio", "--allow-file-access-from-files",
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${userDir}`,
    "--window-size=1200,800", "--force-device-scale-factor=1", "about:blank",
  ], { stdio: "ignore" });

  const ws = new WebSocket(await wsUrl());
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  const cdp = new CDP(ws);
  const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
  const S = (m, p) => cdp.send(m, p, sessionId);
  const evalJs = async (expr) =>
    (await S("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true })).result.value;

  await S("Page.enable"); await S("Runtime.enable");
  await S("Page.navigate", { url: PAGE });
  await sleep(1200);

  const setW = async (w) => {
    await S("Emulation.setDeviceMetricsOverride", {
      width: w, height: 800, deviceScaleFactor: 1, mobile: false,
    });
    await sleep(320); /* 等 ResizeObserver + 一次布局 */
  };

  /* 一次把三档要看的量全取出来 */
  const snap = () => evalJs(`(function(){
    var nav = document.querySelector(".fl-nav");
    var item = nav.querySelector(".fl-nav-item");
    var icon = item && item.querySelector(".fl-nav-icon");
    var label = item && item.querySelector(".fl-nav-label");
    var ind = nav.querySelector('.fl-nav-ind[data-role="pill"]') || nav.querySelector(".fl-nav-ind");
    var floatBtn = document.querySelector(".fl-nav-toggle-float");
    var paneBtn = nav.querySelector(".fl-nav-panehead .fl-nav-toggle");
    var scrim = document.querySelector(".fl-nav-scrim");
    var content = document.querySelector(".fl-content-layer");
    var page = document.querySelector(".fl-page.fl-current");
    var nr = nav.getBoundingClientRect();
    var ir = item ? item.getBoundingClientRect() : null;
    var kr = icon ? icon.getBoundingClientRect() : null;
    var lr = label ? label.getBoundingClientRect() : null;
    var clip = getComputedStyle(nav).clipPath || "none";
    var cm = /inset\\(([^)]*)\\)/.exec(clip);
    var insets = cm ? cm[1].trim().split(/\\s+/).map(parseFloat) : null;
    return {
      mode: nav.dataset.navMode,
      open: nav.dataset.navOpen,
      navW: +nr.width.toFixed(1),
      navLeft: +nr.left.toFixed(1),
      navVis: getComputedStyle(nav).visibility,
      itemW: ir ? +ir.width.toFixed(1) : null,
      itemH: ir ? +ir.height.toFixed(1) : null,
      labelShown: label ? (getComputedStyle(label).display !== "none" && !!lr && lr.width > 2) : false,
      iconCenter: kr ? +(kr.left + kr.width / 2 - nr.left).toFixed(1) : null,
      indTop: ind && ir ? +(ind.getBoundingClientRect().top + ind.getBoundingClientRect().height / 2
                          - (ir.top + ir.height / 2)).toFixed(1) : null,
      contentLeft: content ? +content.getBoundingClientRect().left.toFixed(1) : null,
      pageLeft: page ? +page.getBoundingClientRect().left.toFixed(1) : null,
      clipRight: insets ? insets[1] : null,
      clipRaw: clip,
      floatShown: floatBtn ? getComputedStyle(floatBtn).display !== "none" : false,
      scrimOp: scrim ? +(+getComputedStyle(scrim).opacity).toFixed(2) : null,
      scrimVis: scrim ? getComputedStyle(scrim).visibility : null,
      toggleLabel: paneBtn ? paneBtn.getAttribute("aria-label") : null,
      toggleExpanded: paneBtn ? paneBtn.getAttribute("aria-expanded") : null,
      itemLabel: item ? item.getAttribute("aria-label") : null,
      pageId: page ? page.id : null
    };
  })()`);

  const clickX = async (sel) => {
    const p = await evalJs(`(function(){
      var b = document.querySelector(${JSON.stringify(sel)});
      if (!b) return null;
      var r = b.getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height };
    })()`);
    if (!p || p.w < 1 || p.h < 1) throw new Error("不可点击：" + sel + " " + JSON.stringify(p));
    for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) {
      await S("Input.dispatchMouseEvent", {
        type, x: p.x, y: p.y, button: type === "mouseMoved" ? "none" : "left", clickCount: 1,
      });
    }
    await sleep(360);
  };
  const clickAt = async (x, y) => {
    for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) {
      await S("Input.dispatchMouseEvent", {
        type, x, y, button: type === "mouseMoved" ? "none" : "left", clickCount: 1,
      });
    }
    await sleep(360);
  };
  const keyEsc = async () => {
    await S("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
    await sleep(360);
  };

  /* ---------- ① 1200 = Expanded 打开：240 并排 ---------- */
  await setW(1200);
  let s = await snap();
  check("1200px → expanded 打开：pane 240 并排、内容从 240 起",
    s.mode === "expanded" && s.open === "1" && Math.abs(s.navW - 240) < 1.5 &&
    Math.abs(s.contentLeft - 240) < 1.5 && s.labelShown,
    `mode=${s.mode} open=${s.open} nav=${s.navW} content=${s.contentLeft}`);
  check("expanded：汉堡名称/展开态 + 导航项 aria-label",
    s.toggleLabel === "关闭导航" && s.toggleExpanded === "true" && s.itemLabel === "条目管理",
    `label=${s.toggleLabel} expanded=${s.toggleExpanded} item=${s.itemLabel}`);
  check("expanded：浮动汉堡隐藏", !s.floatShown, `float=${s.floatShown}`);

  /* ---------- ② Expanded 收起 = 48 图标列（clip，不是 0） ---------- */
  await clickX(".fl-nav-panehead .fl-nav-toggle");
  s = await snap();
  check("expanded 点汉堡：clip 收成 48 图标列（不是宽 0），内容从 48 起",
    s.mode === "expanded" && s.open === "0" && Math.abs(s.contentLeft - 48) < 1.5 &&
    Math.abs(s.navW - 240) < 1.5 && Math.abs(s.clipRight - 192) < 1.5 &&
    s.floatShown === false,
    `nav=${s.navW} content=${s.contentLeft} clipR=${s.clipRight} float=${s.floatShown}`);
  check("expanded 收起：项宽 40、文字隐藏、汉堡名称变“打开导航”",
    Math.abs(s.itemW - 40) < 1.5 && !s.labelShown && s.toggleLabel === "打开导航" &&
    s.toggleExpanded === "false",
    `item=${s.itemW} labelShown=${s.labelShown} aria=${s.toggleLabel}/${s.toggleExpanded}`);
  /* 展开动画：clip 与内容 margin 同步；在 click 后立刻抓 transition */
  const expandAnim = await evalJs(`(function(){
    var nav = document.querySelector(".fl-nav");
    var content = document.querySelector(".fl-content-layer");
    var btn = document.querySelector(".fl-nav-panehead .fl-nav-toggle");
    function list(el){ return el.getAnimations().map(function(a){
      return { p: a.transitionProperty, d: a.effect.getTiming().duration, e: a.effect.getTiming().easing };
    }); }
    btn.click();
    return { nav: list(nav), content: list(content) };
  })()`);
  await sleep(360);
  s = await snap();
  check("expanded 再点汉堡：回到 240，内容回到 240",
    s.open === "1" && Math.abs(s.navW - 240) < 1.5 && Math.abs(s.contentLeft - 240) < 1.5,
    `nav=${s.navW} content=${s.contentLeft}`);
  const expClipTr = expandAnim.nav.find((a) => a.p === "clip-path");
  const expMarginTr = expandAnim.content.find((a) => a.p === "margin-left");
  check("expanded 展开动画：clip-path + margin-left 同 250ms / ControlFastOutSlowIn，且无 width 过渡",
    !!expClipTr && !!expMarginTr && expClipTr.d === 250 && expMarginTr.d === 250 &&
    /cubic-bezier\(0(\.\d+)?, ?0, ?0, ?1\)/.test(expClipTr.e) &&
    /cubic-bezier\(0(\.\d+)?, ?0, ?0, ?1\)/.test(expMarginTr.e) &&
    !expandAnim.nav.some((a) => a.p === "width") &&
    !expandAnim.content.some((a) => a.p === "width"),
    `${expClipTr ? expClipTr.d : "—"}/${expMarginTr ? expMarginTr.d : "—"}ms ` +
    `${expClipTr ? expClipTr.e : ""} ${expMarginTr ? expMarginTr.e : ""}`);

  /* ---------- ③ 800 = Compact：关 48 图标列 / 开 240 覆盖 ---------- */
  await setW(800);
  s = await snap();
  check("800px → compact 关闭：48 图标列、内容从 48 起、浮动汉堡隐藏",
    s.mode === "compact" && s.open === "0" && Math.abs(s.contentLeft - 48) < 1.5 &&
    Math.abs(s.itemW - 40) < 1.5 && !s.labelShown && !s.floatShown &&
    Math.abs(s.clipRight - 192) < 1.5,
    `mode=${s.mode} open=${s.open} content=${s.contentLeft} item=${s.itemW} clipR=${s.clipRight}`);

  /* 点汉堡，立刻看过渡：clip-path 250ms / 标准曲线，且没有 width 过渡 */
  const anim = await evalJs(`(function(){
    var nav = document.querySelector(".fl-nav");
    var btn = document.querySelector(".fl-nav-panehead .fl-nav-toggle");
    btn.click();
    return nav.getAnimations().map(function(a){
      return { p: a.transitionProperty, d: a.effect.getTiming().duration, e: a.effect.getTiming().easing };
    });
  })()`);
  await sleep(360);
  s = await snap();
  const clipTr = anim.find((a) => a.p === "clip-path");
  check("compact 点汉堡：打开为 240 覆盖层（不是 48 列）",
    s.mode === "compact" && s.open === "1" && Math.abs(s.navW - 240) < 1.5 &&
    Math.abs(s.navLeft) < 1.5 && s.labelShown && s.itemW > 150,
    `open=${s.open} nav=${s.navW} left=${s.navLeft} item=${s.itemW}`);
  check("compact 打开：内容左边界仍 48（覆盖层不推正文）",
    Math.abs(s.contentLeft - 48) < 1.5, `content=${s.contentLeft}`);
  check("compact 打开：clip 放开 + 遮罩出现 + 名称变“关闭导航”",
    s.clipRight !== null && s.clipRight < 0 && s.scrimOp === 1 && s.scrimVis === "visible" &&
    s.toggleLabel === "关闭导航",
    `clipR=${s.clipRight} scrim=${s.scrimOp} label=${s.toggleLabel}`);
  check("compact 打开过渡：clip-path 250ms / ControlFastOutSlowIn，且无 width 过渡",
    !!clipTr && clipTr.d === 250 && /cubic-bezier\(0(\.\d+)?, ?0, ?0, ?1\)/.test(clipTr.e) &&
    !anim.some((a) => a.p === "width"),
    clipTr ? `${clipTr.d}ms ${clipTr.e}` : JSON.stringify(anim));

  /* ---------- ④ 选中项关闭覆盖层 ---------- */
  await clickX('.fl-nav-item[data-page="page-grid"]');
  s = await snap();
  check("compact 覆盖层里选中项：pane 收起回 48 列、遮罩消失、页面切换",
    s.open === "0" && Math.abs(s.contentLeft - 48) < 1.5 && s.scrimOp === 0 &&
    s.pageId === "page-grid" && Math.abs(s.itemW - 40) < 1.5,
    `open=${s.open} content=${s.contentLeft} scrim=${s.scrimOp} page=${s.pageId}`);

  /* ---------- ⑤ Esc / 遮罩关闭 ---------- */
  await clickX(".fl-nav-panehead .fl-nav-toggle");
  await keyEsc();
  s = await snap();
  check("compact 覆盖层：Esc 关闭", s.open === "0" && s.scrimOp === 0, `open=${s.open}`);
  await clickX(".fl-nav-panehead .fl-nav-toggle");
  await clickAt(760, 300); /* 覆盖层右侧的遮罩区 */
  s = await snap();
  check("compact 覆盖层：点遮罩关闭", s.open === "0" && s.scrimOp === 0, `open=${s.open}`);

  /* ---------- ⑥ 500 = Minimal：收起 / 覆盖，内容不动 ---------- */
  await setW(500);
  s = await snap();
  check("500px → minimal 收起：pane 藏起、浮动汉堡出现、内容从 40 起",
    s.mode === "minimal" && s.open === "0" && s.navVis === "hidden" &&
    s.floatShown && Math.abs(s.pageLeft - 40) < 1.5,
    `mode=${s.mode} open=${s.open} vis=${s.navVis} float=${s.floatShown} page=${s.pageLeft}`);
  await clickX(".fl-nav-toggle-float");
  s = await snap();
  check("minimal 点浮动汉堡：240 覆盖层，内容左边界仍 40（不横跳）",
    s.open === "1" && Math.abs(s.navW - 240) < 1.5 && s.scrimOp === 1 &&
    Math.abs(s.pageLeft - 40) < 1.5,
    `open=${s.open} nav=${s.navW} scrim=${s.scrimOp} page=${s.pageLeft}`);
  await clickX('.fl-nav-item[data-page="page-settings"]');
  s = await snap();
  check("minimal 选中项：覆盖层收起、浮动汉堡回来",
    s.open === "0" && s.navVis === "hidden" && s.floatShown && s.pageId === "page-settings",
    `open=${s.open} vis=${s.navVis} float=${s.floatShown} page=${s.pageId}`);

  /* ---------- ⑦ 换档：minimal → expanded 默认重新打开 ---------- */
  await setW(1200);
  s = await snap();
  check("minimal 选中项（轻关闭）后回 1200：expanded 重新打开 240",
    s.mode === "expanded" && s.open === "1" && Math.abs(s.navW - 240) < 1.5,
    `open=${s.open} nav=${s.navW}`);

  /* ---------- ⑧ 手动关的意图跨档保留 ---------- */
  await clickX(".fl-nav-panehead .fl-nav-toggle");   /* 手动收起 → wasForceClosed */
  await setW(800);
  await setW(1200);
  s = await snap();
  check("expanded 手动收起后 1200→800→1200：仍是 48 图标列（不自动弹开）",
    s.mode === "expanded" && s.open === "0" && Math.abs(s.contentLeft - 48) < 1.5 &&
    Math.abs(s.clipRight - 192) < 1.5,
    `open=${s.open} content=${s.contentLeft} clipR=${s.clipRight}`);
  await clickX(".fl-nav-panehead .fl-nav-toggle");   /* 手动打开，清 wasForceClosed */
  s = await snap();
  check("手动打开后回到 240", s.open === "1" && Math.abs(s.navW - 240) < 1.5, `nav=${s.navW}`);

  /* ---------- ⑨ 换档自动规则：expanded→compact 关；compact→expanded 开 ---------- */
  await setW(800);
  s = await snap();
  check("1200 开着 → 800：compact 自动关闭（48 列）",
    s.mode === "compact" && s.open === "0" && Math.abs(s.contentLeft - 48) < 1.5,
    `open=${s.open} content=${s.contentLeft}`);
  await clickX(".fl-nav-panehead .fl-nav-toggle");   /* compact 打开覆盖层 */
  await setW(1200);
  s = await snap();
  check("800 覆盖层开着 → 1200：变 expanded 并排 240（内容从 240 起）",
    s.mode === "expanded" && s.open === "1" && Math.abs(s.navW - 240) < 1.5 &&
    Math.abs(s.contentLeft - 240) < 1.5,
    `open=${s.open} nav=${s.navW} content=${s.contentLeft}`);

  /* ---------- ⑩ 图标中心 + 指示条 ---------- */
  const center1200 = (await snap()).iconCenter;
  await setW(800);
  const center800 = (await snap()).iconCenter;
  check("图标中心：expanded 与 compact（关闭）同为 pane 内 24",
    Math.abs(center1200 - 24) <= 1.5 && Math.abs(center800 - 24) <= 1.5,
    `expanded=${center1200} compact=${center800}`);
  for (const w of [1200, 800, 500]) {
    await setW(w);
    let t = await snap();
    if (t.mode === "minimal") {          /* minimal 收起时 pane 在视口外，先打开再量指示条 */
      await clickX(".fl-nav-toggle-float");
      t = await snap();
    }
    check(`切到 ${w}px 后指示条仍贴着当前项（垂直偏差 ≤1.5，档=${t.mode}）`,
      t.indTop !== null && Math.abs(t.indTop) <= 1.5, `Δ=${t.indTop}`);
    if (t.mode === "minimal" && t.open === "1") await keyEsc();
  }

  console.log(`\n结果：${pass} 通过 / ${fail} 失败`);
  chrome.kill();
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error("ERROR", e);
  process.exit(1);
});
