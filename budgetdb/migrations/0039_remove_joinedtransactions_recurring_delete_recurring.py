# Generated by Django 4.0.2 on 2023-03-09 00:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0038_alter_budgetedevent_cat1_alter_budgetedevent_cat2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='joinedtransactions',
            name='recurring',
        ),
        migrations.DeleteModel(
            name='Recurring',
        ),
    ]