# credits/views.py - views จัดการเครดิต เติม และถอนเงิน
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum
from django.views.decorators.http import require_POST
import base64, io
from datetime import datetime
from pathlib import PurePath
from uuid import uuid4

from .models import Refill, Withdrawals
from apps.accounts.models import Member
from apps.admin_panel.models import System
from apps.bookings.models import Booking, JobCompletion

# --- สำหรับอ่าน QR Code ---
import cv2
import numpy as np
from PIL import Image


def _read_qr_from_slip(slip):
    """อ่าน QR จากไฟล์สลิปและคืนค่า payload พร้อมข้อความผิดพลาด"""
    try:
        image = Image.open(slip)
        if image.format not in ('PNG', 'JPEG'):
            return None, 'รองรับสลิปเฉพาะไฟล์ PNG หรือ JPG เท่านั้น'
        if image.mode != 'RGB':
            image = image.convert('RGB')

        image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        payload, _, _ = cv2.QRCodeDetector().detectAndDecode(image_cv)
        if not payload:
            try:
                results, _ = cv2.wechat_qrcode_WeChatQRCode().detectAndDecode(image_cv)
                payload = results[0] if results else None
            except Exception:
                payload = None

        if not payload:
            return None, 'ไม่พบ QR Code กรุณาใช้รูปสลิปต้นฉบับจากแอปธนาคารที่เห็น QR Code ชัดเจน'
        return payload, None
    except Exception:
        return None, 'เกิดข้อผิดพลาดในการตรวจสอบไฟล์รูปภาพ กรุณาลองใหม่อีกครั้ง'
    finally:
        slip.seek(0)


def _standard_slip_name(refill_id, original_name):
    """สร้างชื่อสลิปที่ผูกกับ RF และไม่ชนกับไฟล์เดิม"""
    extension = PurePath(original_name or '').suffix.lower()
    if extension not in ('.jpg', '.jpeg', '.png'):
        extension = '.jpg'
    return f'Refill/rf_id{refill_id}_{uuid4().hex[:8]}{extension}'


def _standardize_saved_slip(refill):
    """ย้ายสลิปที่บันทึกแล้วไปยังชื่อมาตรฐานผ่าน Django Storage API"""
    old_name = refill.rf_slip.name
    if not old_name:
        return

    storage = refill.rf_slip.storage
    new_name = _standard_slip_name(refill.pk, old_name)
    with storage.open(old_name, 'rb') as source:
        saved_name = storage.save(new_name, source)

    try:
        Refill.objects.filter(pk=refill.pk).update(rf_slip=saved_name)
        refill.rf_slip.name = saved_name
    except Exception:
        storage.delete(saved_name)
        raise

    transaction.on_commit(lambda: storage.delete(old_name))


@login_required
def promptpay_qr(request):
    amount = request.GET.get('amount', '0')
    system = _get_system()
    if not system or not system.promptpay_id:
        return JsonResponse({'qr': None})
    try:
        qr = _generate_promptpay_qr(system.promptpay_id, amount=float(amount))
        return JsonResponse({'qr': qr})
    except Exception:
        return JsonResponse({'qr': None})


def _get_system():
    return System.objects.first()


def _get_withdrawable_balances(member):
    """คำนวณยอดถอนแยกประเภทจากคำขอที่ยังรอดำเนินการ โดยไม่เพิ่มฟิลด์ใน Member"""
    pending = {
        row['wd_type']: row['total'] or 0
        for row in Withdrawals.objects.filter(
            member=member,
            wd_status=0,
        ).values('wd_type').annotate(total=Sum('wd_credit'))
    }
    pending_deposit = pending.get(0, 0)
    pending_income = pending.get(1, 0)

    # mb_locked_crd รวมทั้งยอดจองเรียนและคำขอถอนที่รอจ่าย
    pending_withdraw = pending_deposit + pending_income
    booking_locked = max(0, member.mb_locked_crd - pending_withdraw)
    booking_locked_deposit = min(member.mb_deposit_crd, booking_locked)
    booking_locked_income = max(0, booking_locked - booking_locked_deposit)

    return {
        'deposit': max(
            0,
            member.mb_deposit_crd - booking_locked_deposit - pending_deposit,
        ),
        'income': max(
            0,
            member.mb_income_crd - booking_locked_income - pending_income,
        ),
        'pending_deposit': pending_deposit,
        'pending_income': pending_income,
    }


