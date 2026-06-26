# -*- coding: utf-8 -*-
"""Seed a compact but useful fake dataset for asset + meeting flows.

Run from the repository root, for example:

    $env:ODOO_RC = "D:\\Work\\HocKy3\\Enterprise_software_integration_and_management\\TTDN-16-01-N6\\odoo.conf"
    python .\\addons\\dnu_meeting_asset\\scripts\\seed_fake_data.py

The script is idempotent for the records it creates, so you can rerun it
without duplicating the same baseline dataset.
"""

from __future__ import annotations

import base64
import os
import sys
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ODOO_RC", str(ROOT / "odoo.conf"))

import odoo  # noqa: E402
from odoo import fields  # noqa: E402
from odoo.tools import config  # noqa: E402


PREFIX = "EVAL-DEMO"


@dataclass
class SeedRefs:
    departments: dict
    positions: dict
    categories: dict
    employees: dict
    hr_employees: dict
    users: dict
    rooms: dict
    assets: dict
    assignments: dict
    bookings: dict
    lendings: dict
    maintenances: dict


def _b64(label: str) -> bytes:
    return base64.b64encode(f"{PREFIX}-{label}".encode("utf-8"))


def _get_or_create(env, model_name, search_domain, values):
    record = env[model_name].search(search_domain, limit=1)
    if record:
        return record
    return env[model_name].create(values)


def _create_nhan_vien(env, code, first, last, dob, email, department, position):
    nv = _get_or_create(env, "nhan_vien", [("ma_dinh_danh", "=", code)], {
        "ma_dinh_danh": code,
        "ho_ten_dem": first,
        "ten": last,
        "ngay_sinh": dob,
        "email": email,
    })
    _get_or_create(env, "lich_su_cong_tac", [
        ("nhan_vien_id", "=", nv.id),
        ("don_vi_id", "=", department.id),
        ("chuc_vu_id", "=", position.id),
        ("loai_chuc_vu", "=", "Chính"),
    ], {
        "nhan_vien_id": nv.id,
        "don_vi_id": department.id,
        "chuc_vu_id": position.id,
        "loai_chuc_vu": "Chính",
    })
    return nv


def _create_user(env, login, name, email, group_xmlids):
    user = env["res.users"].search([("login", "=", login)], limit=1)
    if user:
        return user
    group_ids = [env.ref(x).id for x in group_xmlids]
    return env["res.users"].with_context(no_reset_password=True).create({
        "login": login,
        "name": name,
        "email": email,
        "groups_id": [(6, 0, group_ids)],
    })


