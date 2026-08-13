from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Member
from apps.admin_panel.models import System

from .models import Refill


class ResubmitTopupTests(TestCase):
    def setUp(self):
        self.enterContext(self.settings(MEDIA_ROOT=self.enterContext(TemporaryDirectory())))
        self.user = User.objects.create_user(
            username='member',
            email='member@rmuti.ac.th',
            password='test-password',
        )
        self.member = Member.objects.create(
            user=self.user,
            mb_full_name='สมาชิกทดสอบ',
            mb_email='member@rmuti.ac.th',
        )
        System.objects.create(
            uni_name='มหาวิทยาลัยทดสอบ',
            bank_name='ธนาคารทดสอบ',
            acc_name='บัญชีทดสอบ',
            acc_no='1234567890',
            crd_val=Decimal('10.00'),
            deposit_withdraw_fee_pct=Decimal('0.00'),
            income_withdraw_fee_pct=Decimal('0.00'),
        )
        self.refill = Refill.objects.create(
            rf_date=timezone.now(),
            rf_money=Decimal('100.00'),
            rf_credit=10,
            rf_bank_from='ธนาคารเดิม',
            rf_slip='Refill/test-slip.jpg',
            rf_qr_payload='unique-slip-payload',
            rf_confirm_date=timezone.now(),
            rf_status=2,
            rf_cmt='วันที่: 2026-08-14 10:30 | หมายเหตุ: จำนวนเงินไม่ตรง',
            member=self.member,
        )
        self.url = reverse('credits:resubmit_topup', args=[self.refill.pk])
        self.client.force_login(self.user)

    def test_rejected_refill_can_open_resubmit_page(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'แก้ไขคำขอเติมเครดิต')
        self.assertContains(response, 'ใช้สลิปเดิม')

    def test_resubmit_updates_same_refill_and_keeps_slip_identity(self):
        old_slip_name = self.refill.rf_slip.name
        old_qr_payload = self.refill.rf_qr_payload

        response = self.client.post(self.url, {
            'rf_money': '200.00',
            'bank_from': 'ธนาคารใหม่',
            'tx_date': '2026-08-14',
            'tx_time': '11:45',
        })

        self.assertRedirects(response, reverse('credits:credit'))
        self.refill.refresh_from_db()
        self.assertEqual(self.refill.rf_status, 0)
        self.assertEqual(self.refill.rf_money, Decimal('200.00'))
        self.assertEqual(self.refill.rf_credit, 20)
        self.assertEqual(self.refill.rf_bank_from, 'ธนาคารใหม่')
        self.assertEqual(self.refill.rf_slip.name, old_slip_name)
        self.assertEqual(self.refill.rf_qr_payload, old_qr_payload)
        self.assertIsNone(self.refill.rf_confirm_date)
        self.assertEqual(Refill.objects.count(), 1)

    def test_other_member_cannot_resubmit_refill(self):
        other_user = User.objects.create_user(
            username='other',
            email='other@rmuti.ac.th',
            password='test-password',
        )
        Member.objects.create(
            user=other_user,
            mb_full_name='สมาชิกคนอื่น',
            mb_email='other@rmuti.ac.th',
        )
        self.client.force_login(other_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    @patch('apps.credits.views._read_qr_from_slip')
    def test_resubmit_can_replace_slip(self, read_qr):
        read_qr.return_value = ('replacement-slip-payload', None)
        storage = self.refill.rf_slip.storage
        old_slip_name = storage.save(
            'Refill/old-slip.jpg',
            ContentFile(b'old-image-content'),
        )
        self.refill.rf_slip.name = old_slip_name
        self.refill.save(update_fields=['rf_slip'])
        replacement = SimpleUploadedFile(
            'replacement.jpg',
            b'replacement-image-content',
            content_type='image/jpeg',
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, {
                'rf_money': '100.00',
                'bank_from': 'ธนาคารเดิม',
                'tx_date': '2026-08-14',
                'tx_time': '12:00',
                'rf_slip': replacement,
            })

        self.assertRedirects(response, reverse('credits:credit'))
        self.refill.refresh_from_db()
        self.assertEqual(self.refill.rf_status, 0)
        self.assertEqual(self.refill.rf_qr_payload, 'replacement-slip-payload')
        self.assertRegex(
            self.refill.rf_slip.name,
            rf'^Refill/rf_id{self.refill.pk}_[0-9a-f]{{8}}\.jpg$',
        )
        self.assertTrue(storage.exists(self.refill.rf_slip.name))
        self.assertFalse(storage.exists(old_slip_name))

    @patch('apps.credits.views._read_qr_from_slip')
    def test_new_topup_uses_standard_storage_name(self, read_qr):
        read_qr.return_value = ('new-topup-payload', None)
        slip = SimpleUploadedFile(
            'bank-slip.png',
            b'new-image-content',
            content_type='image/png',
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('credits:topup'), {
                'rf_money': '100.00',
                'bank_from': 'กสิกรไทย (K-Bank)',
                'tx_date': '2026-08-14',
                'tx_time': '12:00',
                'rf_slip': slip,
            })

        self.assertRedirects(response, reverse('credits:credit'))
        refill = Refill.objects.get(rf_qr_payload='new-topup-payload')
        self.assertRegex(
            refill.rf_slip.name,
            rf'^Refill/rf_id{refill.pk}_[0-9a-f]{{8}}\.png$',
        )
        self.assertTrue(refill.rf_slip.storage.exists(refill.rf_slip.name))

    @patch('apps.credits.views._read_qr_from_slip')
    def test_resubmit_rejects_slip_used_by_another_refill(self, read_qr):
        read_qr.return_value = ('other-refill-payload', None)
        Refill.objects.create(
            rf_date=timezone.now(),
            rf_money=Decimal('50.00'),
            rf_credit=5,
            rf_bank_from='ธนาคารอื่น',
            rf_slip='Refill/other.jpg',
            rf_qr_payload='other-refill-payload',
            rf_status=1,
            member=self.member,
        )
        replacement = SimpleUploadedFile(
            'duplicate.jpg',
            b'duplicate-image-content',
            content_type='image/jpeg',
        )

        response = self.client.post(self.url, {
            'rf_money': '100.00',
            'bank_from': 'ธนาคารเดิม',
            'tx_date': '2026-08-14',
            'tx_time': '12:00',
            'rf_slip': replacement,
        })

        self.assertEqual(response.status_code, 200)
        self.refill.refresh_from_db()
        self.assertEqual(self.refill.rf_status, 2)
        self.assertEqual(self.refill.rf_qr_payload, 'unique-slip-payload')
        self.assertContains(response, 'สลิปนี้ถูกใช้กับคำขอเติมเครดิตรายการอื่นแล้ว')