def _promptpay_payload(target: str, amount: float = 0) -> str:
    """สร้าง EMV QR payload ของ PromptPay โดยไม่ใช้ library ภายนอก"""
    import re

    # แปลงเบอร์โทร 0XXXXXXXXX → 0066XXXXXXXXX
    if re.match(r'^0\d{9}$', target):
        target = '0066' + target[1:]

    def tlv(tag: int, val: str) -> str:
        return f"{tag:02d}{len(val):02d}{val}"

    merchant_info = tlv(0, 'A000000677010111') + tlv(1, target)

    parts = (
        tlv(0, '01')
        + tlv(1, '12' if amount else '11')
        + tlv(29, merchant_info)
        + tlv(53, '764')
    )
    if amount:
        parts += tlv(54, f"{amount:.2f}")
    parts += tlv(58, 'TH') + '6304'

    # CRC-16/CCITT-FALSE
    crc = 0xFFFF
    for b in parts.encode('ascii'):
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF

    return parts + f"{crc:04X}"


def _generate_promptpay_qr(promptpay_id, amount=0):
    """สร้าง PromptPay QR base64 สำหรับแสดงในหน้าเว็บ"""
    try:
        import qrcode
        payload = _promptpay_payload(promptpay_id, amount=float(amount))
        img = qrcode.make(payload)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


