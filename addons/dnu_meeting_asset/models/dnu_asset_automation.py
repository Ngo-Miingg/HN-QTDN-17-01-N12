# -*- coding: utf-8 -*-
"""
Asset Management Automation Module
===================================
Các tính năng tự động hóa cho quản lý tài sản:
1. Nhắc trả tài sản mượn + escalations 2 cấp
2. Chặn mượn/cấp phát mới nếu còn phiếu quá hạn
3. Tự tạo bảo trì định kỳ từ lịch bảo trì
4. Nhắc hết hạn bảo hành / kiểm định / hợp đồng
5. Quy trình thu hồi tài sản khi nhân sự nghỉ việc
6. Kiểm kê định kỳ + tự gắn cờ "Missing"
7. Tự động hóa vòng đời khi thanh lý/điều chuyển
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AssetLendingAutomation(models.Model):
    """Mở rộng dnu.asset.lending với các tính năng tự động hóa"""
    _inherit = 'dnu.asset.lending'

    # === Thêm các trường mới cho escalation tracking ===
    overdue_days = fields.Integer(
        string='Số ngày quá hạn',
        compute='_compute_overdue_days',
        store=True,
        help='Số ngày tài sản bị quá hạn trả'
    )
    reminder_sent_date = fields.Date(
        string='Ngày gửi nhắc nhở',
        help='Ngày gửi nhắc nhở trước hạn (T-1)'
    )
    escalation_level = fields.Selection([
        ('0', 'Chưa escalate'),
        ('1', 'Cấp 1 - Nhắc người mượn'),
        ('2', 'Cấp 2 - Nhắc quản lý'),
        ('3', 'Cấp 3 - Nhắc HCNS/Ban giám đốc'),
    ], string='Cấp độ escalation', default='0', tracking=True)
    last_escalation_date = fields.Date(
        string='Ngày escalation gần nhất'
    )
    
    # === Trạng thái approval cho người có quá hạn ===
    requires_approval = fields.Boolean(
        string='Cần phê duyệt',
        default=False,
        help='Đánh dấu nếu người mượn đang có phiếu quá hạn khác'
    )
    approval_note = fields.Text(
        string='Ghi chú phê duyệt'
    )

    @api.depends('date_expected_return', 'state', 'date_actual_return')
    def _compute_overdue_days(self):
        """Tính số ngày quá hạn"""
        now = fields.Datetime.now()
        for lending in self:
            if lending.state in ['borrowed', 'overdue'] and lending.date_expected_return:
                if now > lending.date_expected_return:
                    delta = now - lending.date_expected_return
                    lending.overdue_days = delta.days
                else:
                    lending.overdue_days = 0
            else:
                lending.overdue_days = 0

    # === Feature 2: Chặn mượn/cấp phát mới nếu còn phiếu quá hạn ===
    @api.model
    def create(self, vals):
        """Override create để kiểm tra người mượn có phiếu quá hạn không"""
        record = super(AssetLendingAutomation, self).create(vals)
        record._check_borrower_overdue_status()
        return record

    def _check_borrower_overdue_status(self):
        """Kiểm tra và xử lý nếu người mượn đang có phiếu quá hạn"""
        for lending in self:
            borrower = lending.borrower_id or lending.nhan_vien_muon_id
            if not borrower:
                continue
            
            # Tìm các phiếu mượn quá hạn của người này
            domain = [
                ('state', '=', 'overdue'),
                ('id', '!=', lending.id),
            ]
            
            if lending.borrower_id:
                domain.append(('borrower_id', '=', lending.borrower_id.id))
            elif lending.nhan_vien_muon_id:
                domain.append(('nhan_vien_muon_id', '=', lending.nhan_vien_muon_id.id))
            
            overdue_lendings = self.search(domain)
            
            if overdue_lendings:
                # Có phiếu quá hạn → đánh dấu cần phê duyệt
                lending.write({
                    'requires_approval': True,
                    'approval_note': _('Người mượn đang có %d phiếu mượn quá hạn: %s') % (
                        len(overdue_lendings),
                        ', '.join(overdue_lendings.mapped('name'))
                    ),
                })
                
                # Gửi thông báo cho admin tài sản
                lending.message_post(
                    body=_('⚠️ CẢNH BÁO: Người mượn %s đang có %d phiếu mượn quá hạn. Phiếu này cần được phê duyệt đặc biệt.') % (
                        borrower.name if hasattr(borrower, 'name') else borrower.ho_va_ten,
                        len(overdue_lendings)
                    ),
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )

    def action_request(self):
        """Override để chặn nếu cần phê duyệt đặc biệt"""
        for lending in self:
            if lending.requires_approval:
                # Không cho phép tự request, phải có người duyệt
                lending.write({'state': 'requested'})
                lending.message_post(
                    body=_('⚠️ Yêu cầu mượn cần phê duyệt đặc biệt do người mượn đang có phiếu quá hạn.')
                )
                # Tạo activity cho người duyệt
                lending._create_special_approval_activity()
                return True
        
        return super(AssetLendingAutomation, self).action_request()

    def _create_special_approval_activity(self):
        """Tạo activity yêu cầu phê duyệt đặc biệt"""
        self.ensure_one()
        
        # Tìm group asset manager
        manager_group = self.env.ref('dnu_meeting_asset.group_asset_manager', raise_if_not_found=False)
        if manager_group and manager_group.users:
            for user in manager_group.users[:3]:  # Gửi cho tối đa 3 người
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    date_deadline=fields.Date.today(),
                    summary=_('⚠️ Phê duyệt đặc biệt: %s') % self.name,
                    note=_('Người mượn đang có phiếu quá hạn. Vui lòng xem xét và quyết định.\n%s') % (
                        self.approval_note or ''
                    ),
                )

    # === Feature 1: Cron job nhắc trả + escalation ===
    @api.model
    def _cron_lending_reminder_escalation(self):
        """
        Cron job xử lý nhắc nhở và escalation cho phiếu mượn
        - T-1: Nhắc trước hạn 1 ngày
        - T+1, T+3, T+7: Escalation theo cấp độ
        """
        today = fields.Date.today()
        now = fields.Datetime.now()
        
        _logger.info('=== Bắt đầu cron nhắc nhở mượn tài sản ===')
        
        # === 1. Nhắc trước hạn 1 ngày (T-1) ===
        tomorrow = today + timedelta(days=1)
        tomorrow_start = fields.Datetime.to_datetime(tomorrow)
        tomorrow_end = tomorrow_start + timedelta(days=1)
        
        upcoming_lendings = self.search([
            ('state', '=', 'borrowed'),
            ('date_expected_return', '>=', tomorrow_start),
            ('date_expected_return', '<', tomorrow_end),
            ('reminder_sent_date', '!=', today),  # Chưa gửi nhắc hôm nay
        ])
        
        _logger.info('Tìm thấy %d phiếu sắp đến hạn (T-1)', len(upcoming_lendings))
        
        for lending in upcoming_lendings:
            lending._send_return_reminder()
            lending.write({'reminder_sent_date': today})
        
        # === 2. Xử lý quá hạn và escalation ===
        overdue_lendings = self.search([
            ('state', 'in', ['borrowed', 'overdue']),
            ('date_expected_return', '<', now),
        ])
        
        _logger.info('Tìm thấy %d phiếu quá hạn', len(overdue_lendings))
        
        for lending in overdue_lendings:
            # Cập nhật trạng thái quá hạn nếu chưa
            if lending.state == 'borrowed':
                lending.write({'state': 'overdue'})
            
            # Xử lý escalation theo số ngày quá hạn
            lending._process_escalation()
        
        _logger.info('=== Kết thúc cron nhắc nhở mượn tài sản ===')

    def _send_return_reminder(self):
        """Gửi nhắc nhở trả tài sản (T-1)"""
        self.ensure_one()
        
        # Gửi email
        template = self.env.ref('dnu_meeting_asset.email_template_lending_return_reminder', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True, email_values={
                'email_from': 'noreply@example.com',
            })
        
        # Tạo activity
        borrower_user = self.borrower_id.user_id if self.borrower_id else False
        if borrower_user:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=borrower_user.id,
                date_deadline=self.date_expected_return.date() if self.date_expected_return else fields.Date.today(),
                summary=_('Nhắc nhở trả tài sản'),
                note=_('Tài sản %s sẽ đến hạn trả vào ngày mai. Vui lòng chuẩn bị trả đúng hạn.') % self.asset_id.name,
            )
        
        self.message_post(body=_('📅 Đã gửi nhắc nhở trả tài sản (T-1)'))

    def _process_escalation(self):
        """Xử lý escalation theo số ngày quá hạn"""
        self.ensure_one()
        
        today = fields.Date.today()
        overdue_days = self.overdue_days
        current_level = self.escalation_level
        
        new_level = current_level
        
        # Xác định cấp độ escalation
        if overdue_days >= 7 and current_level != '3':
            new_level = '3'
        elif overdue_days >= 3 and current_level not in ['2', '3']:
            new_level = '2'
        elif overdue_days >= 1 and current_level == '0':
            new_level = '1'
        
        # Nếu cần escalate
        if new_level != current_level:
            self._do_escalation(new_level)
            self.write({
                'escalation_level': new_level,
                'last_escalation_date': today,
            })

    def _do_escalation(self, level):
        """Thực hiện escalation theo cấp độ"""
        self.ensure_one()
        
        borrower_name = self.borrower_name or 'N/A'
        asset_name = self.asset_id.name
        
        if level == '1':
            # Cấp 1: Nhắc người mượn + phụ trách
            self._escalation_level_1()
        
        elif level == '2':
            # Cấp 2: Nhắc quản lý phòng ban
            self._escalation_level_2()
        
        elif level == '3':
            # Cấp 3: Nhắc HCNS/Ban giám đốc
            self._escalation_level_3()

    def _escalation_level_1(self):
        """Escalation cấp 1: Nhắc người mượn và người duyệt"""
        self.ensure_one()
        
        # Gửi email cảnh báo quá hạn
        template = self.env.ref('dnu_meeting_asset.email_template_lending_overdue', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True, email_values={
                'email_from': 'noreply@example.com',
            })
        
        # Tạo activity cho người mượn
        borrower_user = self.borrower_id.user_id if self.borrower_id else False
        if borrower_user:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=borrower_user.id,
                date_deadline=fields.Date.today(),
                summary=_('🔴 QUÁ HẠN: Trả tài sản ngay!'),
                note=_('Tài sản %s đã quá hạn %d ngày. Vui lòng trả NGAY LẬP TỨC.') % (
                    self.asset_id.name, self.overdue_days
                ),
            )
        
        # Tạo activity cho người duyệt
        if self.approved_by:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.approved_by.id,
                date_deadline=fields.Date.today(),
                summary=_('Theo dõi phiếu mượn quá hạn'),
                note=_('Phiếu mượn %s đã quá hạn %d ngày. Người mượn: %s') % (
                    self.name, self.overdue_days, self.borrower_name
                ),
            )
        
        self.message_post(body=_('🔔 ESCALATION Cấp 1: Đã gửi nhắc nhở cho người mượn và người phụ trách'))

    def _escalation_level_2(self):
        """Escalation cấp 2: Nhắc quản lý phòng ban"""
        self.ensure_one()
        
        # Tìm quản lý phòng ban của người mượn
        manager = False
        if self.borrower_id and self.borrower_id.department_id:
            manager = self.borrower_id.department_id.manager_id
        
        if manager and manager.user_id:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=manager.user_id.id,
                date_deadline=fields.Date.today(),
                summary=_('⚠️ Nhân viên có tài sản quá hạn'),
                note=_('Nhân viên %s (Phòng %s) có tài sản mượn quá hạn %d ngày.\n\nTài sản: %s\nPhiếu mượn: %s\n\nVui lòng nhắc nhở nhân viên trả tài sản.') % (
                    self.borrower_name,
                    self.borrower_id.department_id.name if self.borrower_id.department_id else 'N/A',
                    self.overdue_days,
                    self.asset_id.name,
                    self.name,
                ),
            )
        
        # Gửi email cho quản lý
        self._send_escalation_email_to_manager(manager)
        
        self.message_post(body=_('🔔 ESCALATION Cấp 2: Đã thông báo cho quản lý phòng ban'))

    def _escalation_level_3(self):
        """Escalation cấp 3: Nhắc HCNS/Ban giám đốc"""
        self.ensure_one()
        
        # Tìm group admin HCNS
        hr_admin_group = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
        asset_admin_group = self.env.ref('dnu_meeting_asset.group_asset_manager', raise_if_not_found=False)
        
        notified_users = set()
        
        # Thông báo cho HR Manager
        if hr_admin_group:
            for user in hr_admin_group.users[:3]:
                if user.id not in notified_users:
                    self.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=user.id,
                        date_deadline=fields.Date.today(),
                        summary=_('🚨 KHẨN CẤP: Tài sản quá hạn nghiêm trọng'),
                        note=_('Phiếu mượn %s đã quá hạn %d ngày (Escalation cấp 3).\n\nNgười mượn: %s\nTài sản: %s\n\nCần xử lý KHẨN CẤP.') % (
                            self.name, self.overdue_days, self.borrower_name, self.asset_id.name
                        ),
                    )
                    notified_users.add(user.id)
        
        # Thông báo cho Asset Manager
        if asset_admin_group:
            for user in asset_admin_group.users[:3]:
                if user.id not in notified_users:
                    self.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=user.id,
                        date_deadline=fields.Date.today(),
                        summary=_('🚨 KHẨN CẤP: Tài sản quá hạn nghiêm trọng'),
                        note=_('Phiếu mượn %s đã quá hạn %d ngày (Escalation cấp 3).\n\nNgười mượn: %s\nTài sản: %s\n\nCần xử lý KHẨN CẤP.') % (
                            self.name, self.overdue_days, self.borrower_name, self.asset_id.name
                        ),
                    )
                    notified_users.add(user.id)
        
        self.message_post(body=_('🚨 ESCALATION Cấp 3: Đã thông báo cho HCNS/Quản lý tài sản'))

    def _send_escalation_email_to_manager(self, manager):
        """Gửi email escalation cho quản lý"""
        if not manager or not manager.work_email:
            return
        
        template = self.env.ref('dnu_meeting_asset.email_template_lending_escalation_manager', raise_if_not_found=False)
        if template:
            template.with_context(manager_email=manager.work_email).send_mail(self.id, force_send=True, email_values={
                'email_from': 'noreply@example.com',
            })


class AssetAutomation(models.Model):
    """Mở rộng dnu.asset với các tính năng tự động hóa"""
    _inherit = 'dnu.asset'

    # === Feature 4: Các trường cho nhắc hết hạn ===
    warranty_reminder_sent = fields.Boolean(
        string='Đã gửi nhắc bảo hành',
        default=False
    )
    warranty_status = fields.Selection([
        ('valid', 'Còn bảo hành'),
        ('expiring_soon', 'Sắp hết hạn'),
        ('expired', 'Hết bảo hành'),
    ], string='Trạng thái bảo hành', compute='_compute_warranty_status', store=True)
    
    # Ngày kiểm định
    inspection_date = fields.Date(
        string='Ngày kiểm định tiếp theo',
        tracking=True,
        help='Ngày tài sản cần được kiểm định (áp dụng cho thiết bị an toàn, PCCC, điện...)'
    )
    inspection_reminder_sent = fields.Boolean(default=False)
    
    # Ngày hết hạn hợp đồng bảo trì
    maintenance_contract_expiry = fields.Date(
        string='Hết hạn hợp đồng bảo trì',
        tracking=True
    )
    contract_reminder_sent = fields.Boolean(default=False)
    
    # Missing flag
    is_missing = fields.Boolean(
        string='Đánh dấu mất',
        default=False,
        tracking=True,
        help='Tài sản không tìm thấy qua nhiều đợt kiểm kê'
    )
    missing_since = fields.Date(
        string='Mất từ ngày'
    )
    missing_inventory_count = fields.Integer(
        string='Số kỳ kiểm kê không tìm thấy',
        default=0
    )

    @api.depends('warranty_expiry')
    def _compute_warranty_status(self):
        """Tính trạng thái bảo hành"""
        today = fields.Date.today()
        for asset in self:
            if not asset.warranty_expiry:
                asset.warranty_status = False
            elif asset.warranty_expiry < today:
                asset.warranty_status = 'expired'
            elif asset.warranty_expiry <= today + timedelta(days=30):
                asset.warranty_status = 'expiring_soon'
            else:
                asset.warranty_status = 'valid'

    # === Feature 4: Cron nhắc hết hạn bảo hành/kiểm định ===
    @api.model
    def _cron_warranty_inspection_reminder(self):
        """
        Cron job nhắc hết hạn bảo hành, kiểm định, hợp đồng
        - 30 ngày, 14 ngày, 7 ngày trước
        """
        today = fields.Date.today()
        
        _logger.info('=== Bắt đầu cron nhắc hạn bảo hành/kiểm định ===')
        
        reminder_days = [30, 14, 7]
        
        # === 1. Nhắc hết hạn bảo hành ===
        for days in reminder_days:
            target_date = today + timedelta(days=days)
            
            assets = self.search([
                ('warranty_expiry', '=', target_date),
                ('state', '!=', 'disposed'),
            ])
            
            for asset in assets:
                asset._send_warranty_reminder(days)
        
        # Đánh dấu expired
        expired_assets = self.search([
            ('warranty_expiry', '<', today),
            ('warranty_status', '!=', 'expired'),
            ('state', '!=', 'disposed'),
        ])
        for asset in expired_assets:
            asset.message_post(body=_('⚠️ Bảo hành đã HẾT HẠN từ ngày %s') % asset.warranty_expiry)
        
        # === 2. Nhắc kiểm định ===
        for days in reminder_days:
            target_date = today + timedelta(days=days)
            
            assets = self.search([
                ('inspection_date', '=', target_date),
                ('state', '!=', 'disposed'),
            ])
            
            for asset in assets:
                asset._send_inspection_reminder(days)
        
        # === 3. Nhắc hết hạn hợp đồng bảo trì ===
        for days in reminder_days:
            target_date = today + timedelta(days=days)
            
            assets = self.search([
                ('maintenance_contract_expiry', '=', target_date),
                ('state', '!=', 'disposed'),
            ])
            
            for asset in assets:
                asset._send_contract_reminder(days)
        
        _logger.info('=== Kết thúc cron nhắc hạn bảo hành/kiểm định ===')

    def _send_warranty_reminder(self, days_until_expiry):
        """Gửi nhắc nhở hết hạn bảo hành"""
        self.ensure_one()
        
        # Tạo activity cho người quản lý tài sản
        manager_group = self.env.ref('dnu_meeting_asset.group_asset_manager', raise_if_not_found=False)
        if manager_group:
            for user in manager_group.users[:2]:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    date_deadline=self.warranty_expiry,
                    summary=_('⏰ Bảo hành sắp hết hạn: %s') % self.name,
                    note=_('Tài sản %s (%s) sẽ hết bảo hành trong %d ngày (ngày %s).\n\nNhà cung cấp: %s') % (
                        self.name, self.code, days_until_expiry, self.warranty_expiry,
                        self.supplier_id.name if self.supplier_id else 'N/A'
                    ),
                )
        
        self.message_post(body=_('📅 Nhắc nhở: Bảo hành sẽ hết hạn trong %d ngày') % days_until_expiry)

    def _send_inspection_reminder(self, days_until_inspection):
        """Gửi nhắc nhở kiểm định"""
        self.ensure_one()
        
        manager_group = self.env.ref('dnu_meeting_asset.group_asset_manager', raise_if_not_found=False)
        if manager_group:
            for user in manager_group.users[:2]:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    date_deadline=self.inspection_date,
                    summary=_('🔍 Kiểm định sắp đến hạn: %s') % self.name,
                    note=_('Tài sản %s (%s) cần kiểm định trong %d ngày (ngày %s).\n\nVui lòng lên lịch kiểm định.') % (
                        self.name, self.code, days_until_inspection, self.inspection_date
                    ),
                )
        
        self.message_post(body=_('🔍 Nhắc nhở: Kiểm định trong %d ngày') % days_until_inspection)

    def _send_contract_reminder(self, days_until_expiry):
        """Gửi nhắc nhở hết hạn hợp đồng bảo trì"""
        self.ensure_one()
        
        manager_group = self.env.ref('dnu_meeting_asset.group_asset_manager', raise_if_not_found=False)
        if manager_group:
            for user in manager_group.users[:2]:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    date_deadline=self.maintenance_contract_expiry,
                    summary=_('📋 Hợp đồng bảo trì sắp hết: %s') % self.name,
                    note=_('Hợp đồng bảo trì tài sản %s (%s) sẽ hết hạn trong %d ngày.\n\nVui lòng gia hạn hoặc tìm nhà cung cấp mới.') % (
                        self.name, self.code, days_until_expiry
                    ),
                )
        
        self.message_post(body=_('📋 Nhắc nhở: Hợp đồng bảo trì hết hạn trong %d ngày') % days_until_expiry)


class MaintenanceScheduleAutomation(models.Model):
    """Mở rộng dnu.maintenance.schedule với tự động hóa nâng cao"""
    _inherit = 'dnu.maintenance.schedule'

    # === Feature 3: Cron tạo bảo trì định kỳ (nâng cao) ===
    last_generated_date = fields.Date(
        string='Ngày tạo phiếu gần nhất',
        help='Tránh tạo trùng phiếu bảo trì'
    )
    auto_assign = fields.Boolean(
        string='Tự động gán kỹ thuật viên',
        default=True
    )
    notify_before_days = fields.Integer(
        string='Thông báo trước (ngày)',
        default=3,
        help='Số ngày thông báo trước ngày bảo trì'
    )

    @api.model
    def _cron_generate_scheduled_maintenance(self):
        """
        Cron job nâng cao để tạo bảo trì định kỳ
        - Kiểm tra trùng lặp
        - Tự động gán kỹ thuật viên
        - Gửi thông báo
        """
        today = fields.Date.today()
        
        _logger.info('=== Bắt đầu cron tạo bảo trì định kỳ ===')
        
        # Tìm các lịch bảo trì cần tạo phiếu
        schedules = self.search([
            ('state', '=', 'active'),
            ('next_date', '<=', today + timedelta(days=7)),
        ])
        
        created_count = 0
        
        for schedule in schedules:
            # Kiểm tra đã tạo chưa (tránh trùng)
            if schedule.last_generated_date == today:
                continue
            
            # Kiểm tra có phiếu pending không
            pending = self.env['dnu.asset.maintenance'].search([
                ('schedule_id', '=', schedule.id),
                ('state', 'in', ['draft', 'pending', 'in_progress']),
            ], limit=1)
            
            if pending:
                continue
            
            # Tạo phiếu bảo trì
            maintenance = schedule._create_maintenance_request_enhanced()
            
            if maintenance:
                schedule.write({'last_generated_date': today})
                created_count += 1
                
                # Gửi nhắc nhở
                if schedule.send_reminder:
                    schedule._send_maintenance_notification(maintenance)
        
        _logger.info('Đã tạo %d phiếu bảo trì định kỳ', created_count)
        _logger.info('=== Kết thúc cron tạo bảo trì định kỳ ===')

    def _create_maintenance_request_enhanced(self):
        """Tạo phiếu bảo trì với các tính năng nâng cao"""
        self.ensure_one()
        
        vals = {
            'asset_id': self.asset_id.id if self.target_type == 'asset' else False,
            'maintenance_type': self.maintenance_type,
            'description': self.description,
            'date_scheduled': fields.Datetime.now(),
            'schedule_id': self.id,
            'state': 'pending',
            'priority': 'normal',
        }
        
        # Tự động gán kỹ thuật viên
        if self.auto_assign and self.assigned_tech_id:
            vals['assigned_tech_id'] = self.assigned_tech_id.id
        
        maintenance = self.env['dnu.asset.maintenance'].create(vals)
        
        # Cập nhật lịch
        self.write({
            'last_maintenance_date': fields.Date.today(),
            'last_maintenance_id': maintenance.id,
        })
        
        return maintenance

    def _send_maintenance_notification(self, maintenance):
        """Gửi thông báo về phiếu bảo trì mới"""
        self.ensure_one()
        
        target_name = self.asset_id.name if self.target_type == 'asset' else self.room_id.name
        
        # Thông báo cho kỹ thuật viên
        if maintenance.assigned_tech_id and maintenance.assigned_tech_id.user_id:
            maintenance.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=maintenance.assigned_tech_id.user_id.id,
                date_deadline=fields.Date.today() + timedelta(days=self.notify_before_days),
                summary=_('🔧 Bảo trì định kỳ: %s') % target_name,
                note=_('Phiếu bảo trì định kỳ %s đã được tạo.\n\nĐối tượng: %s\nLoại: %s\nMô tả: %s') % (
                    maintenance.name, target_name, 
                    dict(self._fields['maintenance_type'].selection).get(self.maintenance_type),
                    self.description
                ),
            )
        
        self.message_post(
            body=_('✅ Đã tạo phiếu bảo trì định kỳ: %s cho %s') % (maintenance.name, target_name)
        )


class AssetInventoryAutomation(models.Model):
    """Mở rộng dnu.asset.inventory với tự động hóa"""
    _inherit = 'dnu.asset.inventory'

    # === Feature 6: Kiểm kê định kỳ tự động ===
    is_auto_generated = fields.Boolean(
        string='Tự động tạo',
        default=False,
        help='Đánh dấu nếu đợt kiểm kê được tạo tự động bởi cron'
    )

    @api.model
    def _cron_generate_periodic_inventory(self):
        """
        Cron job tạo đợt kiểm kê định kỳ (chạy đầu mỗi tháng hoặc quý)
        """
        today = fields.Date.today()
        
        _logger.info('=== Bắt đầu cron tạo kiểm kê định kỳ ===')
        
        # Chỉ chạy vào ngày 1 hàng tháng
        if today.day != 1:
            _logger.info('Không phải ngày 1, bỏ qua')
            return
        
        # Kiểm tra xem tháng này đã có kiểm kê chưa
        month_start = today.replace(day=1)
        existing = self.search([
            ('date', '>=', month_start),
            ('is_auto_generated', '=', True),
        ], limit=1)
        
        if existing:
            _logger.info('Tháng này đã có kiểm kê tự động, bỏ qua')
            return
        
        # Tạo đợt kiểm kê mới
        inventory = self.create({
            'date': today,
            'inventory_type': 'periodic',
            'scope': 'all',
            'responsible_id': self._get_default_responsible().id,
            'is_auto_generated': True,
            'notes': _('Kiểm kê định kỳ tự động tháng %s/%s') % (today.month, today.year),
        })
        
        # Tạo danh sách tài sản
        inventory.action_generate_inventory()
        
        # Thông báo
        inventory._notify_inventory_created()
        
        _logger.info('Đã tạo đợt kiểm kê định kỳ: %s', inventory.name)

    def _get_default_responsible(self):
        """Lấy người chịu trách nhiệm mặc định cho kiểm kê tự động"""
        # Ưu tiên tìm asset manager
        manager_group = self.env.ref('dnu_meeting_asset.group_asset_manager', raise_if_not_found=False)
        if manager_group and manager_group.users:
            user = manager_group.users[0]
            if user.employee_id:
                return user.employee_id
        
        # Fallback về admin
        return self.env.user.employee_id or self.env['hr.employee'].search([], limit=1)

    def _notify_inventory_created(self):
        """Gửi thông báo khi tạo kiểm kê tự động"""
        self.ensure_one()
        
        manager_group = self.env.ref('dnu_meeting_asset.group_asset_manager', raise_if_not_found=False)
        if manager_group:
            for user in manager_group.users:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    date_deadline=fields.Date.today() + timedelta(days=7),
                    summary=_('📋 Kiểm kê định kỳ: %s') % self.name,
                    note=_('Đợt kiểm kê định kỳ %s đã được tạo tự động.\n\nTổng số tài sản: %d\n\nVui lòng phân công và tiến hành kiểm kê.') % (
                        self.name, self.total_assets
                    ),
                )
        
        self.message_post(body=_('📋 Kiểm kê định kỳ đã được tạo tự động'))

    def _apply_inventory_results(self):
        """Override để tự động gắn cờ Missing"""
        # Gọi method gốc
        super(AssetInventoryAutomation, self)._apply_inventory_results()
        
        # Xử lý tài sản missing
        for line in self.line_ids.filtered(lambda l: l.status == 'missing'):
            asset = line.asset_id
            
            # Tăng counter missing
            new_count = asset.missing_inventory_count + 1
            
            # Nếu missing >= 2 kỳ → gắn cờ và tạo activity truy tìm
            if new_count >= 2 and not asset.is_missing:
                asset.write({
                    'is_missing': True,
                    'missing_since': fields.Date.today(),
                    'missing_inventory_count': new_count,
                })
                asset._create_missing_investigation_task()
            else:
                asset.write({'missing_inventory_count': new_count})


class AssetMissingInvestigation(models.Model):
    """Mở rộng dnu.asset với task truy tìm tài sản mất"""
    _inherit = 'dnu.asset'

    def _create_missing_investigation_task(self):
        """Tạo task truy tìm tài sản mất"""
        self.ensure_one()
        
        # Tạo activity cho asset manager
        manager_group = self.env.ref('dnu_meeting_asset.group_asset_manager', raise_if_not_found=False)
        if manager_group:
            for user in manager_group.users:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    date_deadline=fields.Date.today() + timedelta(days=3),
                    summary=_('🔴 TRUY TÌM: Tài sản mất - %s') % self.name,
                    note=_('Tài sản %s (%s) không tìm thấy qua %d đợt kiểm kê.\n\nNgười cuối cùng được gán: %s\nVị trí cuối: %s\n\nVui lòng điều tra và báo cáo.') % (
                        self.name, self.code, self.missing_inventory_count,
                        self.assigned_to.name if self.assigned_to else 'N/A',
                        self.location or 'N/A'
                    ),
                )
        
        self.message_post(body=_('🔴 Tài sản được đánh dấu MẤT sau %d đợt kiểm kê không tìm thấy. Đã tạo task truy tìm.') % self.missing_inventory_count)


class HrEmployeeOffboardingAutomation(models.Model):
    """Mở rộng hr.employee với tự động hóa thu hồi tài sản khi offboarding"""
    _inherit = 'hr.employee'

    # === Feature 5: Trạng thái thu hồi tài sản ===
    asset_return_status = fields.Selection([
        ('not_required', 'Không cần thu hồi'),
        ('pending', 'Chờ thu hồi'),
        ('in_progress', 'Đang thu hồi'),
        ('completed', 'Đã hoàn tất'),
    ], string='Trạng thái thu hồi tài sản', default='not_required')
    
    pending_asset_return_count = fields.Integer(
        compute='_compute_pending_asset_return',
        string='Số tài sản chờ thu hồi'
    )

    @api.depends('asset_ids', 'asset_lending_ids')
    def _compute_pending_asset_return(self):
        """Tính số tài sản cần thu hồi"""
        for employee in self:
            # Tài sản đang được gán
            assigned_count = len(employee.asset_ids.filtered(lambda a: a.state == 'assigned'))
            
            # Phiếu mượn chưa trả
            lending_count = len(employee.asset_lending_ids.filtered(
                lambda l: l.state in ['borrowed', 'overdue']
            ))
            
            employee.pending_asset_return_count = assigned_count + lending_count

    def write(self, vals):
        """Override để detect offboarding"""
        # Detect khi nhân viên nghỉ việc (active = False hoặc departure_date được set)
        if 'active' in vals and vals['active'] == False:
            for employee in self:
                if employee.pending_asset_return_count > 0:
                    employee._create_asset_return_request()
        
        return super(HrEmployeeOffboardingAutomation, self).write(vals)

    def _create_asset_return_request(self):
        """Tạo yêu cầu thu hồi tài sản khi offboarding"""
        self.ensure_one()
        
        if self.pending_asset_return_count == 0:
            return
        
        # Cập nhật trạng thái
        self.write({'asset_return_status': 'pending'})
        
        # Tạo activity cho admin tài sản
        manager_group = self.env.ref('dnu_meeting_asset.group_asset_manager', raise_if_not_found=False)
        
        # Chuẩn bị danh sách tài sản
        asset_list = []
        
        for asset in self.asset_ids.filtered(lambda a: a.state == 'assigned'):
            asset_list.append('- %s (%s)' % (asset.name, asset.code))
        
        for lending in self.asset_lending_ids.filtered(lambda l: l.state in ['borrowed', 'overdue']):
            asset_list.append('- %s (%s) - Phiếu mượn: %s' % (
                lending.asset_id.name, lending.asset_id.code, lending.name
            ))
        
        note = _('Nhân viên %s đang chuẩn bị nghỉ việc/chuyển công tác.\n\nTài sản cần thu hồi:\n%s\n\nVui lòng liên hệ thu hồi tài sản.') % (
            self.name,
            '\n'.join(asset_list)
        )
        
        if manager_group:
            for user in manager_group.users[:3]:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    date_deadline=fields.Date.today() + timedelta(days=3),
                    summary=_('🔄 Thu hồi tài sản: %s') % self.name,
                    note=note,
                )
        
        # Tạo các transfer request
        for asset in self.asset_ids.filtered(lambda a: a.state == 'assigned'):
            self.env['dnu.asset.transfer'].create({
                'asset_id': asset.id,
                'transfer_type': 'employee',
                'from_employee_id': self.id,
                'to_employee_id': False,  # Trả về kho
                'reason': 'reassignment',
                'reason_detail': _('Thu hồi do nhân viên %s nghỉ việc/chuyển công tác') % self.name,
                'state': 'draft',
            })
        
        self.message_post(
            body=_('🔄 Đã tạo yêu cầu thu hồi %d tài sản do nhân viên chuẩn bị nghỉ việc/chuyển công tác') % self.pending_asset_return_count
        )

    def action_view_pending_returns(self):
        """Action mở danh sách tài sản chờ thu hồi"""
        self.ensure_one()
        
        # Thu thập ID các tài sản và phiếu mượn cần thu hồi
        asset_ids = self.asset_ids.filtered(lambda a: a.state == 'assigned').ids
        lending_ids = self.asset_lending_ids.filtered(lambda l: l.state in ['borrowed', 'overdue']).mapped('asset_id').ids
        
        all_asset_ids = list(set(asset_ids + lending_ids))
        
        return {
            'name': _('Tài sản chờ thu hồi - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', all_asset_ids)],
            'context': {'default_assigned_to': self.id},
        }


class AssetDisposalAutomation(models.Model):
    """Mở rộng dnu.asset.disposal với tự động hóa vòng đời"""
    _inherit = 'dnu.asset.disposal'

    # === Feature 7: Tự động hóa khi thanh lý ===
    def action_complete(self):
        """Override để thêm các automation khi hoàn thành thanh lý"""
        for disposal in self:
            asset = disposal.asset_id
            
            # 1. Kiểm tra và kết thúc các phiếu mượn đang active
            active_lendings = self.env['dnu.asset.lending'].search([
                ('asset_id', '=', asset.id),
                ('state', 'in', ['borrowed', 'overdue', 'approved']),
            ])
            for lending in active_lendings:
                lending.write({
                    'state': 'cancelled',
                    'notes': (lending.notes or '') + _('\n\nTự động hủy do tài sản được thanh lý (%s)') % disposal.name,
                })
                lending.message_post(body=_('Phiếu mượn tự động hủy do tài sản được thanh lý'))
            
            # 2. Kết thúc các assignment đang active
            active_assignments = self.env['dnu.asset.assignment'].search([
                ('asset_id', '=', asset.id),
                ('state', '=', 'active'),
            ])
            active_assignments.write({
                'state': 'returned',
                'date_to': fields.Date.today(),
                'notes': _('Tự động kết thúc do tài sản được thanh lý'),
            })
            
            # 3. Hủy các maintenance pending
            pending_maintenance = self.env['dnu.asset.maintenance'].search([
                ('asset_id', '=', asset.id),
                ('state', 'in', ['draft', 'pending']),
            ])
            pending_maintenance.write({
                'state': 'cancelled',
                'notes': _('Tự động hủy do tài sản được thanh lý'),
            })
            
            # 4. Dừng các maintenance schedule
            schedules = self.env['dnu.maintenance.schedule'].search([
                ('asset_id', '=', asset.id),
                ('state', '=', 'active'),
            ])
            schedules.write({'state': 'stopped'})
        
        # Gọi method gốc
        return super(AssetDisposalAutomation, self).action_complete()


class AssetTransferAutomation(models.Model):
    """Mở rộng dnu.asset.transfer với tự động hóa"""
    _inherit = 'dnu.asset.transfer'

    # === Feature 7: Tự động hóa khi điều chuyển ===
    auto_generate_handover = fields.Boolean(
        string='Tự tạo biên bản',
        default=True
    )

    def action_complete(self):
        """Override để thêm automation khi hoàn thành điều chuyển"""
        for transfer in self:
            # Kết thúc các phiếu mượn cũ nếu chuyển nhân viên
            if transfer.transfer_type == 'employee' and transfer.from_employee_id:
                active_lendings = self.env['dnu.asset.lending'].search([
                    ('asset_id', '=', transfer.asset_id.id),
                    ('borrower_id', '=', transfer.from_employee_id.id),
                    ('state', 'in', ['borrowed', 'overdue']),
                ])
                for lending in active_lendings:
                    lending.write({
                        'state': 'returned',
                        'date_actual_return': fields.Datetime.now(),
                        'return_notes': _('Tự động trả do điều chuyển tài sản theo %s') % transfer.name,
                    })
        
        # Gọi method gốc
        result = super(AssetTransferAutomation, self).action_complete()
        
        # Tạo biên bản nếu cần
        for transfer in self.filtered(lambda t: t.auto_generate_handover):
            transfer._auto_generate_handover_document()
        
        return result

    def _auto_generate_handover_document(self):
        """Tự động tạo biên bản bàn giao"""
        self.ensure_one()
        
        # Log vào message
        handover_info = _('''
<h4>📋 BIÊN BẢN BÀN GIAO TÀI SẢN</h4>
<table style="width: 100%%; border-collapse: collapse;">
<tr><td><strong>Mã luân chuyển:</strong></td><td>%s</td></tr>
<tr><td><strong>Ngày bàn giao:</strong></td><td>%s</td></tr>
<tr><td><strong>Tài sản:</strong></td><td>%s (%s)</td></tr>
<tr><td><strong>Từ:</strong></td><td>%s</td></tr>
<tr><td><strong>Đến:</strong></td><td>%s</td></tr>
<tr><td><strong>Tình trạng:</strong></td><td>%s</td></tr>
<tr><td><strong>Lý do:</strong></td><td>%s</td></tr>
</table>
        ''') % (
            self.name,
            self.handover_date or fields.Date.today(),
            self.asset_id.name, self.asset_id.code,
            self.from_employee_id.ho_va_ten if self.from_employee_id else self.from_location or 'N/A',
            self.to_employee_id.ho_va_ten if self.to_employee_id else self.to_location or 'N/A',
            dict(self._fields['condition_after'].selection).get(self.condition_after) if self.condition_after else 'N/A',
            dict(self._fields['reason'].selection).get(self.reason),
        )
        
        self.message_post(body=handover_info, message_type='notification')
        self.asset_id.message_post(body=handover_info, message_type='notification')
