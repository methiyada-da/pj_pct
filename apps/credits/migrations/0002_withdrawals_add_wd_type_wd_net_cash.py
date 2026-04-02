from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migration: เพิ่ม 2 field ใหม่ในตาราง Withdrawals ตาม Data Dictionary D19
      - wd_type     : ประเภทเครดิตที่ถอน (0 = นำฝาก, 1 = รายได้)
      - wd_net_cash : ยอดสุทธิที่จ่ายจริงหลังหักค่าธรรมเนียม (= wd_cash - wd_fee)
    """

    dependencies = [
        # ชี้ไปที่ migration ล่าสุดของ app นี้ก่อนจะรัน migration นี้
        ('credits', '0001_initial'),  # ← เปลี่ยน 'yourapp' และ '0001_initial' ให้ตรงกับโปรเจกต์จริง
    ]

    operations = [
        # เพิ่ม wd_type — วางหลัง wd_req_date ให้ลำดับตรงกับ Data Dictionary
        migrations.AddField(
            model_name='withdrawals',
            name='wd_type',
            field=models.IntegerField(
                choices=[(0, 'นำฝาก'), (1, 'รายได้')],
                default=0,                      # rows เก่าจะได้ค่า 0 (นำฝาก) โดยอัตโนมัติ
                verbose_name='ประเภทเครดิตที่ถอน',
            ),
        ),
        # เพิ่ม wd_net_cash — วางหลัง wd_fee ให้ลำดับตรงกับ Data Dictionary
        migrations.AddField(
            model_name='withdrawals',
            name='wd_net_cash',
            field=models.DecimalField(
                max_digits=7,
                decimal_places=2,
                default=0,                      # rows เก่าใส่ 0 ไว้ก่อน ควร backfill ด้วย data migration ถ้ามีข้อมูลเดิม
                verbose_name='ยอดสุทธิที่จ่ายจริง',
            ),
            preserve_default=False,             # ไม่เก็บ default=0 ไว้ใน model จริง (บังคับส่งค่ามาเสมอ)
        ),
    ]