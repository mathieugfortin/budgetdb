# Generated by Django 3.1.7 on 2021-04-24 16:41

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0025_joinedtransactions'),
    ]

    operations = [
        migrations.AddField(
            model_name='joinedtransactions',
            name='comment',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='joinedtransactions',
            name='created_date',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='joinedtransactions',
            name='modified_date',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='joinedtransactions',
            name='name',
            field=models.CharField(default=' ', max_length=200),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='statement',
            name='comment',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]