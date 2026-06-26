<h2 align="center">
  <a href="https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin">
    Faculty of Information Technology - Dai Nam University
  </a>
</h2>

<h1 align="center">Hệ thống Quản lý Tài sản & Phòng họp trên Odoo 15</h1>

<p align="center">
  <img src="docs/logo/aiotlab_logo.png" alt="AIoTLab Logo" width="155"/>
  <img src="docs/logo/fitdnu_logo.png" alt="FIT-DNU Logo" width="170"/>
  <img src="docs/logo/dnu_logo.png" alt="Dai Nam University Logo" width="190"/>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Odoo-15.0-714B67?style=for-the-badge&logo=odoo&logoColor=white" alt="Odoo 15"/></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/></a>
  <a href="#"><img src="https://img.shields.io/badge/PostgreSQL-10+-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/></a>
  <a href="#"><img src="https://img.shields.io/badge/Docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/></a>
</p>

<p align="center">
  Bài tập lớn học phần <b>Hội nhập và Quản trị Doanh nghiệp</b><br/>
  Đề tài: <b>Quản lý tài sản + Phòng họp</b><br/>
  Phát triển kế thừa từ repo mẫu và mở rộng theo hướng nghiệp vụ doanh nghiệp, dashboard, báo cáo và AI hỗ trợ.
</p>

---

## 1. Tổng quan đề tài

Dự án xây dựng một module Odoo 15 phục vụ quản lý vòng đời tài sản và điều phối sử dụng phòng họp trong doanh nghiệp/trường học. Hệ thống lấy dữ liệu nhân sự làm dữ liệu gốc để xác định người sử dụng tài sản, người đặt phòng, người phê duyệt và các bên liên quan trong từng luồng nghiệp vụ.

Module chính của đề tài là:

```text
addons/dnu_meeting_asset
```

Các nhóm nghiệp vụ trọng tâm:

| Nhóm nghiệp vụ | Mục tiêu |
| --- | --- |
| Quản lý tài sản | Theo dõi danh mục tài sản, trạng thái, vị trí, người sử dụng và vòng đời sử dụng |
| Cấp phát và bàn giao | Gán tài sản cho nhân viên, lập biên bản bàn giao, theo dõi lịch sử |
| Mượn và trả tài sản | Quản lý tài sản dùng chung, phê duyệt mượn, trả, quá hạn và trạng thái khả dụng |
| Bảo trì | Ghi nhận yêu cầu bảo trì, phân công xử lý, theo dõi chi phí và tình trạng |
| Kiểm kê, luân chuyển, thanh lý | Hỗ trợ nghiệp vụ quản trị tài sản định kỳ và xử lý tài sản hết vòng đời |
| Quản lý phòng họp | Khai báo phòng, sức chứa, thiết bị, đặt lịch, kiểm tra xung đột |
| Dashboard và báo cáo | Tổng hợp dữ liệu vận hành để minh chứng hiệu quả quản trị |
| AI hỗ trợ | Hỏi đáp nghiệp vụ, gợi ý xử lý dựa trên dữ liệu thật trong hệ thống |

---

## 2. Điểm nổi bật

- Kế thừa cấu trúc Odoo 15 từ repo mẫu, không tách rời khỏi nền tảng ERP.
- Thiết kế module theo nghiệp vụ thật: tài sản, nhân sự, phòng họp, mượn trả, bảo trì, đặt lịch.
- Có dữ liệu mẫu phục vụ demo và kiểm thử luồng end-to-end.
- Có dashboard, báo cáo và ảnh giao diện phục vụ báo cáo cuối học phần.
- Có lớp AI hỗ trợ nghiệp vụ theo hướng kiểm soát dữ liệu, hạn chế trả lời chung chung.
- Có script seed dữ liệu để tạo nhanh môi trường demo.

---

## 3. Kiến trúc hệ thống

```text
Người dùng Odoo
    |
    v
Module dnu_meeting_asset
    |
    +-- HR/Employees: dữ liệu nhân viên, phòng ban, chức vụ
    +-- Asset: tài sản, danh mục, cấp phát, mượn trả, bảo trì
    +-- Meeting: phòng họp, đặt phòng, kiểm tra xung đột
    +-- Document/Approval: liên kết văn bản và phê duyệt
    +-- AI Service: trợ lý nghiệp vụ dựa trên dữ liệu hệ thống
    |
    v
PostgreSQL
```

Sơ đồ minh chứng được lưu tại:

```text
docs/diagrams/
```

Ảnh giao diện minh chứng được chọn lọc và lưu tại:

```text
docs/screenshots/
```

---

## 4. Cấu trúc thư mục quan trọng

