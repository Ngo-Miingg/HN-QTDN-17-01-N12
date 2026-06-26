# -*- coding: utf-8 -*-

import json
import logging
import time
import unicodedata
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    requests = None
    _logger.warning("requests library not installed. OpenAI integration won't work.")


class OpenAIConfiguration(models.Model):
    """Cấu hình tích hợp OpenAI API"""
    _name = 'openai.configuration'
    _description = 'Cấu hình OpenAI'
    _rec_name = 'name'
    
    name = fields.Char(
        string='Tên cấu hình',
        required=True,
        default='Cấu hình OpenAI mặc định'
    )
    api_key = fields.Char(
        string='API Key',
        required=True,
        help='OpenAI API Key (bắt đầu bằng sk-...)',
        groups='base.group_system'
    )
    model_name = fields.Selection([
        ('gpt-3.5-turbo', 'GPT-3.5 Turbo (Nhanh, tiết kiệm)'),
        ('gpt-4', 'GPT-4 (Chính xác hơn)'),
        ('gpt-4-turbo', 'GPT-4 Turbo (Nhanh + Chính xác)'),
        ('gpt-4o', 'GPT-4o (Mới nhất)'),
        ('gpt-4o-mini', 'GPT-4o Mini (Tiết kiệm)'),
    ], string='Model', default='gpt-4o-mini', required=True)
    
    max_tokens = fields.Integer(
        string='Max Tokens',
        default=2000,
        help='Số token tối đa cho mỗi response'
    )
    temperature = fields.Float(
        string='Temperature',
        default=0.7,
        help='0 = Chính xác, 1 = Sáng tạo'
    )
    
    active = fields.Boolean(default=True)
    is_default = fields.Boolean(
        string='Mặc định',
        default=False,
        help='Sử dụng cấu hình này làm mặc định'
    )
    
    # Usage tracking
    total_requests = fields.Integer(
        string='Tổng requests',
        default=0,
        readonly=True
    )
    total_tokens_used = fields.Integer(
        string='Tổng tokens sử dụng',
        default=0,
        readonly=True
    )
    last_used = fields.Datetime(
        string='Lần sử dụng cuối',
        readonly=True
    )
    
    # Status
    status = fields.Selection([
        ('active', 'Hoạt động'),
        ('error', 'Lỗi'),
        ('quota_exceeded', 'Vượt quota'),
    ], string='Trạng thái', default='active', readonly=True)
    last_error = fields.Text(string='Lỗi gần nhất', readonly=True)
    
    @api.model
    def get_default_config(self):
        """Lấy cấu hình mặc định"""
        config = self.search([('is_default', '=', True), ('active', '=', True)], limit=1)
        if not config:
            config = self.search([('active', '=', True)], limit=1)
        if not config:
            config = self.search([('is_default', '=', True)], limit=1)
        if not config:
            config = self.search([], limit=1)
        if config and (not config.api_key or config.api_key == 'YOUR_OPENAI_API_KEY_HERE'):
            raise UserError(_(
                'Đã có cấu hình OpenAI mặc định, nhưng chưa nhập API Key hợp lệ. '
                'Vào Cấu hình > OpenAI để dán API key thật rồi bấm kiểm tra kết nối.'
            ))
        if not config:
            raise UserError(_('Chưa cấu hình OpenAI. Vui lòng vào Cấu hình > OpenAI để thiết lập.'))
        return config
    
    def test_connection(self):
        """Kiểm tra kết nối API"""
        self.ensure_one()
        try:
            response = self._call_openai(
                messages=[{"role": "user", "content": "Hello, respond with just 'OK'"}],
                max_tokens=10
            )
            if response:
                self.write({
                    'status': 'active',
                    'last_error': False,
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Thành công'),
                        'message': _('Kết nối OpenAI thành công!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            self.write({
                'status': 'error',
                'last_error': str(e),
            })
            raise UserError(_('Lỗi kết nối OpenAI: %s') % str(e))
    
    def _call_openai(self, messages, max_tokens=None, temperature=None, retry_count=3):
        """
        Gọi OpenAI API với retry logic
        
        Args:
            messages: List of message dicts [{"role": "user", "content": "..."}]
            max_tokens: Override max tokens
            temperature: Override temperature
            retry_count: Số lần retry
        Returns:
            String response content
        """
        response = self._call_openai_with_tools(messages, tools=None, max_tokens=max_tokens, temperature=temperature, retry_count=retry_count)
        return response.get('content', '')
    
    def _call_openai_with_tools(self, messages, tools=None, max_tokens=None, temperature=None, retry_count=3):
        """
        Gọi OpenAI API với function calling support
        
        Returns:
            dict: Response with content and/or tool_calls
        """
        self.ensure_one()
        
        if not requests:
            raise UserError(_('Thư viện requests chưa được cài đặt.'))
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        last_exception = None
        for attempt in range(retry_count):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                
                if response.status_code == 200:
                    result = response.json()
                    message = result.get('choices', [{}])[0].get('message', {})
                    
                    # Update usage stats
                    usage = result.get('usage', {})
                    self.sudo().write({
                        'total_requests': self.total_requests + 1,
                        'total_tokens_used': self.total_tokens_used + usage.get('total_tokens', 0),
                        'last_used': fields.Datetime.now(),
                        'status': 'active',
                        'last_error': False,
                    })
                    
                    # Properly serialize tool_calls to avoid JavaScript boolean issues
                    tool_calls_raw = message.get('tool_calls')
                    tool_calls_serialized = None
                    if tool_calls_raw:
                        tool_calls_serialized = []
                        for tc in tool_calls_raw:
                            tool_calls_serialized.append({
                                "id": tc.get('id') if isinstance(tc, dict) else tc['id'],
                                "type": tc.get('type', 'function') if isinstance(tc, dict) else 'function',
                                "function": {
                                    "name": tc.get('function', {}).get('name') if isinstance(tc, dict) else tc['function']['name'],
                                    "arguments": tc.get('function', {}).get('arguments', '{}') if isinstance(tc, dict) else tc['function']['arguments']
                                }
                            })
                    
                    return {
                        'content': message.get('content'),
                        'tool_calls': tool_calls_serialized,
                    }
                
                elif response.status_code == 429:
                    # Rate limit - wait and retry
                    wait_time = (attempt + 1) * 5
                    _logger.warning(f"OpenAI rate limit hit, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                    
                elif response.status_code == 401:
                    self.sudo().write({
                        'status': 'error',
                        'last_error': 'API Key không hợp lệ'
                    })
                    raise UserError(_('API Key OpenAI không hợp lệ.'))
                    
                elif response.status_code == 402:
                    self.sudo().write({
                        'status': 'quota_exceeded',
                        'last_error': 'Vượt quota OpenAI'
                    })
                    raise UserError(_('Vượt quota OpenAI. Vui lòng kiểm tra billing.'))
                    
                else:
                    error_msg = response.json().get('error', {}).get('message', response.text)
                    last_exception = UserError(_('Lỗi OpenAI: %s') % error_msg)
                    
            except requests.exceptions.Timeout:
                last_exception = UserError(_('Timeout kết nối OpenAI.'))
                time.sleep(2)
            except requests.exceptions.RequestException as e:
                last_exception = UserError(_('Lỗi kết nối: %s') % str(e))
                time.sleep(2)
        
        if last_exception:
            self.sudo().write({
                'status': 'error',
                'last_error': str(last_exception),
            })
            raise last_exception
        
        raise UserError(_('Không thể kết nối OpenAI sau nhiều lần thử.'))


class OpenAIService(models.AbstractModel):
    """Service layer cho các tính năng AI"""
    _name = 'openai.service'
    _description = 'OpenAI Service'

    def _business_response_rules(self, domain_label):
        """Chuẩn trả lời để AI bám đúng nghiệp vụ và dữ liệu thật."""
        return f"""Báº¡n lÃ  trá»£ lÃ½ AI há»— trá»£ nghiá»‡p vá»¥ {domain_label}.

NguyÃªn táº¯c báº¯t buá»™c:
1. Chá»‰ káº¿t luáº­n tá»« dá»¯ liá»‡u Ä‘Æ°á»£c cung cáº¥p hoáº·c function tráº£ vá».
2. Náº¿u thiáº¿u dá»¯ liá»‡u, pháº£i nÃ³i rÃµ "chÆ°a Ä‘á»§ dá»¯ liá»‡u" vÃ  chá»‰ ra pháº§n cÃ²n thiáº¿u.
3. KhÃ´ng tá»± suy diÃªn ngÃ y thÃ¡ng, chi phÃ­, tráº¡ng thÃ¡i, ngÆ°á»i phá»¥ tráº¡ch hay káº¿t quáº£ xá»­ lÃ½.
4. Khi nÃªu sá»‘ liá»‡u hoáº·c Ä‘á»‘i tÆ°á»£ng cá»¥ thá»ƒ, pháº£i viá»‡n dáº«n theo mÃ£/tÃªn báº£n ghi náº¿u cÃ³.
5. Tráº£ lá»i báº±ng tiáº¿ng Viá»‡t, ngáº¯n gá»n, rÃµ, theo vÄƒn phong doanh nghiá»‡p.
6. Náº¿u phÃ¹ há»£p, trÃ¬nh bÃ y theo 3 pháº§n: Káº¿t luáº­n / CÄƒn cá»© dá»¯ liá»‡u / Äá» xuáº¥t.
7. Æ¯u tiÃªn dá»¯ liá»‡u tháº­t hÆ¡n lÃ  tráº£ lá»i chung chung."""
    
    # ==================== ASSET AI FEATURES ====================
    
    def asset_qa(self, question, asset_ids=None):
        """
        Hỏi đáp về tài sản (RAG-based)
        
        Args:
            question: Câu hỏi của người dùng
            asset_ids: List asset IDs để giới hạn context (optional)
        Returns:
            Dict với answer và sources
        """
        config = self.env['openai.configuration'].get_default_config()
        
        # Build context từ database
        context_data = self._build_asset_context(asset_ids)
        
        system_prompt = """Bạn là trợ lý AI chuyên về quản lý tài sản công ty. 
Nhiệm vụ của bạn là trả lời các câu hỏi về tài sản dựa trên dữ liệu được cung cấp.

Quy tắc:
1. Chỉ trả lời dựa trên dữ liệu được cung cấp
2. Nếu không có thông tin, hãy nói rõ
3. Trích dẫn nguồn (mã tài sản) khi đề cập
4. Trả lời bằng tiếng Việt
5. Ngắn gọn, đi thẳng vào vấn đề"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""
DỮ LIỆU TÀI SẢN:
{context_data}

CÂU HỎI: {question}

Hãy trả lời câu hỏi dựa trên dữ liệu trên."""}
        ]
        
        answer = config._call_openai(messages)
        
        return {
            'answer': answer,
            'model': config.model_name,
            'timestamp': fields.Datetime.now(),
        }
    
    def _build_asset_context(self, asset_ids=None, limit=50):
        """Build context string từ assets"""
        domain = [('active', '=', True)]
        if asset_ids:
            domain.append(('id', 'in', asset_ids))
        
        assets = self.env['dnu.asset'].search(domain, limit=limit)
        
        context_parts = []
        for asset in assets:
            info = f"""
--- Tài sản: {asset.code} ---
- Tên: {asset.name}
- Danh mục: {asset.category_id.name if asset.category_id else 'N/A'}
- Trạng thái: {dict(asset._fields['state'].selection).get(asset.state, asset.state)}
- Giá trị mua: {asset.purchase_value:,.0f} VNĐ
- Giá trị hiện tại: {asset.current_value:,.0f} VNĐ
- Ngày mua: {asset.purchase_date or 'N/A'}
- Vị trí: {asset.location or 'N/A'}
- Được gán cho: {asset.assigned_to.name if asset.assigned_to else asset.assigned_nhan_vien_id.ho_va_ten if asset.assigned_nhan_vien_id else 'Chưa gán'}
- Số lần bảo trì: {asset.maintenance_count}
- Mô tả: {asset.description or 'N/A'}"""
            context_parts.append(info)
        
        return "\n".join(context_parts) if context_parts else "Không có dữ liệu tài sản."
    
    def suggest_maintenance(self, asset_id):
        """
        Gợi ý bảo trì dựa trên lịch sử tài sản
        
        Args:
            asset_id: ID tài sản
        Returns:
            Dict với suggestions
        """
        config = self.env['openai.configuration'].get_default_config()
        asset = self.env['dnu.asset'].browse(asset_id)
        
        if not asset.exists():
            raise UserError(_('Tài sản không tồn tại.'))
        
        # Build maintenance history
        maintenance_history = []
        for m in asset.maintenance_ids.sorted('date_reported', reverse=True)[:10]:
            maintenance_history.append({
                'date_reported': str(m.date_reported) if m.date_reported else 'N/A',
                'date_scheduled': str(m.date_scheduled) if m.date_scheduled else '',
                'date_completed': str(m.date_completed) if m.date_completed else '',
                'type': dict(m._fields['maintenance_type'].selection).get(m.maintenance_type, m.maintenance_type or 'N/A'),
                'description': m.description or '',
                'priority': dict(m._fields['priority'].selection).get(m.priority, m.priority or ''),
                'state': dict(m._fields['state'].selection).get(m.state, m.state or ''),
                'technician': m.tech_name or m.assigned_tech_id.name or '',
                'cost_estimate': m.cost_estimate or 0,
                'cost_actual': m.cost_actual or 0,
            })
        
        system_prompt = self._business_response_rules('quáº£n lÃ½ tÃ i sáº£n') + "\n\n" + system_prompt + """

YÃªu cáº§u riÃªng cho há»i Ä‘Ã¡p tÃ i sáº£n:
- Ghi rÃµ mÃ£ tÃ i sáº£n khi Ä‘á» cáº­p tá»›i tá»«ng tÃ i sáº£n.
- Náº¿u cÃ³ dá»¯ liá»‡u Ä‘á»§, tráº£ lá»i theo 3 pháº§n: Káº¿t luáº­n / CÄƒn cá»© dá»¯ liá»‡u / Ghi chÃº.
- Náº¿u cÃ¢u há»i vÆ°á»£t quÃ¡ dá»¯ liá»‡u hiá»‡n cÃ³, pháº£i tá»« chá»‘i suy luáº­n."""

        messages = [
            {"role": "system", "content": """Bạn là chuyên gia bảo trì tài sản. 
Nhiệm vụ: Phân tích lịch sử bảo trì và đề xuất kế hoạch bảo trì hợp lý.
Trả lời bằng tiếng Việt, ngắn gọn và thực tế."""},
            {"role": "user", "content": f"""
THÔNG TIN TÀI SẢN:
- Mã: {asset.code}
- Tên: {asset.name}
- Danh mục: {asset.category_id.name if asset.category_id else 'N/A'}
- Ngày mua: {asset.purchase_date or 'Không rõ'}
- Giá trị: {asset.purchase_value:,.0f} VNĐ
- Trạng thái: {asset.state}

LỊCH SỬ BẢO TRÌ (10 lần gần nhất):
{json.dumps(maintenance_history, ensure_ascii=False, indent=2)}

Hãy đề xuất:
1. Lịch bảo trì định kỳ phù hợp
2. Những vấn đề cần lưu ý
3. Chi phí dự kiến cho bảo trì năm tới"""}
        ]
        
        answer = config._call_openai(messages)
        
        return {
            'asset_code': asset.code,
            'asset_name': asset.name,
            'suggestions': answer,
            'timestamp': fields.Datetime.now(),
        }
    
    def analyze_asset_risk(self, asset_ids=None):
        """
        Phân tích rủi ro tài sản
        
        Args:
            asset_ids: List asset IDs (optional, nếu None sẽ phân tích tất cả)
        Returns:
            Dict với risk analysis
        """
        config = self.env['openai.configuration'].get_default_config()
        
        # Get assets with potential issues
        domain = [('active', '=', True)]
        if asset_ids:
            domain.append(('id', 'in', asset_ids))
        
        assets = self.env['dnu.asset'].search(domain, limit=100)
        
        # Build summary
        summary_data = {
            'total_assets': len(assets),
            'by_state': {},
            'old_assets': [],  # > 5 years
            'high_value': [],  # > 50M VND
            'frequent_maintenance': [],  # > 5 repairs
        }
        
        for asset in assets:
            # Count by state
            state = asset.state
            summary_data['by_state'][state] = summary_data['by_state'].get(state, 0) + 1
            
            # Old assets
            if asset.purchase_date:
                age_days = (fields.Date.today() - asset.purchase_date).days
                if age_days > 5 * 365:
                    summary_data['old_assets'].append({
                        'code': asset.code,
                        'name': asset.name,
                        'age_years': round(age_days / 365, 1),
                        'value': asset.current_value,
                    })
            
            # High value
            if asset.purchase_value and asset.purchase_value > 50000000:
                summary_data['high_value'].append({
                    'code': asset.code,
                    'name': asset.name,
                    'value': asset.purchase_value,
                })
            
            # Frequent maintenance
            if asset.maintenance_count > 5:
                summary_data['frequent_maintenance'].append({
                    'code': asset.code,
                    'name': asset.name,
                    'maintenance_count': asset.maintenance_count,
                })
        
        messages = [
            {"role": "system", "content": """Bạn là chuyên gia phân tích rủi ro tài sản doanh nghiệp.
Nhiệm vụ: Phân tích dữ liệu tài sản và chỉ ra các rủi ro tiềm ẩn.
Trả lời bằng tiếng Việt, có cấu trúc rõ ràng."""},
            {"role": "user", "content": f"""
DỮ LIỆU TÀI SẢN:
{json.dumps(summary_data, ensure_ascii=False, indent=2)}

Hãy phân tích:
1. Các rủi ro chính cần quan tâm
2. Tài sản cần ưu tiên xử lý
3. Đề xuất hành động cụ thể
4. Dự đoán chi phí rủi ro"""}
        ]
        
        answer = config._call_openai(messages)
        
        return {
            'summary': summary_data,
            'analysis': answer,
            'timestamp': fields.Datetime.now(),
        }
    
    # ==================== MEETING AI FEATURES ====================
    
    def generate_meeting_summary(self, booking_id, notes=None):
        """
        Tạo tóm tắt cuộc họp / biên bản họp
        
        Args:
            booking_id: ID booking
            notes: Ghi chú cuộc họp (optional)
        Returns:
            Dict với summary
        """
        config = self.env['openai.configuration'].get_default_config()
        booking = self.env['dnu.meeting.booking'].browse(booking_id)
        
        if not booking.exists():
            raise UserError(_('Không tìm thấy booking.'))
        
        # Build attendee list
        attendees = []
        for att in booking.attendee_ids:
            attendees.append({
                'name': att.name,
                'department': att.department_id.name if att.department_id else 'N/A',
                'job': att.job_title if hasattr(att, 'job_title') else 'N/A',
            })
        
        meeting_info = {
            'subject': booking.subject,
            'room': booking.room_id.name if booking.room_id else 'Online',
            'start': str(booking.start_datetime),
            'end': str(booking.end_datetime),
            'duration': booking.duration,
            'organizer': booking.organizer_name or 'N/A',
            'attendees': attendees,
            'description': booking.description or '',
            'notes': notes or booking.notes or '',
        }
        
        messages = [
            {"role": "system", "content": """Bạn là thư ký chuyên nghiệp, chuyên viết biên bản họp.
Nhiệm vụ: Tạo biên bản họp chuyên nghiệp từ thông tin cuộc họp.

Format biên bản:
1. Tiêu đề: BIÊN BẢN CUỘC HỌP
2. Thông tin cuộc họp (thời gian, địa điểm, thành phần)
3. Nội dung chính (nếu có ghi chú)
4. Kết luận/Hành động tiếp theo (đề xuất nếu có thông tin)
5. Ký tên (placeholder)

Sử dụng tiếng Việt, format Markdown."""},
            {"role": "user", "content": f"""
THÔNG TIN CUỘC HỌP:
{json.dumps(meeting_info, ensure_ascii=False, indent=2)}

Hãy tạo biên bản cuộc họp chuyên nghiệp."""}
        ]
        
        summary = config._call_openai(messages, max_tokens=3000)
        
        return {
            'booking_id': booking_id,
            'subject': booking.subject,
            'summary': summary,
            'timestamp': fields.Datetime.now(),
        }
    
    def suggest_meeting_time(self, attendee_ids, duration_hours=1, preferred_date=None):
        """
        Gợi ý thời gian họp phù hợp dựa trên lịch
        
        Args:
            attendee_ids: List employee IDs
            duration_hours: Thời lượng cuộc họp (giờ)
            preferred_date: Ngày ưu tiên (optional)
        Returns:
            Dict với suggestions
        """
        config = self.env['openai.configuration'].get_default_config()
        
        # Get existing bookings for attendees
        if preferred_date:
            date_from = preferred_date
            date_to = preferred_date + timedelta(days=7)
        else:
            date_from = fields.Date.today()
            date_to = date_from + timedelta(days=7)
        
        # Get all bookings in the period
        bookings = self.env['dnu.meeting.booking'].search([
            ('state', 'not in', ['cancelled', 'draft']),
            ('start_datetime', '>=', date_from),
            ('start_datetime', '<=', date_to),
            '|',
            ('organizer_id', 'in', attendee_ids),
            ('attendee_ids', 'in', attendee_ids),
        ])
        
        # Build calendar data
        busy_slots = []
        for b in bookings:
            busy_slots.append({
                'subject': b.subject,
                'start': str(b.start_datetime),
                'end': str(b.end_datetime),
                'attendees': [a.name for a in b.attendee_ids],
            })
        
        # Get attendee names
        employees = self.env['hr.employee'].browse(attendee_ids)
        attendee_names = [e.name for e in employees]
        
        messages = [
            {"role": "system", "content": """Bạn là trợ lý lên lịch họp thông minh.
Nhiệm vụ: Đề xuất thời gian họp phù hợp dựa trên lịch bận.

Quy tắc:
- Giờ làm việc: 8:00 - 17:00 (không họp giờ nghỉ trưa 12:00-13:30)
- Tránh các slot đã có họp
- Ưu tiên buổi sáng cho họp quan trọng
- Đề xuất 3-5 slot phù hợp nhất
- Format: Ngày - Giờ bắt đầu - Giờ kết thúc"""},
            {"role": "user", "content": f"""
NGƯỜI THAM DỰ: {', '.join(attendee_names)}
THỜI LƯỢNG: {duration_hours} giờ
KHOẢNG THỜI GIAN: {date_from} đến {date_to}

CÁC CUỘC HỌP ĐÃ CÓ:
{json.dumps(busy_slots, ensure_ascii=False, indent=2)}

Hãy đề xuất các slot thời gian phù hợp."""}
        ]
        
        suggestions = config._call_openai(messages)
        
        return {
            'attendees': attendee_names,
            'duration': duration_hours,
            'date_range': f"{date_from} - {date_to}",
            'suggestions': suggestions,
            'timestamp': fields.Datetime.now(),
        }
    
    def generate_meeting_agenda(self, subject, description=None, duration_hours=1):
        """
        Tạo agenda cuộc họp tự động
        
        Args:
            subject: Chủ đề cuộc họp
            description: Mô tả thêm (optional)
            duration_hours: Thời lượng
        Returns:
            Dict với agenda
        """
        config = self.env['openai.configuration'].get_default_config()
        
        messages = [
            {"role": "system", "content": """Bạn là chuyên gia tổ chức cuộc họp.
Nhiệm vụ: Tạo agenda cuộc họp chuyên nghiệp và hiệu quả.

Format agenda:
1. Mở đầu (5-10 phút)
2. Các nội dung chính (phân bổ thời gian hợp lý)
3. Thảo luận/Q&A
4. Kết luận và action items
5. Tổng kết

Sử dụng tiếng Việt, format rõ ràng với thời gian cho mỗi mục."""},
            {"role": "user", "content": f"""
CHỦ ĐỀ: {subject}
MÔ TẢ: {description or 'Không có mô tả thêm'}
THỜI LƯỢNG: {duration_hours} giờ

Hãy tạo agenda chi tiết cho cuộc họp này."""}
        ]
        
        agenda = config._call_openai(messages)
        
        return {
            'subject': subject,
            'duration': duration_hours,
            'agenda': agenda,
            'timestamp': fields.Datetime.now(),
        }
    
    # ==================== GENERAL AI FEATURES ====================
    
    def _get_available_tools(self):
        """Define available tools for AI function calling"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_meeting_rooms",
                    "description": "Lấy danh sách phòng họp với các bộ lọc. Sử dụng khi cần biết có bao nhiêu phòng, phòng nào có sẵn, thông tin chi tiết về phòng.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "Vị trí phòng (tòa nhà, tầng...)"
                            },
                            "min_capacity": {
                                "type": "integer",
                                "description": "Sức chứa tối thiểu"
                            },
                            "available_only": {
                                "type": "boolean",
                                "description": "Chỉ lấy phòng đang sẵn sàng (không bảo trì)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Giới hạn số lượng kết quả",
                                "default": 20
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_bookings",
                    "description": "Lấy danh sách lịch đặt phòng với các bộ lọc. Sử dụng khi cần biết lịch đặt phòng, thống kê booking, tìm cuộc họp theo tiêu chí.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date_from": {
                                "type": "string",
                                "description": "Ngày bắt đầu (YYYY-MM-DD)"
                            },
                            "date_to": {
                                "type": "string",
                                "description": "Ngày kết thúc (YYYY-MM-DD)"
                            },
                            "room_id": {
                                "type": "integer",
                                "description": "ID phòng họp cụ thể"
                            },
                            "state": {
                                "type": "string",
                                "description": "Trạng thái: draft, confirmed, in_progress, done, cancelled"
                            },
                            "organizer_name": {
                                "type": "string",
                                "description": "Tên người tổ chức"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Giới hạn số lượng kết quả",
                                "default": 50
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_booking_statistics",
                    "description": "Lấy thống kê về đặt phòng (tổng số, theo phòng, theo thời gian...). Sử dụng khi cần phân tích, báo cáo.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date_from": {
                                "type": "string",
                                "description": "Ngày bắt đầu (YYYY-MM-DD)"
                            },
                            "date_to": {
                                "type": "string",
                                "description": "Ngày kết thúc (YYYY-MM-DD)"
                            },
                            "group_by": {
                                "type": "string",
                                "description": "Nhóm theo: room, organizer, state, date",
                                "enum": ["room", "organizer", "state", "date"]
                            }
                        }
                    }
                }
            },
            # ==================== ASSET TOOLS ====================
            {
                "type": "function",
                "function": {
                    "name": "get_assets",
                    "description": "Lấy danh sách tài sản với bộ lọc. Dùng khi cần biết có bao nhiêu tài sản, tài sản nào, giá trị, trạng thái...",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category_name": {
                                "type": "string",
                                "description": "Tên danh mục (Máy tính, Điện thoại...)"
                            },
                            "state": {
                                "type": "string",
                                "description": "Trạng thái: available, assigned, maintenance, disposed, lost",
                                "enum": ["available", "assigned", "maintenance", "disposed", "lost"]
                            },
                            "min_value": {
                                "type": "number",
                                "description": "Giá trị tối thiểu (VNĐ)"
                            },
                            "location": {
                                "type": "string",
                                "description": "Vị trí tài sản"
                            },
                            "assigned_to": {
                                "type": "string",
                                "description": "Tên người được gán"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Giới hạn kết quả",
                                "default": 50
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_asset_assignments",
                    "description": "Lấy lịch sử gán tài sản. Dùng khi cần biết tài sản đang/đã gán cho ai, từ khi nào.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "asset_id": {
                                "type": "integer",
                                "description": "ID tài sản cụ thể"
                            },
                            "employee_name": {
                                "type": "string",
                                "description": "Tên nhân viên"
                            },
                            "state": {
                                "type": "string",
                                "description": "Trạng thái: active, returned",
                                "enum": ["active", "returned"]
                            },
                            "date_from": {
                                "type": "string",
                                "description": "Từ ngày (YYYY-MM-DD)"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 50
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_asset_lendings",
                    "description": "Lấy danh sách mượn tài sản. Dùng khi cần biết ai đang/đã mượn tài sản, quá hạn chưa.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "asset_id": {
                                "type": "integer",
                                "description": "ID tài sản"
                            },
                            "borrower_name": {
                                "type": "string",
                                "description": "Tên người mượn"
                            },
                            "state": {
                                "type": "string",
                                "description": "Trạng thái: draft, approved, borrowed, returned, cancelled, overdue"
                            },
                            "overdue_only": {
                                "type": "boolean",
                                "description": "Chỉ lấy phiếu quá hạn"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 50
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_asset_maintenances",
                    "description": "Lấy lịch sử bảo trì tài sản. Dùng khi cần biết tài sản đã bảo trì bao nhiêu lần, chi phí, loại bảo trì.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "asset_id": {
                                "type": "integer",
                                "description": "ID tài sản"
                            },
                            "maintenance_type": {
                                "type": "string",
                                "description": "Loại: preventive, corrective, breakdown"
                            },
                            "state": {
                                "type": "string",
                                "description": "Trạng thái: new, in_progress, done, cancelled"
                            },
                            "date_from": {
                                "type": "string",
                                "description": "Từ ngày (YYYY-MM-DD)"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 50
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_asset_disposals",
                    "description": "Lấy thông tin thanh lý tài sản. Dùng khi cần biết tài sản nào đã/đang thanh lý, lý do, giá trị.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "disposal_type": {
                                "type": "string",
                                "description": "Hình thức: sale, donation, scrap, return_supplier, exchange"
                            },
                            "state": {
                                "type": "string",
                                "description": "Trạng thái: draft, approved, in_progress, completed, cancelled"
                            },
                            "date_from": {
                                "type": "string",
                                "description": "Từ ngày (YYYY-MM-DD)"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 50
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_asset_statistics",
                    "description": "Thống kê tổng quan về tài sản. Dùng khi cần báo cáo, phân tích (tổng giá trị, phân bố theo danh mục/trạng thái...).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "group_by": {
                                "type": "string",
                                "description": "Nhóm theo: category, state, location, assigned_to",
                                "enum": ["category", "state", "location", "assigned_to", "department"]
                            },
                            "include_value": {
                                "type": "boolean",
                                "description": "Tính tổng giá trị",
                                "default": True
                            }
                        }
                    }
                }
            },
            # ==================== HR TOOLS ====================
            {
                "type": "function",
                "function": {
                    "name": "get_employees",
                    "description": "Lấy danh sách nhân viên với bộ lọc. Dùng khi cần biết có bao nhiêu nhân viên, thông tin cá nhân, độ tuổi...",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Tên nhân viên (tìm kiếm gần đúng)"
                            },
                            "department_name": {
                                "type": "string",
                                "description": "Tên phòng ban/đơn vị"
                            },
                            "position_name": {
                                "type": "string",
                                "description": "Tên chức vụ"
                            },
                            "min_age": {
                                "type": "integer",
                                "description": "Tuổi tối thiểu"
                            },
                            "max_age": {
                                "type": "integer",
                                "description": "Tuổi tối đa"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Giới hạn kết quả",
                                "default": 50
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_departments",
                    "description": "Lấy danh sách phòng ban/đơn vị. Dùng khi cần biết có những phòng ban nào, mã đơn vị.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Tên đơn vị (tìm kiếm gần đúng)"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 50
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_positions",
                    "description": "Lấy danh sách chức vụ. Dùng khi cần biết có những chức vụ nào trong công ty.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Tên chức vụ (tìm kiếm gần đúng)"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 50
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_hr_statistics",
                    "description": "Thống kê nhân sự tổng quan. Dùng khi cần phân tích, báo cáo (số lượng theo phòng ban, độ tuổi, chức vụ...).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "group_by": {
                                "type": "string",
                                "description": "Nhóm theo: department, position, age_range",
                                "enum": ["department", "position", "age_range"]
                            }
                        }
                    }
                }
            }
        ]

    def _execute_tool(self, tool_name, arguments):
        """Execute a tool function call"""
        # Meeting tools
        if tool_name == "get_meeting_rooms":
            return self._tool_get_meeting_rooms(**arguments)
        elif tool_name == "get_bookings":
            return self._tool_get_bookings(**arguments)
        elif tool_name == "get_booking_statistics":
            return self._tool_get_booking_statistics(**arguments)
        # Asset tools
        elif tool_name == "get_assets":
            return self._tool_get_assets(**arguments)
        elif tool_name == "get_asset_assignments":
            return self._tool_get_asset_assignments(**arguments)
        elif tool_name == "get_asset_lendings":
            return self._tool_get_asset_lendings(**arguments)
        elif tool_name == "get_asset_maintenances":
            return self._tool_get_asset_maintenances(**arguments)
        elif tool_name == "get_asset_disposals":
            return self._tool_get_asset_disposals(**arguments)
        elif tool_name == "get_asset_statistics":
            return self._tool_get_asset_statistics(**arguments)
        # HR tools
        elif tool_name == "get_employees":
            return self._tool_get_employees(**arguments)
        elif tool_name == "get_departments":
            return self._tool_get_departments(**arguments)
        elif tool_name == "get_positions":
            return self._tool_get_positions(**arguments)
        elif tool_name == "get_hr_statistics":
            return self._tool_get_hr_statistics(**arguments)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def _tool_get_meeting_rooms(self, location=None, min_capacity=None, available_only=False, limit=20):
        """Tool: Get meeting rooms"""
        domain = []
        if location:
            domain.append(('location', 'ilike', location))
        if min_capacity:
            domain.append(('capacity', '>=', min_capacity))
        if available_only:
            domain.append(('state', '=', 'available'))
        
        rooms = self.env['dnu.meeting.room'].search(domain, limit=limit)
        
        result = []
        for room in rooms:
            # Build facilities list from boolean fields
            facilities = []
            if getattr(room, 'has_projector', False):
                facilities.append('Máy chiếu')
            if getattr(room, 'has_tv', False):
                facilities.append('TV')
            if getattr(room, 'has_whiteboard', False):
                facilities.append('Bảng trắng')
            if getattr(room, 'has_video_conference', False):
                facilities.append('Hệ thống họp trực tuyến')
            if getattr(room, 'has_air_conditioning', False):
                facilities.append('Điều hòa')
            if getattr(room, 'has_wifi', False):
                facilities.append('WiFi')
            
            result.append({
                'id': room.id,
                'name': room.name,
                'code': getattr(room, 'code', ''),
                'location': room.location or '',
                'floor': getattr(room, 'floor', ''),
                'building': getattr(room, 'building', ''),
                'capacity': room.capacity,
                'state': room.state,
                'description': room.description or '',
                'facilities': ', '.join(facilities) if facilities else 'Không có',
                'allow_booking': getattr(room, 'allow_booking', True),
            })
        
        return {
            'total': len(result),
            'message': 'KhÃ´ng tÃ¬m tháº¥y phÃ²ng há»p phÃ¹ há»£p.' if not result else 'OK',
            'rooms': result
        }

    def _tool_get_bookings(self, date_from=None, date_to=None, room_id=None, state=None, organizer_name=None, limit=50):
        """Tool: Get bookings"""
        domain = []
        
        if date_from:
            domain.append(('start_datetime', '>=', date_from))
        if date_to:
            domain.append(('start_datetime', '<=', date_to))
        if room_id:
            domain.append(('room_id', '=', room_id))
        if state:
            domain.append(('state', '=', state))
        if organizer_name:
            domain.append(('organizer_name', 'ilike', organizer_name))
        
        bookings = self.env['dnu.meeting.booking'].search(domain, limit=limit, order='start_datetime desc')
        
        result = []
        for booking in bookings:
            result.append({
                'id': booking.id,
                'name': booking.name,
                'subject': booking.subject,
                'room': booking.room_id.name if booking.room_id else 'Online',
                'room_location': booking.room_id.location if booking.room_id else '',
                'start': str(booking.start_datetime),
                'end': str(booking.end_datetime),
                'duration': booking.duration,
                'organizer': booking.organizer_name or '',
                'num_attendees': booking.num_attendees,
                'state': booking.state,
                'description': booking.description or '',
            })
        
        return {
            'total': len(result),
            'message': 'KhÃ´ng tÃ¬m tháº¥y lá»‹ch Ä‘áº·t phÃ²ng phÃ¹ há»£p.' if not result else 'OK',
            'bookings': result
        }

    def _tool_get_booking_statistics(self, date_from=None, date_to=None, group_by='room'):
        """Tool: Get booking statistics"""
        domain = [('state', '!=', 'cancelled')]
        
        if date_from:
            domain.append(('start_datetime', '>=', date_from))
        if date_to:
            domain.append(('start_datetime', '<=', date_to))
        
        bookings = self.env['dnu.meeting.booking'].search(domain)
        
        stats = {
            'total_bookings': len(bookings),
            'total_duration_hours': sum(b.duration for b in bookings),
            'period': f"{date_from or 'All'} to {date_to or 'All'}",
        }
        
        if group_by == 'room':
            room_stats = {}
            for b in bookings:
                room_name = b.room_id.name if b.room_id else 'Online'
                if room_name not in room_stats:
                    room_stats[room_name] = {'count': 0, 'duration': 0}
                room_stats[room_name]['count'] += 1
                room_stats[room_name]['duration'] += b.duration
            stats['by_room'] = room_stats
        
        elif group_by == 'organizer':
            org_stats = {}
            for b in bookings:
                org = b.organizer_name or 'Unknown'
                if org not in org_stats:
                    org_stats[org] = {'count': 0, 'duration': 0}
                org_stats[org]['count'] += 1
                org_stats[org]['duration'] += b.duration
            stats['by_organizer'] = org_stats
        
        elif group_by == 'state':
            state_stats = {}
            for b in bookings:
                if b.state not in state_stats:
                    state_stats[b.state] = 0
                state_stats[b.state] += 1
            stats['by_state'] = state_stats
        
        return stats

    # ==================== ASSET TOOL IMPLEMENTATIONS ====================

    def _tool_get_assets(self, category_name=None, state=None, min_value=None, location=None, assigned_to=None, limit=50):
        """Tool: Get assets list"""
        domain = [('active', '=', True)]
        
        if category_name:
            domain.append(('category_id.name', 'ilike', category_name))
        if state:
            domain.append(('state', '=', state))
        if min_value:
            domain.append(('purchase_value', '>=', min_value))
        if location:
            domain.append(('location', 'ilike', location))
        if assigned_to:
            domain.append('|')
            domain.append(('assigned_to.name', 'ilike', assigned_to))
            domain.append(('assigned_nhan_vien_id.ho_va_ten', 'ilike', assigned_to))
        
        assets = self.env['dnu.asset'].search(domain, limit=limit)
        
        result = []
        for asset in assets:
            assigned_name = ''
            if asset.assigned_to:
                assigned_name = asset.assigned_to.name
            elif asset.assigned_nhan_vien_id:
                assigned_name = asset.assigned_nhan_vien_id.ho_va_ten
            
            result.append({
                'id': asset.id,
                'code': asset.code,
                'name': asset.name,
                'category': asset.category_id.name if asset.category_id else '',
                'state': asset.state,
                'purchase_value': float(asset.purchase_value or 0),
                'current_value': float(asset.current_value or 0),
                'purchase_date': str(asset.purchase_date) if asset.purchase_date else '',
                'location': asset.location or '',
                'assigned_to': assigned_name,
                'maintenance_count': asset.maintenance_count,
            })
        
        return {
            'total': len(result),
            'message': 'KhÃ´ng tÃ¬m tháº¥y tÃ i sáº£n phÃ¹ há»£p.' if not result else 'OK',
            'assets': result
        }

    def _tool_get_asset_assignments(self, asset_id=None, employee_name=None, state=None, date_from=None, limit=50):
        """Tool: Get asset assignments"""
        domain = []
        
        if asset_id:
            domain.append(('asset_id', '=', asset_id))
        if employee_name:
            domain.append(('nhan_vien_id.ho_va_ten', 'ilike', employee_name))
        if state:
            domain.append(('state', '=', state))
        if date_from:
            domain.append(('date_from', '>=', date_from))
        
        assignments = self.env['dnu.asset.assignment'].search(domain, limit=limit, order='date_from desc')
        
        result = []
        for assign in assignments:
            result.append({
                'id': assign.id,
                'asset_code': assign.asset_id.code if assign.asset_id else '',
                'asset_name': assign.asset_id.name if assign.asset_id else '',
                'employee': assign.nhan_vien_id.ho_va_ten if assign.nhan_vien_id else '',
                'department': assign.don_vi_id.ten_don_vi if assign.don_vi_id else '',
                'date_from': str(assign.date_from) if assign.date_from else '',
                'date_to': str(assign.date_to) if assign.date_to else 'Đang sử dụng',
                'state': assign.state,
                'notes': assign.notes or '',
            })
        
        return {
            'total': len(result),
            'assignments': result
        }

    def _tool_get_asset_lendings(self, asset_id=None, borrower_name=None, state=None, overdue_only=False, limit=50):
        """Tool: Get asset lendings"""
        domain = []
        
        if asset_id:
            domain.append(('asset_id', '=', asset_id))
        if borrower_name:
            domain.append('|')
            domain.append(('borrower_id.name', 'ilike', borrower_name))
            domain.append(('nhan_vien_muon_id.ho_va_ten', 'ilike', borrower_name))
        if state:
            domain.append(('state', '=', state))
        if overdue_only:
            domain.append(('state', '=', 'overdue'))
        
        lendings = self.env['dnu.asset.lending'].search(domain, limit=limit, order='date_borrow desc')
        
        result = []
        for lending in lendings:
            borrower = ''
            if lending.borrower_id:
                borrower = lending.borrower_id.name
            elif lending.nhan_vien_muon_id:
                borrower = lending.nhan_vien_muon_id.ho_va_ten
            
            result.append({
                'id': lending.id,
                'name': lending.name,
                'asset_code': lending.asset_id.code if lending.asset_id else '',
                'asset_name': lending.asset_id.name if lending.asset_id else '',
                'borrower': borrower,
                'borrow_date': str(lending.date_borrow) if lending.date_borrow else '',
                'expected_return_date': str(lending.date_expected_return) if lending.date_expected_return else '',
                'actual_return_date': str(lending.date_actual_return) if lending.date_actual_return else '',
                'state': lending.state,
                'purpose': lending.purpose or '',
                'meeting_room': lending.meeting_room_id.name if lending.meeting_room_id else '',
                'booking': lending.booking_id.name if lending.booking_id else '',
            })
        
        return {
            'total': len(result),
            'message': 'KhÃ´ng tÃ¬m tháº¥y phiáº¿u mÆ°á»£n phÃ¹ há»£p.' if not result else 'OK',
            'lendings': result
        }

    def _tool_get_asset_maintenances(self, asset_id=None, maintenance_type=None, state=None, date_from=None, limit=50):
        """Tool: Get asset maintenances"""
        domain = []
        
        if asset_id:
            domain.append(('asset_id', '=', asset_id))
        if maintenance_type:
            domain.append(('maintenance_type', '=', maintenance_type))
        if state:
            domain.append(('state', '=', state))
        if date_from:
            domain.append(('date_reported', '>=', date_from))

        maintenances = self.env['dnu.asset.maintenance'].search(domain, limit=limit, order='date_reported desc')
        
        result = []
        for maint in maintenances:
            result.append({
                'id': maint.id,
                'name': maint.name,
                'asset_code': maint.asset_id.code if maint.asset_id else '',
                'asset_name': maint.asset_id.name if maint.asset_id else '',
                'maintenance_type': dict(maint._fields['maintenance_type'].selection).get(maint.maintenance_type, maint.maintenance_type or ''),
                'date_reported': str(maint.date_reported) if maint.date_reported else '',
                'date_scheduled': str(maint.date_scheduled) if maint.date_scheduled else '',
                'date_started': str(maint.date_started) if maint.date_started else '',
                'date_completed': str(maint.date_completed) if maint.date_completed else '',
                'description': maint.description or '',
                'priority': dict(maint._fields['priority'].selection).get(maint.priority, maint.priority or ''),
                'cost_estimate': float(maint.cost_estimate or 0),
                'cost_actual': float(maint.cost_actual or 0),
                'technician': maint.tech_name or maint.assigned_tech_id.name or '',
                'reporter': maint.reporter_name or '',
                'state': dict(maint._fields['state'].selection).get(maint.state, maint.state or ''),
            })
        
        return {
            'total': len(result),
            'message': 'KhÃ´ng tÃ¬m tháº¥y phiáº¿u báº£o trÃ¬ phÃ¹ há»£p.' if not result else 'OK',
            'maintenances': result
        }

    def _tool_get_asset_disposals(self, disposal_type=None, state=None, date_from=None, limit=50):
        """Tool: Get asset disposals"""
        domain = []
        
        if disposal_type:
            domain.append(('disposal_type', '=', disposal_type))
        if state:
            domain.append(('state', '=', state))
        if date_from:
            domain.append(('date', '>=', date_from))

        disposals = self.env['dnu.asset.disposal'].search(domain, limit=limit, order='date desc')
        
        result = []
        for disposal in disposals:
            result.append({
                'id': disposal.id,
                'name': disposal.name,
                'asset_code': disposal.asset_id.code if disposal.asset_id else '',
                'asset_name': disposal.asset_id.name if disposal.asset_id else '',
                'disposal_type': disposal.disposal_type,
                'reason': disposal.reason if hasattr(disposal, 'reason') else '',
                'disposal_date': str(disposal.date) if disposal.date else '',
                'disposal_value': float(disposal.disposal_value or 0),
                'current_value': float(disposal.current_value or 0),
                'original_value': float(disposal.asset_id.purchase_value or 0) if disposal.asset_id else 0,
                'state': disposal.state,
            })
        
        return {
            'total': len(result),
            'message': 'KhÃ´ng tÃ¬m tháº¥y há»“ sÆ¡ thanh lÃ½ phÃ¹ há»£p.' if not result else 'OK',
            'disposals': result
        }

    def _tool_get_asset_statistics(self, group_by='category', include_value=True):
        """Tool: Get asset statistics"""
        assets = self.env['dnu.asset'].search([('active', '=', True)])
        
        stats = {
            'total_assets': len(assets),
            'total_value': sum(a.purchase_value or 0 for a in assets) if include_value else 0,
            'total_current_value': sum(a.current_value or 0 for a in assets) if include_value else 0,
        }
        
        if group_by == 'category':
            cat_stats = {}
            for asset in assets:
                cat = asset.category_id.name if asset.category_id else 'Không phân loại'
                if cat not in cat_stats:
                    cat_stats[cat] = {'count': 0, 'value': 0}
                cat_stats[cat]['count'] += 1
                if include_value:
                    cat_stats[cat]['value'] += asset.purchase_value or 0
            stats['by_category'] = cat_stats
        
        elif group_by == 'state':
            state_stats = {}
            for asset in assets:
                if asset.state not in state_stats:
                    state_stats[asset.state] = {'count': 0, 'value': 0}
                state_stats[asset.state]['count'] += 1
                if include_value:
                    state_stats[asset.state]['value'] += asset.purchase_value or 0
            stats['by_state'] = state_stats
        
        elif group_by == 'location':
            loc_stats = {}
            for asset in assets:
                loc = asset.location or 'Không rõ'
                if loc not in loc_stats:
                    loc_stats[loc] = {'count': 0, 'value': 0}
                loc_stats[loc]['count'] += 1
                if include_value:
                    loc_stats[loc]['value'] += asset.purchase_value or 0
            stats['by_location'] = loc_stats
        
        elif group_by == 'assigned_to':
            assign_stats = {}
            for asset in assets:
                assigned = ''
                if asset.assigned_to:
                    assigned = asset.assigned_to.name
                elif asset.assigned_nhan_vien_id:
                    assigned = asset.assigned_nhan_vien_id.ho_va_ten
                else:
                    assigned = 'Chưa gán'
                
                if assigned not in assign_stats:
                    assign_stats[assigned] = {'count': 0, 'value': 0}
                assign_stats[assigned]['count'] += 1
                if include_value:
                    assign_stats[assigned]['value'] += asset.purchase_value or 0
            stats['by_assigned_to'] = assign_stats

        elif group_by == 'department':
            dept_stats = {}
            for asset in assets:
                department = ''
                if asset.assigned_to and asset.assigned_to.department_id:
                    department = asset.assigned_to.department_id.name
                elif asset.assigned_nhan_vien_id and asset.assigned_nhan_vien_id.don_vi_chinh_id:
                    department = asset.assigned_nhan_vien_id.don_vi_chinh_id.ten_don_vi
                elif asset.room_id and hasattr(asset.room_id, 'department_id') and asset.room_id.department_id:
                    department = asset.room_id.department_id.name
                else:
                    department = 'Chưa phân phòng ban'

                if department not in dept_stats:
                    dept_stats[department] = {'count': 0, 'value': 0}
                dept_stats[department]['count'] += 1
                if include_value:
                    dept_stats[department]['value'] += asset.purchase_value or 0
            stats['by_department'] = dept_stats
        
        return stats

    # ==================== HR TOOL IMPLEMENTATIONS ====================
    
    def _tool_get_employees(self, name=None, department_name=None, position_name=None, 
                            min_age=None, max_age=None, limit=50):
        """Tool: Get employees"""
        result = []
        if self.env['nhan_vien'].search_count([]):
            domain = []
            if name:
                domain.append(('ho_va_ten', 'ilike', name))
            if department_name:
                domain.append(('don_vi_chinh_id.ten_don_vi', 'ilike', department_name))
            if position_name:
                domain.append(('chuc_vu_chinh_id.ten_chuc_vu', 'ilike', position_name))
            if min_age:
                domain.append(('tuoi', '>=', min_age))
            if max_age:
                domain.append(('tuoi', '<=', max_age))
            
            employees = self.env['nhan_vien'].search(domain, limit=limit)
            for emp in employees:
                result.append({
                    'id': emp.id,
                    'ma_dinh_danh': emp.ma_dinh_danh,
                    'ho_va_ten': emp.ho_va_ten,
                    'tuoi': emp.tuoi,
                    'email': emp.email or '',
                    'so_dien_thoai': emp.so_dien_thoai or '',
                    'que_quan': emp.que_quan or '',
                    'phong_ban': emp.don_vi_chinh_id.ten_don_vi if emp.don_vi_chinh_id else '',
                    'chuc_vu': emp.chuc_vu_chinh_id.ten_chuc_vu if emp.chuc_vu_chinh_id else '',
                })
        else:
            domain = []
            if name:
                domain.append(('name', 'ilike', name))
            if department_name:
                domain.append(('department_id.name', 'ilike', department_name))
            if position_name:
                domain.append(('job_title', 'ilike', position_name))
            employees = self.env['hr.employee'].search(domain, limit=limit)
            for emp in employees:
                result.append({
                    'id': emp.id,
                    'ma_dinh_danh': '',
                    'ho_va_ten': emp.name,
                    'tuoi': '',
                    'email': emp.work_email or '',
                    'so_dien_thoai': emp.mobile_phone or '',
                    'que_quan': '',
                    'phong_ban': emp.department_id.name if emp.department_id else '',
                    'chuc_vu': emp.job_title or '',
                })
        
        return {
            'count': len(result),
            'employees': result
        }
    
    def _tool_get_departments(self, name=None, limit=50):
        """Tool: Get departments"""
        result = []
        if self.env['don_vi'].search_count([]):
            domain = []
            if name:
                domain.append(('ten_don_vi', 'ilike', name))
            departments = self.env['don_vi'].search(domain, limit=limit)
            for dept in departments:
                emp_count = self.env['nhan_vien'].search_count([
                    ('don_vi_chinh_id', '=', dept.id)
                ])
                result.append({
                    'id': dept.id,
                    'ma_don_vi': dept.ma_don_vi,
                    'ten_don_vi': dept.ten_don_vi,
                    'so_nhan_vien': emp_count
                })
        else:
            domain = []
            if name:
                domain.append(('name', 'ilike', name))
            departments = self.env['hr.department'].search(domain, limit=limit)
            for dept in departments:
                result.append({
                    'id': dept.id,
                    'ma_don_vi': '',
                    'ten_don_vi': dept.name,
                    'so_nhan_vien': self.env['hr.employee'].search_count([('department_id', '=', dept.id)])
                })
        
        return {
            'count': len(result),
            'departments': result
        }
    
    def _tool_get_positions(self, name=None, limit=50):
        """Tool: Get positions"""
        result = []
        if self.env['chuc_vu'].search_count([]):
            domain = []
            if name:
                domain.append(('ten_chuc_vu', 'ilike', name))
            positions = self.env['chuc_vu'].search(domain, limit=limit)
            for pos in positions:
                emp_count = self.env['nhan_vien'].search_count([
                    ('chuc_vu_chinh_id', '=', pos.id)
                ])
                result.append({
                    'id': pos.id,
                    'ma_chuc_vu': pos.ma_chuc_vu,
                    'ten_chuc_vu': pos.ten_chuc_vu,
                    'so_nhan_vien': emp_count
                })
        else:
            grouped = {}
            for emp in self.env['hr.employee'].search([], limit=500):
                title = emp.job_title or 'Chưa có chức vụ'
                grouped[title] = grouped.get(title, 0) + 1
            idx = 1
            for title in sorted(grouped.keys()):
                if name and name.lower() not in title.lower():
                    continue
                result.append({
                    'id': idx,
                    'ma_chuc_vu': '',
                    'ten_chuc_vu': title,
                    'so_nhan_vien': grouped[title]
                })
                idx += 1
        
        return {
            'count': len(result),
            'positions': result
        }
    
    def _tool_get_hr_statistics(self, group_by='department'):
        """Tool: Get HR statistics"""
        if not self.env['nhan_vien'].search_count([]):
            employees = self.env['hr.employee'].search([])
            stats = {
                'total_employees': len(employees),
                'average_age': 0,
            }
            if group_by == 'department':
                dept_stats = {}
                for emp in employees:
                    dept = emp.department_id.name if emp.department_id else 'Chưa phân công'
                    if dept not in dept_stats:
                        dept_stats[dept] = {'count': 0}
                    dept_stats[dept]['count'] += 1
                stats['by_department'] = dept_stats
            elif group_by == 'position':
                pos_stats = {}
                for emp in employees:
                    pos = emp.job_title or 'Chưa có chức vụ'
                    if pos not in pos_stats:
                        pos_stats[pos] = {'count': 0}
                    pos_stats[pos]['count'] += 1
                stats['by_position'] = pos_stats
            elif group_by == 'age_range':
                stats['by_age_range'] = {}
            return stats

        employees = self.env['nhan_vien'].search([])
        
        stats = {
            'total_employees': len(employees),
            'average_age': sum(e.tuoi for e in employees if e.tuoi) / len(employees) if employees else 0,
        }
        
        if group_by == 'department':
            dept_stats = {}
            for emp in employees:
                dept = emp.don_vi_chinh_id.ten_don_vi if emp.don_vi_chinh_id else 'Chưa phân công'
                if dept not in dept_stats:
                    dept_stats[dept] = {'count': 0, 'avg_age': []}
                dept_stats[dept]['count'] += 1
                if emp.tuoi:
                    dept_stats[dept]['avg_age'].append(emp.tuoi)
            
            # Calculate average age for each department
            for dept in dept_stats:
                ages = dept_stats[dept]['avg_age']
                dept_stats[dept]['avg_age'] = sum(ages) / len(ages) if ages else 0
            
            stats['by_department'] = dept_stats
        
        elif group_by == 'position':
            pos_stats = {}
            for emp in employees:
                pos = emp.chuc_vu_chinh_id.ten_chuc_vu if emp.chuc_vu_chinh_id else 'Chưa có chức vụ'
                if pos not in pos_stats:
                    pos_stats[pos] = {'count': 0, 'avg_age': []}
                pos_stats[pos]['count'] += 1
                if emp.tuoi:
                    pos_stats[pos]['avg_age'].append(emp.tuoi)
            
            for pos in pos_stats:
                ages = pos_stats[pos]['avg_age']
                pos_stats[pos]['avg_age'] = sum(ages) / len(ages) if ages else 0
            
            stats['by_position'] = pos_stats
        
        elif group_by == 'age_range':
            age_ranges = {
                '18-25': 0,
                '26-35': 0,
                '36-45': 0,
                '46-55': 0,
                '56+': 0
            }
            for emp in employees:
                if emp.tuoi:
                    if emp.tuoi <= 25:
                        age_ranges['18-25'] += 1
                    elif emp.tuoi <= 35:
                        age_ranges['26-35'] += 1
                    elif emp.tuoi <= 45:
                        age_ranges['36-45'] += 1
                    elif emp.tuoi <= 55:
                        age_ranges['46-55'] += 1
                    else:
                        age_ranges['56+'] += 1
            
            stats['by_age_range'] = age_ranges
        
        return stats

    def _fallback_chat_response(self, message):
        """Chatbot nội bộ không cần API key, bám theo nghiệp vụ đề tài."""
        text = (message or '').strip()
        lowered = text.lower()
        normalized = unicodedata.normalize('NFKD', lowered).replace('đ', 'd')
        normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))

        if not text:
            return 'Bạn hãy nhập câu hỏi liên quan đến tài sản, phòng họp, mượn trả, bảo trì, thanh lý hoặc nhân sự.'

        if any(k in normalized for k in ['phong hop']) and any(k in normalized for k in ['bao nhieu', 'danh sach', 'con trong']):
            rooms = self._tool_get_meeting_rooms(limit=20)
            if rooms.get('total', 0) == 0:
                return 'Kết luận: không tìm thấy phòng họp phù hợp.\nCăn cứ dữ liệu: hệ thống không có bản ghi phòng họp khớp điều kiện.'
            names = ', '.join(room['name'] for room in rooms['rooms'][:10])
            return f"Kết luận: hiện có {rooms['total']} phòng họp phù hợp.\nCăn cứ dữ liệu: {names}.\nĐề xuất: có thể hỏi tiếp về sức chứa, vị trí hoặc lịch đặt của từng phòng."

        if any(k in normalized for k in ['dat phong', 'booking', 'lich hop']):
            bookings = self._tool_get_bookings(limit=20)
            if bookings.get('total', 0) == 0:
                return 'Kết luận: hiện chưa có lịch đặt phòng phù hợp.\nCăn cứ dữ liệu: danh sách booking đang rỗng theo điều kiện hỏi.'
            lines = [
                f"- {booking['name']}: {booking['subject']} | {booking['room']} | {booking['start']} - {booking['end']} | trạng thái {booking['state']}"
                for booking in bookings['bookings'][:5]
            ]
            return "Kết luận: đã tìm thấy lịch đặt phòng.\nCăn cứ dữ liệu:\n" + '\n'.join(lines)

        if any(k in normalized for k in ['qua han', 'muon', 'tra']) and any(k in normalized for k in ['tai san', 'thiet bi']):
            lendings = self._tool_get_asset_lendings(overdue_only=True, limit=20)
            if lendings.get('total', 0) == 0:
                return 'Kết luận: hiện không có phiếu mượn tài sản quá hạn.\nCăn cứ dữ liệu: hệ thống không có lending ở trạng thái overdue.'
            lines = [
                f"- {lending['name']}: {lending['asset_name']} ({lending['asset_code']}) do {lending['borrower']} mượn, hạn trả {lending['expected_return_date']}"
                for lending in lendings['lendings'][:5]
            ]
            return "Kết luận: có phiếu mượn tài sản quá hạn.\nCăn cứ dữ liệu:\n" + '\n'.join(lines)

        if any(k in normalized for k in ['bao tri', 'sua chua', 'kiem tra']):
            maintenances = self._tool_get_asset_maintenances(limit=20)
            if maintenances.get('total', 0) == 0:
                return 'Kết luận: hiện chưa có phiếu bảo trì phù hợp.\nCăn cứ dữ liệu: hệ thống chưa ghi nhận maintenance theo điều kiện hỏi.'
            lines = [
                f"- {maint['name']}: {maint['asset_name']} ({maint['asset_code']}) | loại {maint['maintenance_type']} | trạng thái {maint['state']} | ưu tiên {maint['priority']}"
                for maint in maintenances['maintenances'][:5]
            ]
            return "Kết luận: đã tìm thấy phiếu bảo trì liên quan.\nCăn cứ dữ liệu:\n" + '\n'.join(lines)

        if any(k in normalized for k in ['thanh ly', 'scrap', 'huy']):
            disposals = self._tool_get_asset_disposals(limit=20)
            if disposals.get('total', 0) == 0:
                return 'Kết luận: hiện chưa có hồ sơ thanh lý phù hợp.\nCăn cứ dữ liệu: hệ thống chưa có bản ghi disposal khớp điều kiện hỏi.'
            lines = [
                f"- {disposal['name']}: {disposal['asset_name']} ({disposal['asset_code']}) | hình thức {disposal['disposal_type']} | trạng thái {disposal['state']}"
                for disposal in disposals['disposals'][:5]
            ]
            return "Kết luận: đã tìm thấy hồ sơ thanh lý.\nCăn cứ dữ liệu:\n" + '\n'.join(lines)

        if any(k in normalized for k in ['tai san', 'thiet bi']):
            assets = self._tool_get_assets(limit=20)
            if assets.get('total', 0) == 0:
                return 'Kết luận: hiện chưa có tài sản phù hợp.\nCăn cứ dữ liệu: danh mục tài sản đang rỗng theo điều kiện hỏi.'
            lines = [
                f"- {asset['code']}: {asset['name']} | danh mục {asset['category']} | trạng thái {asset['state']} | vị trí {asset['location']}"
                for asset in assets['assets'][:5]
            ]
            return "Kết luận: đã tìm thấy tài sản phù hợp.\nCăn cứ dữ liệu:\n" + '\n'.join(lines)

        if any(k in normalized for k in ['nhan su', 'nhan vien', 'phong ban', 'chuc vu']):
            employees = self._tool_get_employees(limit=20)
            if employees.get('count', 0) == 0:
                return 'Kết luận: hiện chưa có dữ liệu nhân sự phù hợp.\nCăn cứ dữ liệu: hệ thống nhân sự đang không có bản ghi khớp điều kiện hỏi.'
            lines = [
                f"- {emp['ho_va_ten']} | phòng ban {emp['phong_ban']} | chức vụ {emp['chuc_vu']}"
                for emp in employees['employees'][:5]
            ]
            return "Kết luận: đã tìm thấy dữ liệu nhân sự.\nCăn cứ dữ liệu:\n" + '\n'.join(lines)

        return (
            "Tôi đang hỗ trợ tốt nhất cho các nhóm việc: tài sản, phòng họp, mượn trả, bảo trì, thanh lý và nhân sự.\n"
            "Đề xuất tiếp theo: hãy hỏi cụ thể hơn, ví dụ 'Có bao nhiêu phòng họp?', 'Tài sản nào đang quá hạn mượn?', 'Tài sản nào cần bảo trì?'."
        )

    def _normalize_chat_text_v2(self, text):
        """Normalize text for lightweight offline intent parsing."""
        normalized = unicodedata.normalize('NFKD', (text or '').strip().lower()).replace('đ', 'd')
        return ''.join(ch for ch in normalized if not unicodedata.combining(ch))

    def _extract_first_number_v2(self, text):
        import re
        match = re.search(r'\d+', text or '')
        return int(match.group(0)) if match else None

    def _contains_any_v2(self, text, keywords):
        return any(keyword in text for keyword in keywords)

    def _build_list_response_v2(self, title, lines, empty_message, suggestion=None):
        if not lines:
            return empty_message
        response = title + "\nCăn cứ dữ liệu:\n" + '\n'.join(lines)
        if suggestion:
            response += "\nĐề xuất: " + suggestion
        return response

    def _fallback_chat_response_v2(self, message):
        """Offline chatbot that answers from Odoo data without external API."""
        text = (message or '').strip()
        normalized = self._normalize_chat_text_v2(text)
        padded = f" {normalized} "
        number_hint = self._extract_first_number_v2(normalized)

        if not text:
            return 'Bạn hãy nhập câu hỏi liên quan đến tài sản, phòng họp, mượn trả, bảo trì, thanh lý hoặc nhân sự.'

        if self._contains_any_v2(normalized, ['tao ', 'them ', 'xoa ', 'duyet ', 'phe duyet', 'cap nhat ', 'sua ']):
            return (
                "Kết luận: hiện chatbot nội bộ chỉ hỗ trợ tra cứu, thống kê và phân tích nghiệp vụ.\n"
                "Căn cứ dữ liệu: chức năng offline không tự tạo, sửa, xóa hay duyệt chứng từ thay người dùng.\n"
                "Đề xuất: bạn thao tác trực tiếp trên form Odoo, còn tôi có thể hướng dẫn đúng màn hình và đúng bước."
            )

        if self._contains_any_v2(normalized, ['phong hop']) and self._contains_any_v2(normalized, ['bao nhieu', 'danh sach', 'con trong', 'trong', 'phong nao']):
            location = None
            for hint in ['tang 1', 'tang 2', 'tang 3', 'toa a', 'toa b', 'toa c']:
                if hint in normalized:
                    location = hint
                    break
            rooms = self._tool_get_meeting_rooms(location=location, min_capacity=number_hint if 'nguoi' in normalized else None, limit=20)
            if rooms.get('total', 0) == 0:
                return 'Kết luận: không tìm thấy phòng họp phù hợp.\nCăn cứ dữ liệu: hệ thống không có bản ghi phòng họp khớp điều kiện lọc.'
            lines = [
                f"- {room['name']} | vị trí {room['location']} | sức chứa {room['capacity']} | trạng thái {room['state']}"
                for room in rooms['rooms'][:10]
            ]
            return self._build_list_response_v2(
                f"Kết luận: hiện có {rooms['total']} phòng họp phù hợp.",
                lines,
                'Kết luận: không tìm thấy phòng họp phù hợp.',
                'có thể hỏi tiếp phòng nào đang bảo trì, phòng nào phù hợp cho 10-20 người, hoặc lịch đặt theo ngày.'
            )

        if self._contains_any_v2(normalized, ['thong ke phong hop', 'thong ke booking', 'tan suat phong hop']) or (
            'thong ke' in normalized and self._contains_any_v2(normalized, ['phong hop', 'booking', 'cuoc hop'])
        ):
            group_by = 'room'
            if 'nguoi to chuc' in normalized:
                group_by = 'organizer'
            elif 'trang thai' in normalized:
                group_by = 'state'
            elif 'ngay' in normalized:
                group_by = 'date'
            stats = self._tool_get_booking_statistics(group_by=group_by)
            key = {'room': 'by_room', 'organizer': 'by_organizer', 'state': 'by_state', 'date': 'by_date'}[group_by]
            data = stats.get(key, {})
            lines = [f"- {name}: {value}" for name, value in list(data.items())[:10]]
            return self._build_list_response_v2(
                f"Kết luận: đã tổng hợp thống kê đặt phòng theo {group_by}.",
                lines,
                'Kết luận: chưa có dữ liệu thống kê đặt phòng phù hợp.',
                'có thể khoanh tiếp theo ngày, trạng thái hoặc người tổ chức để đọc rõ hơn.'
            )

        if self._contains_any_v2(normalized, ['dat phong', 'booking', 'lich hop', 'cuoc hop']):
            state = None
            if self._contains_any_v2(normalized, ['xac nhan', 'confirmed']):
                state = 'confirmed'
            elif self._contains_any_v2(normalized, ['dang hop', 'in progress']):
                state = 'in_progress'
            elif self._contains_any_v2(normalized, ['hoan thanh', 'done']):
                state = 'done'
            elif self._contains_any_v2(normalized, ['huy', 'cancel']):
                state = 'cancelled'
            bookings = self._tool_get_bookings(state=state, limit=20)
            if bookings.get('total', 0) == 0:
                return 'Kết luận: hiện chưa có lịch đặt phòng phù hợp.\nCăn cứ dữ liệu: danh sách booking đang rỗng theo điều kiện hỏi.'
            lines = [
                f"- {booking['name']}: {booking['subject']} | {booking['room']} | {booking['start']} - {booking['end']} | trạng thái {booking['state']}"
                for booking in bookings['bookings'][:5]
            ]
            return self._build_list_response_v2(
                "Kết luận: đã tìm thấy lịch đặt phòng phù hợp.",
                lines,
                'Kết luận: hiện chưa có lịch đặt phòng phù hợp.',
                'có thể hỏi tiếp thống kê booking theo phòng, theo người tổ chức hoặc theo trạng thái.'
            )

        if self._contains_any_v2(normalized, ['qua han']) or (
            self._contains_any_v2(normalized, ['tai san', 'thiet bi']) and (
                ' muon ' in padded or ' tra ' in padded or ' qua han ' in padded
            )
        ):
            lendings = self._tool_get_asset_lendings(overdue_only=True, limit=20)
            if lendings.get('total', 0) == 0:
                return 'Kết luận: hiện không có phiếu mượn tài sản quá hạn.\nCăn cứ dữ liệu: hệ thống không có lending ở trạng thái overdue.'
            lines = [
                f"- {lending['name']}: {lending['asset_name']} ({lending['asset_code']}) do {lending['borrower']} mượn, hạn trả {lending['expected_return_date']}"
                for lending in lendings['lendings'][:5]
            ]
            return self._build_list_response_v2(
                "Kết luận: có phiếu mượn tài sản quá hạn.",
                lines,
                'Kết luận: hiện không có phiếu mượn tài sản quá hạn.',
                'nên kiểm tra người mượn, hạn trả và tình trạng bàn giao để nhắc xử lý.'
            )

        if self._contains_any_v2(normalized, ['bao tri', 'sua chua', 'kiem tra']):
            maintenance_state = 'pending' if self._contains_any_v2(normalized, ['can', 'cho', 'pending']) else None
            maintenances = self._tool_get_asset_maintenances(state=maintenance_state, limit=20)
            if maintenances.get('total', 0) == 0:
                return 'Kết luận: hiện chưa có phiếu bảo trì phù hợp.\nCăn cứ dữ liệu: hệ thống chưa ghi nhận maintenance theo điều kiện hỏi.'
            lines = [
                f"- {maint['name']}: {maint['asset_name']} ({maint['asset_code']}) | loại {maint['maintenance_type']} | trạng thái {maint['state']} | ưu tiên {maint['priority']}"
                for maint in maintenances['maintenances'][:5]
            ]
            return self._build_list_response_v2(
                "Kết luận: đã tìm thấy phiếu bảo trì liên quan.",
                lines,
                'Kết luận: hiện chưa có phiếu bảo trì phù hợp.',
                'có thể hỏi tiếp tài sản nào bảo trì nhiều nhất hoặc hồ sơ nào đang chờ xử lý.'
            )

        if self._contains_any_v2(normalized, ['thanh ly', 'scrap', 'huy']):
            disposals = self._tool_get_asset_disposals(limit=20)
            if disposals.get('total', 0) == 0:
                return 'Kết luận: hiện chưa có hồ sơ thanh lý phù hợp.\nCăn cứ dữ liệu: hệ thống chưa có bản ghi disposal khớp điều kiện hỏi.'
            lines = [
                f"- {disposal['name']}: {disposal['asset_name']} ({disposal['asset_code']}) | hình thức {disposal['disposal_type']} | trạng thái {disposal['state']}"
                for disposal in disposals['disposals'][:5]
            ]
            return self._build_list_response_v2(
                "Kết luận: đã tìm thấy hồ sơ thanh lý.",
                lines,
                'Kết luận: hiện chưa có hồ sơ thanh lý phù hợp.',
                'có thể hỏi tiếp hồ sơ nào đang chờ duyệt hoặc lý do thanh lý của từng tài sản.'
            )

        if 'thong ke' in normalized and self._contains_any_v2(normalized, ['tai san', 'thiet bi']):
            group_by = 'category'
            if 'trang thai' in normalized:
                group_by = 'state'
            elif 'vi tri' in normalized:
                group_by = 'location'
            elif self._contains_any_v2(normalized, ['phong ban']):
                group_by = 'department'
            elif self._contains_any_v2(normalized, ['nguoi dung', 'nguoi su dung', 'nguoi duoc gan']):
                group_by = 'assigned_to'
            stats = self._tool_get_asset_statistics(group_by=group_by)
            key = {
                'category': 'by_category',
                'state': 'by_state',
                'location': 'by_location',
                'assigned_to': 'by_assigned_to',
                'department': 'by_department',
            }[group_by]
            data = stats.get(key, {})
            lines = []
            for name, value in list(data.items())[:10]:
                if isinstance(value, dict):
                    line = f"- {name}: {value.get('count', 0)} tài sản"
                    if 'value' in value:
                        line += f", nguyên giá {value.get('value', 0):,.0f} VND"
                    lines.append(line)
                else:
                    lines.append(f"- {name}: {value}")
            return self._build_list_response_v2(
                f"Kết luận: đã tổng hợp thống kê tài sản theo {group_by}.",
                lines,
                'Kết luận: chưa có dữ liệu thống kê tài sản phù hợp.',
                'có thể hỏi tiếp theo danh mục, vị trí, trạng thái hoặc người được gán.'
            )

        if self._contains_any_v2(normalized, ['tai san', 'thiet bi']):
            asset_state = None
            if 'san sang' in normalized or 'available' in normalized:
                asset_state = 'available'
            elif 'dang su dung' in normalized or 'assigned' in normalized:
                asset_state = 'assigned'
            elif 'bao tri' in normalized or 'maintenance' in normalized:
                asset_state = 'maintenance'
            elif 'thanh ly' in normalized or 'disposed' in normalized:
                asset_state = 'disposed'
            elif 'that lac' in normalized or 'lost' in normalized:
                asset_state = 'lost'
            assets = self._tool_get_assets(state=asset_state, limit=20)
            if assets.get('total', 0) == 0:
                return 'Kết luận: hiện chưa có tài sản phù hợp.\nCăn cứ dữ liệu: danh mục tài sản đang rỗng theo điều kiện hỏi.'
            lines = [
                f"- {asset['code']}: {asset['name']} | danh mục {asset['category']} | trạng thái {asset['state']} | vị trí {asset['location']}"
                for asset in assets['assets'][:5]
            ]
            return self._build_list_response_v2(
                f"Kết luận: đã tìm thấy {assets['total']} tài sản phù hợp.",
                lines,
                'Kết luận: hiện chưa có tài sản phù hợp.',
                'có thể hỏi tiếp tài sản theo trạng thái, theo người dùng hoặc lịch sử mượn trả.'
            )

        if 'thong ke' in normalized and self._contains_any_v2(normalized, ['nhan su', 'nhan vien', 'phong ban', 'chuc vu']):
            group_by = 'department'
            if 'chuc vu' in normalized:
                group_by = 'position'
            elif 'tuoi' in normalized:
                group_by = 'age_range'
            stats = self._tool_get_hr_statistics(group_by=group_by)
            key = {'department': 'by_department', 'position': 'by_position', 'age_range': 'by_age_range'}[group_by]
            data = stats.get(key, {})
            lines = []
            for name, value in list(data.items())[:10]:
                if isinstance(value, dict):
                    line = f"- {name}: {value.get('count', 0)} nhân sự"
                    if 'avg_age' in value:
                        line += f", tuổi TB {value.get('avg_age', 0):.1f}"
                    lines.append(line)
                else:
                    lines.append(f"- {name}: {value}")
            return self._build_list_response_v2(
                f"Kết luận: đã tổng hợp thống kê nhân sự theo {group_by}.",
                lines,
                'Kết luận: chưa có dữ liệu thống kê nhân sự phù hợp.',
                'có thể hỏi tiếp danh sách nhân viên theo phòng ban hoặc chức vụ cụ thể.'
            )

        if self._contains_any_v2(normalized, ['nhan su', 'nhan vien', 'phong ban', 'chuc vu']):
            department_name = None
            position_name = None
            if 'phong it' in normalized:
                department_name = 'Research & Development'
            elif 'phong hanh chinh' in normalized:
                department_name = 'Hành chính'
            elif 'phong ke toan' in normalized:
                department_name = 'Kế toán'
            if 'giam doc' in normalized:
                position_name = 'Giám đốc'
            elif 'truong phong' in normalized:
                position_name = 'Trưởng phòng'
            employees = self._tool_get_employees(department_name=department_name, position_name=position_name, limit=20)
            if employees.get('count', 0) == 0:
                return 'Kết luận: hiện chưa có dữ liệu nhân sự phù hợp.\nCăn cứ dữ liệu: hệ thống nhân sự đang không có bản ghi khớp điều kiện hỏi.'
            lines = [
                f"- {emp['ho_va_ten']} | phòng ban {emp['phong_ban']} | chức vụ {emp['chuc_vu']}"
                for emp in employees['employees'][:5]
            ]
            return self._build_list_response_v2(
                f"Kết luận: đã tìm thấy {employees['count']} bản ghi nhân sự phù hợp.",
                lines,
                'Kết luận: hiện chưa có dữ liệu nhân sự phù hợp.',
                'có thể hỏi tiếp thống kê theo phòng ban, chức vụ hoặc độ tuổi.'
            )

        return (
            "Tôi đang hỗ trợ tốt nhất cho các nhóm việc: tài sản, phòng họp, mượn trả, bảo trì, thanh lý và nhân sự.\n"
            "Đề xuất tiếp theo: hãy hỏi cụ thể hơn, ví dụ 'Thống kê tài sản theo trạng thái', 'Có bao nhiêu phòng họp tầng 2?', 'Nhân sự phòng IT gồm những ai?', hoặc 'Tài sản nào đang quá hạn mượn?'."
        )

    def chat(self, message, context=None):
        """
        Chat tự do với AI về quản lý tài sản/phòng họp (với function calling)
        
        Args:
            message: Tin nhắn người dùng
            context: Context bổ sung (optional)
        Returns:
            String response
        """
        try:
            config = self.env['openai.configuration'].get_default_config()
        except UserError:
            return self._fallback_chat_response_v2(message)
        
        system_prompt = """Bạn là trợ lý AI cho hệ thống Quản lý Tài sản, Phòng họp & Nhân sự của DNU.
        
