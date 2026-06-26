# -*- coding: utf-8 -*-
{
    'name': "Quản lý Tài sản & Phòng họp",

    'summary': """
        Quản lý tài sản, bàn giao và đặt phòng họp""",

    'description': """
Quản lý tài sản và phòng họp theo luồng nghiệp vụ doanh nghiệp.

Phạm vi cốt lõi:
================
- Tài sản: danh mục, cấp phát, mượn/trả, bàn giao, kiểm kê, bảo trì, thanh lý
- Phòng họp: danh sách phòng, đặt lịch, kiểm tra xung đột, trạng thái sử dụng
- Nhân sự: liên kết với dữ liệu nhân viên để xác định người dùng và người tổ chức

Mục tiêu của module là giữ dữ liệu rõ ràng, luồng xử lý ngắn gọn và dễ bảo vệ khi trình bày bài tập.
    """,

    'author': "FIT-DNU",
    'website': "https://ttdn1501.aiotlabdnu.xyz/web",

    'category': 'Operations/Facility',
    'version': '1.1.0',

    # Dependencies
    'depends': ['base', 'hr', 'nhan_su', 'calendar', 'mail', 'quan_ly_van_ban', 'event_meeting_room_extended'],

    # External dependencies
    'external_dependencies': {
        'python': ['requests'],
    },

    # Data files
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/res_users_data.xml',
        'data/sequence_data.xml',
        'data/disposal_rule_data.xml',
        'data/demo_seed_data.xml',
        'data/openai_data.xml',
        'data/mail_template.xml',
        'data/cron.xml',
        
        # Wizards
        'wizards/wizard_views.xml',
        
        # Views - Assets
        'views/dnu_asset_views.xml',
        'views/dnu_asset_category_views.xml',
        'views/dnu_asset_assignment_views.xml',
        'views/dnu_asset_maintenance_views.xml',
        'views/dnu_asset_lending_views.xml',
        'views/dnu_asset_handover_views.xml',  # Biên bản bàn giao
        'views/dnu_maintenance_schedule_views.xml',
        'views/dnu_asset_depreciation_views.xml',
        'views/dnu_asset_inventory_views.xml',
        'views/dnu_asset_transfer_views.xml',
        'views/dnu_asset_disposal_views.xml',
        'views/dnu_asset_disposal_rule_views.xml',
        'reports/asset_reports.xml',
        'reports/booking_reports.xml',
        
        # Views - Meeting
        'views/dnu_meeting_room_views.xml',
        'views/dnu_meeting_booking_views.xml',

        # Views - Integration / AI / Guide
        'views/integration_views.xml',
        'views/ai_chatbot_views.xml',
        'views/openai_views.xml',
        'views/ai_integration_views.xml',
        'views/ai_history_views.xml',
        'views/user_guide_views.xml',
        'views/oauth_templates.xml',

        # Views - User guide
        'views/hr_employee_views.xml',
        'views/dnu_asset_automation_views.xml',
        'views/dnu_asset_dashboard_views.xml',
        'views/dnu_asset_center_views.xml',
        
        # Menu
        'views/menu_views.xml',
    ],

    # Demo data
    # 'demo': [
    #     'demo/demo_data.xml',
    # ],

    # Technical
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
