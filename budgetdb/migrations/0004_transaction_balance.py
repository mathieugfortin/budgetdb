# Generated by Django 5.0.1 on 2024-02-05 23:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0003_remove_transaction_balance'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='balance',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Balance'),
        ),
    ]
