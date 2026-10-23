/* tests/nav_shots.js —— 导航响应式三档的真机截图（供人工核对 / 文档配图）

产出（默认写到临时目录，`--out <dir>` 可指定）：
  nav-1200.png / nav-800.png / nav-500-0.png / nav-500-1.png
再交给 tests/nav_strip.py 拼成一条对照图。

跑法：node tests/nav_shots.js --out <目录> */
"use strict";
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const CHROME = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9377;
const PAGE = "file:///" + path.join(__dirname, "..", "fluent2-tool-starter.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const argOut = process.argv.indexOf("--out");
const OUT = argOut > -1 ? process.argv[argOut + 1] : fs.mkdtempSync(path.join(os.tmpdir(), "nav-shots-"));

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
  fs.mkdirSync(OUT, { recursive: true });
  const userDir = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-navshot-"));
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

  const shot = async (name) => {
    const { data } = await S("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(path.join(OUT, name), Buffer.from(data, "base64"));
    console.log("saved", name);
  };
  const setW = async (w) => {
    await S("Emulation.setDeviceMetricsOverride", { width: w, height: 720, deviceScaleFactor: 1, mobile: false });
    await sleep(320);
  };

  await setW(1200); await shot("nav-1200.png");
  await setW(800); await shot("nav-800.png");
  await setW(500); await shot("nav-500-0.png");
  await evalJs(`document.querySelector(".fl-nav-toggle-float").click(); 1`);
  await sleep(420); await shot("nav-500-1.png");

  console.log("OUT=" + OUT);
  chrome.kill();
  process.exit(0);
})().catch((e) => {
  console.error("ERROR", e);
  process.exit(1);
});
