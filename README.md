<h2 align="center">
  <a href="https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin">
    Faculty of Information Technology - Dai Nam University
  </a>
</h2>

<h1 align="center">Odoo 15 - Quản lý Tài sản & Phòng họp</h1>

<p align="center">
  <b>Asset Lifecycle Management • Meeting Room Booking • HRM Master Data • Operational Dashboard • AI Assistant</b>
</p>

<p align="center">
  <img src="docs/logo/aiotlab_logo.png" alt="AIoTLab Logo" width="150"/>
  <img src="docs/logo/fitdnu_logo.png" alt="FIT-DNU Logo" width="165"/>
  <img src="docs/logo/dnu_logo.png" alt="Dai Nam University Logo" width="185"/>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Odoo-15.0-714B67?style=for-the-badge&logo=odoo&logoColor=white" alt="Odoo 15"/></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/></a>
  <a href="#"><img src="https://img.shields.io/badge/PostgreSQL-10+-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/></a>
  <a href="#"><img src="https://img.shields.io/badge/Docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/></a>
</p>

---

## 1. Executive Summary

Dự án triển khai một phân hệ Odoo 15 cho bài toán **quản lý tài sản và điều phối phòng họp** trong môi trường doanh nghiệp/trường học. Trọng tâm của hệ thống không chỉ là tạo các màn hình CRUD, mà là xây dựng một luồng vận hành có dữ liệu gốc, trạng thái xử lý, lịch sử, phân quyền, báo cáo và khả năng hỗ trợ quyết định.

Góc nhìn thiết kế của dự án đi theo tư duy HRM/ERP:

- **HRM là dữ liệu gốc**: nhân viên, phòng ban, chức vụ là nguồn tham chiếu cho người nhận tài sản, người mượn tài sản, người đặt phòng, người phê duyệt và người phụ trách xử lý.
- **Tài sản là đối tượng vận hành có vòng đời**: từ ghi nhận, phân loại, cấp phát, mượn/trả, bảo trì, kiểm kê, luân chuyển đến thanh lý.
- **Phòng họp là tài nguyên dùng chung**: cần quản lý sức chứa, thiết bị, lịch đặt, xung đột thời gian và trạng thái phê duyệt.
- **AI là lớp hỗ trợ nghiệp vụ**: AI không thay thế rule của Odoo, mà giúp tra cứu, tóm tắt, gợi ý và lưu lịch sử hỏi đáp dựa trên dữ liệu hệ thống.

Module chính:

```text
addons/dnu_meeting_asset
```

Tài liệu review tính năng cốt lõi:

```text
docs/CORE_FEATURE_REVIEW.md
```

---

## 2. Business Problem

Trong nhiều đơn vị, tài sản và phòng họp thường được quản lý rời rạc bằng Excel, tin nhắn hoặc biểu mẫu thủ công. Cách làm này tạo ra các vấn đề quen thuộc:

| Vấn đề | Hệ quả |
| --- | --- |
| Không biết tài sản đang ở đâu, ai đang giữ | Khó quy trách nhiệm, dễ thất lạc |
| Tài sản dùng chung bị mượn trùng hoặc trả muộn | Gián đoạn công việc, thiếu thiết bị khi cần |
| Bảo trì không có lịch sử rõ ràng | Khó đánh giá chi phí và tình trạng tài sản |
| Phòng họp bị đặt trùng lịch | Xung đột vận hành, mất thời gian điều phối |
| Dữ liệu nhân sự không liên kết với tài sản/phòng họp | Báo cáo thiếu ngữ cảnh phòng ban, chức vụ, người phụ trách |
| Báo cáo làm thủ công | Khó theo dõi tình hình theo thời gian thực |

Dự án này giải quyết các vấn đề trên bằng cách đưa tài sản, phòng họp và nhân sự vào cùng một hệ thống ERP trên Odoo.

---

## 3. Core Capabilities Review

