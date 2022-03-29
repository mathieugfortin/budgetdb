# Generated by Django 4.0.2 on 2022-03-16 02:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('budgetdb', '0003_alter_account_id_alter_accountaudit_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='deleted_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='account',
            name='deleted_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_deletor', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='account',
            name='groups_mod',
            field=models.ManyToManyField(related_name='g_can_mod', to='auth.Group'),
        ),
        migrations.AddField(
            model_name='account',
            name='groups_view',
            field=models.ManyToManyField(related_name='g_can_view', to='auth.Group'),
        ),
        migrations.AddField(
            model_name='account',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='account',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='object_owner', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
    ]
