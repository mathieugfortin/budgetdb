# Generated by Django 4.0.2 on 2022-03-22 00:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0012_alter_account_groups_admin_alter_account_groups_view_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='groups_admin',
        ),
        migrations.RemoveField(
            model_name='account',
            name='groups_view',
        ),
        migrations.RemoveField(
            model_name='accountcategory',
            name='groups_admin',
        ),
        migrations.RemoveField(
            model_name='accountcategory',
            name='groups_view',
        ),
        migrations.RemoveField(
            model_name='accounthost',
            name='groups_admin',
        ),
        migrations.RemoveField(
            model_name='accounthost',
            name='groups_view',
        ),
        migrations.RemoveField(
            model_name='cat1',
            name='groups_admin',
        ),
        migrations.RemoveField(
            model_name='cat1',
            name='groups_view',
        ),
        migrations.RemoveField(
            model_name='cat2',
            name='groups_admin',
        ),
        migrations.RemoveField(
            model_name='cat2',
            name='groups_view',
        ),
        migrations.RemoveField(
            model_name='cattype',
            name='groups_admin',
        ),
        migrations.RemoveField(
            model_name='cattype',
            name='groups_view',
        ),
        migrations.RemoveField(
            model_name='vendor',
            name='groups_admin',
        ),
        migrations.RemoveField(
            model_name='vendor',
            name='groups_view',
        ),
    ]