| Mã | Năng lực cốt lõi | Giá trị nghiệp vụ | Thành phần triển khai |
| --- | --- | --- | --- |
| C01 | HRM Master Data | Dùng nhân viên/phòng ban/chức vụ làm dữ liệu gốc cho toàn bộ luồng | `hr`, `nhan_su`, `hr_employee_extend.py` |
| C02 | Asset Master Data | Quản lý hồ sơ tài sản, mã, danh mục, vị trí, trạng thái, người sử dụng | `dnu_asset.py`, `dnu_asset_category.py` |
| C03 | Asset Assignment & Handover | Cấp phát tài sản cho nhân viên, ghi nhận bàn giao và lịch sử chịu trách nhiệm | `dnu_asset_assignment.py`, `dnu_asset_handover.py` |
| C04 | Asset Lending | Quản lý mượn/trả tài sản dùng chung, kiểm soát trạng thái khả dụng | `dnu_asset_lending.py` |
| C05 | Maintenance Management | Theo dõi bảo trì, phân công xử lý, chi phí, lịch bảo trì định kỳ | `dnu_asset_maintenance.py`, `dnu_maintenance_schedule.py` |
| C06 | Inventory, Transfer, Disposal | Bao phủ vòng đời sau sử dụng: kiểm kê, luân chuyển, thanh lý | `dnu_asset_inventory.py`, `dnu_asset_transfer.py`, `dnu_asset_disposal.py` |
| C07 | Meeting Room Master Data | Quản lý phòng họp, sức chứa, thiết bị, trạng thái sử dụng | `dnu_meeting_room.py` |
| C08 | Meeting Booking | Đặt phòng, kiểm tra xung đột, phê duyệt, theo dõi lịch sử sử dụng | `dnu_meeting_booking.py` |
| C09 | Dashboard & Reports | Tổng hợp dữ liệu vận hành phục vụ quản trị | `dnu_asset_dashboard.py`, `reports/*.xml` |
| C10 | AI Assistant | Hỏi đáp/tóm tắt/gợi ý nghiệp vụ dựa trên dữ liệu Odoo | `openai_integration.py`, `ai_wizard.py`, `ai_history.py` |

Điểm quan trọng khi review: hệ thống có **dữ liệu gốc**, **luồng trạng thái**, **quan hệ giữa các module**, **báo cáo**, và **lịch sử xử lý**. Đây là những yếu tố phân biệt một bài Odoo có nghiệp vụ với một bài chỉ tạo model và menu.

---

## 4. Business Flow

### 4.1. Asset Lifecycle

```text
HR master data
  -> Khai báo tài sản
  -> Phân loại danh mục, vị trí, trạng thái
  -> Cấp phát hoặc đưa vào kho dùng chung
  -> Bàn giao / mượn trả / bảo trì
  -> Kiểm kê / luân chuyển / thanh lý
  -> Dashboard và báo cáo quản trị
```

Ý nghĩa nghiệp vụ:

- Biết tài sản đang ở đâu và do ai chịu trách nhiệm.
- Phân biệt rõ tài sản sẵn sàng, đang sử dụng, đang mượn, đang bảo trì hoặc đã thanh lý.
- Có lịch sử phục vụ kiểm tra, bàn giao và báo cáo.

### 4.2. Meeting Room Booking

```text
HR master data
  -> Khai báo phòng họp
  -> Người dùng tạo phiếu đặt phòng
  -> Kiểm tra thời gian, phòng, sức chứa, xung đột
  -> Phê duyệt hoặc xác nhận
  -> Lưu lịch sử sử dụng phòng
  -> Báo cáo đặt phòng
```

Ý nghĩa nghiệp vụ:

- Giảm đặt trùng lịch.
- Biết phòng nào đang được dùng nhiều.
- Liên kết người đặt với nhân sự/phòng ban.
- Có dữ liệu để tối ưu sử dụng tài nguyên dùng chung.

### 4.3. AI Assisted Operations

```text
Người dùng đặt câu hỏi
  -> AI xác định miền nghiệp vụ
  -> Lấy dữ liệu liên quan trong Odoo
  -> Trả lời có căn cứ
  -> Lưu lịch sử hỏi đáp
```

AI trong dự án được đặt ở vai trò hỗ trợ vận hành. Các quyết định cốt lõi như trạng thái tài sản, phê duyệt đặt phòng, trả tài sản hoặc bảo trì vẫn do rule và dữ liệu Odoo kiểm soát.

---

## 5. Architecture

```text
Odoo Web Client
    |
    v
dnu_meeting_asset
    |
    +-- HRM: nhân viên, phòng ban, chức vụ
    +-- Asset: tài sản, cấp phát, mượn/trả, bảo trì, kiểm kê, thanh lý
    +-- Meeting: phòng họp, đặt phòng, kiểm tra xung đột
    +-- Document/Approval: văn bản và phê duyệt
    +-- Mail/Calendar: thông báo và lịch
    +-- AI Service: hỗ trợ tra cứu, tóm tắt, gợi ý
    |
    v
PostgreSQL
```

Sơ đồ:

```text
docs/diagrams/
```

Ảnh minh chứng chọn lọc:

```text
docs/screenshots/
```

---

## 6. Repository Structure

