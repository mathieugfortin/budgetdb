# Generated by Django 4.0.2 on 2023-03-09 00:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0037_budgetedevent_comment_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='budgetedevent',
            name='cat1',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_category', to='budgetdb.cat1', verbose_name='Category'),
        ),
        migrations.AlterField(
            model_name='budgetedevent',
            name='cat2',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_subcategory', to='budgetdb.cat2', verbose_name='Subcategory'),
        ),
    ]