(() => {
  "use strict";
  const DATA_DIR = "data/catalog/winmart/";
  const grid = document.getElementById("catalog-grid");
  const pager = document.getElementById("catalog-pager");
  const sub = document.getElementById("catalog-sub");
  const countEl = document.getElementById("catalog-count");
  const updatedEl = document.getElementById("catalog-updated");
  const els = {
    search: document.getElementById("f-search"),
    category: document.getElementById("f-category"),
    instock: document.getElementById("f-instock"),
    promo: document.getElementById("f-promo"),
    sort: document.getElementById("f-sort"),
    pagesize: document.getElementById("f-pagesize"),
  };

  let allItems = [];
  let page = 1;

  const deaccent = (s) => (s || "")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();

  const vnd = (n) => n == null ? "–" : `${Math.round(n).toLocaleString("vi-VN")}đ`;

  async function loadCatalog() {
    const idx = await fetch(DATA_DIR + "index.json").then(r => r.json());
    updatedEl.textContent = idx.updated ? `Cập nhật lần cuối: ${idx.updated}` : "";
    for (const cat of idx.categories || []) {
      const opt = document.createElement("option");
      opt.value = cat; opt.textContent = cat;
      els.category.appendChild(opt);
    }
    const parts = await Promise.all(
      (idx.chunks || []).map(f => fetch(DATA_DIR + f).then(r => r.json()))
    );
    allItems = parts.flat();
    sub.textContent = `${idx.total_count?.toLocaleString("vi-VN") ?? allItems.length} sản phẩm` +
      (idx.stats?.so_danh_muc ? ` trong ${idx.stats.so_danh_muc} danh mục` : "") + ".";
    render();
  }

  function filtered() {
    const q = deaccent(els.search.value.trim());
    const cat = els.category.value;
    const onlyStock = els.instock.checked;
    const onlyPromo = els.promo.checked;
    return allItems.filter(it => {
      if (q && !deaccent(it.ten).includes(q)) return false;
      if (cat && it.danh_muc !== cat) return false;
      if (onlyStock && it.trang_thai !== "in_stock") return false;
      if (onlyPromo && !it.gia_khuyen_mai) return false;
      return true;
    });
  }

  function sorted(items) {
    const by = els.sort.value;
    const copy = items.slice();
    if (by === "name-asc") copy.sort((a, b) => (a.ten || "").localeCompare(b.ten || "", "vi"));
    else if (by === "price-asc") copy.sort((a, b) => (a.gia_ban ?? Infinity) - (b.gia_ban ?? Infinity));
    else if (by === "price-desc") copy.sort((a, b) => (b.gia_ban ?? -1) - (a.gia_ban ?? -1));
    else if (by === "discount-desc") copy.sort((a, b) => (b.giam_gia_pct ?? -1) - (a.giam_gia_pct ?? -1));
    return copy;
  }

  function cardHtml(it) {
    const thumb = it.hinh_anh
      ? `<img class="thumb" src="${esc(it.hinh_anh)}" alt="${esc(it.ten)}" loading="lazy">`
      : `<div class="thumb ph">🛒</div>`;
    const badge = it.giam_gia_pct ? `<span class="badge-discount">-${it.giam_gia_pct}%</span>` : "";
    const oldPrice = it.gia_khuyen_mai ? `<span class="price-old-sm">${vnd(it.gia_niem_yet)}</span>` : "";
    const stockNote = it.trang_thai !== "in_stock" ? `<div class="stock-out">Hết hàng</div>` : "";
    return `<a class="card pcard" href="${esc(it.url || '#')}" target="_blank" rel="noopener">
      <div class="thumb-wrap">${thumb}${badge}</div>
      <div class="pn">${esc(it.ten)}</div>
      <div class="pg">${esc(it.danh_muc || "")}</div>
      <div class="pp">${oldPrice}<span class="amt">${vnd(it.gia_ban)}</span><span class="unit"> /${esc(it.don_vi || "sp")}</span></div>
      ${stockNote}
    </a>`;
  }

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function render() {
    const items = sorted(filtered());
    const pageSize = parseInt(els.pagesize.value, 10);
    const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
    if (page > totalPages) page = totalPages;
    if (page < 1) page = 1;

    countEl.textContent = `${items.length.toLocaleString("vi-VN")} kết quả`;

    if (!items.length) {
      grid.innerHTML = `<div class="catalog-empty">Không tìm thấy sản phẩm phù hợp.</div>`;
      pager.innerHTML = "";
      return;
    }

    const start = (page - 1) * pageSize;
    const pageItems = items.slice(start, start + pageSize);
    grid.innerHTML = pageItems.map(cardHtml).join("");
    renderPager(totalPages);
  }

  function renderPager(totalPages) {
    if (totalPages <= 1) { pager.innerHTML = ""; return; }
    const btn = (label, target, opts = {}) =>
      `<button ${opts.disabled ? "disabled" : ""} ${opts.active ? 'class="active"' : ""} data-page="${target}">${label}</button>`;

    let html = btn("←", page - 1, { disabled: page <= 1 });
    const windowSize = 2;
    const shown = new Set([1, totalPages]);
    for (let p = page - windowSize; p <= page + windowSize; p++) if (p >= 1 && p <= totalPages) shown.add(p);
    let prev = 0;
    for (const p of [...shown].sort((a, b) => a - b)) {
      if (prev && p - prev > 1) html += `<span class="pageinfo">…</span>`;
      html += btn(String(p), p, { active: p === page });
      prev = p;
    }
    html += btn("→", page + 1, { disabled: page >= totalPages });
    pager.innerHTML = html;
    pager.querySelectorAll("button[data-page]").forEach(b => {
      b.addEventListener("click", () => { page = parseInt(b.dataset.page, 10); render(); scrollTo({ top: 0, behavior: "smooth" }); });
    });
  }

  for (const el of [els.search, els.category, els.instock, els.promo, els.sort]) {
    el.addEventListener("input", () => { page = 1; render(); });
    el.addEventListener("change", () => { page = 1; render(); });
  }
  els.pagesize.addEventListener("change", () => { page = 1; render(); });

  grid.innerHTML = `<div class="catalog-loading">Đang tải dữ liệu…</div>`;
  loadCatalog().catch(err => {
    sub.textContent = "Không tải được dữ liệu sản phẩm.";
    grid.innerHTML = `<div class="catalog-empty">Lỗi tải dữ liệu: ${esc(err.message)}</div>`;
    console.error(err);
  });
})();
