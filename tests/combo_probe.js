/* tests/combo_probe.js —— ComboBox 弹层几何探针
   跑法：node tests/combo_probe.js [页面] [按钮选择器]
   打印：弹层矩形 / 是否越出视口 / 溢出方向 / 滚动条占宽 / 各项高度。
   典型用途：弹层跑到屏幕外、看不见滚动条、选项折行把弹层撑高。 */
"use strict";
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const CHROME = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9374;
const PAGE = "file:///" + path.resolve(process.argv[2] || path.join(__dirname, "..", "fluent2-tool-starter.html")).replace(/\\/g, "/");
const BTN = process.argv[3] || ".fl-combo-btn";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const userDir = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-combo-"));
  const chrome = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--allow-file-access-from-files",
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${userDir}`,
    "--window-size=1100,760", "--force-device-scale-factor=2", "about:blank",
  ], { stdio: "ignore" });

  let ws;
  for (let i = 0; i < 60; i++) {
    try {
      const j = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json();
      if (j.webSocketDebuggerUrl) { ws = new WebSocket(j.webSocketDebuggerUrl); break; }
    } catch (_) {}
    await sleep(200);
  }
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  let id = 0; const pend = new Map();
  ws.addEventListener("message", (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pend.has(m.id)) { const { resolve } = pend.get(m.id); pend.delete(m.id); resolve(m.result); }
  });
  const send = (method, params, sessionId) => new Promise((res) => {
    const i = ++id; pend.set(i, { resolve: res });
    ws.send(JSON.stringify({ id: i, method, params: params || {}, sessionId }));
  });

  const { targetId } = await send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
  const S = (m, p) => send(m, p, sessionId);
  const evalJs = async (expr) => {
    const r = await S("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails.exception));
    return r.result.value;
  };

  await S("Page.enable");
  await S("Page.navigate", { url: PAGE });
  await sleep(1300);

  /* 真点一下按钮，走完整 JS 路径（place / portal / 开合动画） */
  const box = await evalJs(`(function(){
    var b = document.querySelector(${JSON.stringify(BTN)});
    if (!b) return null;
    b.scrollIntoView({ block: "center" });
    var r = b.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  })()`);
  if (!box) throw new Error("找不到按钮 " + BTN);
  for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) {
    await S("Input.dispatchMouseEvent", {
      type, x: box.x, y: box.y, button: type === "mouseMoved" ? "none" : "left", clickCount: 1,
    });
  }
  await sleep(400);

  const out = await evalJs(`(function(){
    var pop = document.querySelector(".fl-combo-popup.fl-open") ||
              document.querySelector(".fl-combo-popup[data-open=\\"true\\"]") ||
              document.querySelector(".fl-combo-popup");
    if (!pop) return { missing: true };
    var r = pop.getBoundingClientRect(), cs = getComputedStyle(pop);
    var vw = window.innerWidth, vh = window.innerHeight;
    var items = [].map.call(pop.querySelectorAll(".fl-combo-item"), function (el) {
      var ir = el.getBoundingClientRect();
      return { t: el.textContent.trim().slice(0, 12), h: Math.round(ir.height), w: Math.round(ir.width),
               scrollW: el.scrollWidth };
    });
    return {
      rect: { left: Math.round(r.left), top: Math.round(r.top),
              right: Math.round(r.right), bottom: Math.round(r.bottom),
              w: Math.round(r.width), h: Math.round(r.height) },
      viewport: { vw: vw, vh: vh },
      over: { right: Math.round(r.right - vw), bottom: Math.round(r.bottom - vh), left: Math.round(-r.left) },
      /* 滚动条：offset-client 才反映真实占宽（overlay 滚动条为 0） */
      sb: { ow: pop.offsetWidth, cw: pop.clientWidth, sbw: pop.offsetWidth - pop.clientWidth,
            ox: pop.offsetHeight - pop.clientHeight,
            scrollH: pop.scrollHeight, clientH: pop.clientHeight,
            sw: pop.scrollWidth, cwScroll: pop.clientWidth },
      css: { left: cs.left, top: cs.top, minWidth: cs.minWidth, maxWidth: cs.maxWidth,
             maxHeight: cs.maxHeight, position: cs.position, overflowX: cs.overflowX, overflowY: cs.overflowY },
      items: items
    };
  })()`);
  console.log(JSON.stringify(out, null, 1));
  ws.close(); chrome.kill();
}

main().catch((e) => { console.error("FAIL", e.message); process.exit(1); });