@login_required
def credit_view(request):
    member = request.user.member
    system = _get_system()

    tx_list = []

    for r in Refill.objects.filter(member=member).order_by('-rf_date'):
        extracted_bank = r.rf_bank_from or ''
        display_cmt    = ''
        if r.rf_cmt:
            parts = r.rf_cmt.split('|')
            # รองรับข้อมูลเดิมที่ยังเก็บธนาคารไว้ในหมายเหตุ
            if not extracted_bank and r.rf_cmt.startswith('โอนจาก:'):
                extracted_bank = parts[0].replace('โอนจาก:', '').strip()
            for p in parts:
                p = p.strip()
                if p.startswith('หมายเหตุ:'):
                    display_cmt = p.replace('หมายเหตุ:', '', 1).strip()
            if r.rf_status == 2 and not display_cmt and not (
                r.rf_cmt.startswith('โอนจาก:') or r.rf_cmt.startswith('วันที่:')
            ):
                display_cmt = r.rf_cmt
            if r.rf_status != 2:
                display_cmt = ''

        tx_list.append({
            'kind'          : 'topup',
            'rf_id'         : r.rf_id,
            'amount'        : r.rf_credit,
            'money'         : r.rf_money,
            'date'          : r.rf_date,
            'status'        : r.rf_status,
            'slip_url'      : r.rf_slip.url if r.rf_slip else '',
            'extracted_bank': extracted_bank,
            'display_cmt'   : display_cmt,
        })

    for w in Withdrawals.objects.filter(member=member).order_by('-wd_req_date'):
        tx_list.append({
            'kind'      : 'withdraw',
            'wd_id'     : w.wd_id,
            'amount'    : w.wd_credit,
            'net_cash'  : w.wd_net_cash,
            'bank_name' : w.wd_bank_name,
            'date'      : w.wd_req_date,
            'status'    : w.wd_status,
            'wd_cmt'    : w.wd_cmt or '',
            'can_cancel': w.wd_status == 0,
        })

    # การจองที่เสร็จสิ้นแล้ว — ฝั่งผู้เรียน (จ่ายค่าเรียน)
    paid_bookings = (
        Booking.objects
        .filter(member=member, bk_status__in=(4, 5))
        .select_related('tutc_id__crs_id', 'tutc_id__tut_id__tut_id', 'jobcompletion')
    )
    for bk in paid_bookings:
        try:
            confirm_date = bk.jobcompletion.jc_confirm_date or bk.jobcompletion.jc_complete_date
        except JobCompletion.DoesNotExist:
            confirm_date = bk.bk_date
        tx_list.append({
            'kind'        : 'booking_pay',
            'bk_id'       : bk.bk_id,
            'amount'      : bk.total_credit,
            'crs_name'    : bk.tutc_id.crs_id.crs_name,
            'tutor_name'  : bk.tutc_id.tut_id.tut_id.mb_full_name,
            'rate'        : bk.bk_rate_per_person,
            'stu_count'   : bk.bk_stu_count,
            'date'        : confirm_date,
        })

    # การจองที่เสร็จสิ้นแล้ว — ฝั่งติวเตอร์ (รายได้)
    try:
        tutor = member.tutor
        income_bookings = (
            Booking.objects
            .filter(tutc_id__tut_id=tutor, bk_status__in=(4, 5))
            .select_related('tutc_id__crs_id', 'member', 'jobcompletion')
        )
        for bk in income_bookings:
            try:
                confirm_date = bk.jobcompletion.jc_confirm_date or bk.jobcompletion.jc_complete_date
            except JobCompletion.DoesNotExist:
                confirm_date = bk.bk_date
            tx_list.append({
                'kind'         : 'booking_income',
                'bk_id'        : bk.bk_id,
                'amount'       : bk.total_credit,
                'crs_name'     : bk.tutc_id.crs_id.crs_name,
                'student_name' : bk.member.mb_full_name,
                'rate'         : bk.bk_rate_per_person,
                'stu_count'    : bk.bk_stu_count,
                'date'         : confirm_date,
            })
    except Exception:
        pass

    tx_list.sort(key=lambda x: x['date'], reverse=True)

    kind_filter = request.GET.get('kind', '')
    if kind_filter in ('topup', 'withdraw', 'booking_pay', 'booking_income'):
        tx_list = [t for t in tx_list if t['kind'] == kind_filter]

    paginator = Paginator(tx_list, 15)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    available = member.mb_deposit_crd + member.mb_income_crd - member.mb_locked_crd

    return render(request, 'credits/credit.html', {
        'member'      : member,
        'available'   : available,
        'page_obj'    : page_obj,
        'system'      : system,
        'kind_filter' : kind_filter,
    })


@login_required
@require_POST
def cancel_withdraw_view(request, wd_id):
    member = request.user.member

    with transaction.atomic():
        wd = get_object_or_404(
            Withdrawals.objects.select_for_update().select_related('member'),
            pk=wd_id,
            member=member,
        )

        if wd.wd_status != 0:
            messages.warning(request, 'คำขอถอนเครดิตนี้ไม่สามารถยกเลิกได้แล้ว')
            return redirect('credits:credit')

        wd.wd_status = 3
        wd.wd_cmt = 'ผู้ใช้ยกเลิกคำขอถอนเครดิต'
        wd.save(update_fields=['wd_status', 'wd_cmt'])

        locked_member = Member.objects.select_for_update().get(pk=member.pk)
        locked_member.mb_locked_crd = max(
            0,
            locked_member.mb_locked_crd - wd.wd_credit,
        )
        locked_member.save(update_fields=['mb_locked_crd'])

    messages.success(request, f'ยกเลิกคำขอถอน WD{wd.wd_id:05d} แล้ว ระบบคืนเครดิต {wd.wd_credit} เครดิตให้เรียบร้อย')
    return redirect('credits:credit')


