/* tests/popup_motion.js —— 弹出层开合动画（下拉列表 / 更多选项）的运行时判据

官方规范（Learn《Animating pop-up UI (XAML)》/《弹出 UI 动画指南》）：
  · 弹出层 = **淡入 + 垂直平移**，建议距离 **50px**；**没有缩放**
  · 方向：出现在触发元素**下方**就向下滑入（起点在上方 50px）；在上方则向上滑入
  · 入场 FastOutSlowIn(0,0,0,1)；出场 SlowOutFastIn(1,0,1,1)
  · ToolTip / 对话框只用淡入淡出

这里直接读元素的 computed transform/opacity（弹层是普通元素，不是伪元素，可读），
逐 rAF 采样，判定：位移量 = 50px、无缩放、方向符号、开 250ms / 关 167ms。

跑法：node tests/popup_motion.js     （退出码 0 = 通过） */
"use strict";
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const CHROME = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9373;
const PAGE = "file:///" + path.join(__dirname, "..", "fluent2-tool-starter.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let pass = 0, fail = 0;
function check(name, ok, detail) {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}   ${detail === undefined ? "" : detail}`);
  ok ? pass++ : fail++;
}

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
  const userDir = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-popup-"));
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

  await S("Page.enable"); await S("Runtime.enable");
  await S("Page.navigate", { url: PAGE });
  await sleep(1400);

  const clickSel = async (sel) => {
    const p = await evalJs(`(function(){
      var b = document.querySelector(${JSON.stringify(sel)});
      if (!b) return null;
      b.scrollIntoView({ block: "center" });
      var r = b.getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    })()`);
    if (!p) throw new Error("找不到 " + sel);
    for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) {
      await S("Input.dispatchMouseEvent", {
        type, x: p.x, y: p.y, button: type === "mouseMoved" ? "none" : "left", clickCount: 1,
      });
    }
  };

  /* 关态：transform 应该停在 translateY(dir × 50)，并且没有缩放 */
  const state = () => evalJs(`(function(){
    var el = document.getElementById("flyout-more");
    var cs = getComputedStyle(el);
    var m = new DOMMatrixReadOnly(cs.transform === "none" ? "" : cs.transform);
    return { ty: +m.m42.toFixed(2), sx: +m.a.toFixed(3), sy: +m.d.toFixed(3),
             op: +cs.opacity, drop: el.dataset.drop || "", open: el.classList.contains("fl-open") };
  })()`);

  const closed = await state();
  check("关态：位移 = 50px、无缩放、opacity 0",
    Math.abs(Math.abs(closed.ty) - 50) <= 0.6 && Math.abs(closed.sx - 1) < 0.001 &&
    Math.abs(closed.sy - 1) < 0.001 && closed.op === 0,
    JSON.stringify(closed));
  check("关态：默认方向为「从上方滑入」（触发按钮在上、菜单在下 → dir -1）",
    closed.ty < 0, `ty=${closed.ty}`);

  /* 开：逐 rAF 采样（用 requestAnimationFrame 在页面里收集，避免 CDP 往返误差） */
  const trace = async (action) => {
    await evalJs(`(function(){
      window.__t = [];
      var el = document.getElementById("flyout-more");
      var t0 = performance.now();
      function step(){
        var cs = getComputedStyle(el);
        var m = new DOMMatrixReadOnly(cs.transform === "none" ? "" : cs.transform);
        window.__t.push([+(performance.now() - t0).toFixed(1), +m.m42.toFixed(2), +m.a.toFixed(3), +cs.opacity]);
        if (performance.now() - t0 < 700) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
      return 1;
    })()`);
    await action();
    await sleep(820);
    return evalJs("window.__t");
  };

  const openTrace = await trace(() => clickSel("#btn-more"));
  const ty = openTrace.map(r => r[1]);
  const op = openTrace.map(r => r[3]);
  const sx = openTrace.map(r => r[2]);
  check("开：从 -50px 起手（不是 0、也不是 8px）",
    Math.abs(ty[0] + 50) <= 1 && Math.max(...ty.map(Math.abs)) <= 50.5,
    `首帧 ty=${ty[0]}，全程最大位移 ${Math.max(...ty.map(Math.abs))}`);
  check("开：全程无缩放（合成矩阵 a 恒为 1）",
    sx.every(v => Math.abs(v - 1) < 0.005), `min=${Math.min(...sx)} max=${Math.max(...sx)}`);
  check("开：位移单调收敛到 0、透明度同步上升到 1",
    ty.every((v, i) => i === 0 || v >= ty[i - 1] - 0.6) && Math.abs(ty[ty.length - 1]) <= 0.5 &&
    op[op.length - 1] >= 0.99,
    `ty: ${ty.slice(0, 6).join(",")} … ${ty[ty.length - 1]}；op 末 ${op[op.length - 1]}`);
  const motionOf = (rows, target) => {
    const start = rows.find(r => Math.abs(r[1] - rows[0][1]) > 0.2) || rows[0];
    const i0 = rows.indexOf(start);
    const end = rows.slice(i0).find(r => Math.abs(r[1] - target) <= 0.5) || rows[rows.length - 1];
    return { t0: start[0], dur: +(end[0] - start[0]).toFixed(1) };
  };
  const openM = motionOf(openTrace, 0);
  check("开：≈250ms 到位（ControlNormal）",
    openM.dur >= 180 && openM.dur <= 320, `${openM.dur}ms（自 ${openM.t0}ms 起）`);

  /* 关：点空白处轻触消失，应在 ≈167ms 内滑回 -50 */
  const closeTrace = await trace(() => clickSel("#page-main h1, #page-main"));
  console.log("     关态轨迹 ty:", closeTrace.map(r => r[1]).slice(0, 10).join(","));
  const ty2 = closeTrace.map(r => r[1]);
  const closeM = motionOf(closeTrace, -50);
  check("关：滑回 -50px，且比开明显更快（167 vs 250）",
    Math.abs(ty2[ty2.length - 1] + 50) <= 0.6 &&
    closeM.dur >= 100 && closeM.dur <= 240 && closeM.dur < openM.dur - 25,
    `${closeM.dur}ms（开 ${openM.dur}ms）`);

  /* 下拉列表：**另一套动画** —— 从顶边向下"揭示"（clip-path），不淡入、不位移，关闭瞬变。
     依据 2026-10-21 23-13-35.mp4：顶边固定、底边 8 帧扫下去、首帧文字已 97% 对比度、关闭单帧。 */
  const comboState = () => evalJs(`(function(){
    var el = document.getElementById("combo-view-list");
    var cs = getComputedStyle(el);
    var r = el.getBoundingClientRect();
    return { clip: cs.clipPath, op: +cs.opacity, h: +r.height.toFixed(1),
             top: +r.top.toFixed(1), drop: el.dataset.drop || "", open: el.classList.contains("fl-open") };
  })()`);
  await clickSel("#combo-view-btn");
  const comboOpen = [];
  for (let i = 0; i < 14; i++) { comboOpen.push(await comboState()); await sleep(24); }
  const last = comboOpen[comboOpen.length - 1];
  const px = (clip) => {
    const m = /inset\(([^)]+)\)/.exec(clip || "");
    if (!m) return null;
    return m[1].trim().split(/\s+/).map((v) => v);
  };
  const firstBottom = px(comboOpen[0].clip);
  check("下拉列表：开合走 clip-path 揭示（不是位移/缩放）",
    !!firstBottom && Math.abs(last.h - comboOpen[0].h) < 0.5,
    `clip=${comboOpen[0].clip} → ${last.clip}；height 恒 ${comboOpen[0].h}`);
  const clips = [...new Set(comboOpen.map(r => r.clip))];
  check("下拉列表：揭示是逐帧推进的（clip 至少 3 个不同取值，末帧完整）",
    clips.length >= 3 && last.clip.indexOf("-24px)") >= 0,
    `${clips.length} 个取值：${clips.slice(0, 4).join(" | ")}`);
  check("下拉列表：不淡入（opacity 全程 1）",
    comboOpen.every(r => r.op === 1), comboOpen.map(r => r.op).join(","));
  check("下拉列表：顶边固定（揭示只往下长）",
    Math.abs(comboOpen[comboOpen.length - 1].top - comboOpen[0].top) < 0.5,
    `${comboOpen[0].top} → ${comboOpen[comboOpen.length - 1].top}`);

  /* 关闭：瞬变（录屏里没有退场动画） */
  await clickSel("#combo-view-btn");
  await sleep(0);
  const afterClose = [];
  for (let i = 0; i < 4; i++) { afterClose.push(await comboState()); await sleep(20); }
  check("下拉列表：关闭是瞬变（一帧内消失，不做退场动画）",
    afterClose.every(r => !r.open && r.op === 1) && Math.abs(afterClose[0].h - last.h) < 0.5,
    JSON.stringify(afterClose[0]));

  console.log(`\n结果：${pass}/${pass + fail} 通过`);
  ws.close();
  chrome.kill();
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error("FAIL", e); process.exit(1); });
