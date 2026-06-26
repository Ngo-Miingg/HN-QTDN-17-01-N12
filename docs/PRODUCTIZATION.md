# Productization Checklist

## Trang thai hien tai

- Module custom `nhan_su`, `quan_ly_van_ban`, `event_meeting_room_extended`, `dnu_meeting_asset` upgrade thanh cong tren DB `ttdn_n6_dev`.
- Luong duyet van ban da dong bo lai nguon muon tai san va dat phong.
- Cau hinh local dung `addons_path = addons`, PostgreSQL port `5431`, HTTP port `8071`.
- Docker Compose dung named volume de chay tai lap tren may local thay vi bind path Linux co dinh.

## Lenh van hanh

- Chay product local: `.\start-product.ps1`
- Smoke test luong chinh: `.\smoke-product.ps1`
- URL local: `http://localhost:8071`

## Luong da kiem chung

- Cai/upgrade module custom.
- Tao nhan vien, tai san, phieu muon, van ban den phe duyet, van ban di.
- Sau khi duyet van ban muon tai san, phieu muon chuyen sang `approved`.
- Tao phong hop, booking, van ban den phe duyet, van ban di.
- Sau khi duyet van ban dat phong, booking chuyen sang `confirmed`.

## Canh bao con lai khong thuoc module custom

- `wkhtmltopdf` chua duoc cai nen xuat PDF report co the khong hoat dong.
- Odoo 15 upstream dung API cu voi `docutils` va `werkzeug`, sinh deprecation warning khi chay bang thu vien moi.
- Repo dang chua nhieu thay doi trong Odoo core/docs tu truoc; khong nen sua hoac revert neu chua co quyet dinh tach nhanh lam sach.

## Viec nen lam truoc khi demo/giao nop

- Cai `wkhtmltopdf` dung ban cho Odoo 15 neu can in PDF.
- Khong commit file chua secret. Kiem tra `opencode.json` truoc khi day repo.
- Chay `.\smoke-product.ps1` truoc moi lan demo.
