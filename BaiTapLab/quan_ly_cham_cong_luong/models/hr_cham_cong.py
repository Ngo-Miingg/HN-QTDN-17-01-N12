# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrChamCong(models.Model):
    _name = "hr_cham_cong"
    _description = "Cham cong nhan vien"
    _rec_name = "nhan_vien_id"
    _order = "ngay_cham_cong desc, nhan_vien_id"

    nhan_vien_id = fields.Many2one("nhan_vien", string="Nhan vien", required=True)
    ngay_cham_cong = fields.Date(
        string="Ngay cham cong",
        default=fields.Date.context_today,
        required=True,
    )
    trang_thai = fields.Selection(
        [
            ("di_lam", "Di lam du ngay"),
            ("nua_ngay", "Lam nua ngay"),
            ("nghi_co_phep", "Nghi co phep"),
            ("nghi_khong_phep", "Nghi khong phep"),
        ],
        string="Trang thai",
        default="di_lam",
        required=True,
    )
    so_gio_tang_ca = fields.Float(string="So gio tang ca", default=0.0)
    nguoi_xac_nhan = fields.Char(string="Nguoi xac nhan")

    _sql_constraints = [
        (
            "unique_cham_cong_nhan_vien_ngay",
            "unique(nhan_vien_id, ngay_cham_cong)",
            "Moi nhan vien chi duoc cham cong mot lan trong mot ngay.",
        )
    ]

    @api.constrains("so_gio_tang_ca")
    def _check_so_gio_tang_ca(self):
        for record in self:
            if record.so_gio_tang_ca < 0:
                raise ValidationError("So gio tang ca khong duoc am.")
