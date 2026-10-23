/* tests/nav_responsive.js —— 导航响应式三档（对应 XAML NavigationView PaneDisplayMode=Auto）

官方规范（learn.../design/controls/navigationview）：
  · PaneDisplayMode 默认 Auto，按窗口宽度三档切换
  · ≥1008px         展开 Left（pane 并排）
  · 641 ~ 1007px    LeftCompact（只留图标列，CompactPaneLength=48）
  · ≤640px          LeftMinimal（pane 收起，点汉堡浮出 + 覆盖内容）
  · 阈值 641 / 1008 与响应式断点 Small(≤640) / Large(≥1008) 同值

判据：
  ① 三档切换正确（宽度 240 / 48 / 收起），且紧凑档文字确实隐藏
  ② 图标中心在展开态与紧凑态是同一个位置（官方图标盒 40 → 中心 24）
  ③ 极简档：汉堡浮在内容左上，点开 pane 从左侧滑入 + 遮罩出现，点遮罩/Esc 关闭
  ④ 展开档手动收起后 pane 让位（宽 0）、汉堡接管入口
  ⑤ 档位切换后选中指示条仍贴着当前项

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
    await sleep(260); /* 等 ResizeObserver + 一次布局 */
  };

  /* 一次把三档要看的量全取出来 */
  const snap = () => evalJs(`(function(){
    var nav = document.querySelector(".fl-nav");
    var item = nav.querySelector(".fl-nav-item");
    var icon = item && item.querySelector(".fl-nav-icon");
    var label = item && item.querySelector(".fl-nav-label");
    var ind = nav.querySelector('.fl-nav-ind[data-role="pill"]') || nav.querySelector(".fl-nav-ind");
    var floatBtn = document.querySelector(".fl-nav-toggle-float");
    var scrim = document.querySelector(".fl-nav-scrim");
    var nr = nav.getBoundingClientRect();
    var ir = item ? item.getBoundingClientRect() : null;
    var kr = icon ? icon.getBoundingClientRect() : null;
    var lr = label ? label.getBoundingClientRect() : null;
    var add = function (e) { return e ? +(e.getBoundingClientRect ? 0 : 0) : 0; };
    return {
      mode: nav.dataset.navMode,
      open: nav.dataset.navOpen,
      navW: +nr.width.toFixed(1),
      navLeft: +nr.left.toFixed(1),
      navVis: getComputedStyle(nav).visibility,
      itemW: ir ? +ir.width.toFixed(1) : null,
      itemH: ir ? +ir.height.toFixed(1) : null,
      labelShown: lr ? lr.width > 2 : false,
      iconCenter: kr ? +(kr.left + kr.width / 2 - nr.left).toFixed(1) : null,
      indTop: ind && ir ? +(ind.getBoundingClientRect().top + ind.getBoundingClientRect().height / 2
                          - (ir.top + ir.height / 2)).toFixed(1) : null,
      floatShown: floatBtn ? getComputedStyle(floatBtn).display !== "none" : false,
      scrimOp: scrim ? +(+getComputedStyle(scrim).opacity).toFixed(2) : null,
      scrimVis: scrim ? getComputedStyle(scrim).visibility : null
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

  /* ---------- ① 三档 ---------- */
  await setW(1200);
  let s = await snap();
  check("1200px → expanded，pane 并排 240 宽",
    s.mode === "expanded" && Math.abs(s.navW - 240) < 1.5 && s.labelShown,
    `mode=${s.mode} w=${s.navW} label=${s.labelShown}`);

  await setW(800);
  s = await snap();
  check("800px → compact，pane 收成 48 图标列、文字隐藏",
    s.mode === "compact" && Math.abs(s.navW - 48) < 1.5 && !s.labelShown,
    `mode=${s.mode} w=${s.navW} label=${s.labelShown}`);
  check("compact：导航项 40 宽（48 − 左右各 4）",
    Math.abs(s.itemW - 40) < 1.5 && s.itemH >= 35 && s.itemH <= 37,
    `${s.itemW}×${s.itemH}`);
  const compactCenter = s.iconCenter;

  await setW(500);
  s = await snap();
  check("500px → minimal，pane 收起（在视口左外）",
    s.mode === "minimal" && s.navVis === "hidden" && s.open === "0",
    `mode=${s.mode} vis=${s.navVis} open=${s.open}`);
  check("minimal：汉堡浮在内容左上（pane 内的那个随 pane 一起隐藏）",
    s.floatShown, `float=${s.floatShown}`);

  /* ---------- ② 图标中心一致 ---------- */
  await setW(1200);
  const expCenter = (await snap()).iconCenter;
  check("图标中心：展开态与紧凑态同一位置（官方图标盒 40 → 中心 24）",
    Math.abs(expCenter - compactCenter) <= 1.5 && Math.abs(expCenter - 24) <= 1.5,
    `expanded=${expCenter} compact=${compactCenter}`);

  /* ---------- ③ 极简档开合 ---------- */
  await setW(500);
  const anim = await evalJs(`(function(){
    var nav = document.querySelector(".fl-nav");
    var btn = document.querySelector(".fl-nav-toggle-float");
    btn.click();
    var list = nav.getAnimations().map(function(a){
      return { p: a.transitionProperty, d: a.effect.getTiming().duration, e: a.effect.getTiming().easing };
    });
    return list;
  })()`);
  await sleep(360);
  s = await snap();
  const tr = anim.find((a) => a.p === "transform");
  check("极简档打开：pane 滑进来（translateX → 0），不是宽度变化",
    s.open === "1" && Math.abs(s.navLeft) < 1.5 && s.navVis === "visible",
    `open=${s.open} left=${s.navLeft} vis=${s.navVis}`);
  check("极简档打开：transform 过渡 250ms / ControlFastOutSlowIn，且没有过渡 width",
    !!tr && tr.d === 250 && /cubic-bezier\(0(\.\d+)?, ?0, ?0, ?1\)/.test(tr.e) &&
    !anim.some((a) => a.p === "width"),
    tr ? `${tr.d}ms ${tr.e}` : JSON.stringify(anim));
  check("极简档打开：遮罩出现（--fl-smoke）",
    s.scrimOp === 1 && s.scrimVis === "visible", `op=${s.scrimOp} vis=${s.scrimVis}`);

  await clickX(".fl-nav-scrim");
  s = await snap();
  check("点遮罩关闭：pane 退回左侧、遮罩消失、汉堡回来",
    s.open === "0" && s.scrimOp === 0 && s.floatShown,
    `open=${s.open} scrim=${s.scrimOp} float=${s.floatShown}`);

  await clickX(".fl-nav-toggle-float");
  await S("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
  await sleep(360);
  s = await snap();
  check("Esc 关闭极简档 pane", s.open === "0", `open=${s.open}`);

  /* ---------- ④ 展开档手动收起 ---------- */
  await setW(1200);
  await clickX(".fl-nav-panehead .fl-nav-toggle");
  s = await snap();
  check("展开档点汉堡：pane 让位（宽 0），汉堡移到内容左上",
    Math.abs(s.navW) < 1 && s.floatShown && s.open === "0",
    `w=${s.navW} float=${s.floatShown} open=${s.open}`);
  const contentLeft = await evalJs(
    `+document.querySelector(".fl-content-layer").getBoundingClientRect().left.toFixed(1)`);
  check("内容占满（内容层左边界 = 0）", Math.abs(contentLeft) < 1.5, `left=${contentLeft}`);
  await clickX(".fl-nav-toggle-float");
  s = await snap();
  check("再点汉堡：pane 回到 240", Math.abs(s.navW - 240) < 1.5 && s.open === "1", `w=${s.navW}`);

  /* ---------- ⑤ 指示条跟随 ---------- */
  for (const w of [1200, 800]) {
    await setW(w);
    s = await snap();
    check(`切到 ${w}px 后指示条仍贴着当前项（垂直偏差 ≤1.5）`,
      s.indTop !== null && Math.abs(s.indTop) <= 1.5, `Δ=${s.indTop}`);
  }

  console.log(`\n结果：${pass} 通过 / ${fail} 失败`);
  chrome.kill();
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error("ERROR", e);
  process.exit(1);
});
