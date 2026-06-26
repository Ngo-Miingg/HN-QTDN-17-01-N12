from datetime import date, datetime, time, timedelta
import base64


MARKER = "[DEMO_FLOW]"
SIGNATURE = base64.b64encode(b"demo-signature").decode()


def dt(days=0, hours=0, minutes=0):
    return datetime.now() + timedelta(days=days, hours=hours, minutes=minutes)


def d(days=0):
    return date.today() + timedelta(days=days)


def ensure(model_name, domain, values):
    record = env[model_name].search(domain, limit=1)
    if record:
        record.write(values)
        return record
    return env[model_name].create(values)


def ensure_department(name):
    return ensure("hr.department", [("name", "=", name)], {"name": name})


def ensure_job(name):
    return ensure("hr.job", [("name", "=", name)], {"name": name})


def ensure_don_vi(code, name):
    return ensure(
        "don_vi",
        [("ma_don_vi", "=", code)],
        {"ma_don_vi": code, "ten_don_vi": name},
    )


def ensure_chuc_vu(code, name):
    return ensure(
        "chuc_vu",
        [("ma_chuc_vu", "=", code)],
        {"ma_chuc_vu": code, "ten_chuc_vu": name},
    )


def split_name(full_name):
    parts = full_name.split()
    return " ".join(parts[:-1]), parts[-1]


def ensure_employee(key, full_name, email, phone, birth_date, hr_department, hr_job, don_vi, chuc_vu):
    ho_ten_dem, ten = split_name(full_name)
    nhan_vien = ensure(
        "nhan_vien",
        [("ma_dinh_danh", "=", key)],
        {
            "ma_dinh_danh": key,
            "ho_ten_dem": ho_ten_dem,
            "ten": ten,
            "ngay_sinh": birth_date,
            "email": email,
            "so_dien_thoai": phone,
            "que_quan": "Đà Nẵng",
        },
    )

    lich_su = env["lich_su_cong_tac"].search(
        [("nhan_vien_id", "=", nhan_vien.id), ("loai_chuc_vu", "=", "Chính")],
        limit=1,
    )
    if lich_su:
        lich_su.write({"don_vi_id": don_vi.id, "chuc_vu_id": chuc_vu.id})
    else:
        env["lich_su_cong_tac"].create(
            {
                "nhan_vien_id": nhan_vien.id,
                "don_vi_id": don_vi.id,
                "chuc_vu_id": chuc_vu.id,
                "loai_chuc_vu": "Chính",
            }
        )

    employee = ensure(
        "hr.employee",
        [("work_email", "=", email)],
        {
            "name": full_name,
            "work_email": email,
            "work_phone": phone,
            "birthday": birth_date,
            "department_id": hr_department.id,
            "job_id": hr_job.id,
            "nhan_vien_id": nhan_vien.id,
        },
    )
    if nhan_vien.hr_employee_id != employee:
        nhan_vien.write({"hr_employee_id": employee.id})
    if employee.nhan_vien_id != nhan_vien:
        employee.write({"nhan_vien_id": nhan_vien.id})
    return employee, nhan_vien


def ensure_partner(name):
    return ensure(
        "res.partner",
        [("name", "=", name)],
        {
            "name": name,
            "company_type": "company",
            "email": name.lower().replace(" ", ".") + "@example.com",
            "phone": "0900000000",
        },
    )


def ensure_category(code, name):
    return ensure(
        "dnu.asset.category",
        [("code", "=", code)],
        {"code": code, "name": name, "description": MARKER},
    )


def ensure_room(code, name, capacity, location, responsible, **kwargs):
    values = {
        "code": code,
        "name": name,
        "capacity": capacity,
        "location": location,
        "building": kwargs.get("building", "Tòa A"),
        "floor": kwargs.get("floor", "3"),
        "responsible_id": responsible.id,
        "allow_booking": True,
        "state": kwargs.get("state", "available"),
        "has_projector": kwargs.get("has_projector", False),
        "has_tv": kwargs.get("has_tv", False),
        "has_whiteboard": kwargs.get("has_whiteboard", True),
        "has_video_conference": kwargs.get("has_video_conference", False),
        "has_air_conditioning": True,
        "has_wifi": True,
        "description": MARKER,
    }
    return ensure("dnu.meeting.room", [("code", "=", code)], values)


