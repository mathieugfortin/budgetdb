# Generated by Django 4.0.2 on 2022-03-20 18:41

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('budgetdb', '0011_rename_groups_mod_account_groups_admin_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='groups_admin',
            field=models.ManyToManyField(blank=True, related_name='g_can_mod_%(app_label)s_%(class)s', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='account',
            name='groups_view',
            field=models.ManyToManyField(blank=True, related_name='g_can_view_%(app_label)s_%(class)s', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='account',
            name='users_admin',
            field=models.ManyToManyField(blank=True, related_name='users_full_access_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='account',
            name='users_view',
            field=models.ManyToManyField(blank=True, related_name='users_view_access_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='accountcategory',
            name='groups_admin',
            field=models.ManyToManyField(blank=True, related_name='g_can_mod_%(app_label)s_%(class)s', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='accountcategory',
            name='groups_view',
            field=models.ManyToManyField(blank=True, related_name='g_can_view_%(app_label)s_%(class)s', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='accountcategory',
            name='users_admin',
            field=models.ManyToManyField(blank=True, related_name='users_full_access_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='accountcategory',
            name='users_view',
            field=models.ManyToManyField(blank=True, related_name='users_view_access_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='accounthost',
            name='groups_admin',
            field=models.ManyToManyField(blank=True, related_name='g_can_mod_%(app_label)s_%(class)s', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='accounthost',
            name='groups_view',
            field=models.ManyToManyField(blank=True, related_name='g_can_view_%(app_label)s_%(class)s', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='accounthost',
            name='users_admin',
            field=models.ManyToManyField(blank=True, related_name='users_full_access_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='accounthost',
            name='users_view',
            field=models.ManyToManyField(blank=True, related_name='users_view_access_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='cat1',
            name='groups_admin',
            field=models.ManyToManyField(blank=True, related_name='g_can_mod_%(app_label)s_%(class)s', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='cat1',
            name='groups_view',
            field=models.ManyToManyField(blank=True, related_name='g_can_view_%(app_label)s_%(class)s', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='cat1',
            name='users_admin',
            field=models.ManyToManyField(blank=True, related_name='users_full_access_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='cat1',
            name='users_view',
            field=models.ManyToManyField(blank=True, related_name='users_view_access_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='cat2',
            name='groups_admin',
            field=models.ManyToManyField(blank=True, related_name='g_can_mod_%(app_label)s_%(class)s', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='cat2',
            name='groups_view',
            field=models.ManyToManyField(blank=True, related_name='g_can_view_%(app_label)s_%(class)s', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='cat2',
            name='users_admin',
            field=models.ManyToManyField(blank=True, related_name='users_full_access_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='cat2',
            name='users_view',
            field=models.ManyToManyField(blank=True, related_name='users_view_access_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='cattype',
            name='groups_admin',
            field=models.ManyToManyField(blank=True, related_name='g_can_mod_%(app_label)s_%(class)s', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='cattype',
            name='groups_view',
            field=models.ManyToManyField(blank=True, related_name='g_can_view_%(app_label)s_%(class)s', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='cattype',
            name='users_admin',
            field=models.ManyToManyField(blank=True, related_name='users_full_access_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='cattype',
            name='users_view',
            field=models.ManyToManyField(blank=True, related_name='users_view_access_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='vendor',
            name='groups_admin',
            field=models.ManyToManyField(blank=True, related_name='g_can_mod_%(app_label)s_%(class)s', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='vendor',
            name='groups_view',
            field=models.ManyToManyField(blank=True, related_name='g_can_view_%(app_label)s_%(class)s', to='auth.Group'),
        ),
        migrations.AlterField(
            model_name='vendor',
            name='users_admin',
            field=models.ManyToManyField(blank=True, related_name='users_full_access_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='vendor',
            name='users_view',
            field=models.ManyToManyField(blank=True, related_name='users_view_access_%(app_label)s_%(class)s', to=settings.AUTH_USER_MODEL),
        ),
    ]
