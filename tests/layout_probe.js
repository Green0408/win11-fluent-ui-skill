/* tests/layout_probe.js —— 布局探针：打印某个选择器及其子元素的盒模型与溢出原因
   跑法：node tests/layout_probe.js "<页面>" "<选择器>" [子元素选择器]
   典型用途：元素莫名被裁 / 高度不对 / 滚动容器不是预期的那个。 */
"use strict";
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const CHROME = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9371;
const PAGE = "file:///" + path.resolve(process.argv[2] || path.join(__dirname, "..", "fluent2-tool-starter.html")).replace(/\\/g, "/");
const SEL = process.argv[3] || ".fl-page.fl-current";
const CHILD = process.argv[4] || ".fl-listitem";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const userDir = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-layout-"));
  const chrome = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--allow-file-access-from-files",
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${userDir}`,
    "--window-size=1100,760", "--force-device-scale-factor=1", "about:blank",
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
  await S("Page.enable");
  await S("Page.navigate", { url: PAGE });
  await sleep(1300);

  const expr = `(function(){
    function info(el, label){
      if (!el) return { label: label, missing: true };
      var r = el.getBoundingClientRect(), cs = getComputedStyle(el);
      return {
        label: label, tag: el.tagName.toLowerCase() + (el.id ? "#" + el.id : ""),
        top: Math.round(r.top), left: Math.round(r.left),
        w: Math.round(r.width), h: Math.round(r.height),
        overflow: cs.overflow, minH: cs.minHeight, maxH: cs.maxHeight, height: cs.height,
        display: cs.display, flex: cs.flex, alignSelf: cs.alignSelf,
        scroll: [el.scrollTop, el.scrollHeight, el.clientHeight]
      };
    }
    var root = document.querySelector(${JSON.stringify(SEL)});
    var out = { target: info(root, ${JSON.stringify(SEL)}), chain: [], children: [] };
    var el = root;
    while (el && el !== document.documentElement) {
      out.chain.push(info(el, "ancestor"));
      el = el.parentElement;
    }
    if (root) {
      [].slice.call(root.querySelectorAll(${JSON.stringify(CHILD)})).forEach(function(c, i){
        out.children.push(info(c, ${JSON.stringify(CHILD)} + "[" + i + "]"));
      });
    }
    return out;
  })()`;
  const r = await S("Runtime.evaluate", { expression: expr, returnByValue: true });
  console.log(JSON.stringify(r.result.value, null, 1));
  ws.close(); chrome.kill();
}

main().catch((e) => { console.error("FAIL", e); process.exit(1); });