def ensure_asset(name, category, supplier, **kwargs):
    values = {
        "name": name,
        "category_id": category.id,
        "serial_number": kwargs["serial_number"],
        "purchase_date": kwargs.get("purchase_date"),
        "purchase_value": kwargs.get("purchase_value", 0),
        "salvage_value": kwargs.get("salvage_value", 0),
        "supplier_id": supplier.id if supplier else False,
        "warranty_expiry": kwargs.get("warranty_expiry"),
        "state": kwargs.get("state", "available"),
        "assigned_to": kwargs.get("assigned_to").id if kwargs.get("assigned_to") else False,
        "assigned_nhan_vien_id": kwargs.get("assigned_nhan_vien").id if kwargs.get("assigned_nhan_vien") else False,
        "assignment_date": kwargs.get("assignment_date"),
        "location": kwargs.get("location"),
        "room_id": kwargs.get("room").id if kwargs.get("room") else False,
        "description": MARKER,
        "notes": MARKER,
        "active": kwargs.get("active", True),
    }
    return ensure("dnu.asset", [("serial_number", "=", kwargs["serial_number"])], values)


def ensure_assignment(asset, employee, nhan_vien, date_from, state="active", date_to=False, notes=""):
    values = {
        "asset_id": asset.id,
        "employee_id": employee.id if employee else False,
        "nhan_vien_id": nhan_vien.id if nhan_vien else False,
        "don_vi_id": nhan_vien.don_vi_chinh_id.id if nhan_vien and nhan_vien.don_vi_chinh_id else False,
        "date_from": date_from,
        "date_to": date_to,
        "state": state,
        "notes": f"{MARKER} {notes}".strip(),
    }
    assignment = env["dnu.asset.assignment"].search(
        [("asset_id", "=", asset.id), ("notes", "ilike", MARKER), ("date_from", "=", date_from)],
        limit=1,
    )
    if assignment:
        assignment.write(values)
    else:
        assignment = env["dnu.asset.assignment"].create(values)
    assignment._update_asset_status()
    return assignment


def ensure_handover(asset, nhan_vien, handover_type, handover_date, lending=False, notes=""):
    values = {
        "asset_id": asset.id,
        "nhan_vien_id": nhan_vien.id,
        "handover_type": handover_type,
        "handover_date": handover_date,
        "condition_handover": "good",
        "condition_return": "good" if handover_type == "return" else False,
        "expected_return_date": handover_date + timedelta(days=1) if handover_type == "lending" else False,
        "receiver_signature": SIGNATURE,
        "deliverer_signature": SIGNATURE if handover_type == "lending" else False,
        "receiver_signature_date": handover_date,
        "deliverer_signature_date": handover_date if handover_type == "lending" else False,
        "state": "completed",
        "notes": f"{MARKER} {notes}".strip(),
        "lending_id": lending.id if lending else False,
    }
    handover = env["dnu.asset.handover"].search(
        [
            ("asset_id", "=", asset.id),
            ("handover_type", "=", handover_type),
            ("notes", "ilike", MARKER),
        ],
        limit=1,
    )
    if handover:
        handover.write(values)
    else:
        handover = env["dnu.asset.handover"].create(values)
    return handover


def ensure_lending(asset, borrower, borrower_nv, date_borrow, date_return, state, booking=False, handover=False, return_handover=False, notes=""):
    values = {
        "asset_id": asset.id,
        "borrower_id": borrower.id,
        "nhan_vien_muon_id": borrower_nv.id,
        "date_borrow": date_borrow,
        "date_expected_return": date_return,
        "date_actual_return": date_return if state == "returned" else False,
        "purpose": "meeting",
        "booking_id": booking.id if booking else False,
        "location": booking.room_id.name if booking else "Phòng họp dùng chung",
        "state": state,
        "approval_status": "approved" if state in ("approved", "borrowed", "returned") else "none",
        "approval_date": date_borrow if state in ("approved", "borrowed", "returned") else False,
        "require_approval": False,
        "is_auto_created": bool(booking),
        "handover_id": handover.id if handover else False,
        "return_handover_id": return_handover.id if return_handover else False,
        "notes": f"{MARKER} {notes}".strip(),
    }
    lending = env["dnu.asset.lending"].search(
        [("asset_id", "=", asset.id), ("notes", "ilike", MARKER), ("date_borrow", "=", date_borrow)],
        limit=1,
    )
    if lending:
        lending.write(values)
    else:
        lending = env["dnu.asset.lending"].create(values)
    return lending


