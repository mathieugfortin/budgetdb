# Generated by Django 4.0.2 on 2023-02-05 16:59

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0023_preference_currencies_preference_currency_prefered'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='amount_actual_foreign_currency',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='original amount'),
        ),
    ]
