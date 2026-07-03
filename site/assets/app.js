/* Giá Chợ — chart + table helpers. Needs Chart.js (vendored: chart.umd.min.js).
   Pages pass data via window.GIACHO; site-builder overwrites that block weekly. */
(function () {
  "use strict";

  var T1 = "#f4f6fb", T2 = "#a7b0c0", MUTED = "#6b7688";
  var GRID = "rgba(255,255,255,0.06)", HAIR = "rgba(255,255,255,0.12)";
  var SERIES = { chung: "#3987e5", bhx: "#199e70", winmart: "#e66767" };

  var vnd = new Intl.NumberFormat("vi-VN");
  var num1 = new Intl.NumberFormat("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  function fmtIndex(v) { return v == null ? "–" : num1.format(v); }
  function fmtVnd(v) { return v == null ? "–" : vnd.format(Math.round(v)) + "đ"; }

  // Vertical crosshair on hover — readers aim at a week, not a 2px line.
  var crosshair = {
    id: "crosshair",
    afterDraw: function (c) {
      var t = c.tooltip;
      if (!t || !t.getActiveElements || !t.getActiveElements().length) return;
      var x = t.getActiveElements()[0].element.x;
      var ya = c.scales.y;
      var ctx = c.ctx;
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(x, ya.top);
      ctx.lineTo(x, ya.bottom);
      ctx.lineWidth = 1;
      ctx.strokeStyle = HAIR;
      ctx.stroke();
      ctx.restore();
    }
  };

  function baseChartOpts(yTitle, yFmt) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      layout: { padding: { top: 8, right: 12, bottom: 4, left: 4 } },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#1c222e",
          borderColor: "rgba(255,255,255,0.10)",
          borderWidth: 1,
          titleColor: T2,
          bodyColor: T1,
          padding: 10,
          usePointStyle: true,
          callbacks: { label: function (i) { return "  " + i.dataset.label + ": " + yFmt(i.parsed.y); } }
        }
      },
      scales: {
        x: { grid: { color: GRID, drawTicks: false }, border: { color: HAIR },
             ticks: { color: MUTED, font: { size: 12 }, maxRotation: 0, autoSkipPadding: 16 } },
        y: { grid: { color: GRID, drawTicks: false }, border: { display: false },
             ticks: { color: MUTED, font: { size: 12 } },
             title: { display: !!yTitle, text: yTitle || "", color: MUTED, font: { size: 12 } } }
      },
      elements: { line: { borderWidth: 2, tension: 0.25 }, point: { radius: 0, hoverRadius: 5, hitRadius: 24, borderWidth: 2, borderColor: "#141821" } }
    };
  }

  function line(label, data, color, opts) {
    return Object.assign({ label: label, data: data, borderColor: color, backgroundColor: color, pointBackgroundColor: color }, opts || {});
  }

  // Dashboard index chart: 3 series + base-100 reference line.
  function initIndexChart(canvas, d) {
    if (!canvas || !window.Chart) return;
    var base100 = d.labels.map(function () { return 100; });
    var ds = [
      line("Chỉ số chung", d.chung, SERIES.chung, { borderWidth: 2.5 }),
      line("BHX", d.bhx, SERIES.bhx),
      line("WinMart", d.winmart, SERIES.winmart),
      line("Mốc 100", base100, MUTED, { borderWidth: 1, borderDash: [4, 4], pointRadius: 0, hoverRadius: 0, hitRadius: 0, order: 99 })
    ];
    new window.Chart(canvas.getContext("2d"), {
      type: "line",
      data: { labels: d.labels, datasets: ds },
      options: baseChartOpts("", fmtIndex),
      plugins: [crosshair]
    });
  }

  // Item page: 2 chains' đơn giá chuẩn over time.
  function initItemChart(canvas, d) {
    if (!canvas || !window.Chart) return;
    var ds = [ line("BHX", d.bhx, SERIES.bhx), line("WinMart", d.winmart, SERIES.winmart) ];
    new window.Chart(canvas.getContext("2d"), {
      type: "line",
      data: { labels: d.labels, datasets: ds },
      options: baseChartOpts("đ / " + (d.unit || "đơn vị"), fmtVnd),
      plugins: [crosshair]
    });
  }

  // Table-view toggle (accessibility twin for every chart).
  function wireToggle(btn, panel) {
    if (!btn || !panel) return;
    btn.addEventListener("click", function () {
      var hidden = panel.hasAttribute("hidden");
      if (hidden) { panel.removeAttribute("hidden"); btn.textContent = "Ẩn bảng số liệu"; }
      else { panel.setAttribute("hidden", ""); btn.textContent = "Bảng số liệu"; }
    });
  }

  window.GiaCho = { initIndexChart: initIndexChart, initItemChart: initItemChart, wireToggle: wireToggle, fmtIndex: fmtIndex, fmtVnd: fmtVnd };
})();
