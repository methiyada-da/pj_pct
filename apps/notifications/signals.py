from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from apps.accounts.models import Tutor
from apps.bookings.models import Booking
from apps.credits.models import Refill, Withdrawals
from .models import Notification


# ─────────────────────────────────────────
# Helper: ดึง Admin User จาก System config
# ─────────────────────────────────────────
def _get_admin_user():
    """ดึง admin user จาก System (ถ้าไม่มีคืน None)"""
    try:
        from apps.admin_panel.models import System
        system = System.objects.select_related('admin').first()
        return system.admin if system else None
    except Exception:
        return None


def _notif_member(member, notif_type, text, url=''):
    """สร้าง Notification ให้ Member"""
    Notification.objects.create(
        recipient=member,
        notif_type=notif_type,
        notif_text=text,
        notif_url=url,
    )


def _notif_admin(notif_type, text, url=''):
    """สร้าง Notification ให้ Admin"""
    admin = _get_admin_user()
    if not admin:
        return
    Notification.objects.create(
        admin_recipient=admin,
        notif_type=notif_type,
        notif_text=text,
        notif_url=url,
    )


# ─────────────────────────────────────────
# Signal: Booking
# ─────────────────────────────────────────
@receiver(pre_save, sender=Booking)
def booking_pre_save(sender, instance, **kwargs):
    """เก็บ status เดิมไว้เปรียบเทียบใน post_save"""
    if instance.pk:
        try:
            old = Booking.objects.get(pk=instance.pk)
            instance._old_status      = old.bk_status
            instance._old_report_date = old.bk_report_date
        except Booking.DoesNotExist:
            instance._old_status      = None
            instance._old_report_date = None
    else:
        instance._old_status      = None
        instance._old_report_date = None


@receiver(post_save, sender=Booking)
def booking_post_save(sender, instance, created, **kwargs):
    old = getattr(instance, '_old_status', None)
    new = instance.bk_status

    # ดึง tutor member: TutorCourse.tut_id → Tutor → tut_id = Member (OneToOne)
    tutor_member = instance.tutc_id.tut_id.tut_id

    if created and new == 0:
        # จองใหม่ → แจ้ง Tutor ให้ไปดูรายการคำขอ
        course_name = instance.tutc_id.tutc_name
        _notif_member(
            tutor_member,
            'booking_new',
            f'มีการจองติว "{course_name}" ใหม่',
            f'/bookings/tutor/',
        )

    elif old != new:
        member = instance.member

        if new == 1:
            # รับงานแล้ว → แจ้ง Member ให้ไปดูการจองของตัวเอง
            _notif_member(member, 'booking_accepted', 'ติวเตอร์ยืนยันรับการจองของคุณแล้ว', f'/bookings/my/')

        elif new == 3:
            # แจ้งจบงาน → แจ้ง Member ให้กดยืนยันจบงาน
            _notif_member(member, 'booking_completed', 'ติวเตอร์แจ้งจบงาน กรุณายืนยันการเรียน', f'/bookings/my/{instance.pk}/confirm-completion/')

        elif new == 4:
            # ยืนยันจบงาน → แจ้ง Tutor
            _notif_member(tutor_member, 'booking_credited', 'งานเสร็จสิ้น คุณได้รับเครดิตจากการสอนแล้ว', f'/bookings/tutor/')

        elif new == 5:
            # รีวิวแล้ว → แจ้ง Tutor
            _notif_member(tutor_member, 'booking_reviewed', 'มีรีวิวใหม่จากผู้เรียน', f'/bookings/tutor/')

        elif new == 6:
            # ปฏิเสธ → แจ้ง Member
            _notif_member(member, 'booking_rejected', 'ติวเตอร์ปฏิเสธการจองของคุณ', f'/bookings/my/')

    # รายงานปัญหา → แจ้ง Admin + ติวเตอร์
    old_report = getattr(instance, '_old_report_date', None)
    if instance.bk_report_date and not old_report:
        _notif_admin(
            'admin_reported',
            f'มีการรายงานปัญหาจากการจอง BK{instance.pk:05d}',
            f'/panel/report-mgmt/',
        )
        # แจ้งติวเตอร์ว่าผู้เรียนรายงานปัญหา
        _notif_member(
            tutor_member,
            'booking_reported',
            f'ผู้เรียนได้รายงานปัญหาการจอง BK{instance.pk:05d} ไปยังแอดมินแล้ว โปรดรอผลการพิจารณา',
            f'/bookings/tutor/',
        )