Bạn có khả năng TỰ ĐỘNG truy cập dữ liệu thông qua các function:

PHÒNG HỌP & ĐẶT PHÒNG:
- get_meeting_rooms: Lấy thông tin phòng họp (số lượng, vị trí, sức chứa...)
- get_bookings: Lấy lịch đặt phòng (theo thời gian, phòng, người tổ chức...)
- get_booking_statistics: Thống kê booking (tổng số, phân bố theo phòng/người...)

TÀI SẢN:
- get_assets: Lấy danh sách tài sản (theo danh mục, trạng thái, giá trị, vị trí, người dùng...)
- get_asset_assignments: Lấy lịch sử gán tài sản (ai đang/đã dùng tài sản nào)
- get_asset_lendings: Lấy danh sách mượn tài sản (ai mượn, quá hạn chưa...)
- get_asset_maintenances: Lấy lịch sử bảo trì (số lần, chi phí, loại bảo trì...)
- get_asset_disposals: Lấy thông tin thanh lý (hình thức, lý do, giá trị...)
- get_asset_statistics: Thống kê tổng quan tài sản (theo danh mục/trạng thái/vị trí/người dùng)

NHÂN SỰ:
- get_employees: Lấy danh sách nhân viên (theo tên, phòng ban, chức vụ, độ tuổi...)
- get_departments: Lấy danh sách phòng ban/đơn vị (có số lượng nhân viên)
- get_positions: Lấy danh sách chức vụ (có số lượng người đảm nhiệm)
- get_hr_statistics: Thống kê nhân sự (theo phòng ban/chức vụ/độ tuổi)

