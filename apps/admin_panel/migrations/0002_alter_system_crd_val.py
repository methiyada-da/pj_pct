# apps/admin_panel/migrations/0002_alter_system_crd_val.py

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='system',
            name='crd_val',
            field=models.DecimalField(
                decimal_places=2,
                max_digits=5,          # แก้จาก 3 → 5
                verbose_name='มูลค่าเครดิต',
            ),
        ),
    ]