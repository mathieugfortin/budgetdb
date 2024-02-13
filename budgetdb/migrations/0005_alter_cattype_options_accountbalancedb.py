# Generated by Django 5.0.2 on 2024-02-09 23:52

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0004_transaction_balance'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cattype',
            options={'ordering': ['name'], 'verbose_name': 'Category Type', 'verbose_name_plural': 'Categories Type'},
        ),
        migrations.CreateModel(
            name='AccountBalanceDB',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('db_date', models.DateField(blank=True)),
                ('audit', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='audited amount')),
                ('delta', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='relative change for the day')),
                ('balance', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='balance for the day')),
                ('account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='budgetdb.account')),
            ],
        ),
    ]
