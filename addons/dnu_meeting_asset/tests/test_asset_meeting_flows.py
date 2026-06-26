# -*- coding: utf-8 -*-

import base64
from datetime import timedelta
from uuid import uuid4
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, standalone


@tagged('dnu_meeting_asset', 'post_install')
class TestAssetMeetingFlows(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.department = cls.env['don_vi'].create({
            'ma_don_vi': 'QA-DV-ASSET',
            'ten_don_vi': 'QA Asset Department',
        })
        cls.director_department = cls.env['don_vi'].create({
            'ma_don_vi': 'BGD-QA-ASSET',
            'ten_don_vi': 'QA Board',
        })
        cls.position = cls.env['chuc_vu'].create({
            'ma_chuc_vu': 'QA-CV-ASSET',
            'ten_chuc_vu': 'QA Staff',
        })
        cls.director_position = cls.env['chuc_vu'].create({
            'ma_chuc_vu': 'QA-CV-DIR',
            'ten_chuc_vu': 'QA Director',
        })
        cls.category = cls.env['dnu.asset.category'].create({'name': 'QA Category'})

        cls.director_nv = cls.env['nhan_vien'].create({
            'ma_dinh_danh': 'qa-director-asset',
            'ho_ten_dem': 'QA Director',
            'ten': 'Asset',
            'ngay_sinh': '1990-01-01',
            'email': 'qa.director.asset@example.com',
        })
        cls.manager_nv = cls.env['nhan_vien'].create({
            'ma_dinh_danh': 'qa-manager-asset',
            'ho_ten_dem': 'QA Manager',
            'ten': 'Asset',
            'ngay_sinh': '1991-01-01',
            'email': 'qa.manager.asset@example.com',
        })
        cls.staff_nv = cls.env['nhan_vien'].create({
            'ma_dinh_danh': 'qa-staff-asset',
            'ho_ten_dem': 'QA Staff',
            'ten': 'Asset',
            'ngay_sinh': '1992-01-01',
            'email': 'qa.staff.asset@example.com',
        })

        for employee, department, position in [
            (cls.director_nv, cls.director_department, cls.director_position),
            (cls.manager_nv, cls.department, cls.position),
            (cls.staff_nv, cls.department, cls.position),
        ]:
            cls.env['lich_su_cong_tac'].create({
                'nhan_vien_id': employee.id,
                'don_vi_id': department.id,
                'chuc_vu_id': position.id,
            })

        cls.director_hr = cls.director_nv.hr_employee_id
        cls.manager_hr = cls.manager_nv.hr_employee_id
        cls.staff_hr = cls.staff_nv.hr_employee_id

        Users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.manager_user = Users.create({
            'name': 'QA Manager User',
            'login': 'qa_manager_asset_user',
            'email': 'qa.manager.user@example.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.staff_user = Users.create({
            'name': 'QA Staff User',
            'login': 'qa_staff_asset_user',
            'email': 'qa.staff.user@example.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.manager_hr.user_id = cls.manager_user
        cls.staff_hr.user_id = cls.staff_user
        cls.manager_nv.user_id = cls.manager_user
        cls.staff_nv.user_id = cls.staff_user

    def _create_asset(self, suffix):
        return self.env['dnu.asset'].create({
            'name': f'QA Asset {suffix}',
            'category_id': self.category.id,
            'purchase_value': 1000,
        })

    def _complete_handover(self, handover, include_deliverer=True):
        signature = base64.b64encode(b'sig')
        values = {'receiver_signature': signature}
        if include_deliverer:
            values['deliverer_signature'] = signature
        handover.write(values)
        handover.action_complete()

    def test_assignment_handover_activates_asset(self):
        asset = self._create_asset('assignment')
        assignment = self.env['dnu.asset.assignment'].create({
            'asset_id': asset.id,
            'nhan_vien_id': self.staff_nv.id,
            'employee_id': self.staff_hr.id,
            'date_from': fields.Date.today(),
        })

        handover_action = assignment.action_create_handover()
        handover = self.env['dnu.asset.handover'].browse(handover_action['res_id'])
        self.assertEqual(handover.handover_type, 'assignment')
        self.assertEqual(handover.assignment_id, assignment)
        self.assertTrue(handover.name)

        self._complete_handover(handover)
        assignment.action_confirm()

        self.assertEqual(assignment.state, 'active')
        self.assertEqual(asset.state, 'assigned')
        self.assertEqual(asset.assigned_nhan_vien_id, self.staff_nv)

    def test_lending_request_uses_active_assignment_and_valid_handover_fields(self):
        asset = self._create_asset('lending')
        assignment = self.env['dnu.asset.assignment'].create({
            'asset_id': asset.id,
            'nhan_vien_id': self.manager_nv.id,
            'employee_id': self.manager_hr.id,
            'date_from': fields.Date.today(),
        })
        assignment.action_confirm()

        lending = self.env['dnu.asset.lending'].create({
            'asset_id': asset.id,
            'borrower_id': self.staff_hr.id,
            'nhan_vien_muon_id': self.staff_nv.id,
            'date_borrow': fields.Datetime.now(),
            'date_expected_return': fields.Datetime.now() + timedelta(days=1),
            'purpose': 'meeting',
        })

        lending.action_request()

        self.assertEqual(lending.assigned_person_id, self.manager_hr)
        self.assertEqual(lending.state, 'pending_approval')
        self.assertTrue(lending.handover_id)
        self.assertEqual(lending.handover_id.deliverer_id, self.manager_nv)
        self.assertEqual(lending.handover_id.nhan_vien_id, self.staff_nv)

    def test_lending_return_creates_maintenance_for_damaged_asset(self):
        asset = self._create_asset('return')
        lending = self.env['dnu.asset.lending'].create({
            'asset_id': asset.id,
            'borrower_id': self.staff_hr.id,
            'nhan_vien_muon_id': self.staff_nv.id,
            'date_borrow': fields.Datetime.now(),
            'date_expected_return': fields.Datetime.now() + timedelta(days=1),
            'purpose': 'meeting',
        })

        lending.action_create_handover()
        self._complete_handover(lending.handover_id)
        lending.action_approve()
        lending.action_lend()

        return_action = lending.action_create_return_handover()
        return_handover = self.env['dnu.asset.handover'].browse(return_action['res_id'])
        return_handover.write({
            'condition_return': 'damaged',
            'receiver_signature': base64.b64encode(b'sig'),
        })
        return_handover.action_complete()

        lending.write({
            'return_condition': 'damaged',
            'return_notes': 'Broken during use',
        })
        lending.action_return()

        maintenance = self.env['dnu.asset.maintenance'].search([
            ('lending_id', '=', lending.id),
        ], limit=1)
        self.assertEqual(lending.state, 'returned')
        self.assertTrue(lending.date_actual_return)
        self.assertTrue(maintenance)
        self.assertEqual(maintenance.state, 'pending')

    def test_booking_direct_approve_marks_document_and_conflict_blocks_overlap(self):
        room = self.env['dnu.meeting.room'].create({
            'name': 'QA Room Approval',
            'code': 'QA-ROOM-APPROVAL',
            'capacity': 10,
            'allow_booking': True,
            'state': 'available',
        })
        start = fields.Datetime.now() + timedelta(days=1)
        end = start + timedelta(hours=1)
        booking = self.env['dnu.meeting.booking'].create({
            'subject': 'QA booking approval',
            'room_id': room.id,
            'nhan_vien_to_chuc_id': self.manager_nv.id,
            'organizer_id': self.manager_hr.id,
            'start_datetime': start,
            'end_datetime': end,
            'meeting_type': 'offline',
            'num_attendees': 3,
        })

        with patch.object(type(booking), '_create_google_calendar_event', autospec=True, return_value=None), \
             patch.object(type(booking), '_send_confirmation_email', autospec=True, return_value=None), \
             patch.object(type(booking), '_send_notification_emails', autospec=True, return_value=None):
            booking.action_submit()
            approval_doc = self.env['van_ban_den'].search([
                ('source_model', '=', 'dnu.meeting.booking'),
                ('source_res_id', '=', booking.id),
                ('request_type', '=', 'booking_approval'),
            ], limit=1)
            booking.action_direct_approve()

        self.assertEqual(booking.state, 'confirmed')
        self.assertTrue(approval_doc)
        self.assertEqual(approval_doc.approval_state, 'approved')

        overlap = self.env['dnu.meeting.booking'].create({
            'subject': 'QA booking overlap',
            'room_id': room.id,
            'nhan_vien_to_chuc_id': self.staff_nv.id,
            'organizer_id': self.staff_hr.id,
            'start_datetime': start + timedelta(minutes=15),
            'end_datetime': end + timedelta(minutes=15),
            'meeting_type': 'offline',
            'num_attendees': 2,
        })
        with self.assertRaises(ValidationError):
            overlap.action_confirm()

    def test_booking_email_helper_forces_safe_sender(self):
        room = self.env['dnu.meeting.room'].create({
            'name': 'QA Room Mail',
            'code': 'QA-ROOM-MAIL',
            'capacity': 8,
            'allow_booking': True,
            'state': 'available',
        })
        booking = self.env['dnu.meeting.booking'].create({
            'subject': 'QA booking mail',
            'room_id': room.id,
            'nhan_vien_to_chuc_id': self.manager_nv.id,
            'organizer_id': self.manager_hr.id,
            'start_datetime': fields.Datetime.now() + timedelta(days=2),
            'end_datetime': fields.Datetime.now() + timedelta(days=2, hours=1),
            'meeting_type': 'offline',
            'num_attendees': 2,
        })
        template = self.env.ref('dnu_meeting_asset.email_template_booking_confirmation')

        with patch.object(type(template), 'send_mail', autospec=True, return_value=True) as mocked_send:
            booking._send_email_with_tracking(
                'dnu_meeting_asset.email_template_booking_confirmation',
                ['qa.receiver@example.com'],
                event_type='notification',
            )

        self.assertTrue(mocked_send.called)
        self.assertEqual(
            mocked_send.call_args.kwargs['email_values']['email_from'],
            'noreply@example.com',
        )

    def test_van_ban_booking_approval_runs_full_booking_confirmation(self):
        room = self.env['dnu.meeting.room'].create({
            'name': 'QA Room Van Ban',
            'code': 'QA-ROOM-VB',
            'capacity': 6,
            'allow_booking': True,
            'state': 'available',
        })
        booking = self.env['dnu.meeting.booking'].create({
            'subject': 'QA booking via van ban',
            'room_id': room.id,
            'nhan_vien_to_chuc_id': self.manager_nv.id,
            'organizer_id': self.manager_hr.id,
            'start_datetime': fields.Datetime.now() + timedelta(days=3),
            'end_datetime': fields.Datetime.now() + timedelta(days=3, hours=1),
            'meeting_type': 'offline',
            'num_attendees': 4,
        })

        booking.action_submit()
        approval_doc = self.env['van_ban_den'].search([
            ('source_model', '=', 'dnu.meeting.booking'),
            ('source_res_id', '=', booking.id),
            ('request_type', '=', 'booking_approval'),
        ], limit=1)
        self.assertTrue(approval_doc)

        with patch.object(type(booking), '_create_calendar_event', autospec=True, return_value=None) as calendar_mock, \
             patch.object(type(booking), '_create_google_calendar_event', autospec=True, return_value=None) as gcal_mock, \
             patch.object(type(booking), '_send_confirmation_email', autospec=True, return_value=None), \
             patch.object(type(booking), '_send_notification_emails', autospec=True, return_value=None):
            approval_doc.action_approve()

        booking.invalidate_cache()
        self.assertEqual(booking.state, 'confirmed')
        self.assertTrue(calendar_mock.called)
        self.assertTrue(gcal_mock.called)

    def test_pending_lending_manager_approval_works_without_handover_approve_api(self):
        asset = self._create_asset('pending-approval')
        assignment = self.env['dnu.asset.assignment'].create({
            'asset_id': asset.id,
            'nhan_vien_id': self.manager_nv.id,
            'employee_id': self.manager_hr.id,
            'date_from': fields.Date.today(),
        })
        assignment.action_confirm()

        lending = self.env['dnu.asset.lending'].create({
            'asset_id': asset.id,
            'borrower_id': self.staff_hr.id,
            'nhan_vien_muon_id': self.staff_nv.id,
            'date_borrow': fields.Datetime.now(),
            'date_expected_return': fields.Datetime.now() + timedelta(days=2),
            'purpose': 'meeting',
        })
        lending.action_request()
        self.assertEqual(lending.state, 'pending_approval')
        self.assertTrue(lending.handover_id)

        lending.with_user(self.manager_user).action_approve_lending()

        self.assertEqual(lending.state, 'approved')
        self.assertEqual(lending.approval_status, 'approved')
        self.assertEqual(lending.approved_by, self.manager_user)

    def test_hrm_links_are_strictly_one_to_one(self):
        extra_hr = self.env['hr.employee'].create({
            'name': 'QA Duplicate HR',
            'company_id': self.env.company.id,
        })
        with self.assertRaises(ValidationError):
            extra_hr.write({'nhan_vien_id': self.staff_nv.id})

        with self.assertRaises(ValidationError):
            self.env['nhan_vien'].create({
                'ma_dinh_danh': 'qa-staff-asset-duplicate-link',
                'ho_ten_dem': 'QA Duplicate',
                'ten': 'Link',
                'ngay_sinh': '1993-01-01',
                'hr_employee_id': self.staff_hr.id,
            })


def _prepare_standalone_data(env, token=None):
    token = token or uuid4().hex[:8]
    department = env['don_vi'].create({
        'ma_don_vi': f'QA-DV-STANDALONE-{token}',
        'ten_don_vi': f'QA Standalone Department {token}',
    })
    position = env['chuc_vu'].create({
        'ma_chuc_vu': f'QA-CV-STANDALONE-{token}',
        'ten_chuc_vu': f'QA Standalone Staff {token}',
    })
    category = env['dnu.asset.category'].create({'name': f'QA Standalone Category {token}'})

    manager_nv = env['nhan_vien'].create({
        'ma_dinh_danh': f'qa-standalone-manager-{token}',
        'ho_ten_dem': 'QA Standalone',
        'ten': f'Manager {token}',
        'ngay_sinh': '1991-01-01',
        'email': f'qa.standalone.manager.{token}@example.com',
    })
    staff_nv = env['nhan_vien'].create({
        'ma_dinh_danh': f'qa-standalone-staff-{token}',
        'ho_ten_dem': 'QA Standalone',
        'ten': f'Staff {token}',
        'ngay_sinh': '1992-01-01',
        'email': f'qa.standalone.staff.{token}@example.com',
    })

    for employee in (manager_nv, staff_nv):
        env['lich_su_cong_tac'].create({
            'nhan_vien_id': employee.id,
            'don_vi_id': department.id,
            'chuc_vu_id': position.id,
        })

    manager_hr = manager_nv.hr_employee_id
    staff_hr = staff_nv.hr_employee_id
    Users = env['res.users'].with_context(no_reset_password=True)
    manager_user = Users.create({
        'name': f'QA Standalone Manager User {token}',
        'login': f'qa_standalone_manager_user_{token}',
        'email': f'qa.standalone.manager.user.{token}@example.com',
        'groups_id': [(6, 0, [
            env.ref('base.group_user').id,
            env.ref('dnu_meeting_asset.group_asset_manager').id,
            env.ref('dnu_meeting_asset.group_meeting_manager').id,
        ])],
    })
    staff_user = Users.create({
        'name': f'QA Standalone Staff User {token}',
        'login': f'qa_standalone_staff_user_{token}',
        'email': f'qa.standalone.staff.user.{token}@example.com',
        'groups_id': [(6, 0, [env.ref('base.group_user').id])],
    })
    manager_hr.user_id = manager_user
    staff_hr.user_id = staff_user
    manager_nv.user_id = manager_user
    staff_nv.user_id = staff_user

    return {
        'department': department,
        'position': position,
        'category': category,
        'manager_nv': manager_nv,
        'staff_nv': staff_nv,
        'manager_hr': manager_hr,
        'staff_hr': staff_hr,
        'manager_user': manager_user,
        'staff_user': staff_user,
    }


@standalone('dnu_meeting_asset')
def standalone_hrm_links(env):
    data = _prepare_standalone_data(env)
    token = uuid4().hex[:8]
    extra_hr = env['hr.employee'].create({
        'name': f'QA Duplicate HR {token}',
        'company_id': env.company.id,
    })
    try:
        extra_hr.write({'nhan_vien_id': data['staff_nv'].id})
        raise AssertionError('duplicate hr_employee link should fail')
    except ValidationError:
        pass

    try:
        env['nhan_vien'].create({
            'ma_dinh_danh': f'qa-staff-standalone-duplicate-{token}',
            'ho_ten_dem': 'QA Duplicate',
            'ten': f'Link {token}',
            'ngay_sinh': '1993-01-01',
            'hr_employee_id': data['staff_hr'].id,
        })
        raise AssertionError('duplicate nhan_vien link should fail')
    except ValidationError:
        pass


@standalone('dnu_meeting_asset')
def standalone_booking_flow(env):
    data = _prepare_standalone_data(env)
    room = env['dnu.meeting.room'].create({
        'name': f'QA Standalone Room {uuid4().hex[:8]}',
        'code': f'QA-ROOM-STANDALONE-{uuid4().hex[:8]}',
        'capacity': 10,
        'allow_booking': True,
        'state': 'available',
    })
    start = fields.Datetime.now() + timedelta(days=1)
    booking = env['dnu.meeting.booking'].create({
        'subject': 'Standalone booking',
        'room_id': room.id,
        'nhan_vien_to_chuc_id': data['manager_nv'].id,
        'organizer_id': data['manager_hr'].id,
        'start_datetime': start,
        'end_datetime': start + timedelta(hours=1),
        'meeting_type': 'offline',
        'num_attendees': 4,
    })
    booking.action_submit()
    approval_doc = env['van_ban_den'].search([
        ('source_model', '=', 'dnu.meeting.booking'),
        ('source_res_id', '=', booking.id),
        ('request_type', '=', 'booking_approval'),
    ], limit=1)
    assert approval_doc, 'booking approval document not created'
    approval_doc.write({'signature': base64.b64encode(b'qa-standalone-signature')})
    approval_doc.action_approve()
    booking.invalidate_cache()
    assert booking.state == 'confirmed', booking.state


@standalone('dnu_meeting_asset')
def standalone_lending_flow(env):
    data = _prepare_standalone_data(env)
    asset = env['dnu.asset'].create({
        'name': f'QA Standalone Asset {uuid4().hex[:8]}',
        'category_id': data['category'].id,
        'purchase_value': 1000,
    })
    assignment = env['dnu.asset.assignment'].create({
        'asset_id': asset.id,
        'nhan_vien_id': data['manager_nv'].id,
        'employee_id': data['manager_hr'].id,
        'date_from': fields.Date.today(),
    })
    assignment.action_confirm()

    lending = env['dnu.asset.lending'].create({
        'asset_id': asset.id,
        'borrower_id': data['staff_hr'].id,
        'nhan_vien_muon_id': data['staff_nv'].id,
        'date_borrow': fields.Datetime.now(),
        'date_expected_return': fields.Datetime.now() + timedelta(days=1),
        'purpose': 'meeting',
    })
    lending.action_request()
    assert lending.state == 'pending_approval', lending.state
    lending.with_user(data['manager_user']).action_approve_lending()
    assert lending.state == 'approved', lending.state
