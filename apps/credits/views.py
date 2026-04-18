from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
import base64, io

from .models import Refill, Withdrawals
from apps.admin_panel.models import System


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
        extracted_bank = ''
        display_cmt    = ''
        if r.rf_cmt and r.rf_cmt.startswith('โอนจาก:'):
            parts = r.rf_cmt.split('|')
            extracted_bank = parts[0].replace('โอนจาก:', '').strip()
            for p in parts[2:]:
                p = p.strip()
                if p.startswith('หมายเหตุ:'):
                    display_cmt = p.replace('หมายเหตุ:', '', 1).strip()
            if r.rf_status != 2:
                display_cmt = ''
        elif r.rf_cmt and r.rf_status == 2:
            display_cmt = r.rf_cmt

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
        })

    tx_list.sort(key=lambda x: x['date'], reverse=True)

    kind_filter = request.GET.get('kind', '')
    if kind_filter in ('topup', 'withdraw', 'income'):
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
        if not slip:
            errors.append('กรุณาอัปโหลดสลิปการโอนเงิน')

        if not errors:
            rf_credit = round(rf_money_f / crd_val)
            cmt = f'โอนจาก: {bank_from} | วันที่: {tx_date} {tx_time}'
            Refill.objects.create(
                rf_date   = timezone.now(),
                rf_money  = rf_money_f,
                rf_credit = rf_credit,
                rf_slip   = slip,
                rf_status = 0,
                rf_cmt    = cmt,
                member    = member,
            )
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
def withdraw_view(request):
    member = request.user.member
    system = _get_system()
    crd_val = float(system.crd_val) if system and system.crd_val else 10.0

    # อัตราค่าธรรมเนียมตามประเภท (%)
    deposit_fee_pct = float(system.deposit_withdraw_fee_pct) if system else 0
    income_fee_pct  = float(system.income_withdraw_fee_pct)  if system else 0

    available_deposit = member.mb_deposit_crd - member.mb_locked_crd
    available_income  = member.mb_income_crd
    if available_deposit < 0:
        available_deposit = 0

    if request.method == 'POST':
        wd_type    = request.POST.get('wd_type', '0')
        wd_credit  = request.POST.get('wd_credit', '0').strip()
        bank_name  = request.POST.get('bank_name', '').strip()
        acc_name   = request.POST.get('acc_name', '').strip()
        acc_no     = request.POST.get('acc_no', '').strip()

        errors = []
        try:
            wd_type_i  = int(wd_type)
            wd_credit_i = int(wd_credit)
            if wd_credit_i <= 0:
                errors.append('กรุณากรอกจำนวนเครดิตที่ต้องการถอน')
        except (ValueError, TypeError):
            errors.append('จำนวนเครดิตไม่ถูกต้อง')
            wd_credit_i = 0
            wd_type_i = 0

        if not bank_name:
            errors.append('กรุณากรอกชื่อธนาคาร')
        if not acc_name:
            errors.append('กรุณากรอกชื่อบัญชีธนาคาร')
        if not acc_no:
            errors.append('กรุณากรอกเลขที่บัญชี')

        if not errors:
            avail = available_income if wd_type_i == 1 else available_deposit
            if wd_credit_i > avail:
                errors.append(f'เครดิตไม่เพียงพอ (มีอยู่ {avail} เครดิต)')

        if not errors:
            fee_pct  = income_fee_pct if wd_type_i == 1 else deposit_fee_pct
            wd_cash  = round(wd_credit_i * crd_val, 2)
            wd_fee   = round(wd_cash * fee_pct / 100, 2)
            wd_net   = round(wd_cash - wd_fee, 2)

            Withdrawals.objects.create(
                wd_req_date = timezone.now(),
                wd_type     = wd_type_i,
                wd_credit   = wd_credit_i,
                wd_cash     = wd_cash,
                wd_bank_name= bank_name,
                wd_acc_name = acc_name,
                wd_acc_no   = acc_no,
                wd_fee      = wd_fee,
                wd_net_cash = wd_net,
                wd_status   = 0,
                member      = member,
            )
            # หักเครดิตทันทีเมื่อส่งคำขอ
            if wd_type_i == 1:
                member.mb_income_crd  = max(0, member.mb_income_crd  - wd_credit_i)
            else:
                member.mb_deposit_crd = max(0, member.mb_deposit_crd - wd_credit_i)
            member.save(update_fields=['mb_income_crd', 'mb_deposit_crd'])
            messages.success(request, 'ส่งคำขอถอนเครดิตเรียบร้อยแล้ว ระบบจะดำเนินการภายใน 3-5 วันทำการ')
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