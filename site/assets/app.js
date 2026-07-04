/* Giá Chợ — the ONLY client JS: draw the Chart.js charts and wire the table
   toggle. All data is server-rendered into the HTML by scripts/build_run.py; the
   chart series ride on the <canvas> data-* attributes (no data script, no fetch). */
(function () {
  "use strict";
  var T1 = "#f4f6fb", T2 = "#a7b0c0", MUTED = "#6b7688";
  var GRID = "rgba(255,255,255,0.06)", HAIR = "rgba(255,255,255,0.12)";
  var SERIES = { chung: "#3987e5", bhx: "#199e70", winmart: "#e66767" };
  var vnd = new Intl.NumberFormat("vi-VN");
  var num1 = new Intl.NumberFormat("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  function attr(el, name) {
    var v = el.getAttribute(name);
    if (!v) return null;
    try { return JSON.parse(v); } catch (e) { return null; }
  }

  var crosshair = {
    id: "crosshair",
    afterDraw: function (c) {
      var t = c.tooltip;
      if (!t || !t.getActiveElements || !t.getActiveElements().length) return;
      var x = t.getActiveElements()[0].element.x, y = c.scales.y, ctx = c.ctx;
      ctx.save(); ctx.beginPath(); ctx.moveTo(x, y.top); ctx.lineTo(x, y.bottom);
      ctx.lineWidth = 1; ctx.strokeStyle = HAIR; ctx.stroke(); ctx.restore();
    }
  };

  function opts(fmt) {
    return {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      layout: { padding: { top: 8, right: 12, bottom: 4, left: 4 } },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#1c222e", borderColor: "rgba(255,255,255,0.10)", borderWidth: 1,
          titleColor: T2, bodyColor: T1, padding: 10, usePointStyle: true,
          callbacks: { label: function (i) { return "  " + i.dataset.label + ": " + fmt(i.parsed.y); } }
        }
      },
      scales: {
        x: { grid: { color: GRID, drawTicks: false }, border: { color: HAIR },
             ticks: { color: MUTED, font: { size: 12 }, maxRotation: 0, autoSkipPadding: 16 } },
        y: { grid: { color: GRID, drawTicks: false }, border: { display: false },
             ticks: { color: MUTED, font: { size: 12 } } }
      },
      elements: { line: { borderWidth: 2, tension: 0.25 },
                  point: { radius: 0, hoverRadius: 5, hitRadius: 24, borderWidth: 2, borderColor: "#141821" } }
    };
  }

  function ds(label, data, color, extra) {
    return Object.assign({ label: label, data: data, borderColor: color, backgroundColor: color, pointBackgroundColor: color }, extra || {});
  }

  function drawIndex(cv) {
    var labels = attr(cv, "data-labels") || [];
    var base = labels.map(function () { return 100; });
    new window.Chart(cv.getContext("2d"), {
      type: "line",
      data: { labels: labels, datasets: [
        ds("Chỉ số chung", attr(cv, "data-chung") || [], SERIES.chung, { borderWidth: 2.5 }),
        ds("BHX", attr(cv, "data-bhx") || [], SERIES.bhx),
        ds("WinMart", attr(cv, "data-winmart") || [], SERIES.winmart),
        ds("Mốc 100", base, MUTED, { borderWidth: 1, borderDash: [4, 4], pointRadius: 0, hoverRadius: 0, hitRadius: 0, order: 99 })
      ] },
      options: opts(function (v) { return v == null ? "–" : num1.format(v); }),
      plugins: [crosshair]
    });
  }

  function drawItem(cv) {
    var unit = cv.getAttribute("data-unit") || "đv";
    new window.Chart(cv.getContext("2d"), {
      type: "line",
      data: { labels: attr(cv, "data-labels") || [], datasets: [
        ds("BHX", attr(cv, "data-bhx") || [], SERIES.bhx),
        ds("WinMart", attr(cv, "data-winmart") || [], SERIES.winmart)
      ] },
      options: opts(function (v) { return v == null ? "–" : vnd.format(Math.round(v)) + "đ"; }),
      plugins: [crosshair]
    });
    cv.setAttribute("aria-label", "Lịch sử đơn giá (đ/" + unit + ")");
  }

  function init() {
    if (window.Chart) {
      var ic = document.getElementById("indexChart"); if (ic) drawIndex(ic);
      var it = document.getElementById("itemChart"); if (it) drawItem(it);
    }
    // table toggles: <button class="toggle" data-target="panelId">
    Array.prototype.forEach.call(document.querySelectorAll(".toggle[data-target]"), function (btn) {
      btn.addEventListener("click", function () {
        var p = document.getElementById(btn.getAttribute("data-target"));
        if (!p) return;
        var hidden = p.hasAttribute("hidden");
        if (hidden) { p.removeAttribute("hidden"); btn.textContent = "Ẩn bảng số liệu"; }
        else { p.setAttribute("hidden", ""); btn.textContent = "Bảng số liệu"; }
      });
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
