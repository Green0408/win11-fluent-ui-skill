/* tests/direction_test.js —— 用最小 DOM 桩跑真实的 M.transitionTo，断言四个方向的符号
   跑法：node tests/direction_test.js  （零依赖，不需要浏览器）
   目的：把「竖向只能从下方进入」这类缺陷锁死 —— 它当初能溜过去，就是因为没有行为级测试。 */
"use strict";
const fs = require("fs");
const path = require("path");

/* ---------- 最小 DOM 桩 ---------- */
function makeEl(id, attrs) {
  const el = {
    id: id || "",
    _attrs: attrs || {},
    _props: {},
    _classes: new Set(id === "page-current" ? ["fl-page", "fl-current"] : ["fl-page"]),    style: { setProperty: (k, v) => { el._props[k] = v; }, removeProperty: (k) => { delete el._props[k]; } },
    offsetWidth: 100,
    offsetHeight: 100,
    parentElement: { style: {} },
    classList: {
      contains: (c) => el._classes.has(c),
      add: (...cs) => cs.forEach((c) => el._classes.add(c)),
      remove: (...cs) => cs.forEach((c) => el._classes.delete(c)),
    },
    getAttribute: (k) => (k in el._attrs ? el._attrs[k] : null),
    querySelectorAll: () => [],
    addEventListener: () => {},
    removeEventListener: () => {},
  };
  return el;
}

function boot(pages, navItems) {
  const byId = {};
  pages.forEach((p) => { byId[p.id] = p; });
  navItems.forEach((n) => { byId["nav:" + n.page] = n; });

  const doc = {
    getElementById: (id) => byId[id] || null,
    querySelectorAll: (sel) => {
      if (sel.startsWith(".fl-page")) return pages;
      if (sel.startsWith(".fl-nav-item")) return navItems;
      if (sel.startsWith(".fl-entrance")) return [];
      return [];
    },
    querySelector: (sel) => {
      if (sel === ".fl-page.fl-current") return pages.find((p) => p.classList.contains("fl-current")) || null;
      return null;
    },
    addEventListener: () => {},
    documentElement: { getAttribute: () => "dark", setAttribute: () => {} },
  };
  const win = {
    document: doc,
    matchMedia: () => ({ matches: false, addEventListener: () => {} }),
    setTimeout: (fn) => 0,
    requestAnimationFrame: (fn) => 0,
    console,
  };
  const code = fs.readFileSync(path.join(__dirname, "..", "fluent2-motion.js"), "utf8");
  new Function("window", "document", "globalThis", code)(win, doc, win);
  return win.M;
}