BANK_CHOICES = [
    ('กสิกรไทย (K-Bank)',    'กสิกรไทย (K-Bank)'),
    ('ไทยพาณิชย์ (SCB)',     'ไทยพาณิชย์ (SCB)'),
    ('กรุงเทพ (BBL)',        'กรุงเทพ (BBL)'),
    ('กรุงไทย (KTB)',        'กรุงไทย (KTB)'),
    ('กรุงศรีอยุธยา (BAY)', 'กรุงศรีอยุธยา (BAY)'),
    ('ทหารไทยธนชาต (TTB)',   'ทหารไทยธนชาต (TTB)'),
    ('ออมสิน (GSB)',         'ออมสิน (GSB)'),
    ('ธ.ก.ส. (BAAC)',       'ธ.ก.ส. (BAAC)'),
    ('อื่นๆ',               'อื่นๆ'),
]


@login_required
def topup_view(request):
    member = request.user.member
    system = _get_system()
    # อัตราแลก: crd_val บาท = 1 เครดิต (default 10)
    crd_val = float(system.crd_val) if system and system.crd_val else 10.0

    if request.method == 'POST':
        rf_money  = request.POST.get('rf_money', '0').strip()
        bank_from = request.POST.get('bank_from', '')
        tx_date   = request.POST.get('tx_date', '')
        tx_time   = request.POST.get('tx_time', '')
        slip      = request.FILES.get('rf_slip')

        errors = []
        qr_payload = None

        try:
            rf_money_f = float(rf_money)
            if rf_money_f <= 0:
                errors.append('กรุณากรอกจำนวนเครดิตที่ต้องการ')
        except ValueError:
            errors.append('จำนวนเครดิตไม่ถูกต้อง')
            rf_money_f = 0

        if not bank_from:
            errors.append('กรุณาเลือกธนาคาร')
        if not tx_date:
            errors.append('กรุณากรอกวันที่โอน')
        if not tx_time:
            errors.append('กรุณากรอกเวลาโอน')

        if tx_date and tx_time:
            try:
                transfer_datetime = timezone.make_aware(
                    datetime.strptime(f'{tx_date} {tx_time}', '%Y-%m-%d %H:%M')
                )
                if transfer_datetime > timezone.now():
                    errors.append('วันที่และเวลาโอนต้องไม่เกินเวลาปัจจุบัน')
            except ValueError:
                errors.append('วันที่หรือเวลาโอนไม่ถูกต้อง')
            
        if not slip:
            errors.append('กรุณาอัปโหลดสลิปการโอนเงิน')
        else:
            qr_payload, slip_error = _read_qr_from_slip(slip)
            if slip_error:
                errors.append(slip_error)

            # ตรวจสอบการใช้งานซ้ำใน Database
            if qr_payload:
                if Refill.objects.filter(rf_qr_payload=qr_payload).exists():
                    errors.append('สลิปนี้ถูกใช้งานเติมเครดิตในระบบไปแล้ว ไม่สามารถใช้ซ้ำได้')

        if not errors:
            rf_credit = round(rf_money_f / crd_val)
            cmt = f'วันที่: {tx_date} {tx_time}'

            with transaction.atomic():
                # สร้างรายการก่อนเพื่อให้ได้ rf_id แล้วจัดชื่อไฟล์ผ่าน storage
                refill = Refill.objects.create(
                    rf_date       = timezone.now(),
                    rf_money      = rf_money_f,
                    rf_credit     = rf_credit,
                    rf_bank_from  = bank_from,
                    rf_slip       = slip,
                    rf_qr_payload = qr_payload,
                    rf_status     = 0,
                    rf_cmt        = cmt,
                    member        = member,
                )
                _standardize_saved_slip(refill)

            messages.success(request, 'ส่งคำขอเติมเครดิตเรียบร้อยแล้ว กรุณารอการตรวจสอบ 15-30 นาที')
            return redirect('credits:credit')

        for err in errors:
            messages.error(request, err)

        # ส่งข้อมูลที่กรอกไปแล้วกลับมาด้วย
        qr_img = None
        if system and system.promptpay_id:
            qr_img = _generate_promptpay_qr(system.promptpay_id, amount=0)
        return render(request, 'credits/topup.html', {
            'member'      : member,
            'system'      : system,
            'bank_choices': BANK_CHOICES,
            'crd_val'     : crd_val,
            'qr_img'      : qr_img,
            'promptpay_id': system.promptpay_id if system and system.promptpay_id else '',
            'prev'        : request.POST,
        })

    qr_img = None
    if system and system.promptpay_id:
        qr_img = _generate_promptpay_qr(system.promptpay_id, amount=0)

    available = member.mb_deposit_crd + member.mb_income_crd - member.mb_locked_crd

    return render(request, 'credits/topup.html', {
        'member'      : member,
        'system'      : system,
        'bank_choices': BANK_CHOICES,
        'crd_val'     : crd_val,
        'qr_img'      : qr_img,
        'promptpay_id': system.promptpay_id if system and system.promptpay_id else '',
        'available'   : available,
        'prev'        : {},
    })


