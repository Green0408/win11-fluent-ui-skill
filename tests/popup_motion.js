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

  /* 关态：transform 应该停在 translateY(dir × 弹层自身高度)，并且没有缩放 */
  const state = () => evalJs(`(function(){
    var el = document.getElementById("flyout-more");
    var cs = getComputedStyle(el);
    var m = new DOMMatrixReadOnly(cs.transform === "none" ? "" : cs.transform);
    return { ty: +m.m42.toFixed(2), h: +el.getBoundingClientRect().height.toFixed(2),
             sx: +m.a.toFixed(3), sy: +m.d.toFixed(3),
             op: +cs.opacity, drop: el.dataset.drop || "", open: el.classList.contains("fl-open") };
  })()`);

  const closed = await state();
  /* 菜单 = 滑入 + 裁剪到自身矩形（clip-path 与 transform 同长同曲线） */
  const clipState = await evalJs(`(function(){
    var el = document.getElementById("flyout-more");
    return { clipClosed: getComputedStyle(el).clipPath };
  })()`);
  check("关态：裁剪成零高、贴在最终顶边（inset(100% 0 0 0)）",
    /inset\(100%\s+0px\s+0px/.test(clipState.clipClosed), clipState.clipClosed);
  /* MenuPopupThemeTransition：整个弹层滑入视野，行程 = 自身高度（不是 50px） */
  check("关态：位移 = 弹层自身高度、无缩放、不靠透明度隐藏",
    Math.abs(closed.ty + closed.h) <= 1.5 && Math.abs(closed.sx - 1) < 0.001 &&
    Math.abs(closed.sy - 1) < 0.001 && closed.op === 1,
    `ty=${closed.ty} h=${closed.h} op=${closed.op}`);
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

  let openAnims = [];
  const openTrace = await trace(async () => {
    await clickSel("#btn-more");
    /* getAnimations() 只返回**在播**的过渡 → 开完立刻读，采样等待之后就读不到了 */
    openAnims = await evalJs(`document.getElementById("flyout-more").getAnimations().map(function(a){
      return { p: a.transitionProperty, d: a.effect.getTiming().duration, e: a.effect.getTiming().easing };
    })`);
  });
  const ty = openTrace.map(r => r[1]);
  const op = openTrace.map(r => r[3]);
  const sx = openTrace.map(r => r[2]);
  check("开：从 -自身高度 起手（整个弹层在视野外，不是 50px 微移）",
    Math.abs(ty[0] + closed.h) <= 1.5 && Math.min(...ty) >= -closed.h - 1.5,
    `首帧 ty=${ty[0]}，menuH=${closed.h}，全程最小 ${Math.min(...ty)}`);
  check("开：全程无缩放（合成矩阵 a 恒为 1）",
    sx.every(v => Math.abs(v - 1) < 0.005), `min=${Math.min(...sx)} max=${Math.max(...sx)}`);
  check("开：位移单调收敛到 0、且**不淡入**（opacity 全程 1）",
    ty.every((v, i) => i === 0 || v >= ty[i - 1] - 0.6) && Math.abs(ty[ty.length - 1]) <= 0.5 &&
    op.every((v) => v >= 0.999),
    `ty: ${ty.slice(0, 6).join(",")} … ${ty[ty.length - 1]}；op 集合 ${[...new Set(op)].join(",")}`);
  const motionOf = (rows, target) => {
    const start = rows.find(r => Math.abs(r[1] - rows[0][1]) > 0.2) || rows[0];
    const i0 = rows.indexOf(start);
    const end = rows.slice(i0).find(r => Math.abs(r[1] - target) <= 0.5) || rows[rows.length - 1];
    return { t0: start[0], dur: +(end[0] - start[0]).toFixed(1) };
  };
  const openM = motionOf(openTrace, 0);
  check("开：≈250ms 到位（ControlNormal）",
    openM.dur >= 180 && openM.dur <= 320, `${openM.dur}ms（自 ${openM.t0}ms 起）`);
  /* 录屏里 60fps 下位移是 0.46/0.59/0.75/0.85/0.89/0.92/0.96/1.00 的减速曲线 → 至少 4 帧可辨 */
  const seen = ty.filter((v, i) => i === 0 || Math.abs(v - ty[i - 1]) > closed.h * 0.02).length;
  check("开：60fps 下至少 4 帧位移可辨（整段滑行看得出来）",
    seen >= 4, `${seen} 帧有可辨位移 / 共 ${ty.length} 采样`);
  /* 裁剪必须跟位移同步同长：否则位移在动、揭示边界不动（等于没裁，会盖住触发元素） */
  const clipAnim = openAnims.find((a) => a.p === "clip-path");
  const trAnim = openAnims.find((a) => a.p === "transform");
  check("开：clip-path 与 transform 两条过渡同时存在、时长与曲线一致",
    !!clipAnim && !!trAnim && clipAnim.d === trAnim.d && clipAnim.e === trAnim.e,
    JSON.stringify(openAnims));

  /* 关：点空白处轻触消失，应在 ≈167ms 内滑回去 */
  const closeTrace = await trace(() => clickSel("#page-main h1, #page-main"));
  console.log("     关态轨迹 ty:", closeTrace.map(r => r[1]).slice(0, 10).join(","));
  const ty2 = closeTrace.map(r => r[1]);
  const closeM = motionOf(closeTrace, -closed.h);
  check("关：滑回 -自身高度，且比开明显更快（167 vs 250）",
    Math.abs(ty2[ty2.length - 1] + closed.h) <= 1.5 &&
    closeM.dur >= 100 && closeM.dur <= 240 && closeM.dur < openM.dur - 25,
    `${closeM.dur}ms（开 ${openM.dur}ms）`);

  /* 右键菜单（place:false）：方向要按"菜单相对鼠标"判断。
     坑：关态弹层被 translateY(-100%) 抬起，getBoundingClientRect 带着这个位移 ——
     不还原位移就会一直判成"在上方"，菜单从下往上滑。 */
  const ctx = await evalJs(`(function(){
    var f = document.getElementById("flyout-more");
    M.flyout.hide("flyout-more");
    f.style.right = "auto"; f.style.top = "520px"; f.style.left = "200px";
    var anchor = { getBoundingClientRect: function(){ return { top: 400, height: 0, left: 200, width: 0, right: 200, bottom: 400 }; } };
    M.flyout.show("flyout-more", anchor, { place: false });
    var below = f.dataset.drop;
    M.flyout.hide("flyout-more");
    f.style.top = "120px";
    var anchor2 = { getBoundingClientRect: function(){ return { top: 420, height: 0, left: 200, width: 0, right: 200, bottom: 420 }; } };
    M.flyout.show("flyout-more", anchor2, { place: false });
    var above = f.dataset.drop;
    M.flyout.hide("flyout-more");
    return { below: below, above: above };
  })()`);
  check("右键菜单：菜单在鼠标下方 → drop=down（-100% 位移不许把方向骗反）",
    ctx.below === "down", JSON.stringify(ctx));
  check("右键菜单：菜单在鼠标上方 → drop=up",
    ctx.above === "up", JSON.stringify(ctx));

  /* ================= 下拉列表（ComboBox 弹层）：另一套动画 =================
     ① 位置：**选中项那一行正好盖住按钮**（弹层压在按钮上、顶边露一小条），
        依据 2026-10-21 23-13-35.mp4：按钮 y 543..602，选中行 543..605，弹层顶边 526；
     ② 揭示：clip-path 从顶边往下扫（不淡入、不位移、关闭瞬变）；
     ③ 速率：官方 ControlFastOutSlowIn cubic-bezier(0,0,0,1) @167ms。
        录屏逐帧 0.60/0.80/0.87/0.90/0.94/0.97/1.00 的"首帧 60%"是**采样相位**（59.73fps）造成的，
        不能当曲线形状照抄：真机 167ms 里第一帧（16.7ms）不许过半，否则观感就是「没有动画」
        （用户实测反馈）。 */
  const comboState = () => evalJs(`(function(){
    var el = document.getElementById("combo-view-list");
    var cs = getComputedStyle(el);
    var r = el.getBoundingClientRect();
    return { clip: cs.clipPath, op: +cs.opacity, h: +r.height.toFixed(1),
             top: +r.top.toFixed(1), left: +r.left.toFixed(1), w: +r.width.toFixed(1),
             bottom: +r.bottom.toFixed(1),
             drop: el.dataset.drop || "", open: el.classList.contains("fl-open") };
  })()`);

  /* 逐 rAF 采样 clip-path + 顶边/高度/透明度，换算成"已揭示高度比例" */
  await evalJs(`(function(){
    window.__c = [];
    var el = document.getElementById("combo-view-list");
    var t0 = 0;
    window.__startC = function(){ t0 = performance.now(); step(); };
    function step(){
      var cs = getComputedStyle(el), r = el.getBoundingClientRect();
      window.__c.push([+(performance.now() - t0).toFixed(1), cs.clipPath,
                       +r.top.toFixed(1), +r.height.toFixed(1), +cs.opacity]);
      if (performance.now() - t0 < 400) requestAnimationFrame(step);
    }
    return 1;
  })()`);
  await clickSel("#combo-view-btn");
  await evalJs("window.__startC()");
  await sleep(450);
  const comboOpen = await evalJs("window.__c");
  const geo = await evalJs(`(function(){
    var p = document.getElementById("combo-view-list");
    var b = document.getElementById("combo-view-btn");
    var pr = p.getBoundingClientRect(), br = b.getBoundingClientRect();
    var sel = p.querySelector('.fl-combo-item[aria-selected="true"]');
    var sr = sel ? sel.getBoundingClientRect() : null;
    return { popupTop: +pr.top.toFixed(1), popupBottom: +pr.bottom.toFixed(1),
             popupLeft: +pr.left.toFixed(1), popupW: +pr.width.toFixed(1), popupH: +pr.height.toFixed(1),
             btnTop: +br.top.toFixed(1), btnBottom: +br.bottom.toFixed(1),
             btnLeft: +br.left.toFixed(1), btnW: +br.width.toFixed(1), btnH: +br.height.toFixed(1),
             selTop: sr ? +sr.top.toFixed(1) : null, selH: sr ? +sr.height.toFixed(1) : null };
  })()`);

  check("下拉列表：弹层压在按钮上（顶边在按钮顶边上方 2~12px）",
    geo.btnTop - geo.popupTop >= 2 && geo.btnTop - geo.popupTop <= 12,
    `弹层 ${geo.popupTop} / 按钮 ${geo.btnTop} → 露出 ${(geo.btnTop - geo.popupTop).toFixed(1)}px`);
  check("下拉列表：选中项那一行正好盖住按钮（行顶 = 按钮顶 ±1.5px）",
    geo.selTop !== null && Math.abs(geo.selTop - geo.btnTop) <= 1.5,
    `选中行 ${geo.selTop} vs 按钮 ${geo.btnTop}`);
  check("下拉列表：弹层左对齐按钮、宽度不小于按钮、且盖过按钮底部",
    Math.abs(geo.popupLeft - geo.btnLeft) <= 0.5 && geo.popupW >= geo.btnW - 0.5 &&
    geo.popupBottom > geo.btnBottom + 4,
    `left ${geo.popupLeft}/${geo.btnLeft}  w ${geo.popupW}/${geo.btnW}  bottom ${geo.popupBottom}/${geo.btnBottom}`);

  /* clip-path → 已揭示比例 */
  const H0 = geo.popupH;
  const insetBottom = (clip) => {
    const m = /inset\(([\s\S]*)\)/.exec(clip || "");
    if (!m) return null;
    const toks = m[1].match(/calc\([^)]*\)|[-+]?[\d.]+(?:e[-+]?\d+)?(?:px|%)/gi) || [];
    const v = toks.length >= 3 ? toks[2] : toks[0];
    if (!v) return null;
    let val = 0;
    const pct = /(-?[\d.]+(?:e[-+]?\d+)?)%/i.exec(v);
    if (pct) val += parseFloat(pct[1]) / 100 * H0;
    const pxs = /[-+]\s*[\d.]+(?:e[-+]?\d+)?px|^[-+]?[\d.]+(?:e[-+]?\d+)?px/i.exec(v);
    if (pxs) val += parseFloat(pxs[0].replace(/\s+/g, ""));
    return val;
  };
  const series = comboOpen
    .map(([t, clip, top, h, op]) => ({ t, top, h, op, b: insetBottom(clip) }))
    .filter((r) => r.b !== null)
    .map((r) => ({ t: r.t, top: r.top, h: r.h, op: r.op,
                   p: +Math.max(0, Math.min(1, (H0 - r.b + 24) / (H0 + 48))).toFixed(3) }));
  const last = series[series.length - 1];
  const firstMove = series.find((r) => r.p > 0.02) || series[0];
  const done = series.find((r) => r.p >= 0.995) || last;

  check("下拉列表：开合走 clip-path 揭示（不是位移/缩放）",
    series.length > 3 && Math.abs(last.p - 1) < 0.01,
    `${series.length} 个采样，末帧 ${last.p}`);
  /* 第一帧（≈16.7ms）不许过半：上一版 0.58 时真机第一帧就近乎全开，用户反馈「动画没了」 */
  check("下拉列表：第一个渲染帧只走 20%~50%（起手有可见加速段，不是一帧全开）",
    firstMove.p >= 0.20 && firstMove.p <= 0.50, `首帧 ${firstMove.p}（ControlFastOutSlowIn@167ms ≈0.45）`);
  /* 真正决定"看得见动画"的是**能被眼睛分辨的帧数**：60fps 下至少 4 帧揭示高度不同 */
  const distinct = series.filter((r, i) => i === 0 || Math.abs(r.p - series[i - 1].p) > 0.03).length;
  check("下拉列表：60fps 下至少 4 帧揭示高度不同（量得出才发现得了）",
    distinct >= 4, `${distinct} 帧有可辨变化 / 共 ${series.length} 采样`);
  check("下拉列表：整段 100~210ms 收尾（ControlFast 档）",
    done.t - firstMove.t >= 90 && done.t - firstMove.t <= 210,
    `${(done.t - firstMove.t).toFixed(0)}ms（录屏 ≈167ms）`);
  const mid = series.find((r) => r.t >= (firstMove.t + done.t) / 2);
  check("下拉列表：半程进度 ≥ 0.80（快起慢收，不是线性）",
    mid && mid.p >= 0.80, `半程 ${mid ? mid.p : "-"}（ControlFastOutSlowIn 半程 ≈0.89）`);
  check("下拉列表：进度单调不回退",
    series.every((r, i) => i === 0 || r.p >= series[i - 1].p - 0.001),
    series.slice(0, 8).map((r) => r.p).join(","));
  check("下拉列表：不淡入（opacity 全程 1）",
    series.every((r) => r.op === 1), [...new Set(series.map((r) => r.op))].join(","));
  check("下拉列表：揭示期间顶边与盒高都不动（只裁、不长高，避免重排）",
    series.every((r) => Math.abs(r.top - series[0].top) < 0.6 && Math.abs(r.h - series[0].h) < 0.6),
    `top ${Math.min(...series.map((r) => r.top))}~${Math.max(...series.map((r) => r.top))}，` +
    `h ${Math.min(...series.map((r) => r.h))}~${Math.max(...series.map((r) => r.h))}`);

  /* 关闭：瞬变（录屏里没有退场动画） */
  const beforeClose = await comboState();
  await clickSel("#combo-view-btn");
  const afterClose = [];
  for (let i = 0; i < 4; i++) { afterClose.push(await comboState()); await sleep(20); }
  check("下拉列表：关闭是瞬变（一帧内消失，不做退场动画）",
    afterClose.every((r) => !r.open) &&
    Math.abs(parseFloat(afterClose[0].h) - parseFloat(beforeClose.h)) < 0.5,
    JSON.stringify({ open: afterClose[0].open, h: afterClose[0].h }));

  console.log(`\n结果：${pass}/${pass + fail} 通过`);
  ws.close();
  chrome.kill();
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error("FAIL", e); process.exit(1); });