```text
.
|-- addons/
|   |-- dnu_meeting_asset/          # Module chính của đề tài
|   |   |-- models/                 # Model nghiệp vụ
|   |   |-- views/                  # Giao diện Odoo XML
|   |   |-- wizards/                # Wizard thao tác nhanh
|   |   |-- reports/                # Báo cáo PDF/action
|   |   |-- security/               # Nhóm quyền và phân quyền model
|   |   |-- data/                   # Sequence, cron, cấu hình, seed XML
|   |   |-- scripts/                # Script seed dữ liệu demo
|   |   |-- tests/                  # Test nghiệp vụ chính
|   |   |-- static/                 # CSS/icon/module assets
|   |   |-- README.md               # Tài liệu riêng của module
|   |
|   |-- nhan_su/                    # Module nhân sự dùng làm dữ liệu gốc
|   |-- quan_ly_van_ban/            # Module văn bản/phê duyệt liên quan
|
|-- docs/
|   |-- diagrams/                   # Kiến trúc, ERD, use case, workflow
|   |-- screenshots/                # Ảnh giao diện chọn lọc cho báo cáo/demo
|   |-- PRODUCTIZATION.md           # Ghi chú đóng gói và demo sản phẩm
|
|-- docker-compose.yml              # PostgreSQL phục vụ chạy Odoo local
|-- odoo-bin                        # Entry point Odoo
|-- requirements.txt                # Phụ thuộc Python
```

---

## 5. Các model nghiệp vụ chính

| Model | Vai trò |
| --- | --- |
| `dnu.asset` | Hồ sơ tài sản |
| `dnu.asset.category` | Danh mục tài sản |
| `dnu.asset.assignment` | Phiếu gán/cấp phát tài sản |
| `dnu.asset.lending` | Phiếu mượn/trả tài sản dùng chung |
| `dnu.asset.handover` | Biên bản bàn giao tài sản |
| `dnu.asset.maintenance` | Yêu cầu bảo trì tài sản |
| `dnu.maintenance.schedule` | Lịch bảo trì định kỳ |
| `dnu.asset.inventory` | Đợt kiểm kê tài sản |
| `dnu.asset.transfer` | Luân chuyển tài sản |
| `dnu.asset.disposal` | Thanh lý tài sản |
| `dnu.meeting.room` | Hồ sơ phòng họp |
| `dnu.meeting.booking` | Phiếu đặt phòng họp |
| `openai.config`, `ai.history` | Cấu hình và lịch sử AI |

---

## 6. Luồng nghiệp vụ chính

### 6.1. Luồng quản lý tài sản

```text
Tạo tài sản
  -> Phân loại danh mục, vị trí, trạng thái
  -> Gán cho nhân viên hoặc đưa vào kho dùng chung
  -> Bàn giao, mượn/trả, bảo trì, kiểm kê
  -> Luân chuyển hoặc thanh lý khi cần
  -> Báo cáo vòng đời tài sản
```

### 6.2. Luồng mượn/trả tài sản

```text
Nhân viên tạo phiếu mượn
  -> Hệ thống kiểm tra trạng thái tài sản
  -> Quản lý phê duyệt
  -> Tài sản chuyển sang trạng thái đang mượn/đã cấp phát
  -> Nhân viên trả tài sản
  -> Hệ thống cập nhật trạng thái khả dụng
```

### 6.3. Luồng đặt phòng họp

```text
Người dùng chọn phòng và thời gian
  -> Hệ thống kiểm tra xung đột lịch
  -> Tạo phiếu đặt phòng
  -> Phê duyệt hoặc xác nhận
  -> Theo dõi lịch sử sử dụng phòng
  -> Tổng hợp báo cáo đặt phòng
```

### 6.4. Luồng AI hỗ trợ nghiệp vụ

```text
Người dùng đặt câu hỏi
  -> AI xác định nhóm nghiệp vụ: tài sản, phòng họp, nhân sự, bảo trì
  -> Hệ thống lấy dữ liệu liên quan trong Odoo
  -> AI trả lời có căn cứ dữ liệu
  -> Ghi lịch sử hỏi đáp để kiểm tra lại
```

---

## 7. Cài đặt và chạy local

### 7.1. Yêu cầu môi trường

- Windows 10/11 hoặc Ubuntu/WSL2
- Python phù hợp với Odoo 15
- PostgreSQL hoặc Docker Desktop
- Git
- Các thư viện trong `requirements.txt`

### 7.2. Khởi động PostgreSQL bằng Docker

```powershell
cd D:\Work\HocKy3\Enterprise_software_integration_and_management\TTDN-16-01-N6
docker compose up -d postgres-odoo-base-15-01
```

Kiểm tra cổng database:

```powershell
Test-NetConnection localhost -Port 5431
```

### 7.3. Chạy Odoo

```powershell
cd D:\Work\HocKy3\Enterprise_software_integration_and_management\TTDN-16-01-N6
python .\odoo-bin -c .\odoo.conf
```

Đường dẫn truy cập:

```text
http://localhost:8071
```

Tài khoản demo thường dùng:

```text
Email: admin
Password: admin
```

---

## 8. Cài module trong Odoo

1. Vào `Apps`.
2. Bấm `Update Apps List` nếu chưa thấy module.
3. Tìm `Quản lý Tài sản & Phòng họp`.
4. Bấm `Install`.
5. Sau khi cài xong, vào menu `Tài sản & Phòng họp`.

Menu chính sau khi cài:

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

## 9. Tạo dữ liệu demo

Module có sẵn XML seed trong:

