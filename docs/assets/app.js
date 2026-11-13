/* 学习路径站点的交互层：渲染路线图、节点抽屉、笔记/代码查看。 */

(() => {
  "use strict";

  const ROADMAP = window.ROADMAP;
  const $ = (sel, root = document) => root.querySelector(sel);

  const state = {
    manifest: { notes: [], code: [], research: [], generatedAt: "" },
    activeNode: null,
    activeTab: "overview",
  };

  /* ---------------------------------------------------------------- 数据 */

  const notesByDay = () => groupBy(state.manifest.notes, "day");
  const codeByDay = () => groupBy(state.manifest.code, "day");

  function groupBy(list, key) {
    return list.reduce((acc, item) => {
      (acc[item[key]] ||= []).push(item);
      return acc;
    }, {});
  }

  function nodeNotes(node) {
    const byDay = notesByDay();
    return (node.days || []).flatMap((day) => byDay[day] || []);
  }

  function nodeCode(node) {
    const byDay = codeByDay();
    return (node.days || []).flatMap((day) => byDay[day] || []);
  }

  function nodeRatio(node) {
    const days = node.days || [];
    if (!days.length) return { label: "未排期", filled: 0, total: 0 };
    const byDay = notesByDay();
    const code = codeByDay();
    const filled = days.filter((d) => (byDay[d] || []).length || (code[d] || []).length).length;
    return { label: `${filled}/${days.length}`, filled, total: days.length };
  }

  /* -------------------------------------------------------------- 渲染图 */

  function renderLegend() {
    $("#legend").innerHTML = ROADMAP.bands
      .map(
        (band) =>
          `<span class="legend-item" data-accent="${band.accent}">` +
          `<span class="legend-dot"></span>${esc(band.name)}</span>`
      )
      .join("");
  }

  function renderRoadmap() {
    const root = $("#roadmap");
    root.innerHTML = ROADMAP.bands
      .map((band, index) => {
        const nodes = ROADMAP.nodes.filter((n) => n.band === band.id);
        const cards = nodes.map((node) => renderCard(node)).join("");
        return `
          <section class="band" data-accent="${band.accent}">
            <div class="band-head">
              <span class="band-index">${String(index + 1).padStart(2, "0")}</span>
              <h2 class="band-name">${esc(band.name)}</h2>
              <span class="band-note">${esc(band.note)}</span>
              <span class="band-line"></span>
            </div>
            <div class="band-body">
              <div class="band-rail"></div>
              <div class="band-cards">${cards}</div>
            </div>
          </section>`;
      })
      .join("");

    root.querySelectorAll(".node").forEach((el) => {
      el.addEventListener("click", () => openNode(el.dataset.id));
    });
  }

  function renderCard(node) {
    const ratio = nodeRatio(node);
    const hasContent = ratio.filled > 0;
    const dots = ratio.total
      ? Array.from({ length: ratio.total }, (_, i) =>
          `<span class="node-dot${i < ratio.filled ? " is-on" : ""}"></span>`
        ).join("")
      : "";

    return `
      <button class="node${hasContent ? "" : " is-empty"}" data-id="${esc(node.id)}" type="button">
        <div class="node-top">
          <span class="node-badge">${esc(node.badge)}</span>
          <span class="node-ratio">${esc(ratio.label)}</span>
        </div>
        <h3 class="node-name">${esc(node.name)}</h3>
        <p class="node-sub">${esc(node.sub)}</p>
        <p class="node-lead">${esc(node.lead)}</p>
        <div class="node-dots">${dots}</div>
      </button>`;
  }

  function renderStops() {
    $("#stop-list").innerHTML = ROADMAP.stops
      .map(
        (stop) =>
          `<li><span class="stop-day">${esc(stop.day)}</span><span>${esc(stop.text)}</span></li>`
      )
      .join("");
  }

  function renderStats() {
    const byDay = notesByDay();
    const code = codeByDay();
    const days = new Set([...Object.keys(byDay), ...Object.keys(code)]);
    $("#stat-progress .stat-num").textContent = days.size;
    $("#build-stamp").textContent = state.manifest.generatedAt
      ? `构建于 ${state.manifest.generatedAt}`
      : "";
  }

  /* ------------------------------------------------------------ 节点抽屉 */

  function openNode(id) {
    const node = ROADMAP.nodes.find((n) => n.id === id);
    if (!node) return;
    state.activeNode = node;

    const band = ROADMAP.bands.find((b) => b.id === node.band);
    const drawer = $("#drawer");
    drawer.dataset.accent = band.accent;

    $("#drawer-kicker").textContent = `${band.name} · ${band.note}`;
    $("#drawer-title").textContent = node.name;
    $("#drawer-lead").textContent = node.lead;
    $("#drawer-tags").innerHTML = (node.skills || [])
      .map((s) => `<span class="tag">${esc(s)}</span>`)
      .join("");

    const notes = nodeNotes(node);
    const code = nodeCode(node);
    $("#count-notes").textContent = notes.length;
    $("#count-code").textContent = code.length;

    renderOverview(node, band);
    renderDocList("notes", notes, node);
    renderDocList("code", code, node);

    switchTab("overview");
    document.body.classList.add("drawer-open");
    document.body.classList.add("is-locked");
    drawer.setAttribute("aria-hidden", "false");
    $("#drawer-close").focus({ preventScroll: true });
    history.replaceState(null, "", `#${node.id}`);
  }

  function closeDrawer() {
    state.activeNode = null;
    document.body.classList.remove("drawer-open");
    document.body.classList.remove("is-locked");
    $("#drawer").setAttribute("aria-hidden", "true");
    history.replaceState(null, "", location.pathname);
  }

  function renderOverview(node, band) {
    const gaps = node.gap
      ? `<div class="gap-note"><span>⚠</span><span>${esc(node.gap)}</span></div>`
      : "";

    const plan = node.plan
      .map(
        (row) => `
        <div class="plan-row${row.done ? " is-done" : ""}">
          <span class="plan-day">${esc(row.day)}</span>
          <div>
            <p class="plan-task">${esc(row.task)}${row.done ? '<span class="done-mark">已完成</span>' : ""}</p>
            <p class="plan-out">${esc(row.out)}</p>
          </div>
        </div>`
      )
      .join("");

    $("#panel-overview").innerHTML = `
      <p class="lede">${esc(node.desc)}</p>
      ${gaps}
      <div class="block">
        <h3 class="block-title">计划与产出</h3>
        <div class="plan">${plan}</div>
      </div>
      <div class="block">
        <h3 class="block-title">涉及技能</h3>
        <div class="skill-list">${(node.skills || [])
          .map((s) => `<span class="skill">${esc(s)}</span>`)
          .join("")}</div>
      </div>`;
  }

  function renderDocList(panelName, items, node) {
    const panel = $(`#panel-${panelName}`);
    if (!items.length) {
      panel.innerHTML =
        panelName === "notes"
          ? `<div class="empty">这个节点还没有产出的笔记。<br>每天写完 <code>notes/${node.days[0] || "dayNN"}/</code> 后会自动出现在这里。</div>`
          : `<div class="empty">这个节点还没有产出的代码。<br>每天写完 <code>${node.days[0] || "dayNN"}/python/</code> 后会自动出现在这里。</div>`;
      return;
    }

    panel.innerHTML = `<div class="doc-list">${items
      .map((item) => {
        const isNote = panelName === "notes";
        const name = isNote ? item.title : item.name;
        const meta = isNote
          ? [item.day, item.status === "done" ? "已完成" : "", (item.tags || [])[0] || ""]
              .filter(Boolean)
              .join(" · ")
          : `${item.dir === "java" ? "Java 对照" : "Python"} · ${item.lines} 行`;
        return `
          <button class="doc-item" type="button"
                  data-path="${esc(item.path)}"
                  data-title="${esc(name)}"
                  data-meta="${esc(meta)}"
                  data-kind="${isNote ? "note" : "code"}">
            <span class="doc-icon">${isNote ? "¶" : "</>"}</span>
            <span class="doc-main">
              <span class="doc-name">${esc(name)}</span>
              <span class="doc-meta">${esc(meta)}</span>
            </span>
          </button>`;
      })
      .join("")}</div>`;

    panel.querySelectorAll(".doc-item").forEach((el) => {
      el.addEventListener("click", () => openDoc(panelName, el.dataset));
    });
  }

  async function openDoc(panelName, data) {
    const panel = $(`#panel-${panelName}`);
    const previous = panel.innerHTML;

    panel.innerHTML = `<div class="empty">加载中…</div>`;
    try {
      const response = await fetch(`content/${data.path}`);
      if (!response.ok) throw new Error(String(response.status));
      const html = await response.text();
      panel.innerHTML = `
        <div class="block">
          <button class="doc-item" type="button" id="doc-back">
            <span class="doc-icon">←</span>
            <span class="doc-main">
              <span class="doc-name">返回列表</span>
              <span class="doc-meta">${esc(data.title)}</span>
            </span>
          </button>
        </div>
        <div class="md ${data.kind === "code" ? "is-code" : ""}">${html}</div>`;
      $("#doc-back").addEventListener("click", () => {
        panel.innerHTML = previous;
        panel.querySelectorAll(".doc-item").forEach((el) => {
          el.addEventListener("click", () => openDoc(panelName, el.dataset));
        });
        $(".drawer-scroll").scrollTop = 0;
      });
      $(".drawer-scroll").scrollTop = 0;
    } catch (error) {
      panel.innerHTML = `<div class="empty">加载失败：${esc(String(error.message))}</div>`;
    }
  }

  /* ---------------------------------------------------------------- tabs */

  function switchTab(name) {
    state.activeTab = name;
    document.querySelectorAll(".tab").forEach((tab) => {
      tab.classList.toggle("is-active", tab.dataset.tab === name);
    });
    document.querySelectorAll(".panel").forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.panel === name);
    });
    const scroller = $(".drawer-scroll");
    if (scroller) scroller.scrollTop = 0;
  }

  /* -------------------------------------------------------------- 调研弹窗 */

  function renderResearch() {
    const groups = state.manifest.research.reduce((acc, item) => {
      (acc[item.group] ||= []).push(item);
      return acc;
    }, {});

    const html = Object.entries(groups)
      .map(
        ([group, items]) => `
        <div class="research-group">
          <h3>${esc(group)}</h3>
          <div class="doc-list">${items
            .map(
              (item) => `
            <button class="doc-item" type="button" data-path="${esc(item.path)}" data-title="${esc(item.title)}">
              <span class="doc-icon">¶</span>
              <span class="doc-main">
                <span class="doc-name">${esc(item.title)}</span>
                <span class="doc-meta">markdown 渲染</span>
              </span>
            </button>`
            )
            .join("")}</div>
        </div>`
      )
      .join("");

    $("#modal-body").innerHTML = html;
    $("#modal-body").querySelectorAll(".doc-item").forEach((el) => {
      el.addEventListener("click", async () => {
        const response = await fetch(`content/${el.dataset.path}`);
        const text = await response.text();
        $("#modal-body").innerHTML = `
          <button class="doc-item" type="button" id="modal-back">
            <span class="doc-icon">←</span>
            <span class="doc-main"><span class="doc-name">返回列表</span></span>
          </button>
          <div class="md">${text}</div>`;
        $("#modal-back").addEventListener("click", renderResearch);
      });
    });
  }

  function openModal() {
    $("#modal").classList.add("is-open");
    $("#modal").setAttribute("aria-hidden", "false");
    document.body.classList.add("is-locked");
  }

  function closeModal() {
    $("#modal").classList.remove("is-open");
    $("#modal").setAttribute("aria-hidden", "true");
    if (!document.body.classList.contains("drawer-open")) {
      document.body.classList.remove("is-locked");
    }
  }

  /* --------------------------------------------------------------- 主题 */

  function initTheme() {
    let theme = localStorage.getItem("jal-theme");
    if (theme !== "light" && theme !== "dark") {
      theme = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    }
    document.documentElement.dataset.theme = theme;

    $("#btn-theme").addEventListener("click", () => {
      const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      localStorage.setItem("jal-theme", next);
    });
  }

  /* ---------------------------------------------------------------- 工具 */

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[ch]);
  }

  /* ---------------------------------------------------------------- 启动 */

  async function boot() {
    initTheme();
    renderLegend();
    renderRoadmap();
    renderStops();

    try {
      const response = await fetch("content/manifest.json", { cache: "no-store" });
      state.manifest = await response.json();
    } catch {
      console.warn("manifest 未找到，先运行 tools/build_site.py");
    }

    renderStats();
    renderRoadmap();
    renderResearch();

    $("#drawer-close").addEventListener("click", closeDrawer);
    $("#scrim").addEventListener("click", closeDrawer);
    $("#btn-research").addEventListener("click", openModal);
    $("#modal-close").addEventListener("click", closeModal);
    $("#modal").addEventListener("click", (event) => {
      if (event.target.id === "modal") closeModal();
    });

    $("#tabs").addEventListener("click", (event) => {
      const tab = event.target.closest(".tab");
      if (tab) switchTab(tab.dataset.tab);
    });

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if ($("#modal").classList.contains("is-open")) closeModal();
      else if (state.activeNode) closeDrawer();
    });

    const hash = location.hash.replace("#", "");
    if (hash && ROADMAP.nodes.some((n) => n.id === hash)) openNode(hash);
  }

  boot();
})();
