# Generated by Django 4.0.2 on 2023-02-01 22:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0018_rename_catbudget_cat1_catbudget_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='account',
            options={'ordering': ['account_host__name', 'name'], 'verbose_name': 'Account', 'verbose_name_plural': 'Accounts'},
        ),
        migrations.AlterModelOptions(
            name='accountpresentation',
            options={'managed': False},
        ),
        migrations.AddField(
            model_name='account',
            name='date_closed',
            field=models.DateTimeField(blank=True, null=True, verbose_name='date closed'),
        ),
        migrations.AddField(
            model_name='account',
            name='date_open',
            field=models.DateTimeField(blank=True, null=True, verbose_name='date opened'),
        ),
        migrations.AlterField(
            model_name='account',
            name='account_parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='account_children', to='budgetdb.account'),
        ),
        migrations.AlterField(
            model_name='budgetedevent',
            name='repeat_weekofmonth_mask',
            field=models.IntegerField(default=63, verbose_name='binary mask of applicable month week. Always Applicable ALL=31'),
        ),
    ]