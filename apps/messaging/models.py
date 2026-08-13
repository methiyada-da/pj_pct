# messaging/models.py - models ของ Inbox และ Message
from django.db import models
from apps.accounts.models import Member


# 4.3.1.14 ตารางข้อมูลกล่องข้อความ
class Inbox(models.Model):
    ib_id   = models.AutoField(primary_key=True, verbose_name="รหัสกล่องข้อความ")
    member1 = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name='inbox_as_member1',
        verbose_name="รหัสสมาชิกคนที่ 1"
    )
    member2 = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name='inbox_as_member2',
        verbose_name="รหัสสมาชิกคนที่ 2"
    )

    class Meta:
        db_table        = 'inbox'
        verbose_name    = "ข้อมูลกล่องข้อความ"
        unique_together = [['member1', 'member2']]

    def __str__(self):
        return f"Inbox | {self.member1.mb_full_name} ↔ {self.member2.mb_full_name}"

    def get_other_member(self, me):
        """คืน Member อีกฝั่งที่ไม่ใช่ตัวเอง"""
        return self.member2 if self.member1 == me else self.member1

    def unread_count_for(self, me):
        """จำนวนข้อความที่ me ยังไม่ได้อ่าน"""
        return self.message_set.filter(msg_is_read=False).exclude(sender=me).count()

    def last_message(self):
        """ข้อความล่าสุดใน inbox นี้"""
        return self.message_set.order_by('-msg_sent_time').first()


# 4.3.1.15 ตารางข้อมูลรายการข้อความ
class Message(models.Model):
    msg_id        = models.AutoField(primary_key=True, verbose_name="ลำดับข้อความ")
    msg_sent_time = models.DateTimeField(auto_now_add=True, verbose_name="วันเวลาที่ส่ง")
    msg           = models.TextField(blank=True, verbose_name="ข้อความ")
    msg_img       = models.ImageField(
        upload_to='chat/',
        blank=True,
        null=True,
        verbose_name="รูปภาพในข้อความ"
    )
    msg_is_read   = models.BooleanField(default=False, verbose_name="อ่านแล้ว")
    sender        = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        verbose_name="รหัสผู้ส่ง"
    )
    inbox         = models.ForeignKey(
        Inbox,
        on_delete=models.CASCADE,
        verbose_name="รหัสกล่องข้อความ"
    )

    class Meta:
        db_table     = 'message'
        verbose_name = "ข้อมูลรายการข้อความ"
        ordering     = ['msg_sent_time']

    def __str__(self):
        return f"MSG{self.msg_id} | {self.sender.mb_full_name}: {self.msg[:30]}"
