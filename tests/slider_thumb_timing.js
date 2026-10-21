/* tests/slider_thumb_timing.js —— 滑块内点"放大/缩小"的**速率**验证
   规范（XAML SliderThumbStyle 的 VisualState KeyTime）：
     PointerOver / Pressed → ControlNormalAnimationDuration = 250ms
     Normal（移开、缩回去）→ ControlFastAnimationDuration  = 167ms
     曲线三态都是 ControlFastOutSlowIn = cubic-bezier(0,0,0,1)
   ⇒ 放大比缩小慢，比值 250/167 ≈ 1.50。

   怎么量：真按 250ms 采样根本分不清（截图一次就要几十毫秒），所以把两个时长 token
   按同比例放大 4 倍（1000 / 667ms），逐张截图量内点直径 → 找"到位时间"。
   比值不受缩放影响，正好用来判"逐状态时长有没有生效"。

   跑法：node tests/slider_thumb_timing.js     （退出码 0 = 通过） */
"use strict";
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const CHROME = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9367;
const OUT = path.join(os.tmpdir(), "shots");
const PAGE = "file:///" + path.join(__dirname, "..", "fluent2-tool-starter.html").replace(/\\/g, "/");
const DSF = 2, CLIP_HALF = 16, CLIP_CSS = CLIP_HALF * 2;
const SCALE = 4;                       // 时长整体放大倍数
const DUR_IN = 250 * SCALE, DUR_OUT = 167 * SCALE;

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
  const userDir = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-slider-t-"));
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
    /* 时长整体放大，其他一切不动 */
    el.style.setProperty("--fl-dur-control-normal", "${DUR_IN}ms");
    el.style.setProperty("--fl-dur-control-fast", "${DUR_OUT}ms");
    var r = el.getBoundingClientRect();
    return { cx: r.left + 10 + 0.4 * (r.width - 20), cy: r.top + r.height / 2 };
  })()`);
  await sleep(200);

  const clip = { x: geo.cx - CLIP_HALF, y: geo.cy - CLIP_HALF,
                 width: CLIP_CSS, height: CLIP_CSS, scale: DSF };
  const series = [];
  const sample = async (tag, i, base) => {
    const ts = Date.now() - base;              // 截图开始时刻（相对该段的 t0/t1）
    const r = await S("Page.captureScreenshot", { format: "png", clip });
    const f = path.join(OUT, `timing-${tag}-${String(i).padStart(2, "0")}.png`);
    fs.writeFileSync(f, Buffer.from(r.data, "base64"));
    series.push({ tag, i, ts, f });
  };

  /* 悬停进入：从鼠标离开状态开始，记录鼠标移动的时刻作为 t=0 */
  await S("Input.dispatchMouseEvent", { type: "mouseMoved", x: 4, y: 4, button: "none" });
  await sleep(600);
  const t0 = Date.now();
  await S("Input.dispatchMouseEvent", { type: "mouseMoved", x: geo.cx, y: geo.cy, button: "none" });
  for (let i = 0; i < 16; i++) { await sample("in", i, t0); await sleep(55); }

  /* 移开：鼠标一离开就开始缩回 */
  await sleep(500);
  const t1 = Date.now();
  await S("Input.dispatchMouseEvent", { type: "mouseMoved", x: 4, y: 4, button: "none" });
  for (let i = 0; i < 14; i++) { await sample("out", i, t1); await sleep(55); }

  const meta = { dIn: DUR_IN, dOut: DUR_OUT, scale: SCALE, dsf: DSF, clipCss: CLIP_CSS };
  fs.writeFileSync(path.join(OUT, "timing.json"), JSON.stringify({ meta, series }, null, 1));
  console.log(`时长放大 ${SCALE}× → 进入 ${DUR_IN}ms / 缩回 ${DUR_OUT}ms，截图 ${series.length} 张`);
  console.log("清单：", path.join(OUT, "timing.json"));
  console.log("下一步：python tests/slider_thumb_timing.py");

  ws.close();
  chrome.kill();
}

main().catch((e) => { console.error("FAIL", e); process.exit(1); });