@login_required
def resubmit_topup_view(request, rf_id):
    """แก้ไขและส่งคำขอเติมเครดิตที่ถูกปฏิเสธกลับเข้าคิวตรวจสอบ"""
    member = request.user.member
    system = _get_system()
    crd_val = float(system.crd_val) if system and system.crd_val else 10.0
    refill = get_object_or_404(Refill, pk=rf_id, member=member)

    if refill.rf_status != 2:
        messages.warning(request, 'ส่งคำขอใหม่ได้เฉพาะรายการเติมเครดิตที่ถูกปฏิเสธเท่านั้น')
        return redirect('credits:credit')

    tx_date = ''
    tx_time = ''
    if refill.rf_cmt:
        import re
        tx_match = re.search(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})', refill.rf_cmt)
        if tx_match:
            tx_date, tx_time = tx_match.groups()

    prev = {
        'bank_from': refill.rf_bank_from or '',
        'rfCredits': refill.rf_credit,
        'tx_date': tx_date,
        'tx_time': tx_time,
    }

    if request.method == 'POST':
        rf_money = request.POST.get('rf_money', '0').strip()
        bank_from = request.POST.get('bank_from', '').strip()
        tx_date = request.POST.get('tx_date', '').strip()
        tx_time = request.POST.get('tx_time', '').strip()
        replacement_slip = request.FILES.get('rf_slip')
        replacement_qr_payload = None
        errors = []

        try:
            rf_money_f = float(rf_money)
            if rf_money_f <= 0:
                errors.append('กรุณากรอกจำนวนเครดิตที่ต้องการ')
        except (TypeError, ValueError):
            rf_money_f = 0
            errors.append('จำนวนเงินไม่ถูกต้อง')

        if not bank_from:
            errors.append('กรุณาเลือกธนาคารที่โอน')
        if not tx_date:
            errors.append('กรุณากรอกวันที่โอน')
        if not tx_time:
            errors.append('กรุณากรอกเวลาโอน')

        if replacement_slip:
            replacement_qr_payload, slip_error = _read_qr_from_slip(replacement_slip)
            if slip_error:
                errors.append(slip_error)
            elif Refill.objects.filter(
                rf_qr_payload=replacement_qr_payload,
            ).exclude(pk=refill.pk).exists():
                errors.append('สลิปนี้ถูกใช้กับคำขอเติมเครดิตรายการอื่นแล้ว ไม่สามารถใช้ซ้ำได้')

        if not errors:
            with transaction.atomic():
                locked_refill = get_object_or_404(
                    Refill.objects.select_for_update(),
                    pk=rf_id,
                    member=member,
                )
                if locked_refill.rf_status != 2:
                    messages.warning(request, 'สถานะรายการนี้เปลี่ยนแปลงแล้ว ไม่สามารถส่งคำขอซ้ำได้')
                    return redirect('credits:credit')

                locked_refill.rf_money = rf_money_f
                locked_refill.rf_credit = round(rf_money_f / crd_val)
                locked_refill.rf_bank_from = bank_from
                locked_refill.rf_date = timezone.now()
                locked_refill.rf_confirm_date = None
                locked_refill.rf_status = 0
                locked_refill.rf_cmt = f'วันที่: {tx_date} {tx_time}'
                update_fields = [
                    'rf_money', 'rf_credit', 'rf_bank_from', 'rf_date',
                    'rf_confirm_date', 'rf_status', 'rf_cmt',
                ]
                if replacement_slip:
                    old_slip_name = locked_refill.rf_slip.name
                    storage = locked_refill.rf_slip.storage
                    new_slip_name = storage.save(
                        _standard_slip_name(locked_refill.pk, replacement_slip.name),
                        replacement_slip,
                    )
                    locked_refill.rf_slip.name = new_slip_name
                    locked_refill.rf_qr_payload = replacement_qr_payload
                    update_fields.extend(['rf_slip', 'rf_qr_payload'])
                try:
                    locked_refill.save(update_fields=update_fields)
                except Exception:
                    if replacement_slip:
                        storage.delete(new_slip_name)
                    raise
                if replacement_slip and old_slip_name != new_slip_name:
                    transaction.on_commit(lambda: storage.delete(old_slip_name))

            messages.success(
                request,
                f'ส่งคำขอเติมเครดิต RF{refill.rf_id:05d} ใหม่เรียบร้อยแล้ว กรุณารอแอดมินตรวจสอบ',
            )
            return redirect('credits:credit')

        for error in errors:
            messages.error(request, error)
        prev = request.POST

    qr_img = None
    if system and system.promptpay_id:
        qr_img = _generate_promptpay_qr(system.promptpay_id, amount=0)

    available = member.mb_deposit_crd + member.mb_income_crd - member.mb_locked_crd
    return render(request, 'credits/topup.html', {
        'member': member,
        'system': system,
        'bank_choices': BANK_CHOICES,
        'crd_val': crd_val,
        'qr_img': qr_img,
        'promptpay_id': system.promptpay_id if system and system.promptpay_id else '',
        'available': available,
        'prev': prev,
        'resubmit_refill': refill,
    })


