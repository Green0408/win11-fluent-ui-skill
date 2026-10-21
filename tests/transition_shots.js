/* tests/transition_shots.js —— 抓某次转场的连续帧（默认 drill 进详情页）
   跑法：node tests/transition_shots.js [选择器] [标签]
   用途：转场"有问题"这类观感缺陷必须先看到中间帧；静态截图和终态断言都看不出来。
   产出：%TEMP%/shots/<标签>-f00..fNN.png + <标签>-sheet.png 联系表 */
"use strict";
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const CHROME = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9351;
const OUT = path.join(os.tmpdir(), "shots");
const PAGE = "file:///" + path.join(__dirname, "..", "fluent2-tool-starter.html").replace(/\\/g, "/");
const SELECTOR = process.argv[2] || "#btn-open-detail";
const TAG = process.argv[3] || "drill";
const PRE = process.argv[4] || "";   // 可选：先点这个，再抓第二次转场（如先钻取再返回）
const SCROLL = parseInt(process.argv[5] || "0", 10);  // 可选：先把页面滚到某个 y 再点
const FRAMES = 10;
const STEP_MS = 40;

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
  const userDir = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-trans-"));
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

  const clickSel = async (sel) => {
    const p0 = await evalJs(`(function(){
      var b = document.querySelector(${JSON.stringify(sel)});
      if (!b) return null;
      b.scrollIntoView({ block: "center" });
      var r = b.getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    })()`);
    if (!p0) throw new Error("找不到 " + sel);
    for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) {
      await S("Input.dispatchMouseEvent", {
        type, x: p0.x, y: p0.y, button: type === "mouseMoved" ? "none" : "left", clickCount: 1,
      });
    }
  };

  if (PRE) {                       // 先走到起始状态（等转场彻底结束再抓下一段）
    await clickSel(PRE);
    await sleep(600);
  }
  if (SCROLL) {
    await evalJs(`window.scrollTo(0, ${SCROLL})`);
    await sleep(200);
  }

  const box = await evalJs(`(function(){
    var b = document.querySelector(${JSON.stringify(SELECTOR)});
    if (!b) return null;
    b.scrollIntoView({ block: "center" });
    return { x: b.getBoundingClientRect().left + 10, y: b.getBoundingClientRect().top + 10 };
  })()`);
  if (!box) throw new Error("找不到 " + SELECTOR);
  await sleep(300);

  // 前置状态：动效尺度、内容区几何
  const before = await evalJs(`(function(){
    var layer = document.querySelector(".fl-content-layer");
    return {
      layerW: layer.clientWidth, layerScrollW: layer.scrollWidth,
      docScrollW: document.documentElement.scrollWidth,
      winW: innerWidth, scrollY: window.scrollY
    };
  })()`);

  const shot = async (name) => {
    const r = await S("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(path.join(OUT, `${TAG}-${name}.png`), Buffer.from(r.data, "base64"));
  };

  await S("Input.dispatchMouseEvent", { type: "mouseMoved", x: box.x, y: box.y, button: "none" });
  await S("Input.dispatchMouseEvent", { type: "mousePressed", x: box.x, y: box.y, button: "left", clickCount: 1 });
  await S("Input.dispatchMouseEvent", { type: "mouseReleased", x: box.x, y: box.y, button: "left", clickCount: 1 });

  const frames = [];
  for (let i = 0; i < FRAMES; i++) {
    const t0 = Date.now();
    const info = await evalJs(`(function(){
      var inn = document.querySelector(".fl-page.fl-page-in");
      var out = document.querySelector(".fl-page.fl-page-leaving");
      function r(el){ if(!el) return null; var b = el.getBoundingClientRect();
        return { id: el.id, x: +b.left.toFixed(1), y: +b.top.toFixed(1), w: +b.width.toFixed(1), h: +b.height.toFixed(1) }; }
      var layer = document.querySelector(".fl-content-layer");
      return {
        in: r(inn), out: r(out),
        minH: layer ? layer.style.minHeight : "",
        scrollY: window.scrollY,
        inFromX: inn ? inn.style.getPropertyValue("--fl-page-from-x") : "",
        inFromY: inn ? inn.style.getPropertyValue("--fl-page-from-y") : ""
      };
    })()`);
    await shot(`f${String(i).padStart(2, "0")}`);
    frames.push({ t: Date.now() - t0, ...info });
    await sleep(STEP_MS);
  }

  await sleep(500);
  await shot("end");
  const after = await evalJs(`(function(){
    var layer = document.querySelector(".fl-content-layer");
    return { layerW: layer.clientWidth, layerScrollW: layer.scrollWidth,
             docScrollW: document.documentElement.scrollWidth, minH: layer.style.minHeight,
             scrollY: window.scrollY };
  })()`);

  console.log("前置：", JSON.stringify(before));
  frames.forEach((f, i) => console.log(
    `f${i}`, JSON.stringify({ in: f.in && [f.in.x, f.in.y, f.in.w, f.in.h], out: f.out && [f.out.x, f.out.y, f.out.w, f.out.h], minH: f.minH, fromX: f.inFromX, fromY: f.inFromY })));
  console.log("终态：", JSON.stringify(after));
  console.log("帧输出：", path.join(OUT, `${TAG}-f*.png`));

  ws.close();
  chrome.kill();
}

main().catch((e) => { console.error("FAIL", e); process.exit(1); });