def ensure_booking(subject, room, organizer, organizer_nv, start_dt, end_dt, state, attendees, required_assets=False, notes=""):
    values = {
        "subject": subject,
        "room_id": room.id,
        "organizer_id": organizer.id,
        "nhan_vien_to_chuc_id": organizer_nv.id,
        "start_datetime": start_dt,
        "end_datetime": end_dt,
        "num_attendees": len(attendees) + 1,
        "attendee_ids": [(6, 0, [emp.id for emp in attendees])],
        "required_equipment_ids": [(6, 0, [asset.id for asset in (required_assets or [])])],
        "meeting_type": "offline",
        "need_projector": any(asset.category_id.code == "PRJ" for asset in (required_assets or [])),
        "need_video_conference": any("webcam" in asset.name.lower() or "jabra" in asset.name.lower() for asset in (required_assets or [])),
        "need_whiteboard": True,
        "state": "draft",
        "notes": f"{MARKER} {notes}".strip(),
        "description": f"<p>{MARKER} Dữ liệu mẫu phục vụ kiểm thử luồng đặt phòng.</p>",
    }
    booking = env["dnu.meeting.booking"].search(
        [("subject", "=", subject), ("notes", "ilike", MARKER)],
        limit=1,
    )
    if booking:
        booking.write(values)
    else:
        booking = env["dnu.meeting.booking"].create(values)
    if booking.state != state:
        booking.write({"state": state})
    if state == "in_progress":
        booking.write({"checkin_datetime": start_dt + timedelta(minutes=5), "checkin_by": env.user.id})
    if state == "done":
        booking.write(
            {
                "checkin_datetime": start_dt + timedelta(minutes=2),
                "checkout_datetime": end_dt,
                "checkin_by": env.user.id,
            }
        )
    return booking


def ensure_maintenance(asset, reporter, reporter_nv, tech, tech_nv, state, description, notes="", related_lending=False, related_handover=False):
    values = {
        "asset_id": asset.id,
        "maintenance_type": "corrective",
        "reporter_id": reporter.id if reporter else False,
        "nhan_vien_bao_cao_id": reporter_nv.id if reporter_nv else False,
        "assigned_tech_id": tech.id if tech else False,
        "nhan_vien_ky_thuat_id": tech_nv.id if tech_nv else False,
        "date_reported": dt(days=-7),
        "date_scheduled": dt(days=-6),
        "description": description,
        "priority": "high" if state in ("pending", "in_progress") else "normal",
        "state": state,
        "work_done": "Đã kiểm tra và xử lý theo quy trình." if state == "done" else False,
        "date_started": dt(days=-5) if state in ("in_progress", "done") else False,
        "date_completed": dt(days=-3) if state == "done" else False,
        "notes": f"{MARKER} {notes}".strip(),
        "lending_id": related_lending.id if related_lending else False,
        "handover_id": related_handover.id if related_handover else False,
    }
    maintenance = env["dnu.asset.maintenance"].search(
        [("asset_id", "=", asset.id), ("notes", "ilike", MARKER)],
        limit=1,
    )
    if maintenance:
        maintenance.write(values)
    else:
        maintenance = env["dnu.asset.maintenance"].create(values)
    return maintenance


def ensure_depreciation(asset, start_date, useful_life, state="running", post_count=0):
    values = {
        "asset_id": asset.id,
        "method": "linear",
        "purchase_value": asset.purchase_value,
        "salvage_value": asset.salvage_value or 0.0,
        "start_date": start_date,
        "useful_life": useful_life,
        "notes": f"{MARKER} Khấu hao mẫu cho {asset.name}",
        "state": "draft",
    }
    depreciation = env["dnu.asset.depreciation"].search(
        [("asset_id", "=", asset.id), ("notes", "ilike", MARKER)],
        limit=1,
    )
    if depreciation:
        depreciation.depreciation_line_ids.unlink()
        depreciation.write(values)
    else:
        depreciation = env["dnu.asset.depreciation"].create(values)

    depreciation.action_start()
    lines = depreciation.depreciation_line_ids.sorted("date")
    for line in lines[:post_count]:
        if line.state != "posted":
            line.action_post()
    if state == "completed":
        for line in lines:
            if line.state != "posted":
                line.action_post()
        depreciation.action_complete()
    return depreciation


