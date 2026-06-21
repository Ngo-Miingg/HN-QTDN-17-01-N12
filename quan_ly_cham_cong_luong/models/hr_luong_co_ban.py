# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrLuongCoBan(models.Model):
    _name = "hr_luong_co_ban"
    _description = "Luong co ban theo nhan vien"
    _rec_name = "nhan_vien_id"
    _order = "nhan_vien_id"

    nhan_vien_id = fields.Many2one("nhan_vien", string="Nhan vien", required=True)
    ma_dinh_danh = fields.Char(
        string="Ma dinh danh",
        related="nhan_vien_id.ma_dinh_danh",
        store=True,
    )
    luong_co_ban = fields.Float(string="Luong co ban", required=True, default=0.0)
    phu_cap_an_trua = fields.Float(string="Phu cap an trua", default=0.0)
    phu_cap_trach_nhiem = fields.Float(string="Phu cap trach nhiem", default=0.0)
    ghi_chu = fields.Text(string="Ghi chu")

    _sql_constraints = [
        (
            "unique_luong_co_ban_nhan_vien",
            "unique(nhan_vien_id)",
            "Moi nhan vien chi co mot cau hinh luong co ban.",
        )
    ]

    @api.constrains("luong_co_ban", "phu_cap_an_trua", "phu_cap_trach_nhiem")
    def _check_positive_amounts(self):
        for record in self:
            if (
                record.luong_co_ban < 0
                or record.phu_cap_an_trua < 0
                or record.phu_cap_trach_nhiem < 0
            ):
                raise ValidationError("Cac khoan luong va phu cap khong duoc am.")