# ─────────────────────────────────────────
# Signal: Tutor
# ─────────────────────────────────────────
@receiver(pre_save, sender=Tutor)
def tutor_pre_save(sender, instance, **kwargs):
    """เก็บ status เดิม"""
    if instance.pk:
        try:
            instance._old_status = Tutor.objects.get(pk=instance.pk).tut_status
        except Tutor.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Tutor)
def tutor_post_save(sender, instance, created, **kwargs):
    old    = getattr(instance, '_old_status', None)
    new    = instance.tut_status
    member = instance.tut_id  # tut_id = OneToOne กับ Member

    if (created or old != new) and new == 0:
        # สมัครใหม่ หรือ ส่งคำขออีกครั้งหลังถูกปฏิเสธ → แจ้ง Admin
        _notif_admin(
            'admin_tutor_new',
            f'มีติวเตอร์สมัครใหม่รอการอนุมัติ: {member.mb_full_name}',
            '/panel/tutor-mgmt/',
        )

    elif old != new:
        if new == 1:
            _notif_member(member, 'tutor_approved', 'ยินดีด้วย! บัญชีติวเตอร์ของคุณได้รับการอนุมัติแล้ว', '/tutoring/manage/')
        elif new == 2:
            _notif_member(member, 'tutor_rejected', 'บัญชีติวเตอร์ของคุณไม่ผ่านการอนุมัติ', '/tutoring/register/')
        elif new == 3:
            _notif_member(member, 'tutor_suspended', 'บัญชีติวเตอร์ของคุณถูกระงับการสอนชั่วคราว', '/tutoring/register/')


# ─────────────────────────────────────────
# Signal: Refill
# ─────────────────────────────────────────
@receiver(pre_save, sender=Refill)
def refill_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_status = Refill.objects.get(pk=instance.pk).rf_status
        except Refill.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Refill)
def refill_post_save(sender, instance, created, **kwargs):
    old    = getattr(instance, '_old_status', None)
    new    = instance.rf_status
    member = instance.member

    if created and new == 0:
        # คำขอใหม่ → แจ้ง Admin
        _notif_admin(
            'admin_refill',
            f'มีคำขอเติมเครดิต {instance.rf_credit} เครดิต จาก {member.mb_full_name}',
            '/panel/refill-mgmt/',
        )

    elif old != new:
        if new == 1:
            _notif_member(member, 'refill_approved', f'การเติมเครดิต {instance.rf_credit} เครดิต ผ่านการตรวจสอบแล้ว', '/credits/')
        elif new == 2:
            _notif_member(member, 'refill_rejected', f'การเติมเครดิต {instance.rf_credit} เครดิต ไม่ผ่านการตรวจสอบ', '/credits/')


# ─────────────────────────────────────────
# Signal: Withdrawals
# ─────────────────────────────────────────
@receiver(pre_save, sender=Withdrawals)
def withdrawals_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_status = Withdrawals.objects.get(pk=instance.pk).wd_status
        except Withdrawals.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Withdrawals)
def withdrawals_post_save(sender, instance, created, **kwargs):
    old    = getattr(instance, '_old_status', None)
    new    = instance.wd_status
    member = instance.member

    if created and new == 0:
        # คำขอใหม่ → แจ้ง Admin
        _notif_admin(
            'admin_withdraw',
            f'มีคำขอถอนเครดิต {instance.wd_credit} เครดิต จาก {member.mb_full_name}',
            '/panel/payment-mgmt/',
        )

    elif old != new:
        if new == 1:
            _notif_member(
                member,
                'withdraw_paid',
                f'การถอนเงิน {instance.wd_net_cash} บาท เข้าบัญชีธนาคารเรียบร้อยแล้ว',
                '/credits/',
            )