def ensure_transfer(asset, from_nv, to_nv, state, reason, notes=""):
    values = {
        "asset_id": asset.id,
        "date": d(-2),
        "transfer_type": "employee",
        "from_employee_id": from_nv.id if from_nv else False,
        "from_department_id": from_nv.don_vi_chinh_id.id if from_nv and from_nv.don_vi_chinh_id else False,
        "from_location": "Tầng 2 - Khu hành chính",
        "to_employee_id": to_nv.id if to_nv else False,
        "reason": reason,
        "handover_date": d(-1),
        "handover_by": from_nv.id if from_nv else False,
        "received_by": to_nv.id if to_nv else False,
        "condition_before": "good",
        "condition_after": "good",
        "state": state,
        "notes": f"{MARKER} {notes}".strip(),
    }
    transfer = env["dnu.asset.transfer"].search(
        [("asset_id", "=", asset.id), ("notes", "ilike", MARKER)],
        limit=1,
    )
    if transfer:
        transfer.write(values)
    else:
        transfer = env["dnu.asset.transfer"].create(values)
    if state == "completed":
        asset.write(
            {
                "state": "assigned",
                "assigned_nhan_vien_id": to_nv.id if to_nv else False,
                "assigned_to": to_nv.hr_employee_id.id if to_nv and to_nv.hr_employee_id else False,
                "assignment_date": d(-1),
                "location": to_nv.don_vi_chinh_id.ten_don_vi if to_nv and to_nv.don_vi_chinh_id else "Văn phòng mới",
            }
        )
    return transfer


def ensure_disposal(asset, requested_by, state, disposal_type, reason, current_value, disposal_value, notes=""):
    values = {
        "asset_id": asset.id,
        "date": d(-1),
        "disposal_type": disposal_type,
        "reason": reason,
        "requested_by": requested_by.id,
        "executed_by": requested_by.id,
        "current_value": current_value,
        "disposal_value": disposal_value,
        "disposal_value_is_manual": True,
        "state": state,
        "executed_date": d(0) if state == "done" else False,
        "notes": f"{MARKER} {notes}".strip(),
    }
    disposal = env["dnu.asset.disposal"].search(
        [("asset_id", "=", asset.id), ("notes", "ilike", MARKER)],
        limit=1,
    )
    if disposal:
        disposal.write(values)
    else:
        disposal = env["dnu.asset.disposal"].create(values)
    if state == "done":
        asset.write({"state": "disposed", "active": False})
    return disposal


def seed_inventory(responsible, team, assets, found_ids, damaged_ids, missing_ids):
    inventory = env["dnu.asset.inventory"].search([("notes", "ilike", MARKER)], limit=1)
    values = {
        "date": d(0),
        "inventory_type": "spot",
        "scope": "custom",
        "responsible_id": responsible.id,
        "team_ids": [(6, 0, [member.id for member in team])],
        "state": "done",
        "start_date": dt(days=-1),
        "end_date": dt(days=-1, hours=2),
        "notes": f"{MARKER} Kiểm kê mẫu theo luồng kiểm thử",
        "recommendations": "Theo dõi các tài sản có dấu hiệu hư hỏng và rà soát chênh lệch vị trí.",
    }
    if inventory:
        inventory.line_ids.unlink()
        inventory.write(values)
    else:
        inventory = env["dnu.asset.inventory"].create(values)

    for asset in assets:
        status = "found"
        if asset.id in damaged_ids:
            status = "damaged"
        elif asset.id in missing_ids:
            status = "missing"
        line = env["dnu.asset.inventory.line"].create(
            {
                "inventory_id": inventory.id,
                "asset_id": asset.id,
                "expected_location": asset.location,
                "expected_assigned_to": asset.assigned_to.id if asset.assigned_to else False,
                "actual_location": asset.location,
                "actual_assigned_to": asset.assigned_to.id if asset.assigned_to else False,
                "state": "checked",
                "status": status,
                "checked_date": dt(days=-1, hours=1),
                "checked_by": responsible.id,
                "condition": "poor" if status == "damaged" else "good",
                "notes": MARKER,
            }
        )
        if status == "missing":
            line.write({"actual_location": False, "actual_assigned_to": False})
    inventory._generate_summary()
    inventory._apply_inventory_results()
    return inventory