@login_required
def withdraw_view(request):
    member = request.user.member
    system = _get_system()
    crd_val = float(system.crd_val) if system and system.crd_val else 10.0

    # อัตราค่าธรรมเนียมตามประเภท (%)
    deposit_fee_pct = float(system.deposit_withdraw_fee_pct) if system else 0
    income_fee_pct  = float(system.income_withdraw_fee_pct)  if system else 0

    balances = _get_withdrawable_balances(member)
    available_deposit = balances['deposit']
    available_income = balances['income']

    if request.method == 'POST':
        wd_type      = request.POST.get('wd_type', '0')
        wd_credit    = request.POST.get('wd_credit', '0').strip()
        bank_name    = request.POST.get('bank_name', '').strip()
        acc_name     = request.POST.get('acc_name', '').strip()
        acc_no       = request.POST.get('acc_no', '').strip()
        promptpay_no = request.POST.get('promptpay_no', '').strip()

        errors = []
        try:
            wd_type_i  = int(wd_type)
            wd_credit_i = int(wd_credit)
            if wd_type_i not in (0, 1):
                errors.append('ประเภทเครดิตที่ถอนไม่ถูกต้อง')
            if wd_credit_i <= 0:
                errors.append('กรุณากรอกจำนวนเครดิตที่ต้องการถอน')
        except (ValueError, TypeError):
            errors.append('จำนวนเครดิตไม่ถูกต้อง')
            wd_credit_i = 0
            wd_type_i = 0

        if not bank_name:
            errors.append('กรุณาเลือกธนาคาร')
        if not acc_name:
            errors.append('กรุณากรอกชื่อบัญชีธนาคาร')
        if not acc_no:
            errors.append('กรุณากรอกเลขที่บัญชี')
        elif len(acc_no) > 20:
            errors.append('เลขที่บัญชีต้องไม่เกิน 20 ตัวอักษร กรุณาตรวจสอบอีกครั้ง')
            
        if not promptpay_no:
            errors.append('กรุณากรอกหมายเลขพร้อมเพย์')
        elif len(promptpay_no) > 20:
            errors.append('หมายเลขพร้อมเพย์ต้องไม่เกิน 20 ตัวอักษร กรุณาตรวจสอบอีกครั้ง')

        if not errors:
            fee_pct  = income_fee_pct if wd_type_i == 1 else deposit_fee_pct
            wd_cash  = round(wd_credit_i * crd_val, 2)
            wd_fee   = round(wd_cash * fee_pct / 100, 2)
            wd_net   = round(wd_cash - wd_fee, 2)

            with transaction.atomic():
                locked_member = Member.objects.select_for_update().get(pk=member.pk)
                balances = _get_withdrawable_balances(locked_member)
                available = balances['income'] if wd_type_i == 1 else balances['deposit']
                if wd_credit_i > available:
                    errors.append(f'เครดิตไม่เพียงพอ (มีอยู่ {available} เครดิต)')
                else:
                    Withdrawals.objects.create(
                        wd_req_date     = timezone.now(),
                        wd_type         = wd_type_i,
                        wd_credit       = wd_credit_i,
                        wd_cash         = wd_cash,
                        wd_bank_name    = bank_name,
                        wd_acc_name     = acc_name,
                        wd_acc_no       = acc_no,
                        wd_promptpay_no = promptpay_no,
                        wd_fee          = wd_fee,
                        wd_net_cash     = wd_net,
                        wd_status       = 0,
                        member          = locked_member,
                    )
                    # ล็อกเครดิตรวมไว้ในฟิลด์เดิมเพื่อรองรับโครงสร้างปัจจุบัน
                    locked_member.mb_locked_crd += wd_credit_i
                    locked_member.save(update_fields=['mb_locked_crd'])

            if errors:
                for err in errors:
                    messages.error(request, err)
                return render(request, 'credits/withdraw.html', {
                    'member'           : member,
                    'system'           : system,
                    'crd_val'          : crd_val,
                    'bank_choices'     : BANK_CHOICES,
                    'available_deposit': available_deposit,
                    'available_income' : available_income,
                    'deposit_fee_pct'  : deposit_fee_pct,
                    'income_fee_pct'   : income_fee_pct,
                    'prev'             : request.POST,
                })
            
            messages.success(request, 'ส่งคำขอถอนเครดิตเรียบร้อยแล้ว ระบบจะดำเนินการภายใน 3-5 วันทำการ (เครดิตของคุณจะถูกล็อกไว้จนกว่าแอดมินจะอนุมัติ)')
            return redirect('credits:credit')

        for err in errors:
            messages.error(request, err)

        return render(request, 'credits/withdraw.html', {
            'member'           : member,
            'system'           : system,
            'crd_val'          : crd_val,
            'bank_choices'     : BANK_CHOICES,
            'available_deposit': available_deposit,
            'available_income' : available_income,
            'deposit_fee_pct'  : deposit_fee_pct,
            'income_fee_pct'   : income_fee_pct,
            'prev'             : request.POST,
        })

    return render(request, 'credits/withdraw.html', {
        'member'           : member,
        'system'           : system,
        'crd_val'          : crd_val,
        'bank_choices'     : BANK_CHOICES,
        'available_deposit': available_deposit,
        'available_income' : available_income,
        'deposit_fee_pct'  : deposit_fee_pct,
        'income_fee_pct'   : income_fee_pct,
        'prev'             : {},
    })
