# Generated by Django 4.0.2 on 2022-03-20 02:31

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0009_accountcategory_deleted_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='friends',
            field=models.ManyToManyField(related_name='friends_users', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='user',
            name='invited',
            field=models.ManyToManyField(related_name='invited_users', to=settings.AUTH_USER_MODEL),
        ),
    ]