Khi người dùng hỏi về tài sản, phòng họp, hoặc nhân sự, hãy CHỦ ĐỘNG gọi function phù hợp để lấy data CẬP NHẬT, thay vì đoán hoặc yêu cầu thông tin cụ thể.

Ví dụ:
- "Có bao nhiêu máy tính?" → gọi get_assets(category_name='máy tính')
- "Ai đang dùng laptop Lenovo?" → gọi get_assets() + filter
- "Có bao nhiêu nhân viên?" → gọi get_employees()
- "Phòng IT có mấy người?" → gọi get_employees(department_name='IT')
- "Ai là giám đốc?" → gọi get_employees(position_name='giám đốc')
- "Tài sản nào cần bảo trì?" → gọi get_asset_maintenances() hoặc get_assets(state='maintenance')
- "Phòng họp tầng 2 có mấy phòng?" → gọi get_meeting_rooms(location='tầng 2')
- "Thống kê tài sản theo phòng ban" → gọi get_asset_statistics(group_by='department')

Quy tắc:
- Trả lời bằng tiếng Việt
- Luôn ưu tiên lấy data thật từ function
- Ngắn gọn, đi thẳng vào vấn đề
- Nếu cần nhiều thông tin, gọi nhiều function trong 1 lượt
- Trình bày số liệu dưới dạng dễ đọc (danh sách, bảng nếu cần)"""

        messages = [{"role": "system", "content": system_prompt}]
        
        if context:
            messages.append({"role": "system", "content": f"Context bổ sung: {context}"})
        
        messages.append({
            "role": "system",
            "content": self._business_response_rules('quáº£n lÃ½ tÃ i sáº£n, phÃ²ng há»p vÃ  nhÃ¢n sá»±') + """

