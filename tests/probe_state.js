/* tests/probe_state.js —— 一次性诊断脚本：把鼠标真的移到某个元素上，截该元素的图并打印计算样式
   跑法：node tests/probe_state.js <page.html> <selector> [输出名]
   用途：hover / active 这类纯视觉态没法用静态截图验收，得真派发鼠标事件再采样。 */
"use strict";
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const CHROME = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9341;
const OUT = path.join(os.tmpdir(), "shots");

const pageArg = process.argv[2] || path.join(__dirname, "..", "selftest.html");
const selector = process.argv[3] || "#set-slider";
const tag = process.argv[4] || "probe";
const PAGE = "file:///" + path.resolve(pageArg).replace(/\\/g, "/");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

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

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const userDir = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-probe-"));
  const chrome = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio",
    "--allow-file-access-from-files", `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${userDir}`, "--window-size=1100,1000",
    "--force-device-scale-factor=2", "about:blank",
  ], { stdio: "ignore" });

  const ws = new WebSocket(await wsUrl());
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  const cdp = new CDP(ws);
  const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
  const S = (m, p) => cdp.send(m, p, sessionId);

  await S("Page.enable");
  await S("Runtime.enable");
  await S("Emulation.setEmulatedMedia", {
    features: [{ name: "prefers-reduced-motion", value: "reduce" }],
  });
  await S("Page.navigate", { url: PAGE });
  await sleep(1500);

  const box = await S("Runtime.evaluate", {
    expression: `(function(){
      var el = document.querySelector(${JSON.stringify(selector)});
      if (!el) return null;
      el.scrollIntoView({block:"center"});
      var r = el.getBoundingClientRect();
      return { x: r.x, y: r.y, w: r.width, h: r.height };
    })()`,
    returnByValue: true,
  });
  const b = box.result.value;
  if (!b) throw new Error("找不到 " + selector);
  await sleep(300);

  // 重取一次（scrollIntoView 之后坐标变了）；captureScreenshot 的 clip 用页面坐标，要加 scrollY
  const box2 = await S("Runtime.evaluate", {
    expression: `(function(){
      var r = document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();
      return { x: r.x, y: r.y, w: r.width, h: r.height, sy: window.scrollY };
    })()`,
    returnByValue: true,
  });
  const bbV = box2.result.value;            // 视口坐标：派发鼠标事件用这个
  const bb = { x: bbV.x, y: bbV.y + bbV.sy, w: bbV.w, h: bbV.h };  // 页面坐标：截图 clip 用这个
  const cx = bbV.x + bbV.w / 2, cy = bbV.y + bbV.h / 2;

  const readStyle = async () => (await S("Runtime.evaluate", {
    expression: `(function(){
      var el = document.querySelector(${JSON.stringify(selector)});
      var cs = getComputedStyle(el);
      var o = {
        accent: cs.getPropertyValue("--fl-slider-accent").trim(),
        rest: cs.getPropertyValue("--fl-slider-rest").trim(),
        pct: cs.getPropertyValue("--fl-slider-pct").trim(),
        opacity: cs.opacity,
        /* 滚动条占宽：经典滚动条 = offset-client（含边框）；overlay 滚动条恒等于 border */
        ow: el.offsetWidth, cw: el.clientWidth, sbw: el.offsetWidth - el.clientWidth,
        sbwCss: cs.scrollbarWidth || "", sbColor: cs.scrollbarColor || "",
      };
      try { o.trackImg = getComputedStyle(el, "::-webkit-slider-runnable-track").backgroundImage; } catch(e) {}
      return o;
    })()`, returnByValue: true,
  })).result.value;

  await S("Input.dispatchMouseEvent", { type: "mouseMoved", x: 5, y: 5, button: "none" });
  await sleep(200);
  const rest = await readStyle();
  const shot = async (name) => {
    const r = await S("Page.captureScreenshot", {
      format: "png",
      clip: { x: bb.x - 8, y: bb.y - 8, width: bb.w + 16, height: bb.h + 16, scale: 2 },
    });
    fs.writeFileSync(path.join(OUT, `${tag}-${name}.png`), Buffer.from(r.data, "base64"));
  };
  await shot("rest");

  await S("Input.dispatchMouseEvent", { type: "mouseMoved", x: cx, y: cy, button: "none" });
  await sleep(400);
  const hover = await readStyle();
  await shot("hover");

  await S("Input.dispatchMouseEvent", { type: "mousePressed", x: cx, y: cy, button: "left", clickCount: 1 });
  await sleep(400);
  const active = await readStyle();
  await shot("active");
  await S("Input.dispatchMouseEvent", { type: "mouseReleased", x: cx, y: cy, button: "left", clickCount: 1 });

  console.log("选择器:", selector);
  console.log("rest   ", JSON.stringify(rest));
  console.log("hover  ", JSON.stringify(hover));
  console.log("active ", JSON.stringify(active));
  console.log("截图:", path.join(OUT, `${tag}-{rest,hover,active}.png`));

  ws.close();
  chrome.kill();
}

main().catch((e) => { console.error("FAIL", e); process.exit(1); });
