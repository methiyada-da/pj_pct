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


def _generate_promptpay_qr(promptpay_id, amount=0):
    """สร้าง PromptPay QR base64 สำหรับแสดงในหน้าเว็บ"""
    try:
        import qrcode
        from promptpay import qrcode as pp_qr
        payload = pp_qr.generate_payload(promptpay_id, amount=float(amount))
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

    refills_qs = Refill.objects.filter(member=member).order_by('-rf_date')
    refills = []
    
    for r in refills_qs:
        r.extracted_bank = ""
        r.display_cmt = r.rf_cmt if r.rf_cmt else ""

        # ถ้าในหมายเหตุมีคำว่า "โอนจาก:" ให้ตัดเอาเฉพาะชื่อธนาคารมา
        if r.rf_cmt and r.rf_cmt.startswith('โอนจาก:'):
            parts = r.rf_cmt.split('|')
            r.extracted_bank = parts[0].replace('โอนจาก:', '').strip()

            # ดึง admin note จาก part ที่ 3 (format: "โอนจาก:... | วันที่:... | หมายเหตุ: ...")
            admin_note = ''
            for p in parts[2:]:
                p = p.strip()
                if p.startswith('หมายเหตุ:'):
                    admin_note = p.replace('หมายเหตุ:', '', 1).strip()

            r.display_cmt = admin_note if r.rf_status == 2 else ""
        
        refills.append(r)

    withdrawals = Withdrawals.objects.filter(member=member).values(
        'wd_id', 'wd_req_date', 'wd_credit', 'wd_status', 'wd_bank_name'
    )

    tx_list = []
    for r in refills:
        tx_list.append({
            'type'  : 'topup',
            'title' : 'เติมเครดิต',
            'sub'   : 'ผ่าน Mobile Banking',
            'amount': r.rf_credit,
            'sign'  : '+',
            'date'  : r.rf_date,
            'status': r.rf_status,
        })
    for w in withdrawals:
        tx_list.append({
            'type'  : 'withdraw',
            'title' : 'ถอนเครดิต',
            'sub'   : f'ถอนเข้าบัญชี{w["wd_bank_name"]}',
            'amount': w['wd_credit'],
            'sign'  : '-',
            'date'  : w['wd_req_date'],
            'status': w['wd_status'],
        })

    tx_list.sort(key=lambda x: x['date'], reverse=True)

    paginator = Paginator(tx_list, 10)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    available = member.mb_deposit_crd + member.mb_income_crd - member.mb_locked_crd

    return render(request, 'credits/credit.html', {
        'member'   : member,
        'available': available,
        'page_obj' : page_obj,
        'system'   : system,
        'refills'  : refills,
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
    })