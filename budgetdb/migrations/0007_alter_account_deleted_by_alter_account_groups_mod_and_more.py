# Generated by Django 4.0.2 on 2022-03-16 21:30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('budgetdb', '0006_vendor_deleted_at_vendor_deleted_by_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='deleted_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='deleted_by_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='account',
            name='groups_mod',
            field=models.ManyToManyField(related_name='g_can_mod_%(app_label)s_%(class)s', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='account',
            name='groups_view',
            field=models.ManyToManyField(related_name='g_can_view_%(app_label)s_%(class)s', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='account',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='object_owner_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='vendor',
            name='deleted_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='deleted_by_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
    ]
