# -*- coding: utf-8 -*-

from calendar import monthrange
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrPhieuLuong(models.Model):
    _name = "hr_phieu_luong"
    _description = "Phieu luong thang"
    _rec_name = "nhan_vien_id"
    _order = "nam desc, thang desc, nhan_vien_id"

    thang = fields.Integer(string="Thang", required=True, default=lambda self: date.today().month)
    nam = fields.Integer(string="Nam", required=True, default=lambda self: date.today().year)
    nhan_vien_id = fields.Many2one("nhan_vien", string="Nhan vien", required=True)
    ma_dinh_danh = fields.Char(
        string="Ma dinh danh",
        related="nhan_vien_id.ma_dinh_danh",
        store=True,
    )
    so_ngay_di_lam = fields.Float(
        string="So ngay di lam du ngay",
        compute="_compute_luong",
    )
    so_ngay_nua_ngay = fields.Float(
        string="So ngay nua ngay",
        compute="_compute_luong",
    )
    so_ngay_cong = fields.Float(
        string="So ngay cong tinh luong",
        compute="_compute_luong",
    )
    luong_co_ban = fields.Float(string="Luong co ban", compute="_compute_luong")
    tong_phu_cap = fields.Float(string="Tong phu cap", compute="_compute_luong")
    tong_khen_thuong = fields.Float(string="Tong khen thuong", compute="_compute_luong")
    tong_ky_luat = fields.Float(string="Tong ky luat", compute="_compute_luong")
    thuc_linh = fields.Float(string="Thuc linh", compute="_compute_luong")
    ghi_chu = fields.Text(string="Ghi chu")

    _sql_constraints = [
        (
            "unique_phieu_luong_nhan_vien_thang",
            "unique(nhan_vien_id, thang, nam)",
            "Moi nhan vien chi co mot phieu luong trong mot thang.",
        )
    ]

    @api.constrains("thang", "nam")
    def _check_thang_nam(self):
        for record in self:
            if record.thang < 1 or record.thang > 12:
                raise ValidationError("Thang phai nam trong khoang 1 den 12.")
            if record.nam < 1900:
                raise ValidationError("Nam khong hop le.")

    @api.depends("nhan_vien_id", "thang", "nam")
    def _compute_luong(self):
        for record in self:
            record.so_ngay_di_lam = 0.0
            record.so_ngay_nua_ngay = 0.0
            record.so_ngay_cong = 0.0
            record.luong_co_ban = 0.0
            record.tong_phu_cap = 0.0
            record.tong_khen_thuong = 0.0
            record.tong_ky_luat = 0.0
            record.thuc_linh = 0.0

            if not record.nhan_vien_id or not record.thang or not record.nam:
                continue

            date_from, date_to = record._get_month_range()
            attendance_domain = [
                ("nhan_vien_id", "=", record.nhan_vien_id.id),
                ("ngay_cham_cong", ">=", date_from),
                ("ngay_cham_cong", "<=", date_to),
            ]
            di_lam_count = self.env["hr_cham_cong"].search_count(
                attendance_domain + [("trang_thai", "=", "di_lam")]
            )
            nua_ngay_count = self.env["hr_cham_cong"].search_count(
                attendance_domain + [("trang_thai", "=", "nua_ngay")]
            )

            luong_config = self.env["hr_luong_co_ban"].search(
                [("nhan_vien_id", "=", record.nhan_vien_id.id)],
                limit=1,
            )
            reward_lines = self.env["hr_khen_thuong_ky_luat"].search(
                [
                    ("nhan_vien_id", "=", record.nhan_vien_id.id),
                    ("ngay_ap_dung", ">=", date_from),
                    ("ngay_ap_dung", "<=", date_to),
                ]
            )

            tong_khen_thuong = sum(
                line.so_tien for line in reward_lines if line.loai_quyet_dinh == "khen_thuong"
            )
            tong_ky_luat = sum(
                line.so_tien for line in reward_lines if line.loai_quyet_dinh == "ky_luat"
            )
            luong_co_ban = luong_config.luong_co_ban if luong_config else 0.0
            tong_phu_cap = (
                luong_config.phu_cap_an_trua + luong_config.phu_cap_trach_nhiem
                if luong_config
                else 0.0
            )
            so_ngay_cong = di_lam_count + (nua_ngay_count * 0.5)

            record.so_ngay_di_lam = di_lam_count
            record.so_ngay_nua_ngay = nua_ngay_count
            record.so_ngay_cong = so_ngay_cong
            record.luong_co_ban = luong_co_ban
            record.tong_phu_cap = tong_phu_cap
            record.tong_khen_thuong = tong_khen_thuong
            record.tong_ky_luat = tong_ky_luat
            record.thuc_linh = (
                (luong_co_ban / 26.0) * so_ngay_cong
                + tong_phu_cap
                + tong_khen_thuong
                - tong_ky_luat
            )

    def _get_month_range(self):
        self.ensure_one()
        last_day = monthrange(self.nam, self.thang)[1]
        return date(self.nam, self.thang, 1), date(self.nam, self.thang, last_day)
