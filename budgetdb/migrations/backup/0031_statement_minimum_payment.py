# Generated by Django 4.0.2 on 2022-02-04 20:07

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0030_account_deleted_accountaudit_deleted_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='statement',
            name='minimum_payment',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.0000'), max_digits=10, verbose_name='Minimum Payment'),
        ),
    ]