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

  /* 再点回第 0 项（条目管理，更靠上）→ 应从上方进入（负号） */
  await clickAt(await navBox(0));
  await sleep(110);
  await shot("x0-transition-up");     // 转场中段：新页偏上
  const up = await evaluate(`(function(){
    var p = document.getElementById("page-main");
    return { fromY: p.style.getPropertyValue("--fl-page-from-y") };
  })()`);
  await sleep(400);
  check("点上方导航项 → 自上方进入（-shift-y）", /calc\(var\(--fl-page-shift-y\) \* -1\)/.test(up.fromY), JSON.stringify(up));

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

  /* ---- 5) reduced-motion 下终态正确 ---- */
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