```text
.
|-- addons/
|   |-- dnu_meeting_asset/          # Module chính của đề tài
|   |   |-- models/                 # Business models
|   |   |-- views/                  # Odoo XML views
|   |   |-- wizards/                # Wizard thao tác nhanh
|   |   |-- reports/                # Báo cáo
|   |   |-- security/               # Access right và security rule
|   |   |-- data/                   # Sequence, cron, seed, cấu hình mặc định
|   |   |-- scripts/                # Seed dữ liệu demo
|   |   |-- tests/                  # Test luồng nghiệp vụ
|   |
|-- BaiTapLab/                      # Bài lab chấm công/lương, tách riêng khỏi bài tập lớn
|-- docs/
|   |-- CORE_FEATURE_REVIEW.md      # Review tính năng cốt lõi
|   |-- diagrams/                   # ERD, use case, workflow, architecture
|   |-- screenshots/                # Ảnh demo chọn lọc
|   |-- PRODUCTIZATION.md           # Ghi chú demo/đóng gói
|
|-- docker-compose.yml              # PostgreSQL local
|-- odoo-bin                        # Odoo entry point
|-- requirements.txt                # Python dependencies
```

---

## 7. Evidence Package

Repo chỉ giữ ảnh đại diện để tránh rối và thiếu chuyên nghiệp:

| File | Minh chứng |
| --- | --- |
| `docs/screenshots/01-dashboard.png` | Dashboard tổng quan |
| `docs/screenshots/02-assets-list.png` | Danh sách tài sản |
| `docs/screenshots/03-asset-lending.png` | Phiếu mượn/trả tài sản |
| `docs/screenshots/04-asset-maintenance.png` | Bảo trì tài sản |
| `docs/screenshots/05-meeting-rooms.png` | Danh sách phòng họp |
| `docs/screenshots/06-room-bookings.png` | Danh sách đặt phòng |
| `docs/screenshots/07-booking-approval.png` | Phê duyệt đặt phòng |
| `docs/screenshots/08-asset-report.png` | Báo cáo tài sản |
| `docs/screenshots/09-ai-chatbot.png` | AI chatbot |
| `docs/screenshots/10-ai-history.png` | Lịch sử AI |

Tài liệu review sâu:

```text
docs/CORE_FEATURE_REVIEW.md
```

---

## 8. Quick Start

Mục tiêu của phần này là để một người mới clone repo có thể dựng môi trường local theo các bước rõ ràng. Dự án đã có `docker-compose.yml`, `odoo.conf.template` và script chạy nhanh cho Windows.

### 8.1. Prerequisites

- Git.
- Docker Desktop.
- Python phù hợp với Odoo 15. Khuyến nghị dùng Python 3.8-3.10 để giảm lỗi phụ thuộc.
- PostgreSQL không cần cài riêng nếu dùng Docker.

### 8.2. Clone repository

```powershell
git clone https://github.com/Ngo-Miingg/HN-QTDN-17-01-N12.git
cd HN-QTDN-17-01-N12
```

### 8.3. Create local configuration

File `odoo.conf` không được commit vì là cấu hình local. Khi chạy `start-product.ps1`, file này sẽ được tạo tự động từ `odoo.conf.template`. Nếu muốn tạo thủ công:

```powershell
Copy-Item .\odoo.conf.template .\odoo.conf
```

Cấu hình mặc định:

```text
PostgreSQL host: localhost
PostgreSQL port: 5431
PostgreSQL user: odoo
PostgreSQL password: odoo
Odoo HTTP port: 8071
Database: ttdn_n6_dev
```

### 8.4. Install Python dependencies

Khuyến nghị tạo virtual environment riêng:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 8.5. One-command startup on Windows

Script này sẽ:

- Tạo `odoo.conf` nếu chưa có.
- Khởi động PostgreSQL bằng Docker.
- Cài/nâng cấp các module cần thiết.
- Chạy Odoo ở cổng `8071`.

```powershell
.\start-product.ps1
```

URL:

```text
http://localhost:8071
```

Tài khoản demo thường dùng sau khi tạo database:

```text
Email: admin
Password: admin
```

### 8.6. Manual startup

Nếu không dùng script:

```powershell
docker compose up -d postgres-odoo-base-15-01
python .\odoo-bin.py -c .\odoo.conf -d ttdn_n6_dev --http-port 8071 -u nhan_su,quan_ly_van_ban,event_meeting_room_extended,dnu_meeting_asset --stop-after-init
python .\odoo-bin.py -c .\odoo.conf -d ttdn_n6_dev --http-port 8071
```

Kiểm tra database port:

```powershell
Test-NetConnection localhost -Port 5431
```

### 8.7. Install Module From UI

Nếu chạy theo script, module đã được upgrade bằng command line. Nếu cài thủ công trong UI:

```text
Apps -> Update Apps List -> tìm "Quản lý Tài sản & Phòng họp" -> Install
```

