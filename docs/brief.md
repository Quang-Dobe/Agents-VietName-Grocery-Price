# Brief: `vn-grocery-price-index` — Giá thực phẩm / hàng tiêu dùng

> Original brief this project is built from. The actionable, decision-locked
> version is [`PLAN.md`](PLAN.md); feasibility evidence is
> [`research/POC-FINDINGS.md`](research/POC-FINDINGS.md).

---

## 1. Mục tiêu

Theo dõi giá một **"rổ hàng hóa" cố định (~30-50 SKU)** từ Bách Hóa Xanh và WinMart
online **hàng tuần**, xây dựng **chỉ số giá sinh hoạt tự tạo** (CPI mini, base 100
tại tuần đầu), deploy dashboard static lên GitHub Pages. Agent tự viết nhận xét
tuần bằng chính session routine (KHÔNG dùng Claude API).

## 2. Hạ tầng: Claude Code Routines

- **1 Routine chính**, trigger: scheduled weekly, **thứ Bảy** (+1 run dự phòng Chủ
  nhật, prompt kiểm tra: nếu `data/prices/` đã có snapshot tuần này thì exit sớm)
- **Custom cloud environment**: thêm allowed domains `bachhoaxanh.com`,
  `www.bachhoaxanh.com`, `winmart.vn`, `www.winmart.vn` (+ domain API nội bộ nếu
  phát hiện)
- **Deploy**: bật unrestricted branch push → commit thẳng `main` → GitHub Pages
- Không có backfill — dữ liệu tích lũy từ tuần đầu chạy

## 3. Rủi ro lớn nhất: chống bot

BHX/WinMart có thể dùng Cloudflare hoặc chặn IP datacenter. Routine chạy từ IP
cloud Anthropic → rủi ro bị chặn cao hơn. Cần proof-of-concept sớm:
- Tìm JSON API nội bộ của 2 trang
- Nếu HTML bị chặn: thử headers/User-Agent hợp lý, tốc độ chậm
- Fallback cuối: chuyển sang Desktop scheduled task (local) — IP dân cư

## 4. Multi-agent orchestration

| Agent | Nhiệm vụ | Chạy |
|---|---|---|
| `crawler-bhx` | Crawl giá SKU từ BHX; tự xử lý hết hàng/đổi URL | Song song |
| `crawler-winmart` | Tương tự cho WinMart | Song song |
| `validator` | Phát hiện giá bất thường, giữ/loại, ghi lý do | Sau crawl |
| `index-calculator` | Tính chỉ số có trọng số, top tăng/giảm | Sau validate |
| `site-builder` | Build dashboard + trang chi tiết; viết nhận xét tuần | Cuối |

## 5. Thiết kế rổ hàng

File `basket.json` cố định. Nhóm hàng: gạo, thịt heo/gà/bò, cá, trứng, rau củ, dầu
ăn, nước mắm, đường, muối, sữa, mì gói, cà phê, giấy vệ sinh, nước rửa chén. Xử lý:
giá KM vs giá gốc (lưu cả hai), quy đổi đơn giá chuẩn, SKU hết hàng carry-forward
tối đa 2 tuần.

## 6. Schema & công thức

Laspeyres đơn giản, base 100 tại tuần đầu. Tính riêng BHX, WinMart và chỉ số chung.

## 7. Static site

Dashboard (chỉ số + delta + biểu đồ + top tăng/giảm + so sánh + nhận xét), trang
chi tiết mỗi mặt hàng (Chart.js), trang phương pháp luận.

## 8. Các quyết định cần chốt

SKU + trọng số; chính sách thay thế; mở rộng chain khác; robots.txt + tốc độ; cloud
vs local. → tất cả đã chốt trong [`PLAN.md`](PLAN.md) §0.
