# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Asset(models.Model):
    _name = 'dnu.asset'
    _description = 'Tài sản công ty'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name, code'

    name = fields.Char(
        string='Tên tài sản',
        required=True,
        tracking=True,
        index=True
    )
    code = fields.Char(
        string='Mã tài sản',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    category_id = fields.Many2one(
        'dnu.asset.category',
        string='Danh mục',
        required=True,
        tracking=True
    )
    serial_number = fields.Char(
        string='Số serial',
        tracking=True
    )
    barcode = fields.Char(
        string='Mã vạch/QR Code',
        copy=False
    )
    
    # Purchase information
    purchase_date = fields.Date(
        string='Ngày mua',
        tracking=True
    )
    purchase_value = fields.Float(
        string='Giá trị mua (VNĐ)',
        tracking=True
    )
    salvage_value = fields.Float(
        string='Giá trị thanh lý (VNĐ)',
        default=0.0,
        tracking=True,
        help='Giá trị còn lại sau khi khấu hao hết'
    )
    supplier_id = fields.Many2one(
        'res.partner',
        string='Nhà cung cấp',
        domain=[('is_company', '=', True)]
    )
    warranty_expiry = fields.Date(string='Hết hạn bảo hành')
    
    # Status and assignment
    state = fields.Selection([
        ('available', 'Sẵn sàng'),
        ('assigned', 'Đã gán'),
        ('maintenance', 'Bảo trì'),
        ('disposed', 'Đã thanh lý'),
    ], string='Trạng thái', default='available', required=True, tracking=True)
    
    assigned_to = fields.Many2one(
        'hr.employee',
        string='Được gán cho',
        tracking=True,
        help='Nhân viên hiện đang sử dụng tài sản này'
    )
    assigned_nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string='Được gán cho (Nhân sự)',
        tracking=True,
        help='Nhân viên trong hệ thống Nhân sự đang sử dụng tài sản này'
    )
    assignment_date = fields.Date(
        string='Ngày gán',
        tracking=True
    )
    
    # Location
    location = fields.Char(
        string='Vị trí',
        tracking=True
    )
    room_id = fields.Many2one(
        'dnu.meeting.room',
        string='Phòng họp',
        help='Nếu tài sản được gắn cố định trong phòng họp'
    )
    
    # Relations
    assignment_ids = fields.One2many(
        'dnu.asset.assignment',
        'asset_id',
        string='Lịch sử gán'
    )
    maintenance_ids = fields.One2many(
        'dnu.asset.maintenance',
        'asset_id',
        string='Lịch sử bảo trì'
    )
    lending_ids = fields.One2many(
        'dnu.asset.lending',
        'asset_id',
        string='Lịch sử mượn'
    )
    handover_ids = fields.One2many(
        'dnu.asset.handover',
        'asset_id',
        string='Biên bản bàn giao'
    )
    depreciation_ids = fields.One2many(
        'dnu.asset.depreciation',
        'asset_id',
        string='Khấu hao'
    )
    transfer_ids = fields.One2many(
        'dnu.asset.transfer',
        'asset_id',
        string='Lịch sử luân chuyển'
    )
    inventory_line_ids = fields.One2many(
        'dnu.asset.inventory.line',
        'asset_id',
        string='Kiểm kê'
    )
    disposal_ids = fields.One2many(
        'dnu.asset.disposal',
        'asset_id',
        string='Thanh lý'
    )
    
    # Computed fields
    assignment_count = fields.Integer(
        compute='_compute_assignment_count',
        string='Số lần gán'
    )
    maintenance_count = fields.Integer(
        compute='_compute_maintenance_count',
        string='Số lần bảo trì'
    )
    is_borrowed = fields.Boolean(
        compute='_compute_is_borrowed',
        string='Đang được mượn',
        store=False,
        help='Tài sản hiện đang được mượn và chưa trả'
    )
    current_borrower = fields.Char(
        compute='_compute_is_borrowed',
        string='Người đang mượn',
        store=False
    )
    lending_count = fields.Integer(
        compute='_compute_lending_count',
        string='Số lần mượn'
    )
    handover_count = fields.Integer(
        compute='_compute_handover_count',
        string='Số biên bản'
    )
    ai_request_count = fields.Integer(
        compute='_compute_ai_request_count',
        string='Số lượt hỏi AI'
    )
    transfer_count = fields.Integer(
        compute='_compute_transfer_count',
        string='Số lần luân chuyển'
    )
    current_value = fields.Float(
        compute='_compute_current_value',
        string='Giá trị hiện tại',
        store=True
    )
    
    # Additional fields
    description = fields.Text(string='Mô tả')
    image = fields.Binary(string='Hình ảnh')
    notes = fields.Html(string='Ghi chú')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )
    
    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('dnu.asset') or _('New')
        return super(Asset, self).create(vals)
    
    @api.depends('assignment_ids')
    def _compute_assignment_count(self):
        for asset in self:
            asset.assignment_count = len(asset.assignment_ids)
    
    @api.depends('maintenance_ids')
    def _compute_maintenance_count(self):
        for asset in self:
            asset.maintenance_count = len(asset.maintenance_ids)
    
    @api.depends('lending_ids', 'lending_ids.state', 'lending_ids.date_expected_return', 'lending_ids.borrower_name')
    def _compute_is_borrowed(self):
        """Kiểm tra xem tài sản có đang được mượn không"""
        for asset in self:
            # Tìm phiếu mượn đang active (đã duyệt hoặc đang mượn)
            active_lending = self.env['dnu.asset.lending'].search([
                ('asset_id', '=', asset.id),
                ('state', 'in', ['approved', 'borrowed', 'overdue']),
            ], limit=1, order='date_borrow desc')
            
            asset.is_borrowed = bool(active_lending)
            asset.current_borrower = active_lending.borrower_name if active_lending else False
    
    @api.depends('lending_ids')
    def _compute_lending_count(self):
        for asset in self:
            asset.lending_count = len(asset.lending_ids)

    @api.depends('handover_ids')
    def _compute_handover_count(self):
        for asset in self:
            asset.handover_count = len(asset.handover_ids)

    def _compute_ai_request_count(self):
        Request = self.env['ai.request']
        for asset in self:
            asset.ai_request_count = Request.search_count([
                ('context_model', '=', asset._name),
                ('context_res_id', '=', asset.id),
            ])
    
    @api.depends('transfer_ids')
    def _compute_transfer_count(self):
        for asset in self:
            asset.transfer_count = len(asset.transfer_ids)
    
    @api.depends('purchase_value', 'purchase_date')
    def _compute_current_value(self):
        """Tính giá trị hiện tại (đơn giản: giảm 10% mỗi năm)"""
        for asset in self:
            if asset.purchase_value and asset.purchase_date:
                from datetime import datetime
                years = (fields.Date.today() - asset.purchase_date).days / 365.0
                depreciation = asset.purchase_value * 0.1 * years
                asset.current_value = max(0, asset.purchase_value - depreciation)
            else:
                asset.current_value = asset.purchase_value or 0.0
    
    def action_assign_to_employee(self):
        """Mở wizard để gán tài sản cho nhân viên"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Gán tài sản',
            'res_model': 'dnu.asset.assignment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_id': self.id,
                'default_date_from': fields.Date.today(),
            }
        }
    
    def action_create_maintenance(self):
        """Tạo yêu cầu bảo trì"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tạo yêu cầu bảo trì',
            'res_model': 'dnu.asset.maintenance',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_id': self.id,
                'default_reporter_id': self.env.user.employee_id.id,
            }
        }
    
    def action_view_assignments(self):
        """Xem lịch sử gán"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lịch sử gán tài sản',
            'res_model': 'dnu.asset.assignment',
            'view_mode': 'tree,form',
            'domain': [('asset_id', '=', self.id)],
        }
    
    def action_view_maintenances(self):
        """Xem lịch sử bảo trì"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lịch sử bảo trì',
            'res_model': 'dnu.asset.maintenance',
            'view_mode': 'tree,form',
            'domain': [('asset_id', '=', self.id)],
        }

    def action_view_lendings(self):
        """Xem lịch sử mượn"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lịch sử mượn tài sản',
            'res_model': 'dnu.asset.lending',
            'view_mode': 'kanban,tree,form',
            'domain': [('asset_id', '=', self.id)],
        }

    def action_view_handovers(self):
        """Xem biên bản bàn giao"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Biên bản bàn giao',
            'res_model': 'dnu.asset.handover',
            'view_mode': 'tree,form',
            'domain': [('asset_id', '=', self.id)],
        }

    def action_view_ai_history(self):
        """Xem lịch sử hỏi AI của tài sản"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lịch sử hỏi AI',
            'res_model': 'ai.request',
            'view_mode': 'tree,form',
            'domain': [
                ('context_model', '=', self._name),
                ('context_res_id', '=', self.id),
            ],
            'context': {
                'default_context_model': self._name,
                'default_context_res_id': self.id,
                'default_channel': 'asset',
            },
        }
    
    def action_ai_suggest_maintenance(self):
        """Mở wizard AI gợi ý bảo trì"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': '🤖 AI Gợi ý bảo trì',
            'res_model': 'ai.asset.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_action_type': 'maintenance',
                'default_asset_id': self.id,
                'ai_context_model': self._name,
                'ai_context_res_id': self.id,
            }
        }
    
    @api.constrains('state', 'assigned_to', 'assigned_nhan_vien_id')
    def _check_state_assigned(self):
        """Kiểm tra logic trạng thái và gán"""
        for asset in self:
            has_assignee = asset.assigned_to or asset.assigned_nhan_vien_id
            if asset.state == 'assigned' and not has_assignee:
                raise ValidationError(_('Tài sản ở trạng thái "Đã gán" phải có nhân viên được gán.'))
            # Chỉ kiểm tra nếu đang ở trạng thái available (sẵn sàng) mà có người gán thì báo lỗi
            # Các trạng thái khác như maintenance, disposed có thể vẫn giữ thông tin người gán
            if asset.state == 'available' and has_assignee:
                raise ValidationError(_('Tài sản ở trạng thái "Sẵn sàng" không thể có người được gán.'))
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã tài sản phải là duy nhất!'),
        ('serial_unique', 'unique(serial_number)', 'Số serial phải là duy nhất!'),
    ]
