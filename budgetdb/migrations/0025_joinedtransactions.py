# Generated by Django 3.1.7 on 2021-04-24 16:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budgetdb', '0024_accountpresentation'),
    ]

    operations = [
        migrations.CreateModel(
            name='JoinedTransactions',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('budgetedevents', models.ManyToManyField(related_name='budgeted_events', to='budgetdb.BudgetedEvent')),
                ('transactions', models.ManyToManyField(related_name='transactions', to='budgetdb.Transaction')),
            ],
            options={
                'verbose_name': 'Joined Transactions',
                'verbose_name_plural': 'Joined Transactions',
            },
        ),
    ]