def cleanup_demo_records():
    cleanup_rules = [
        ("dnu.asset.inventory", [("notes", "ilike", MARKER)]),
        ("dnu.asset.disposal", [("notes", "ilike", MARKER)]),
        ("dnu.asset.transfer", [("notes", "ilike", MARKER)]),
        ("dnu.asset.maintenance", ["|", ("notes", "ilike", MARKER), ("description", "ilike", MARKER)]),
        ("dnu.asset.lending", [("notes", "ilike", MARKER)]),
        ("dnu.asset.handover", [("notes", "ilike", MARKER)]),
        ("dnu.meeting.booking", [("notes", "ilike", MARKER)]),
        ("dnu.asset.assignment", [("notes", "ilike", MARKER)]),
        ("dnu.asset.depreciation", [("notes", "ilike", MARKER)]),
    ]
    for model_name, domain in cleanup_rules:
        records = env[model_name].search(domain)
        if records:
            records.unlink()


cleanup_demo_records()

dept_facility = ensure_department("Demo Facility Management")
dept_admin = ensure_department("Demo Hành chính")
dept_board = ensure_department("Demo Điều hành")

job_manager = ensure_job("Demo Quản lý tài sản")
job_technician = ensure_job("Demo Kỹ thuật viên")
job_admin = ensure_job("Demo Chuyên viên hành chính")
job_director = ensure_job("Demo Điều phối dự án")

don_vi_facility = ensure_don_vi("DV-DEMO-FM", "Phòng Bảo trì")
don_vi_admin = ensure_don_vi("DV-DEMO-AD", "Phòng Hành chính")
don_vi_board = ensure_don_vi("DV-DEMO-BD", "Ban Điều hành")

chuc_vu_checker = ensure_chuc_vu("CV-DEMO-KK", "Kiểm kê tài sản")
chuc_vu_technician = ensure_chuc_vu("CV-DEMO-KT", "Kỹ Thuật Viên")
chuc_vu_admin = ensure_chuc_vu("CV-DEMO-HC", "Chuyên viên hành chính")
chuc_vu_manager = ensure_chuc_vu("CV-DEMO-QL", "Trưởng bộ phận")

asset_manager, nv_asset_manager = ensure_employee(
    "demoqlts",
    "Nguyễn Minh Khang",
    "demo.flow.asset.manager@example.com",
    "0901111111",
    d(-12000),
    dept_facility,
    job_manager,
    don_vi_facility,
    chuc_vu_checker,
)
technician, nv_technician = ensure_employee(
    "demoktv",
    "Trần Quốc Bảo",
    "demo.flow.technician@example.com",
    "0902222222",
    d(-11000),
    dept_facility,
    job_technician,
    don_vi_facility,
    chuc_vu_technician,
)
admin_staff, nv_admin_staff = ensure_employee(
    "demohc",
    "Phạm Thu Hà",
    "demo.flow.admin@example.com",
    "0903333333",
    d(-10500),
    dept_admin,
    job_admin,
    don_vi_admin,
    chuc_vu_admin,
)
project_lead, nv_project_lead = ensure_employee(
    "demopm",
    "Lê Đức Anh",
    "demo.flow.pm@example.com",
    "0904444444",
    d(-9800),
    dept_board,
    job_director,
    don_vi_board,
    chuc_vu_manager,
)
operations_staff, nv_operations_staff = ensure_employee(
    "demoops",
    "Võ Thanh Tùng",
    "demo.flow.ops@example.com",
    "0905555555",
    d(-9600),
    dept_admin,
    job_admin,
    don_vi_admin,
    chuc_vu_admin,
)

supplier_it = ensure_partner("Demo Tech Supply")
supplier_office = ensure_partner("Demo Office Furniture")

cat_laptop = ensure_category("LAP", "Laptop")
cat_projector = ensure_category("PRJ", "Máy chiếu & hội nghị")
cat_room = ensure_category("ROM", "Thiết bị phòng họp")
cat_printer = ensure_category("PRN", "Máy in & văn phòng")

