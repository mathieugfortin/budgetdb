# Generated by Django 4.0.2 on 2024-01-11 15:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0050_transaction_unit_qty_transaction_unit_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='Unit_QTY',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=9, null=True, verbose_name='Number of units'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='Unit_price',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=9, null=True, verbose_name='Price per unit'),
        ),
    ]