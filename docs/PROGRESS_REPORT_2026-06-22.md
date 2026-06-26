# Bao cao tien do du an Quan ly tai san + Phong hop

## 1. Muc tieu hien tai

Du an duoc phat trien tren repo ke thua `TTDN-16-01-N6`, tap trung vao de tai:

- Quan ly tai san
- Quan ly phong hop
- Lien ket du lieu nhan su de xac dinh nguoi muon, nguoi nhan ban giao, nguoi to chuc hop

Huong trien khai hien tai uu tien dung nghiep vu, giu duoc luong xu ly doanh nghiep va giam bot cac phan menu/giao dien khong phai trong tam demo.

## 2. Cong viec da hoan thanh

### 2.1. Ra soat cau truc repo ke thua

- Da phan tich repo `TTDN-16-01-N6` va xac dinh module trung tam la `addons/dnu_meeting_asset`
- Da xac dinh module phu thuoc nghiep vu chinh:
  - `nhan_su`
  - `quan_ly_van_ban`
  - `event_meeting_room_extended`
  - `hr`, `calendar`, `mail`

### 2.2. Chinh lai pham vi giao dien theo de tai

Da don lai menu va man hinh de tap trung vao nghiep vu cot loi:

- Tai san:
  - Tai san
  - Danh muc
  - Lich su gan
  - Muon tai san
  - Bao tri
  - Lich bao tri dinh ky
  - Khau hao
  - Kiem ke
  - Luan chuyen
  - Thanh ly
  - Quy tac gia thanh ly
- Phong hop:
  - Dat phong
  - Dat phong nhanh
  - Duyet dat phong
  - Phong hop
  - Bao cao

### 2.3. Chinh sua file va nghiep vu da lam

Da cap nhat cac file chinh sau:

- [__manifest__.py](D:/Work/HocKy3/Enterprise_software_integration_and_management/TTDN-16-01-N6/addons/dnu_meeting_asset/__manifest__.py)
  - Rut gon mo ta module
  - Giu lai cac view va report can cho demo nghiep vu
- [menu_views.xml](D:/Work/HocKy3/Enterprise_software_integration_and_management/TTDN-16-01-N6/addons/dnu_meeting_asset/views/menu_views.xml)
  - To chuc lai menu theo nhom Tai san va Phong hop
  - Chuan hoa quyen cho menu duyet dat phong
- [dnu_meeting_booking_views.xml](D:/Work/HocKy3/Enterprise_software_integration_and_management/TTDN-16-01-N6/addons/dnu_meeting_asset/views/dnu_meeting_booking_views.xml)
  - Giu lai luong dat phong, duyet, check-in, check-out, canh bao xung dot
  - Bo bot cac the/man hinh phu khong can cho demo cot loi
- [dnu_asset_disposal_views.xml](D:/Work/HocKy3/Enterprise_software_integration_and_management/TTDN-16-01-N6/addons/dnu_meeting_asset/views/dnu_asset_disposal_views.xml)
  - Xoa khoi nut thong ke bi lap trong form thanh ly
- [ir.model.access.csv](D:/Work/HocKy3/Enterprise_software_integration_and_management/TTDN-16-01-N6/addons/dnu_meeting_asset/security/ir.model.access.csv)
  - Bo sung quyen doc cho model `dnu.asset.center` de tranh canh bao khi load module

### 2.4. Dung moi truong chay that

Da hoan thanh cac buoc van hanh:

- Cai PostgreSQL trong WSL Ubuntu
- Tao role/database:
  - user: `odoo`
  - password: `odoo`
  - database: `ttdn_n6_dev`
- Cap nhat [odoo.conf](D:/Work/HocKy3/Enterprise_software_integration_and_management/TTDN-16-01-N6/odoo.conf)
  - `db_port = 5432`
  - `xmlrpc_port = 8070`
- Cai moi module `dnu_meeting_asset` tren database `ttdn_n6_dev`
- Da reset lai mat khau admin cua Odoo ve:
  - user: `admin`
  - password: `admin`

### 2.5. Kiem tra ky thuat

Da xac nhan:

- XML cua cac file da sua parse thanh cong
- Manifest parse thanh cong
- Module `dnu_meeting_asset` cai dat thanh cong tren database dev
- Odoo co the khoi dong va phuc vu trang dang nhap

## 3. Trang thai hien tai

### 3.1. Da on dinh

- Khung nghiep vu tai san + phong hop da len duoc
- Phu thuoc du lieu nhan su da xac dinh ro
- Menus/action cot loi khong bi vo khi cai module
- Moi truong WSL + PostgreSQL + Odoo da dung duoc

### 3.2. Con ton dong

- Website frontend cua Odoo dang co canh bao compile SCSS khi vao `/web/login`
- Mot so module phu (`nhan_su`, `quan_ly_van_ban`) thieu file demo va thieu `license` trong manifest
- Van chua test tay day du end-to-end tren tung man hinh trong giao dien

## 4. Huong nghiep vu da dat duoc

### 4.1. Tai san

Luong chinh dang duoc giu:

1. Tao tai san
2. Gan/ban giao cho nhan vien
3. Muon/tra tai san
4. Bao tri tai san
5. Kiem ke tai san
6. Luan chuyen hoac thanh ly tai san

### 4.2. Phong hop

Luong chinh dang duoc giu:

1. Tao phong hop
2. Tao lich dat phong
3. Kiem tra xung dot
4. Duyet dat phong
5. Check-in / Check-out
6. Theo doi bao cao dat phong

## 5. Buoc tiep theo de hoan thien

1. Chay test tay tren giao dien cho tung menu chinh
2. Sua cac loi frontend/asset cua trang login neu can de demo dep hon
3. Chup anh minh hoa cho tung luong nghiep vu
4. Hoan thien README va bao cao cuoi ky
5. Neu can nang diem:
   - them dashboard nghiep vu that su huu ich
   - them canh bao den han/qua han
   - them bao cao dep hon cho tai san va phong hop

## 6. Cach chay hien tai

### 6.1. CSDL

PostgreSQL dang chay trong WSL Ubuntu, port `5432`.

### 6.2. Odoo

Chay Odoo trong thu muc repo:

```bash
./run_odoo_n6.sh
```

Hoac:

```bash
/mnt/d/Work/HocKy3/Enterprise_software_integration_and_management/Business-Internship/venv/bin/python odoo-bin.py -c odoo.conf -d ttdn_n6_dev
```

### 6.3. Dang nhap

- URL mac dinh theo config: `http://localhost:8070`
- Tai khoan: `admin`
- Mat khau: `admin`

## 7. Danh gia tong quan

Tien do hien tai da di qua giai doan doc repo va chinh giao dien, sang giai doan co moi truong chay that va module cai duoc tren database dev. Day la moc quan trong vi tu diem nay co the test nghiep vu truc tiep, chup anh giao dien va tiep tuc hoan thien bai tap lon theo huong chac chan hon.
