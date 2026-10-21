/* tests/motion_trace.js —— 用 rAF 在页面内高频采样转场，导出「时间 → 位移/透明度」曲线
   跑法：node tests/motion_trace.js [选择器] [标签]
   为什么不用截图：截图每次 ~60-100ms，采样率太低，看不出"起手是否卡住"。
   rAF 采样能拿到 60fps 的真实轨迹，直接和录屏的逐帧进度对比。 */
"use strict";
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const CHROME = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9361;
const OUT = path.join(os.tmpdir(), "shots");
const PAGE = "file:///" + path.join(__dirname, "..", "fluent2-tool-starter.html").replace(/\\/g, "/");
const SELECTOR = process.argv[2] || "#btn-open-detail";
const TAG = process.argv[3] || "trace";

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
  const userDir = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-trace-"));
  const chrome = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--mute-audio", "--allow-file-access-from-files",
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${userDir}`,
    "--window-size=1100,760", "--force-device-scale-factor=1", "about:blank",
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
  await sleep(1400);

  const box = await evalJs(`(function(){
    var b = document.querySelector(${JSON.stringify(SELECTOR)});
    var r = b.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  })()`);

  /* 采样器：点下去之后连续 700ms 记录入/离页的 left 与 opacity */
  await evalJs(`(function(){
    window.__trace = [];
    var t0 = 0, running = false;
    window.__startTrace = function () {
      t0 = performance.now(); running = true;
      function tick(now) {
        var inn = document.querySelector(".fl-page.fl-page-in");
        var out = document.querySelector(".fl-page.fl-page-leaving");
        window.__trace.push({
          t: +(now - t0).toFixed(1),
          inX: inn ? +inn.getBoundingClientRect().left.toFixed(1) : null,
          inY: inn ? +inn.getBoundingClientRect().top.toFixed(1) : null,
          inOp: inn ? +getComputedStyle(inn).opacity : null,
          outX: out ? +out.getBoundingClientRect().left.toFixed(1) : null,
          outY: out ? +out.getBoundingClientRect().top.toFixed(1) : null,
          outOp: out ? +getComputedStyle(out).opacity : null
        });
        if (running && now - t0 < 700) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    };
    return true;
  })()`);

  for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) {
    await S("Input.dispatchMouseEvent", {
      type, x: box.x, y: box.y, button: type === "mouseMoved" ? "none" : "left", clickCount: 1,
    });
    if (type === "mousePressed") await evalJs("window.__startTrace()");
  }

  await sleep(900);
  const trace = await evalJs("window.__trace");
  fs.writeFileSync(path.join(OUT, `${TAG}-trace.json`), JSON.stringify(trace, null, 1));

  const first = trace.find((p) => p.inX !== null || p.outX !== null) || trace[0];
  const baseX = 240;                       // 内容层左缘（页内边距已挪到 .fl-page 上）
  /* 行程 = 首帧新页相对终点的偏移；由数据算出，避免硬编码（改 token 不用改脚本） */
  const firstIn = trace.find((p) => p.inX !== null && p.inX > baseX);
  const startOffset = Math.max((firstIn ? firstIn.inX - baseX : 1), 1);
  console.log(`${TAG}：采样 ${trace.length} 帧（≈${Math.round(trace[0].t)}–${Math.round(trace[trace.length - 1].t)}ms）`);
  console.log("t(ms)\t新页x\t新页y\t新页不透明\t旧页x\t旧页y\t旧页不透明");
  for (const p of trace) {
    if (p.t > 520 && p.t % 1 > 0.5) continue;
    /* 分母用实测首帧偏移（= 行程），不写死像素：行程改了脚本不用跟着改 */
    const prog = p.inX === null ? "" : ((p.inX - baseX) / startOffset).toFixed(3);
    if (p.inX === null && p.outX === null) continue;
    console.log(`${p.t}\t${p.inX ?? "-"}\t${p.inY ?? "-"}\t${p.inOp ?? "-"}\t${p.outX ?? "-"}\t${p.outY ?? "-"}\t${p.outOp ?? "-"}`);
  }
  console.log("原始序列：", path.join(OUT, `${TAG}-trace.json`));
  ws.close();
  chrome.kill();
}

main().catch((e) => { console.error("FAIL", e); process.exit(1); });
