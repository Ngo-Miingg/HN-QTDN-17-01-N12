# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrKhenThuongKyLuat(models.Model):
    _name = "hr_khen_thuong_ky_luat"
    _description = "Khen thuong va ky luat"
    _rec_name = "nhan_vien_id"
    _order = "ngay_ap_dung desc, nhan_vien_id"

    nhan_vien_id = fields.Many2one("nhan_vien", string="Nhan vien", required=True)
    loai_quyet_dinh = fields.Selection(
        [
            ("khen_thuong", "Khen thuong"),
            ("ky_luat", "Ky luat"),
        ],
        string="Loai quyet dinh",
        required=True,
        default="khen_thuong",
    )
    so_tien = fields.Float(string="So tien", required=True, default=0.0)
    ngay_ap_dung = fields.Date(
        string="Ngay ap dung",
        required=True,
        default=fields.Date.context_today,
    )
    ghi_chu = fields.Text(string="Ghi chu")

    @api.constrains("so_tien")
    def _check_so_tien(self):
        for record in self:
            if record.so_tien < 0:
                raise ValidationError("So tien khong duoc am.")
