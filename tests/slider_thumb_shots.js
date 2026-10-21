/* tests/slider_thumb_shots.js —— 滑块 thumb 三态定格截图（rest / hover / pressed）
   跑法：node tests/slider_thumb_shots.js
   为什么要真截图：`::-webkit-slider-thumb` 的计算样式在 Chromium 里读不到（getComputedStyle 拿不到伪元素），
   而"外框会不会跟着变大"只能看像素。这里把三态各截一张小图，交给
   tests/slider_thumb_pixels.py 量外框直径与内点直径。
   产出：%TEMP%/shots/slider-<state>.png，并打印 thumb 中心的设备像素坐标 */
"use strict";
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const CHROME = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9357;
const OUT = path.join(os.tmpdir(), "shots");
const PAGE = "file:///" + path.join(__dirname, "..", "fluent2-tool-starter.html").replace(/\\/g, "/");
const DSF = 2;                 // 设备像素比：量出来的 px / 2 = CSS px
const CLIP_HALF = 16;          // 以 thumb 中心为中心，截 32×32 CSS

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
  const userDir = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-slider-"));
  const chrome = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--mute-audio", "--allow-file-access-from-files",
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${userDir}`,
    "--window-size=1100,760", `--force-device-scale-factor=${DSF}`, "about:blank",
  ], { stdio: "ignore" });

  const ws = new WebSocket(await wsUrl());
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  const cdp = new CDP(ws);
  const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
  const S = (m, p) => cdp.send(m, p, sessionId);
  const evalJs = async (expr) =>
    (await S("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true })).result.value;

  await S("Page.enable");
  await S("Runtime.enable");
  await S("Page.navigate", { url: PAGE });
  await sleep(1500);

  /* 切到设置页（滑块在那儿），滚到可见，并把值设成 40（thumb 落在轨道中段，方便取中心） */
  const navBox = await evalJs(`(function(){
    var it = document.querySelectorAll(".fl-nav-item")[2].getBoundingClientRect();
    return { x: it.left + it.width / 2, y: it.top + it.height / 2 };
  })()`);
  for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) {
    await S("Input.dispatchMouseEvent", { type, x: navBox.x, y: navBox.y,
      button: type === "mouseMoved" ? "none" : "left", clickCount: 1 });
  }
  await sleep(600);

  const geo = await evalJs(`(function(){
    var el = document.getElementById("set-slider");
    el.scrollIntoView({ block: "center" });
    el.value = 40; el.dispatchEvent(new Event("input", { bubbles: true }));
    var r = el.getBoundingClientRect();
    var pct = 0.4;
    /* thumb 盒宽 12（缩放不参与布局）、行程 = 轨道宽 - 12，中心 = 6 + 0.4×(W-12) */
    var cx = r.left + 10 + pct * (r.width - 20);
    return { cx: cx, cy: r.top + r.height / 2, w: r.width, h: r.height };
  })()`);
  await sleep(120);

  const clip = {
    x: geo.cx - CLIP_HALF, y: geo.cy - CLIP_HALF,
    width: CLIP_HALF * 2, height: CLIP_HALF * 2, scale: DSF,
  };
  const shot = async (state) => {
    const r = await S("Page.captureScreenshot", { format: "png", clip });
    const f = path.join(OUT, `slider-${state}.png`);
    fs.writeFileSync(f, Buffer.from(r.data, "base64"));
    return f;
  };

  await S("Input.dispatchMouseEvent", { type: "mouseMoved", x: 4, y: 4, button: "none" });
  await sleep(420);
  const rest = await shot("rest");

  await S("Input.dispatchMouseEvent", { type: "mouseMoved", x: geo.cx, y: geo.cy, button: "none" });
  await sleep(420);                      // 过渡 250ms，多留一倍余量
  const hover = await shot("hover");

  await S("Input.dispatchMouseEvent", { type: "mousePressed", x: geo.cx, y: geo.cy, button: "left", clickCount: 1 });
  await sleep(420);
  const press = await shot("pressed");
  await S("Input.dispatchMouseEvent", { type: "mouseReleased", x: geo.cx, y: geo.cy, button: "left", clickCount: 1 });
  await S("Input.dispatchMouseEvent", { type: "mouseMoved", x: 4, y: 4, button: "none" });

  /* 过渡到底有没有"中间态"：把时长拉长到 2400ms 再悬停，隔一段截一张。
     250ms 的过渡配截图延迟（几十毫秒）根本分不清是"动画"还是"跳变"，拉长后一目了然。 */
  await evalJs(`(function(){
    var st = document.createElement("style");
    st.textContent = ".fl-slider::-webkit-slider-thumb{transition-duration:2400ms !important}";
    document.head.appendChild(st);
    return 1;
  })()`);
  await sleep(700);
  await S("Input.dispatchMouseEvent", { type: "mouseMoved", x: geo.cx, y: geo.cy, button: "none" });
  await sleep(700);
  const slowA = await shot("slow-a");
  await sleep(900);
  const slowB = await shot("slow-b");
  await S("Input.dispatchMouseEvent", { type: "mouseMoved", x: 4, y: 4, button: "none" });

  console.log("thumb 中心(视口 CSS)：", geo.cx.toFixed(1), geo.cy.toFixed(1), " 轨道宽：", geo.w.toFixed(1));
  console.log("截图：", rest, hover, press);
  console.log("慢放（2400ms 过渡的中间态）：", slowA, slowB);
  console.log(`（裁切 ${CLIP_HALF * 2}×${CLIP_HALF * 2} CSS，设备像素比 ${DSF} → 图幅应为其 ${DSF} 倍）`);

  ws.close();
  chrome.kill();
}

main().catch((e) => { console.error("FAIL", e); process.exit(1); });
