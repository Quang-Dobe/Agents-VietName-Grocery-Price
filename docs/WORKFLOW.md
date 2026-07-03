# Cách hoạt động — Workflow

> Trang này giải thích chỉ số giá được tạo ra như thế nào, mỗi tuần. Dashboard liên
> kết tới đây. Ngắn gọn, dễ hiểu.

## Tóm tắt một dòng

Mỗi tuần, một routine tự động ghé BHX và WinMart, lấy giá của **40 mặt hàng cố
định**, tính ra một **chỉ số giá** (base 100 ở tuần đầu), rồi cập nhật dashboard.

## Sơ đồ

```
   Thứ Bảy hàng tuần (tự động)
            │
   ┌────────┴────────┐
   │  crawler-bhx    │  ─┐  chạy song song
   │  crawler-winmart│  ─┘  → giá thô của 40 SKU × 2 siêu thị
   └────────┬────────┘
            │
      validator        → lọc giá bất thường (nhảy > 50% = nghi lỗi)
            │
   index-calculator    → tính chỉ số có trọng số + top tăng/giảm
            │
     site-builder      → dựng lại dashboard + viết nhận xét tuần
            │
   commit → GitHub Pages tự cập nhật
```

## 5 bước

1. **Thu thập giá** — Hai agent chạy song song, mỗi agent lấy giá một siêu thị qua
   **API nội bộ** của trang (nhanh, ít bị chặn, dễ đọc hơn HTML). Lấy cả *giá niêm
   yết* và *giá khuyến mãi*, rồi quy về **đơn giá chuẩn** (đ/kg, đ/lít, đ/quả) để so
   sánh công bằng giữa hai nơi.
2. **Kiểm tra** — Một agent soát lỗi: giá nhảy quá 50% so với tuần trước bị nghi là
   lỗi và loại, hàng hết được giữ giá cũ tối đa 2 tuần. Mọi quyết định đều ghi log.
3. **Tính chỉ số** — Trung bình có trọng số của tỷ lệ *giá tuần này / giá tuần đầu*
   (Laspeyres đơn giản). Tính riêng BHX, WinMart, và chỉ số chung.
4. **Dựng trang** — Cập nhật biểu đồ, top tăng/giảm, và **một đoạn nhận xét ngắn do
   agent tự viết** (không dùng API).
5. **Xuất bản** — Commit lên `main`, GitHub Pages tự deploy.

## Vì sao dùng agent thay vì script cứng?

Khi một mặt hàng biến mất hoặc đổi đường dẫn, agent có thể **tìm sản phẩm thay thế
cùng nhóm, cùng quy cách**, cập nhật rổ hàng kèm ghi chú, và **nối chuỗi giá** để
chỉ số không bị nhảy. Script thường chỉ báo lỗi rồi dừng.

## Trọng số & phương pháp

Chi tiết rổ hàng, trọng số (dựa trên cơ cấu chi tiêu CPI của Tổng cục Thống kê), và
công thức nằm ở **trang Phương pháp luận** (`methodology.html`) và
[`PLAN.md`](PLAN.md).

## Minh bạch

- Mọi thay đổi rổ hàng: `data/substitutions-log.md`
- Nhật ký mỗi lần chạy: `data/run-log.md`
- Lịch sử chỉ số: `data/index-history.csv`
