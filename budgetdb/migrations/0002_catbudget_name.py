# Generated by Django 3.1.7 on 2021-02-25 22:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='catbudget',
            name='name',
            field=models.CharField(default='A', max_length=200),
            preserve_default=False,
        ),
    ]