/* ---------- 断言 ---------- */
let fail = 0;
function eq(label, actual, expect) {
  const ok = actual === expect;
  if (!ok) fail++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${label}  期望 ${expect}  实际 ${actual}`);
}

/* 场景：三个导航项 main / grid / settings，顺序即侧栏顺序 */
function scenario() {
  const main = makeEl("page-main");
  main._classes.add("fl-current");   // 初始当前页 = main（侧栏第一项）
  const grid = makeEl("page-grid");
  const settings = makeEl("page-settings");
  const nav = [
    makeEl("nav:main", { "data-page": "page-main" }),
    makeEl("nav:grid", { "data-page": "page-grid" }),
    makeEl("nav:settings", { "data-page": "page-settings" }),
  ];
  return { pages: [main, grid, settings], nav };
}

/* 1) 点下面的导航项 → 新页自下方进入（+72px） */
{
  const s = scenario();
  const M = boot(s.pages, s.nav);
  M.transitionTo("page-settings");         // 从 main 跳到 settings（更靠下）
  eq("main→settings 入页起点 y", s.pages[2]._props["--fl-page-from-y"], "var(--fl-page-shift-y)");
  eq("main→settings 出页终点 y", s.pages[0]._props["--fl-page-to-y"], "calc(var(--fl-page-shift-y) * -1)");
  eq("main→settings 无 x 位移", s.pages[2]._props["--fl-page-from-x"], "0px");
}

/* 2) 点上面的导航项 → 新页自上方进入（-72px）—— 这是修复前拿不到的方向 */
{
  const s = scenario();
  const M = boot(s.pages, s.nav);
  M.transitionTo("page-settings");          // 先到 settings
  s.pages[0]._classes.delete("fl-current");
  s.pages[2]._classes.add("fl-current");
  M.transitionTo("page-main");              // 再点回最上面的 main
  eq("settings→main 入页起点 y", s.pages[0]._props["--fl-page-from-y"], "calc(var(--fl-page-shift-y) * -1)");
  eq("settings→main 出页终点 y", s.pages[2]._props["--fl-page-to-y"], "var(--fl-page-shift-y)");
}

/* 3) 页面栈语义：settings→main 是「点上面那条」，不是返回，栈不能被截断 */
{
  const s = scenario();
  const M = boot(s.pages, s.nav);
  M.transitionTo("page-settings");
  s.pages[0]._classes.delete("fl-current");
  s.pages[2]._classes.add("fl-current");
  M.transitionTo("page-main");
  s.pages[2]._classes.delete("fl-current");
  s.pages[0]._classes.add("fl-current");
  M.back("nav");                            // 栈顶应是 settings，而不是 grid
  eq("up 不截断栈，back 回到 settings", s.pages[2]._classes.has("fl-current"), true);
  eq("back 的入页起点 y（回到上一页 = 自上方进入）", s.pages[2]._props["--fl-page-from-y"],
     "calc(var(--fl-page-shift-y) * -1)");
}

/* 4) 显式 dir:up / down 覆盖自动推断 */
{
  const s = scenario();
  const M = boot(s.pages, s.nav);
  M.transitionTo("page-grid", { dir: "up" });   // 目标是下方项，但强制"从上方进入"
  eq("显式 dir:up 入页起点 y", s.pages[1]._props["--fl-page-from-y"], "calc(var(--fl-page-shift-y) * -1)");
}
{
  const s = scenario();
  const M = boot(s.pages, s.nav);
  M.transitionTo("page-settings", { dir: "left" });  // 显式左 → 走 x 轴 176px
  eq("显式 dir:left 入页起点 x（负=自左侧进入）", s.pages[2]._props["--fl-page-from-x"],
     "calc(var(--fl-page-shift-x) * -1)");
  eq("显式 dir:left 无 y 位移", s.pages[2]._props["--fl-page-from-y"], "0px");
}

/* 5) drill + 显式 up：轴由方向定 → 变垂直，行程仍是 72 */
{
  const s = scenario();
  const M = boot(s.pages, s.nav);
  M.transitionTo("page-grid", { kind: "drill", dir: "up" });
  eq("drill+up 改走 y 轴", s.pages[1]._props["--fl-page-from-y"], "calc(var(--fl-page-shift-y) * -1)");
  eq("drill+up 无 x 位移", s.pages[1]._props["--fl-page-from-x"], "0px");
}

/* 6) drill 缺省仍为水平 right（与旧行为一致） */
{
  const s = scenario();
  const M = boot(s.pages, s.nav);
  M.transitionTo("page-grid", { kind: "drill" });
  eq("drill 缺省入页起点 x", s.pages[1]._props["--fl-page-from-x"], "var(--fl-page-shift-x)");
}

/* 7) 非法 dir 不再静默变成 forward：回退自动推断（这里是向下项 → +y），并告警 */
{
  const s = scenario();
  const M = boot(s.pages, s.nav);
  const warns = [];
  const orig = console.warn;
  console.warn = (...a) => warns.push(a.join(" "));
  M.transitionTo("page-settings", { dir: "top" });
  console.warn = orig;
  eq("非法 dir 回退为导航序（向下）", s.pages[2]._props["--fl-page-from-y"], "var(--fl-page-shift-y)");
  eq("非法 dir 触发告警", warns.length > 0, true);
}

/* 8) 点同一个导航项：早退，不写变量、不动栈 */
{
  const s = scenario();
  const M = boot(s.pages, s.nav);
  M.transitionTo("page-main");
  eq("同项早退不写变量", Object.keys(s.pages[0]._props).length, 0);
  eq("同项早退不入栈（栈仍为空，back 返回 null）", M.stack().length, 0);
}

console.log(fail === 0 ? "\n全部通过" : `\n${fail} 项失败`);
process.exit(fail === 0 ? 0 : 1);
