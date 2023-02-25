# Generated by Django 4.0.2 on 2023-02-05 16:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0022_transaction_currency'),
    ]

    operations = [
        migrations.AddField(
            model_name='preference',
            name='currencies',
            field=models.ManyToManyField(related_name='currencies', to='budgetdb.Currency'),
        ),
        migrations.AddField(
            model_name='preference',
            name='currency_prefered',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.DO_NOTHING, related_name='currency_prefered', to='budgetdb.currency'),
            preserve_default=False,
        ),
    ]
