/* tests/nav_indicator_shots.js —— 指示条"换项"动画的定格条带
   跑法：node tests/nav_indicator_shots.js
   为什么不用实时截图：60fps 采样抓不到"峰值只有一帧"的时刻；pause() + currentTime 才能定死。
   产出：%TEMP%/shots/navind-<t>.png + 终端打印每帧 pill/ghost 的 rect（判"有没有跑出按钮"）
   对照：video-analysis/ 里同一动作的录屏实测（ind_edges.py）——峰值 1.6×、始终在项内。 */
"use strict";
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const CHROME = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9353;
const OUT = path.join(os.tmpdir(), "shots");
const PAGE = "file:///" + path.join(__dirname, "..", "fluent2-tool-starter.html").replace(/\\/g, "/");
const TIMES = [0, 50, 100, 150, 167, 200, 250, 333, 500];
const ITEM = parseInt(process.argv[2] || "2", 10);

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
  const userDir = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-navind-"));
  const chrome = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--mute-audio", "--allow-file-access-from-files",
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${userDir}`,
    "--window-size=1100,760", "--force-device-scale-factor=2", "about:blank",
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

  const geo = await evalJs(`(function(){
    var items = document.querySelectorAll(".fl-nav-item");
    var src = document.querySelector('.fl-nav-item[aria-current="page"]');
    var it = items[${ITEM}], r = it.getBoundingClientRect();
    var sr = src.getBoundingClientRect();
    var nav = document.querySelector(".fl-nav").getBoundingClientRect();
    var y0 = Math.min(r.top, sr.top) - 12;
    return { x: r.left + r.width / 2, y: r.top + r.height / 2,
             clip: { x: Math.max(0, nav.left - 2), y: Math.max(0, y0),
                     width: 132, height: Math.abs(r.top - sr.top) + r.height + 24 },
             itemTop: r.top, itemBottom: r.bottom, itemH: r.height,
             srcTop: sr.top, srcBottom: sr.bottom };
  })()`);

  for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) {
    await S("Input.dispatchMouseEvent", {
      type, x: geo.x, y: geo.y, button: type === "mouseMoved" ? "none" : "left", clickCount: 1,
    });
  }

  /* 立刻暂停两侧指示条动画（页面转场动画不停，没影响：裁的是侧栏） */
  await evalJs(`(function(){
    window.__ind = document.getAnimations().filter(function(a){
      var t = a.effect && a.effect.target;
      return t && t.classList && t.classList.contains("fl-nav-ind");
    });
    window.__ind.forEach(function(a){ a.pause(); a.currentTime = 0; });
    return window.__ind.length;
  })()`);

  const shots = [];
  for (const t of TIMES) {
    const info = await evalJs(`(function(){
      window.__ind.forEach(function(a){ if (a.playState !== "finished") a.currentTime = ${t}; });
      var nav = document.querySelector(".fl-nav");
      var pill = nav.querySelector('.fl-nav-ind[data-role="pill"]');
      var ghost = nav.querySelector('.fl-nav-ind[data-role="ghost"]');
      function r(el){ var b = el.getBoundingClientRect();
        return { top: +b.top.toFixed(1), bottom: +b.bottom.toFixed(1), h: +b.height.toFixed(1),
                 op: +getComputedStyle(el).opacity }; }
      return { pill: r(pill), ghost: r(ghost) };
    })()`);
    const r = await S("Page.captureScreenshot", {
      format: "png",
      clip: { x: geo.clip.x, y: geo.clip.y, width: geo.clip.width, height: geo.clip.height, scale: 2 },
    });
    const f = path.join(OUT, `navind-${String(t).padStart(3, "0")}.png`);
    fs.writeFileSync(f, Buffer.from(r.data, "base64"));
    shots.push({ t, f, ...info });
  }

  console.log("目标项 rect：", geo.itemTop.toFixed(1), "~", geo.itemBottom.toFixed(1),
    `(h=${geo.itemH})　源项 rect：`, geo.srcTop.toFixed(1), "~", geo.srcBottom.toFixed(1));
  for (const s of shots) {
    const out = [`t=${String(s.t).padStart(3)}ms`,
      `pill ${s.pill.top}~${s.pill.bottom} h=${s.pill.h} op=${s.pill.op}`,
      `ghost ${s.ghost.top}~${s.ghost.bottom} h=${s.ghost.h} op=${s.ghost.op}`];
    /* 旧条只能待在源项里、新条只能待在目标项里；越界 >0 就是"跑出按钮" */
    const spillG = Math.max(0, geo.srcTop - s.ghost.top, s.ghost.bottom - geo.srcBottom);
    const spillP = Math.max(0, geo.itemTop - s.pill.top, s.pill.bottom - geo.itemBottom);
    console.log(out.join("  ") + `  越界 ghost ${spillG.toFixed(1)} / pill ${spillP.toFixed(1)}px`);
  }
  console.log("帧：", path.join(OUT, "navind-*.png"));

  ws.close();
  chrome.kill();
}

main().catch((e) => { console.error("FAIL", e); process.exit(1); });