room_alpha = ensure_room(
    "R-ALPHA",
    "Phòng họp Alpha",
    12,
    "Tầng 3 - Tòa A",
    admin_staff,
    floor="3",
    has_projector=True,
    has_tv=True,
    has_whiteboard=True,
    has_video_conference=True,
)
room_beta = ensure_room(
    "R-BETA",
    "Phòng họp Beta",
    20,
    "Tầng 5 - Tòa A",
    admin_staff,
    floor="5",
    has_projector=True,
    has_tv=True,
    has_whiteboard=True,
    has_video_conference=True,
)
room_gamma = ensure_room(
    "R-GAMMA",
    "Phòng thảo luận Gamma",
    6,
    "Tầng 2 - Tòa B",
    admin_staff,
    building="Tòa B",
    floor="2",
    has_projector=False,
    has_tv=True,
    has_whiteboard=True,
    has_video_conference=False,
)

asset_dell = ensure_asset(
    "Laptop Dell Latitude 5440",
    cat_laptop,
    supplier_it,
    serial_number="DEMO-LAP-001",
    purchase_date=d(-420),
    purchase_value=23500000,
    salvage_value=3000000,
    warranty_expiry=d(300),
    location="Kho thiết bị tầng 2",
)
asset_lenovo = ensure_asset(
    "Laptop Lenovo ThinkPad T14",
    cat_laptop,
    supplier_it,
    serial_number="DEMO-LAP-002",
    purchase_date=d(-520),
    purchase_value=26500000,
    salvage_value=4000000,
    warranty_expiry=d(180),
    state="assigned",
    assigned_to=project_lead,
    assigned_nhan_vien=nv_project_lead,
    assignment_date=d(-45),
    location="Phòng Điều hành",
)
asset_epson = ensure_asset(
    "Máy chiếu Epson EB-FH06",
    cat_projector,
    supplier_it,
    serial_number="DEMO-PRJ-001",
    purchase_date=d(-800),
    purchase_value=18000000,
    salvage_value=2000000,
    warranty_expiry=d(90),
    location="Kho thiết bị tầng 2",
)
asset_jabra = ensure_asset(
    "Loa hội nghị Jabra Speak 750",
    cat_projector,
    supplier_it,
    serial_number="DEMO-PRJ-002",
    purchase_date=d(-600),
    purchase_value=9500000,
    salvage_value=1000000,
    location="Kho thiết bị tầng 2",
)
asset_webcam = ensure_asset(
    "Webcam Logitech Brio 4K",
    cat_projector,
    supplier_it,
    serial_number="DEMO-PRJ-003",
    purchase_date=d(-500),
    purchase_value=5200000,
    salvage_value=500000,
    location="Kho thiết bị tầng 2",
)
asset_tv = ensure_asset(
    "TV Samsung 55 inch phòng Alpha",
    cat_room,
    supplier_office,
    serial_number="DEMO-ROM-001",
    purchase_date=d(-900),
    purchase_value=16000000,
    salvage_value=1500000,
    location="Phòng họp Alpha",
    room=room_alpha,
)
asset_interactive = ensure_asset(
    "Màn hình tương tác ViewSonic 65 inch",
    cat_room,
    supplier_office,
    serial_number="DEMO-ROM-002",
    purchase_date=d(-730),
    purchase_value=42000000,
    salvage_value=5000000,
    location="Phòng họp Beta",
    room=room_beta,
)
asset_printer = ensure_asset(
    "Máy in Brother HL-L8360CDW",
    cat_printer,
    supplier_office,
    serial_number="DEMO-PRN-001",
    purchase_date=d(-660),
    purchase_value=11000000,
    salvage_value=1200000,
    location="Khu hành chính tầng 2",
)
asset_hp_old = ensure_asset(
    "Laptop HP ProBook 440 G7",
    cat_laptop,
    supplier_it,
    serial_number="DEMO-LAP-003",
    purchase_date=d(-1200),
    purchase_value=17000000,
    salvage_value=1000000,
    state="disposed",
    active=False,
    location="Kho chờ thanh lý",
)