```text
addons/dnu_meeting_asset/data/demo_seed_data.xml
```

Ngoài ra có script seed dữ liệu demo lớn hơn:

```powershell
$env:ODOO_RC = "D:\Work\HocKy3\Enterprise_software_integration_and_management\TTDN-16-01-N6\odoo.conf"
python .\addons\dnu_meeting_asset\scripts\seed_fake_data.py
```

Dữ liệu demo bao gồm:

- Phòng ban, chức vụ, nhân viên
- Phòng họp, sức chứa, thiết bị
- Tài sản văn phòng, thiết bị IT, thiết bị phòng họp
- Phiếu gán tài sản, mượn/trả tài sản
- Phiếu đặt phòng họp
- Yêu cầu bảo trì
- Dữ liệu phục vụ dashboard và báo cáo

---

## 10. AI hỗ trợ nghiệp vụ

AI trong dự án được thiết kế theo hướng hỗ trợ ra quyết định, không thay thế dữ liệu nghiệp vụ của Odoo.

Các khả năng chính:

- Hỏi đáp tình trạng tài sản.
- Gợi ý xử lý tài sản đang bảo trì, quá hạn trả hoặc sắp thanh lý.
- Tóm tắt lịch đặt phòng và phát hiện nguy cơ xung đột.
- Hỗ trợ tra cứu nhân sự liên quan đến tài sản/phòng họp.
- Lưu lịch sử phiên hỏi đáp để phục vụ kiểm tra demo.

Lưu ý khi demo:

- Không commit API key thật.
- Không đưa `opencode.json`, `.env`, file cấu hình cá nhân hoặc log lên GitHub.
- Có thể demo chế độ fallback/rule-based nếu không muốn dùng API trả phí.

---

## 11. Kiểm thử nhanh

Kiểm tra cú pháp Python của module:

```powershell
python -m py_compile `
  .\addons\dnu_meeting_asset\models\*.py `
  .\addons\dnu_meeting_asset\wizards\*.py `
  .\addons\dnu_meeting_asset\controllers\*.py
```

Cài hoặc nâng cấp module:

```powershell
python .\odoo-bin -c .\odoo.conf -d ttdn_n6_dev -u dnu_meeting_asset --stop-after-init
```

Chạy test nghiệp vụ nếu môi trường đã sẵn sàng:

```powershell
python .\odoo-bin -c .\odoo.conf -d ttdn_n6_dev --test-enable -u dnu_meeting_asset --stop-after-init
```

---

## 12. Bộ ảnh và tài liệu báo cáo

Repo chỉ giữ một bộ ảnh đại diện, đủ minh chứng luồng chính nhưng không làm nặng và rối phần trình bày:

```text
docs/screenshots/
```

Ảnh đang giữ:

| File | Minh chứng |
| --- | --- |
| `01-dashboard.png` | Dashboard tổng quan |
| `02-assets-list.png` | Danh sách tài sản |
| `03-asset-lending.png` | Phiếu mượn/trả tài sản |
| `04-asset-maintenance.png` | Bảo trì tài sản |
| `05-meeting-rooms.png` | Danh sách phòng họp |
| `06-room-bookings.png` | Danh sách đặt phòng |
| `07-booking-approval.png` | Phê duyệt đặt phòng |
| `08-asset-report.png` | Báo cáo tổng hợp tài sản |
| `09-ai-chatbot.png` | AI chatbot hỗ trợ nghiệp vụ |
| `10-ai-history.png` | Lịch sử AI |

Các ảnh chi tiết khác nên để trong báo cáo Word/PDF hoặc thư mục cá nhân khi cần, không đẩy tràn lên GitHub.

---

## 13. Ghi chú GitHub

Remote mẫu:

```text
https://github.com/lamngoctuu18/TTDN-16-01-N6.git
```

Remote nộp bài:

```text
https://github.com/Ngo-Miingg/HN-QTDN-17-01-N12.git
```

Trước khi đẩy GitHub cần kiểm tra:

```powershell
git status -sb
git diff --stat
git ls-files --others --exclude-standard
```

Không đẩy:

- API key, token, mật khẩu.
- Log chạy server.
- Database dump.
- File `.env`, `opencode.json`, cấu hình cá nhân.
- Bản nháp báo cáo `.docx` nếu không được yêu cầu.

---

## 14. Thành viên và phạm vi nộp bài

Dự án phục vụ học phần Hội nhập và Quản trị Doanh nghiệp, tập trung vào việc hiểu bài toán doanh nghiệp, xác định module tích hợp, triển khai luồng nghiệp vụ trên Odoo và đánh giá rủi ro khi đưa ERP vào vận hành.

Phần nộp bài nên bao gồm:

- Source code module Odoo.
- README hướng dẫn chạy.
- Dữ liệu demo.
- Ảnh giao diện theo luồng.
- Báo cáo phân tích nghiệp vụ và thiết kế hệ thống.
- Kịch bản demo.

---

## 15. License

Dự án phát triển cho mục đích học tập trên nền Odoo Community Edition. Các module tùy biến được sử dụng trong phạm vi bài tập lớn của học phần.
