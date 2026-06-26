param(
    [string]$Database = "ttdn_n6_dev"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-Location -LiteralPath $root

$existingContainer = docker ps -a --filter "name=^/postgres_odoo-base-15-01$" --format "{{.Names}}"
if ($existingContainer) {
    docker start postgres_odoo-base-15-01 | Out-Null
} else {
    docker compose up -d postgres-odoo-base-15-01
}
python odoo-bin.py -c odoo.conf -d $Database --stop-after-init -u nhan_su,quan_ly_van_ban,event_meeting_room_extended,dnu_meeting_asset

$script = @'
import base64
from datetime import timedelta
from odoo import fields

env = globals()["env"]

Employee = env["nhan_vien"].sudo()
HrEmployee = env["hr.employee"].sudo()
AssetCategory = env["dnu.asset.category"].sudo()
Asset = env["dnu.asset"].sudo()
Lending = env["dnu.asset.lending"].sudo()
Room = env["dnu.meeting.room"].sudo()
Booking = env["dnu.meeting.booking"].sudo()
VanBanDen = env["van_ban_den"].sudo()

sig = base64.b64encode(b"SMOKE_SIGNATURE")

employee = Employee.create({
    "ma_dinh_danh": "SMOKE-PRODUCT-USER",
    "ho_ten_dem": "Smoke Product",
    "ten": "User",
    "email": "smoke.product@example.com",
})
hr_employee = HrEmployee.create({
    "name": "Smoke Product User",
    "work_email": "smoke.product@example.com",
    "nhan_vien_id": employee.id,
})
category = AssetCategory.create({"name": "Smoke Product Category", "code": "SMOKE-PRODUCT"})
asset = Asset.create({
    "name": "Smoke Product Asset",
    "code": "SMOKE-PRODUCT-ASSET",
    "category_id": category.id,
    "state": "available",
})
lending = Lending.create({
    "asset_id": asset.id,
    "nhan_vien_muon_id": employee.id,
    "purpose": "meeting",
    "purpose_note": "Smoke product approval",
    "date_borrow": fields.Datetime.now(),
    "date_expected_return": fields.Datetime.now() + timedelta(hours=2),
})
lending.action_request()
doc = VanBanDen.search([("source_model", "=", "dnu.asset.lending"), ("source_res_id", "=", lending.id)], limit=1)
assert doc, "Lending approval document was not created"
doc.write({"signature": sig})
doc.action_approve()
lending.invalidate_cache()
assert lending.state == "approved", "Lending source was not approved"
assert lending.approval_status == "approved", "Lending approval_status was not approved"

room = Room.create({
    "name": "Smoke Product Room",
    "code": "SMOKE-PRODUCT-ROOM",
    "capacity": 8,
    "state": "available",
})
booking = Booking.create({
    "subject": "Smoke Product Booking",
    "room_id": room.id,
    "organizer_id": hr_employee.id,
    "nhan_vien_to_chuc_id": employee.id,
    "start_datetime": fields.Datetime.now() + timedelta(days=1),
    "end_datetime": fields.Datetime.now() + timedelta(days=1, hours=1),
    "description": "Smoke product booking approval",
})
booking.action_submit()
doc = VanBanDen.search([("source_model", "=", "dnu.meeting.booking"), ("source_res_id", "=", booking.id)], limit=1)
assert doc, "Booking approval document was not created"
doc.write({"signature": sig})
doc.action_approve()
booking.invalidate_cache()
assert booking.state == "confirmed", "Booking source was not confirmed"

env.cr.rollback()
print("PRODUCT_SMOKE_OK")
'@

$script | python odoo-bin.py shell -c odoo.conf -d $Database
