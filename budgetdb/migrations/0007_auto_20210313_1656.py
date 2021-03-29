# Generated by Django 3.1.7 on 2021-03-13 21:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0006_auto_20210308_2304'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='BudgetedEvent_index',
        ),
        migrations.AddField(
            model_name='transaction',
            name='statement',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='budgetdb.statement'),
        ),
        migrations.AlterField(
            model_name='statement',
            name='payment_transaction',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='payment_transaction', to='budgetdb.transaction'),
        ),
    ]