room_alpha.write({"equipment_ids": [(6, 0, [asset_tv.id])]})
room_beta.write({"equipment_ids": [(6, 0, [asset_interactive.id])]})

assignment_active = ensure_assignment(
    asset_lenovo,
    project_lead,
    nv_project_lead,
    d(-45),
    state="active",
    notes="Gán laptop làm việc cho điều phối dự án",
)
assignment_returned = ensure_assignment(
    asset_dell,
    operations_staff,
    nv_operations_staff,
    d(-20),
    state="returned",
    date_to=d(-5),
    notes="Lịch sử bàn giao tạm thời cho khối vận hành",
)
asset_dell.write({"state": "available", "assigned_to": False, "assigned_nhan_vien_id": False, "assignment_date": False})

dep_running = ensure_depreciation(asset_epson, d(-240), 12, state="running", post_count=6)
dep_completed = ensure_depreciation(asset_hp_old, d(-420), 12, state="completed", post_count=12)

booking_draft = ensure_booking(
    "Họp lập kế hoạch kiểm kê quý III",
    room_alpha,
    admin_staff,
    nv_admin_staff,
    dt(days=5, hours=9 - datetime.now().hour),
    dt(days=5, hours=11 - datetime.now().hour),
    "draft",
    [project_lead, technician],
    notes="Booking mới tạo, chưa trình duyệt",
)
booking_submitted = ensure_booking(
    "Họp phê duyệt mua sắm thiết bị",
    room_beta,
    admin_staff,
    nv_admin_staff,
    dt(days=4, hours=14 - datetime.now().hour),
    dt(days=4, hours=16 - datetime.now().hour),
    "submitted",
    [asset_manager, project_lead, operations_staff],
    notes="Booking đang chờ duyệt",
)
booking_confirmed = ensure_booking(
    "Họp kickoff triển khai ERP cơ sở vật chất",
    room_beta,
    project_lead,
    nv_project_lead,
    dt(days=2, hours=9 - datetime.now().hour),
    dt(days=2, hours=11 - datetime.now().hour),
    "confirmed",
    [admin_staff, technician, operations_staff],
    required_assets=[asset_epson],
    notes="Booking đã xác nhận và chờ cấp thiết bị",
)
booking_in_progress = ensure_booking(
    "Họp vận hành sáng thứ Hai",
    room_alpha,
    admin_staff,
    nv_admin_staff,
    dt(hours=-1),
    dt(hours=1),
    "in_progress",
    [technician, operations_staff],
    required_assets=[asset_jabra],
    notes="Booking đang diễn ra",
)
booking_done = ensure_booking(
    "Họp tổng kết bảo trì tháng trước",
    room_gamma,
    asset_manager,
    nv_asset_manager,
    dt(days=-2, hours=9 - datetime.now().hour),
    dt(days=-2, hours=10 - datetime.now().hour),
    "done",
    [admin_staff, technician],
    required_assets=[asset_webcam],
    notes="Booking hoàn tất để test hậu kiểm",
)
booking_cancelled = ensure_booking(
    "Họp đã hủy do đổi lịch ban giám đốc",
    room_alpha,
    project_lead,
    nv_project_lead,
    dt(days=7, hours=13 - datetime.now().hour),
    dt(days=7, hours=14 - datetime.now().hour),
    "cancelled",
    [asset_manager, admin_staff],
    notes="Booking bị hủy",
)

lending_approved = ensure_lending(
    asset_epson,
    project_lead,
    nv_project_lead,
    booking_confirmed.start_datetime,
    booking_confirmed.end_datetime + timedelta(hours=2),
    "approved",
    booking=booking_confirmed,
    notes="Thiết bị giữ chỗ cho cuộc họp đã duyệt",
)

lending_borrowed = ensure_lending(
    asset_jabra,
    admin_staff,
    nv_admin_staff,
    booking_in_progress.start_datetime,
    booking_in_progress.end_datetime,
    "borrowed",
    booking=booking_in_progress,
    notes="Thiết bị đã bàn giao cho cuộc họp đang diễn ra",
)
handover_borrowed = ensure_handover(
    asset_jabra,
    nv_admin_staff,
    "lending",
    booking_in_progress.start_datetime,
    lending=lending_borrowed,
    notes="Biên bản bàn giao cho loa hội nghị",
)
lending_borrowed.write({"handover_id": handover_borrowed.id})
asset_jabra.write(
    {
        "state": "assigned",
        "assigned_to": admin_staff.id,
        "assigned_nhan_vien_id": nv_admin_staff.id,
        "assignment_date": d(0),
    }
)

