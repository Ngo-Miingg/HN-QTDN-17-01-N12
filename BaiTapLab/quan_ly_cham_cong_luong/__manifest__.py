# -*- coding: utf-8 -*-

{
    "name": "Quan ly cham cong va luong",
    "summary": "Quan ly cham cong, thuong ky luat va tinh phieu luong",
    "description": """
Module bai tap lab cham cong - luong.
Ke thua du lieu nhan vien tu module nhan_su.
    """,
    "author": "Student",
    "category": "Human Resources",
    "version": "15.0.1.0.0",
    "depends": ["base", "nhan_su"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_luong_co_ban_views.xml",
        "views/hr_cham_cong_views.xml",
        "views/hr_khen_thuong_ky_luat_views.xml",
        "views/hr_phieu_luong_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