Menu sau khi cài:

```text
Tài sản & Phòng họp
|-- Dashboard
|-- Quản lý tài sản
|-- Quản lý phòng họp
|-- Báo cáo
|-- AI hỗ trợ
|-- Cấu hình
```

---

## 9. Demo Data

Seed XML:

```text
addons/dnu_meeting_asset/data/demo_seed_data.xml
```

Seed dữ liệu demo lớn hơn:

```powershell
$env:ODOO_RC = "D:\Work\HocKy3\Enterprise_software_integration_and_management\TTDN-16-01-N6\odoo.conf"
python .\addons\dnu_meeting_asset\scripts\seed_fake_data.py
```

Dữ liệu demo bao gồm:

- Nhân viên, phòng ban, chức vụ.
- Tài sản văn phòng, thiết bị IT, thiết bị phòng họp.
- Phòng họp, sức chứa, thiết bị.
- Phiếu gán tài sản, phiếu mượn/trả, bảo trì.
- Phiếu đặt phòng và dữ liệu báo cáo.

---

## 10. Testing

Kiểm tra cú pháp Python:

```powershell
Get-ChildItem .\addons\dnu_meeting_asset\models\*.py, `
  .\addons\dnu_meeting_asset\wizards\*.py, `
  .\addons\dnu_meeting_asset\controllers\*.py | ForEach-Object {
    python -m py_compile $_.FullName
  }
```

Nâng cấp module:

```powershell
python .\odoo-bin -c .\odoo.conf -d ttdn_n6_dev -u dnu_meeting_asset --stop-after-init
```

Chạy test nghiệp vụ:

```powershell
python .\odoo-bin -c .\odoo.conf -d ttdn_n6_dev --test-enable -u dnu_meeting_asset --stop-after-init
```

---

## 11. Demo Script For Review

Thứ tự trình bày nên đi theo nghiệp vụ:

1. Mở dashboard để giới thiệu bức tranh vận hành.
2. Mở danh sách tài sản, giải thích mã tài sản, trạng thái, vị trí, người sử dụng.
3. Mở phiếu mượn/trả tài sản, nhấn mạnh rule khả dụng và trách nhiệm người mượn.
4. Mở bảo trì tài sản, giải thích người phụ trách, chi phí, trạng thái.
5. Mở danh sách phòng họp, giải thích sức chứa và thiết bị.
6. Mở đặt phòng, giải thích thời gian, người đặt, xung đột và phê duyệt.
7. Mở báo cáo tổng hợp.
8. Mở AI chatbot và lịch sử AI để chứng minh lớp hỗ trợ nghiệp vụ.

---

## 12. Security & Repository Hygiene

Không commit:

- API key, token, mật khẩu.
- `.env`, `opencode.json`, cấu hình cá nhân.
- Log runtime.
- Database dump.
- Bản nháp báo cáo Word/PDF nếu không phục vụ trực tiếp cho repo.

Repo đã tách:

- `BaiTapLab/`: bài lab nhỏ, không lẫn với bài tập lớn.
- `addons/dnu_meeting_asset/`: module bài tập lớn.
- `docs/screenshots/`: ảnh chọn lọc.
- `docs/CORE_FEATURE_REVIEW.md`: review tính năng trọng tâm.

---

## 13. Project Evaluation

Tiêu chí tự đánh giá:

| Tiêu chí | Đánh giá |
| --- | --- |
| Hiểu bài toán doanh nghiệp | Có: tài sản, phòng họp, HRM master data, luồng vận hành |
| Thiết kế module Odoo | Có: model, view, security, wizard, report, cron, seed |
| Tích hợp dữ liệu | Có: HRM, tài sản, phòng họp, văn bản, mail/calendar |
| Luồng nghiệp vụ end-to-end | Có: cấp phát, mượn/trả, bảo trì, đặt phòng, phê duyệt, báo cáo |
| Nâng cao | Có: dashboard, AI assistant, dữ liệu demo, test |
| Tính sẵn sàng demo | Có: script chạy, seed data, ảnh minh chứng, core review |

Kết luận: dự án đủ điều kiện trình bày như một phân hệ ERP/Odoo có nghiệp vụ, có dữ liệu liên kết và có định hướng mở rộng, không dừng ở mức tạo form cơ bản.

---

## 14. References

- Odoo 15 Community Edition
- PostgreSQL
- Python
- Docker
- FIT-DNU Business Internship repository structure

---

## 15. License

Dự án phục vụ mục đích học tập trong học phần Hội nhập và Quản trị Doanh nghiệp. Các phần tùy biến được sử dụng trong phạm vi bài tập lớn.