lending_returned = ensure_lending(
    asset_webcam,
    asset_manager,
    nv_asset_manager,
    booking_done.start_datetime,
    booking_done.end_datetime,
    "returned",
    booking=booking_done,
    notes="Thiết bị đã trả xong sau cuộc họp hoàn tất",
)
handover_lending_returned = ensure_handover(
    asset_webcam,
    nv_asset_manager,
    "lending",
    booking_done.start_datetime,
    lending=lending_returned,
    notes="Biên bản giao webcam",
)
handover_returned = ensure_handover(
    asset_webcam,
    nv_asset_manager,
    "return",
    booking_done.end_datetime,
    lending=lending_returned,
    notes="Biên bản trả webcam",
)
lending_returned.write(
    {
        "handover_id": handover_lending_returned.id,
        "return_handover_id": handover_returned.id,
        "return_condition": "good",
        "return_notes": "Thiết bị nguyên trạng sau khi sử dụng",
    }
)
asset_webcam.write({"state": "available", "assigned_to": False, "assigned_nhan_vien_id": False})

maintenance_pending = ensure_maintenance(
    asset_printer,
    admin_staff,
    nv_admin_staff,
    technician,
    nv_technician,
    "pending",
    f"{MARKER} Máy in bị kẹt giấy liên tục, cần kiểm tra cụm sấy.",
    notes="Phiếu đang chờ kỹ thuật xử lý",
)
maintenance_done = ensure_maintenance(
    asset_interactive,
    admin_staff,
    nv_admin_staff,
    technician,
    nv_technician,
    "done",
    f"{MARKER} Màn hình cảm ứng bị lệch điểm chạm, đã hiệu chỉnh lại.",
    notes="Phiếu hoàn tất để test báo cáo bảo trì",
)
asset_interactive.write({"state": "available"})

transfer_completed = ensure_transfer(
    asset_lenovo,
    nv_project_lead,
    nv_operations_staff,
    "completed",
    "reassignment",
    notes="Luân chuyển laptop giữa hai nhân sự dự án",
)

disposal_submitted = ensure_disposal(
    asset_printer,
    asset_manager,
    "submitted",
    "sale",
    "obsolete",
    current_value=3500000,
    disposal_value=2500000,
    notes="Đề xuất thanh lý máy in cũ đang chờ duyệt",
)
disposal_done = ensure_disposal(
    asset_hp_old,
    asset_manager,
    "done",
    "scrap",
    "end_life",
    current_value=1000000,
    disposal_value=0,
    notes="Hồ sơ thanh lý hoàn tất",
)

inventory = seed_inventory(
    asset_manager,
    [asset_manager, technician],
    [asset_dell, asset_epson, asset_printer, asset_tv],
    found_ids={asset_dell.id, asset_epson.id, asset_tv.id},
    damaged_ids={asset_printer.id},
    missing_ids=set(),
)

summary = {
    "hr_employee": env["hr.employee"].search_count([("work_email", "ilike", "demo.flow.")]),
    "nhan_vien": env["nhan_vien"].search_count([("ma_dinh_danh", "like", "demo%")]),
    "rooms": env["dnu.meeting.room"].search_count([("description", "ilike", MARKER)]),
    "assets": env["dnu.asset"].search_count([("description", "ilike", MARKER)]),
    "bookings": env["dnu.meeting.booking"].search_count([("notes", "ilike", MARKER)]),
    "lendings": env["dnu.asset.lending"].search_count([("notes", "ilike", MARKER)]),
    "maintenances": env["dnu.asset.maintenance"].search_count([("notes", "ilike", MARKER)]),
    "transfers": env["dnu.asset.transfer"].search_count([("notes", "ilike", MARKER)]),
    "disposals": env["dnu.asset.disposal"].search_count([("notes", "ilike", MARKER)]),
    "inventories": env["dnu.asset.inventory"].search_count([("notes", "ilike", MARKER)]),
}

print("Seed demo flow completed:")
for key, value in summary.items():
    print(f" - {key}: {value}")
