# Generated by Django 5.0.2 on 2024-02-24 22:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0011_preference_testsrtdfcurrencies'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='preference',
            name='testsrtdfcurrencies',
        ),
    ]