Quy táº¯c bá»• sung cho chat:
- Vá»›i cÃ¢u há»i thuá»™c cÃ¡c miá»n nghiá»‡p vá»¥ nÃªu trÃªn, pháº£i Æ°u tiÃªn gá»i function trÆ°á»›c khi tráº£ lá»i.
- Sau khi function tráº£ vá», chá»‰ Ä‘Æ°á»£c dá»±a trÃªn káº¿t quáº£ Ä‘Ã³ Ä‘á»ƒ káº¿t luáº­n.
- Náº¿u function tráº£ vá» total = 0 hoáº·c danh sÃ¡ch rá»—ng, pháº£i nÃ³i rÃµ lÃ  khÃ´ng tÃ¬m tháº¥y dá»¯ liá»‡u phÃ¹ há»£p.
- Náº¿u cÃ¢u há»i yÃªu cáº§u thao tÃ¡c thay Ä‘á»•i dá»¯ liá»‡u nhÆ° duyá»‡t, táº¡o, xÃ³a, sá»­a thÃ¬ hÃ£y nÃ³i hiá»‡n chá»‰ há»— trá»£ tra cá»©u/phÃ¢n tÃ­ch.
- Káº¿t thÃºc cÃ¢u tráº£ lá»i báº±ng pháº§n Äá» xuáº¥t tiáº¿p theo náº¿u hÆ°á»›ng xá»­ lÃ½ cÃ²n má»."""
        })
        messages.append({"role": "user", "content": message})
        
        tools = self._get_available_tools()
        max_iterations = 4
        
        for iteration in range(max_iterations):
            response = config._call_openai_with_tools(messages, tools)
            
            if not response.get('tool_calls'):
                return response.get('content', '')
            
            # Append assistant message with tool calls (already serialized)
            messages.append({
                "role": "assistant",
                "content": response.get('content'),
                "tool_calls": response['tool_calls']
            })
            
            # Execute each tool and append results
            for tool_call in response['tool_calls']:
                tool_name = tool_call['function']['name']
                try:
                    arguments = json.loads(tool_call['function']['arguments'] or '{}')
                except Exception:
                    arguments = {}
                
                _logger.info(f"AI calling tool: {tool_name} with args: {arguments}")
                try:
                    tool_result = self._execute_tool(tool_name, arguments)
                except Exception as e:
                    tool_result = {
                        'error': str(e),
                        'tool_name': tool_name,
                    }
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call['id'],
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })
        
        return "Đã vượt quá số lần gọi function tối đa."
