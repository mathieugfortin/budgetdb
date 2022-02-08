# Generated by Django 4.0.2 on 2022-02-03 19:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0029_auto_20210829_2124'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='deleted, should not be used in any calculations'),
        ),
        migrations.AddField(
            model_name='accountaudit',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='deleted, should not be used in any calculations'),
        ),
        migrations.AddField(
            model_name='accountcategory',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='deleted, should not be used in any calculations'),
        ),
        migrations.AddField(
            model_name='accounthost',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='deleted, should not be used in any calculations'),
        ),
        migrations.AddField(
            model_name='budgetedevent',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='deleted, should not be used in any calculations'),
        ),
        migrations.AddField(
            model_name='cat1',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='deleted, should not be used in any calculations'),
        ),
        migrations.AddField(
            model_name='cat2',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='deleted, should not be used in any calculations'),
        ),
        migrations.AddField(
            model_name='catbudget',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='deleted, should not be used in any calculations'),
        ),
        migrations.AddField(
            model_name='cattype',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='deleted, should not be used in any calculations'),
        ),
        migrations.AddField(
            model_name='joinedtransactions',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='deleted, should not be used in any calculations'),
        ),
        migrations.AddField(
            model_name='statement',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='deleted, should not be used in any calculations'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='deleted, should not be used in any calculations'),
        ),
        migrations.AddField(
            model_name='vendor',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='deleted, should not be used in any calculations'),
        ),
    ]