def seed_dataset(env):
    departments = {
        "board": _get_or_create(env, "don_vi", [("ma_don_vi", "=", f"{PREFIX}-DV-BOARD")], {
            "ma_don_vi": f"{PREFIX}-DV-BOARD",
            "ten_don_vi": "Ban Giám đốc",
        }),
        "admin": _get_or_create(env, "don_vi", [("ma_don_vi", "=", f"{PREFIX}-DV-ADMIN")], {
            "ma_don_vi": f"{PREFIX}-DV-ADMIN",
            "ten_don_vi": "Hành chính",
        }),
        "it": _get_or_create(env, "don_vi", [("ma_don_vi", "=", f"{PREFIX}-DV-IT")], {
            "ma_don_vi": f"{PREFIX}-DV-IT",
            "ten_don_vi": "Công nghệ thông tin",
        }),
        "maint": _get_or_create(env, "don_vi", [("ma_don_vi", "=", f"{PREFIX}-DV-MAINT")], {
            "ma_don_vi": f"{PREFIX}-DV-MAINT",
            "ten_don_vi": "Bảo trì",
        }),
    }

    positions = {
        "director": _get_or_create(env, "chuc_vu", [("ma_chuc_vu", "=", f"{PREFIX}-CV-DIRECTOR")], {
            "ma_chuc_vu": f"{PREFIX}-CV-DIRECTOR",
            "ten_chuc_vu": "Giám đốc",
        }),
        "deputy": _get_or_create(env, "chuc_vu", [("ma_chuc_vu", "=", f"{PREFIX}-CV-DEPUTY")], {
            "ma_chuc_vu": f"{PREFIX}-CV-DEPUTY",
            "ten_chuc_vu": "Phó Giám đốc",
        }),
        "coordinator": _get_or_create(env, "chuc_vu", [("ma_chuc_vu", "=", f"{PREFIX}-CV-COORD")], {
            "ma_chuc_vu": f"{PREFIX}-CV-COORD",
            "ten_chuc_vu": "Cán bộ điều phối",
        }),
        "staff": _get_or_create(env, "chuc_vu", [("ma_chuc_vu", "=", f"{PREFIX}-CV-STAFF")], {
            "ma_chuc_vu": f"{PREFIX}-CV-STAFF",
            "ten_chuc_vu": "Nhân viên",
        }),
        "checker": _get_or_create(env, "chuc_vu", [("ma_chuc_vu", "=", f"{PREFIX}-CV-CHECK")], {
            "ma_chuc_vu": f"{PREFIX}-CV-CHECK",
            "ten_chuc_vu": "Kiểm Kê",
        }),
        "technician": _get_or_create(env, "chuc_vu", [("ma_chuc_vu", "=", f"{PREFIX}-CV-TECH")], {
            "ma_chuc_vu": f"{PREFIX}-CV-TECH",
            "ten_chuc_vu": "Kỹ Thuật Viên",
        }),
    }

    users = {
        "director": _create_user(
            env,
            f"{PREFIX.lower()}_director",
            "Eval Director",
            f"{PREFIX.lower()}.director@example.com",
            ["base.group_user", "dnu_meeting_asset.group_asset_manager", "dnu_meeting_asset.group_meeting_manager"],
        ),
        "asset_manager": _create_user(
            env,
            f"{PREFIX.lower()}_asset_manager",
            "Eval Asset Manager",
            f"{PREFIX.lower()}.asset.manager@example.com",
            ["base.group_user", "dnu_meeting_asset.group_asset_manager"],
        ),
        "meeting_manager": _create_user(
            env,
            f"{PREFIX.lower()}_meeting_manager",
            "Eval Meeting Manager",
            f"{PREFIX.lower()}.meeting.manager@example.com",
            ["base.group_user", "dnu_meeting_asset.group_meeting_manager"],
        ),
        "staff": _create_user(
            env,
            f"{PREFIX.lower()}_staff",
            "Eval Staff",
            f"{PREFIX.lower()}.staff@example.com",
            ["base.group_user"],
        ),
    }

    employee_specs = [
        ("EMP-BOARD-01", "Nguyễn Văn", "Bình", "1982-04-12", "board@example.com", departments["board"], positions["director"], users["director"]),
        ("EMP-BOARD-02", "Trần Thị", "Linh", "1986-07-03", "board2@example.com", departments["board"], positions["deputy"], None),
        ("EMP-ADMIN-01", "Lê Quốc", "Huy", "1991-02-21", "admin1@example.com", departments["admin"], positions["coordinator"], users["meeting_manager"]),
        ("EMP-ADMIN-02", "Phạm Thảo", "Vy", "1994-10-30", "admin2@example.com", departments["admin"], positions["staff"], users["staff"]),
        ("EMP-IT-01", "Võ Minh", "Khang", "1990-11-08", "it1@example.com", departments["it"], positions["staff"], None),
        ("EMP-IT-02", "Đặng Thu", "Trang", "1993-05-16", "it2@example.com", departments["it"], positions["staff"], None),
        ("EMP-MAINT-01", "Bùi Thanh", "Sơn", "1988-01-25", "maint1@example.com", departments["maint"], positions["technician"], users["asset_manager"]),
        ("EMP-MAINT-02", "Hà Hải", "Yến", "1995-09-09", "maint2@example.com", departments["maint"], positions["checker"], None),
    ]

    employees = {}
    hr_employees = {}
    for code, first, last, dob, email, dept, pos, user in employee_specs:
        nv = _create_nhan_vien(env, code, first, last, dob, email, dept, pos)
        employees[code] = nv
        hr_emp = nv.hr_employee_id or env["hr.employee"].search([("nhan_vien_id", "=", nv.id)], limit=1)
        if user and hr_emp:
            hr_emp.write({"user_id": user.id})
            nv.write({"user_id": user.id})
        hr_employees[code] = hr_emp

    categories = {
        "it": _get_or_create(env, "dnu.asset.category", [("code", "=", "IT-EVAL")], {
            "name": "Thiết bị IT - EVAL",
            "code": "IT-EVAL",
            "description": "Máy tính và thiết bị công nghệ.",
            "color": 3,
        }),
        "display": _get_or_create(env, "dnu.asset.category", [("code", "=", "DISP-EVAL")], {
            "name": "Trình chiếu - EVAL",
            "code": "DISP-EVAL",
            "description": "Máy chiếu và màn hình.",
            "color": 5,
        }),
        "audio": _get_or_create(env, "dnu.asset.category", [("code", "=", "AUD-EVAL")], {
            "name": "Âm thanh - EVAL",
            "code": "AUD-EVAL",
            "description": "Micro, loa, tai nghe.",
            "color": 7,
        }),
        "office": _get_or_create(env, "dnu.asset.category", [("code", "=", "OFF-EVAL")], {
            "name": "Văn phòng - EVAL",
            "code": "OFF-EVAL",
            "description": "Thiết bị văn phòng dùng chung.",
            "color": 9,
        }),
    }

    assets = {
        "projector": _get_or_create(env, "dnu.asset", [("serial_number", "=", "EVAL-PROJ-01")], {
            "name": "Máy chiếu Epson EB-2250U",
            "category_id": categories["display"].id,
            "serial_number": "EVAL-PROJ-01",
            "purchase_date": fields.Date.today() - timedelta(days=800),
            "purchase_value": 15000000,
            "location": "Kho thiết bị tầng 1",
            "description": "Máy chiếu dùng cho phòng họp lớn.",
        }),
        "laptop": _get_or_create(env, "dnu.asset", [("serial_number", "=", "EVAL-LAP-01")], {
            "name": "Laptop Dell Latitude 5420",
            "category_id": categories["it"].id,
            "serial_number": "EVAL-LAP-01",
            "purchase_date": fields.Date.today() - timedelta(days=420),
            "purchase_value": 25000000,
            "location": "Phòng IT",
            "description": "Laptop dự phòng cho cán bộ.",
        }),
        "tv": _get_or_create(env, "dnu.asset", [("serial_number", "=", "EVAL-TV-01")], {
            "name": "TV Samsung 75 inch",
            "category_id": categories["display"].id,
            "serial_number": "EVAL-TV-01",
            "purchase_date": fields.Date.today() - timedelta(days=600),
            "purchase_value": 45000000,
            "location": "Phòng họp lớn",
            "description": "TV cố định cho phòng hội thảo.",
        }),
        "microphone": _get_or_create(env, "dnu.asset", [("serial_number", "=", "EVAL-MIC-01")], {
            "name": "Micro không dây Sennheiser",
            "category_id": categories["audio"].id,
            "serial_number": "EVAL-MIC-01",
            "purchase_date": fields.Date.today() - timedelta(days=500),
            "purchase_value": 8000000,
            "location": "Kho âm thanh",
            "description": "Bộ micro dùng cho sự kiện.",
        }),
        "wifi": _get_or_create(env, "dnu.asset", [("serial_number", "=", "EVAL-WIFI-01")], {
            "name": "Bộ phát WiFi TP-Link",
            "category_id": categories["office"].id,
            "serial_number": "EVAL-WIFI-01",
            "purchase_date": fields.Date.today() - timedelta(days=300),
            "purchase_value": 3200000,
            "location": "Kho văn phòng",
            "description": "Thiết bị mạng dùng cho phòng họp.",
        }),
        "camera": _get_or_create(env, "dnu.asset", [("serial_number", "=", "EVAL-CAM-01")], {
            "name": "Camera hội nghị Logitech",
            "category_id": categories["display"].id,
            "serial_number": "EVAL-CAM-01",
            "purchase_date": fields.Date.today() - timedelta(days=210),
            "purchase_value": 12000000,
            "location": "Phòng IT",
            "description": "Camera họp trực tuyến.",
        }),
    }

    rooms = {
        "room_a": _get_or_create(env, "dnu.meeting.room", [("code", "=", "ROOM-EVAL-A")], {
            "name": "Phòng Họp A",
            "code": "ROOM-EVAL-A",
            "capacity": 8,
            "location": "Tầng 3, Tòa A",
            "floor": "3",
            "building": "Tòa A",
            "allow_booking": True,
            "state": "available",
            "has_projector": True,
            "has_whiteboard": True,
            "has_wifi": True,
            "description": "Phòng nhỏ cho họp nhóm.",
        }),
        "room_b": _get_or_create(env, "dnu.meeting.room", [("code", "=", "ROOM-EVAL-B")], {
            "name": "Phòng Họp B",
            "code": "ROOM-EVAL-B",
            "capacity": 16,
            "location": "Tầng 3, Tòa A",
            "floor": "3",
            "building": "Tòa A",
            "allow_booking": True,
            "state": "available",
            "has_projector": True,
            "has_whiteboard": True,
            "has_video_conference": True,
            "has_wifi": True,
            "description": "Phòng tiêu chuẩn cho buổi họp nội bộ.",
        }),
        "room_c": _get_or_create(env, "dnu.meeting.room", [("code", "=", "ROOM-EVAL-C")], {
            "name": "Phòng Hội thảo",
            "code": "ROOM-EVAL-C",
            "capacity": 40,
            "location": "Tầng 4, Tòa A",
            "floor": "4",
            "building": "Tòa A",
            "allow_booking": True,
            "state": "available",
            "has_projector": True,
            "has_tv": True,
            "has_whiteboard": True,
            "has_video_conference": True,
            "has_wifi": True,
            "has_air_conditioning": True,
            "description": "Phòng lớn cho hội thảo và đào tạo.",
        }),
        "room_d": _get_or_create(env, "dnu.meeting.room", [("code", "=", "ROOM-EVAL-D")], {
            "name": "Phòng Zoom",
            "code": "ROOM-EVAL-D",
            "capacity": 6,
            "location": "Tầng 2, Tòa B",
            "floor": "2",
            "building": "Tòa B",
            "allow_booking": False,
            "state": "maintenance",
            "has_video_conference": True,
            "has_wifi": True,
            "description": "Phòng đang bảo trì để test trạng thái đóng.",
        }),
    }

    rooms["room_a"].write({"equipment_ids": [(6, 0, [assets["projector"].id, assets["microphone"].id])]} )
    rooms["room_b"].write({"equipment_ids": [(6, 0, [assets["camera"].id, assets["wifi"].id])]} )
    rooms["room_c"].write({"equipment_ids": [(6, 0, [assets["tv"].id, assets["microphone"].id, assets["camera"].id])]} )

    assignments = {}
    assignment_specs = [
        ("ASSIGN-001", assets["projector"], hr_employees["EMP-MAINT-01"], employees["EMP-MAINT-01"], fields.Date.today() - timedelta(days=14), "active"),
        ("ASSIGN-002", assets["laptop"], hr_employees["EMP-IT-01"], employees["EMP-IT-01"], fields.Date.today() - timedelta(days=30), "returned"),
        ("ASSIGN-003", assets["wifi"], hr_employees["EMP-IT-02"], employees["EMP-IT-02"], fields.Date.today() - timedelta(days=5), "cancelled"),
        ("ASSIGN-004", assets["camera"], hr_employees["EMP-ADMIN-02"], employees["EMP-ADMIN-02"], fields.Date.today() - timedelta(days=2), "active"),
    ]
    for name, asset, employee_hr, employee_nv, date_from, state in assignment_specs:
        assignment = _get_or_create(env, "dnu.asset.assignment", [("name", "=", name)], {
            "name": name,
            "asset_id": asset.id,
            "employee_id": employee_hr.id if employee_hr else False,
            "nhan_vien_id": employee_nv.id if employee_nv else False,
            "date_from": date_from,
            "state": "draft",
            "notes": f"{PREFIX} assignment {name}",
        })
        if state == "active":
            assignment.action_confirm()
        elif state == "returned":
            if assignment.state != "active":
                assignment.action_confirm()
            assignment.action_return()
        elif state == "cancelled":
            assignment.action_cancel()
        assignments[name] = assignment

    maintenances = {}
    maintenance_specs = [
        ("MAINT-001", assets["projector"], employees["EMP-MAINT-02"], hr_employees["EMP-MAINT-02"], employees["EMP-MAINT-01"], hr_employees["EMP-MAINT-01"], "high", "in_progress"),
        ("MAINT-002", assets["microphone"], employees["EMP-ADMIN-02"], hr_employees["EMP-ADMIN-02"], None, None, "normal", "pending"),
        ("MAINT-003", assets["tv"], employees["EMP-MAINT-01"], hr_employees["EMP-MAINT-01"], None, None, "urgent", "cancelled"),
    ]
    for name, asset, reporter_nv, reporter_hr, tech_nv, tech_hr, priority, target_state in maintenance_specs:
        maintenance = _get_or_create(env, "dnu.asset.maintenance", [("name", "=", name)], {
            "name": name,
            "asset_id": asset.id,
            "nhan_vien_bao_cao_id": reporter_nv.id if reporter_nv else False,
            "reporter_id": reporter_hr.id if reporter_hr else False,
            "nhan_vien_ky_thuat_id": tech_nv.id if tech_nv else False,
            "assigned_tech_id": tech_hr.id if tech_hr else False,
            "description": f"Sự cố kiểm thử {name}",
            "priority": priority,
            "state": "draft",
            "date_reported": fields.Datetime.now() - timedelta(days=3),
        })
        if target_state == "in_progress":
            maintenance.action_start()
            maintenance.action_done()
        elif target_state == "pending":
            maintenance.action_submit()
        elif target_state == "cancelled":
            maintenance.action_cancel()
        maintenances[name] = maintenance

    bookings = {}
    booking_specs = [
        ("BOOK-001", rooms["room_a"], employees["EMP-BOARD-01"], hr_employees["EMP-BOARD-01"], 6, True, True, "confirmed"),
        ("BOOK-002", rooms["room_b"], employees["EMP-ADMIN-01"], hr_employees["EMP-ADMIN-01"], 12, False, False, "submitted"),
        ("BOOK-003", rooms["room_c"], employees["EMP-ADMIN-02"], hr_employees["EMP-ADMIN-02"], 24, False, True, "cancelled"),
    ]
    for name, room, organizer_nv, organizer_hr, attendees, need_proj, need_vc, target_state in booking_specs:
        start = fields.Datetime.now() + timedelta(days=1)
        booking = _get_or_create(env, "dnu.meeting.booking", [("name", "=", name)], {
            "name": name,
            "subject": f"Họp kiểm thử {name}",
            "room_id": room.id,
            "nhan_vien_to_chuc_id": organizer_nv.id if organizer_nv else False,
            "organizer_id": organizer_hr.id if organizer_hr else False,
            "start_datetime": start,
            "end_datetime": start + timedelta(hours=1),
            "meeting_type": "offline",
            "num_attendees": attendees,
            "need_projector": need_proj,
            "need_video_conference": need_vc,
            "need_whiteboard": True,
            "state": "draft",
        })
        if target_state == "confirmed":
            booking.action_submit()
            approval_doc = env["van_ban_den"].search([
                ("source_model", "=", "dnu.meeting.booking"),
                ("source_res_id", "=", booking.id),
                ("request_type", "=", "booking_approval"),
            ], limit=1)
            if approval_doc:
                approval_doc.write({"signature": _b64(name)})
                approval_doc.action_approve()
        elif target_state == "submitted":
            booking.action_submit()
        elif target_state == "cancelled":
            booking.action_submit()
            booking.action_cancel()
        bookings[name] = booking

    lendings = {}
    lending_specs = [
        ("LEND-001", assets["laptop"], hr_employees["EMP-BOARD-01"], employees["EMP-ADMIN-02"], "approved_returned"),
        ("LEND-002", assets["camera"], hr_employees["EMP-MAINT-01"], employees["EMP-ADMIN-01"], "pending_approval"),
        ("LEND-003", assets["wifi"], hr_employees["EMP-ADMIN-01"], employees["EMP-ADMIN-01"], "requested"),
    ]
    for name, asset, manager_hr, borrower_nv, flow_state in lending_specs:
        lending = _get_or_create(env, "dnu.asset.lending", [("name", "=", name)], {
            "name": name,
            "asset_id": asset.id,
            "borrower_id": borrower_nv.hr_employee_id.id if borrower_nv and borrower_nv.hr_employee_id else False,
            "nhan_vien_muon_id": borrower_nv.id if borrower_nv else False,
            "date_borrow": fields.Datetime.now() - timedelta(days=2),
            "date_expected_return": fields.Datetime.now() + timedelta(days=3),
            "purpose": "meeting",
            "purpose_note": f"Mượn kiểm thử {name}",
            "state": "draft",
        })
        if flow_state == "approved_returned":
            lending.action_request()
            approval_doc = env["van_ban_den"].search([
                ("source_model", "=", "dnu.asset.lending"),
                ("source_res_id", "=", lending.id),
                ("request_type", "=", "lending_approval"),
            ], limit=1)
            if approval_doc:
                approval_doc.write({"signature": _b64(name)})
                approval_doc.action_approve()
            handover = lending.handover_id or lending.action_create_handover()
            handover = lending.handover_id or handover
            handover.write({
                "deliverer_signature": _b64(f"{name}-deliverer"),
                "receiver_signature": _b64(f"{name}-receiver"),
            })
            handover.action_complete()
            return_handover = lending.action_create_return_handover()
            return_handover = lending.return_handover_id or return_handover
            return_handover.write({"receiver_signature": _b64(f"{name}-return")})
            return_handover.action_complete()
        elif flow_state == "pending_approval":
            lending.action_request()
        elif flow_state == "requested":
            lending.action_request()
        lendings[name] = lending

    return SeedRefs(
        departments=departments,
        positions=positions,
        categories=categories,
        employees=employees,
        hr_employees=hr_employees,
        users=users,
        rooms=rooms,
        assets=assets,
        assignments=assignments,
        bookings=bookings,
        lendings=lendings,
        maintenances=maintenances,
    )


def main():
    db_name = config["db_name"]
    if not db_name:
        raise SystemExit("No database configured. Set ODOO_RC or pass db_name in odoo.conf.")

    with odoo.registry(db_name).cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        refs = seed_dataset(env)
        cr.commit()

    print("Seed completed for:", db_name)
    print("Departments:", len(refs.departments))
    print("Positions:", len(refs.positions))
    print("Employees:", len(refs.employees))
    print("Rooms:", len(refs.rooms))
    print("Assets:", len(refs.assets))
    print("Assignments:", len(refs.assignments))
    print("Bookings:", len(refs.bookings))
    print("Lendings:", len(refs.lendings))
    print("Maintenances:", len(refs.maintenances))


if __name__ == "__main__":
    main()
