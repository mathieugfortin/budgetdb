# Generated by Django 4.0.2 on 2022-03-23 18:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0014_budgetedevent_owner_budgetedevent_users_admin_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='deleted',
        ),
        migrations.RemoveField(
            model_name='accountcategory',
            name='deleted',
        ),
        migrations.RemoveField(
            model_name='accounthost',
            name='deleted',
        ),
    ]
