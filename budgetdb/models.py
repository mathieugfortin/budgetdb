import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.db.models.functions import Cast, Coalesce
from django.db.models import Sum, Q
from django.urls import reverse


class AccountBalances(models.Model):
    db_date = models.DateField(blank=True)
    account = models.ForeignKey("Account", on_delete=models.DO_NOTHING, blank=True, null=True)
    audit = models.DecimalField('audited amount', decimal_places=2, max_digits=10,
                                blank=True, null=True)
    delta = models.DecimalField('relative change for the day', decimal_places=2, max_digits=10,
                                blank=True, null=True)
    balance = models.DecimalField('balance for the day', decimal_places=2, max_digits=10,
                                  blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'budgetdb_accounttotal'


class MyBoolMap(models.IntegerField):
    def db_type(self, connection):
        return 'integer'

    def rel_db_type(self, connection):
        return 'integer'


class MyCalendar(models.Model):
    class Meta:
        verbose_name = 'Calendar'
        verbose_name_plural = 'Calendars'

    db_date = models.DateField('date')  #
    year = models.IntegerField('year')  #
    month = models.IntegerField('month')  # 1 to 12
    day = models.IntegerField('year')  # 1 to 31
    quarter = models.IntegerField('quarter')  # 1 to 4
    week = models.IntegerField('week')  # 1 to 52/53
    day_name = models.CharField('Day name EN', max_length=9)  # 'Monday'...
    month_name = models.CharField('Month Name EN', max_length=9)  # 'January'..
    holiday_flag = models.BooleanField('Holiday Flag', default=False)
    weekend_flag = models.BooleanField('Weekend Flag', default=False)
    event = models.CharField('Event name', max_length=50)

    def __str__(self):
        return f'{self.db_date.year}-{self.db_date.month}-{self.db_date.day}'


class CatBudget(models.Model):
    class Meta:
        verbose_name = 'Category Budget'
        verbose_name_plural = 'Categories Budgets'

    name = models.CharField(max_length=200)
    FREQUENCIES = (
        ('D', 'Daily'),
        ('W', 'Weekly'),
        ('M', 'Monthly'),
        ('Y', 'Yearly'),
    )
    amount = models.DecimalField(decimal_places=2, max_digits=10)
    amount_frequency = models.CharField(max_length=1, choices=FREQUENCIES,
                                        default='D')

    def __str__(self):
        return self.name

    def budget_daily(self):
        if self.amount_frequency == 'D':
            return self.amount
        elif self.amount_frequency == 'W':
            return self.amount/7
        elif self.amount_frequency == 'M':
            return self.amount/30
        elif self.amount_frequency == 'Y':
            return self.amount/365
        else:
            return 0

    def budget_weekly(self):
        if self.amount_frequency == 'D':
            return self.amount*7
        elif self.amount_frequency == 'W':
            return self.amount
        elif self.amount_frequency == 'M':
            return self.amount / 4.33
        elif self.amount_frequency == 'Y':
            return self.amount / 52
        else:
            return 0

    def budget_monthly(self):
        if self.amount_frequency == 'D':
            return self.amount * 30
        elif self.amount_frequency == 'W':
            return self.amount * 4.33
        elif self.amount_frequency == 'M':
            return self.amount
        elif self.amount_frequency == 'Y':
            return self.amount / 12
        else:
            return 0

    def budget_yearly(self):
        if self.amount_frequency == 'D':
            return self.amount * 365
        elif self.amount_frequency == 'W':
            return self.amount * 52
        elif self.amount_frequency == 'M':
            return self.amount * 12
        elif self.amount_frequency == 'Y':
            return self.amount
        else:
            return 0


class Cat1(models.Model):
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
    name = models.CharField(max_length=200)
    CatBudget = models.ForeignKey(CatBudget, on_delete=models.CASCADE,
                                  blank=True, null=True)

    def __str__(self):
        return self.name


class Cat2(models.Model):
    class Meta:
        verbose_name = 'Sub Category'
        verbose_name_plural = 'Sub Categories'

    cat1 = models.ForeignKey(Cat1, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    CatBudget = models.ForeignKey(CatBudget, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.name


class AccountHost(models.Model):
    class Meta:
        verbose_name = 'Financial Institution'
        verbose_name_plural = 'Financial Institutions'
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Account(models.Model):
    class Meta:
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    AccountHost = models.ForeignKey(AccountHost, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=200)

    def __str__(self):
        return self.name

    def balance_by_EOD3(self, dateCheck):
        closestAudit = Transaction.objects.filter(account_source_id=self.id, date_actual__lte=dateCheck, audit=True).order_by('date_actual')[:1]

        if closestAudit.count() == 0:
            balance = Decimal(0.00)
            events = Transaction.objects.filter(date_actual__lte=dateCheck)
        else:
            balance = Decimal(closestAudit.first().amount_actual)
            events = Transaction.objects.filter(date_actual__gt=closestAudit.first().date_actual, date_actual__lte=dateCheck)

        events = events.filter(account_source_id=self.id) | events.filter(account_destination_id=self.id)

        for event in events:
            amount = Decimal(0.00)
            if event.audit is True:
                balance = event.amount_actual
            else:
                if event.account_destination_id == self.id:
                    amount += event.amount_actual
                if event.account_source_id == self.id:
                    amount -= event.amount_actual
                balance = balance + amount

        return balance

    def build_report_with_balance3(self, start_date, end_date):
        events = Transaction.objects.filter(date_actual__gt=start_date, date_actual__lte=end_date).order_by('date_actual')
        events = events.filter(account_destination_id=self.id) | events.filter(account_source_id=self.id)
        balance = Decimal(Account.objects.get(id=self.id).balance_by_EOD3(start_date))
        for event in events:
            amount = Decimal(0.00)
            if event.audit is True:
                balance = event.amount_actual
                event.calc_amount = ""
                event.viewname = f'{event._meta.app_label}:details_transaction_Audit'
            else:
                if event.account_destination_id == self.id:
                    amount += event.amount_actual
                if event.account_source_id == self.id:
                    amount -= event.amount_actual
                balance = balance + amount
                event.calc_amount = str(amount) + "$"
                event.viewname = f'{event._meta.app_label}:details_transaction'
            event.balance = str(balance) + "$"
        return events

    def build_balance_array(self, start_date, end_date):
        # don't do the sql = thing in prod
        sqlst = f"SELECT " \
                f"row_number() OVER () as id, " \
                f"c.db_date, " \
                f"{self.id} as account_id, " \
                f"ta.amount_actual AS audit, " \
                f"sum(case " \
                f"  when t.account_source_id={self.id} Then -t.amount_actual " \
                f"  when t.account_destination_id={self.id} then t.amount_actual " \
                f"END) AS delta " \
                f"FROM budgetdb.budgetdb_mycalendar c " \
                f"left join budgetdb.budgetdb_transaction t ON c.db_date = t.date_actual " \
                f"    AND (t.account_source_id={self.id} OR t.account_destination_id={self.id}) AND t.audit = 0 " \
                f"LEFT JOIN budgetdb.budgetdb_transaction ta ON c.db_date = ta.date_actual " \
                f"    AND ta.audit = 1 AND ta.account_source_id = {self.id} " \
                f"WHERE c.db_date BETWEEN '{start_date}' AND '{end_date}' " \
                f"GROUP BY c.db_date " \
                f"ORDER BY c.db_date "

        accountbalances = AccountBalances.objects.raw(sqlst)
        # print(accountbalances)
        return accountbalances


class AccountCategory(models.Model):
    class Meta:
        verbose_name = 'Account Category'
        verbose_name_plural = 'Account Categories'
    accounts = models.ManyToManyField(Account, related_name='account_categories')
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class AccountAudit(models.Model):
    # Force an account to a specific balance on a given date.
    class Meta:
        verbose_name = 'Account audit point'
        verbose_name_plural = 'Account audit points'

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='audit_account')
    audit_date = models.DateField('date of the audit')
    audit_amount = models.DecimalField('audit amount', decimal_places=2, max_digits=10, default=Decimal('0.0000'))
    comment = models.CharField(max_length=200)

    def __str__(self):
        return self.audit_amount


class Vendor(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Transaction(models.Model):
    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    BudgetedEvent = models.ForeignKey("BudgetedEvent", on_delete=models.CASCADE, blank=True,
                                      null=True)
    date_planned = models.DateField('planned date', blank=True, null=True)
    # date_planned only populated if linked to a budgeted_event
    # will break if repetition pattern of BE changes... so BE can't change if it has attached Ts
    date_actual = models.DateField('date of the transaction')
    amount_actual = models.DecimalField(
        'real transaction amount', decimal_places=2, max_digits=10, default=Decimal('0.00')
    )
    description = models.CharField('transaction description', max_length=200)
    comment = models.CharField('optional comment', max_length=200, blank=True, null=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, blank=True, null=True)
    cat1 = models.ForeignKey(Cat1, on_delete=models.CASCADE, blank=True, null=True)
    cat2 = models.ForeignKey(Cat2, on_delete=models.CASCADE, blank=True, null=True)
    # should be null if it is linked to a budgeted event
    account_source = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='t_account_source', blank=True, null=True
    )
    account_destination = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='t_account_destination', blank=True, null=True
    )
    statement = models.ForeignKey("Statement", on_delete=models.CASCADE, blank=True, null=True)
    verified = models.BooleanField('confirmed in a statement.  Prevents deletion in case of budgetedEvent change', default=False)
    audit = models.BooleanField('Special transaction that overrides an account balance.  Used to set the initial value.  Use account_source as account_id', default=False)
    # how do I ensure the audit transaction is always last for a day?

    def __str__(self):
        return self.description

    def save(self, *args, **kwargs):
        if self._state.adding:
            if Transaction.objects.filter(BudgetedEvent=self.BudgetedEvent, date_planned=self.date_planned).exists():
                # don't save a duplicate
                pass
            else:
                super(Transaction, self).save(*args, **kwargs)


class BudgetedEvent(models.Model):
    # description of budgeted events
    class Meta:
        verbose_name = 'Budgeted Event'
        verbose_name_plural = 'Budgeted Events'

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    generated_interval_start = models.DateTimeField('begining of the generated events interval', blank=True, null=True)
    generated_interval_stop = models.DateTimeField('end of the generated events interval', blank=True, null=True)
    amount_planned = models.DecimalField('Budgeted amount', decimal_places=2, max_digits=10,
                                         blank=True, null=True)
    percent_planned = models.DecimalField('percent of another event.  say 10% of pay goes to RRSP',
                                          decimal_places=2, max_digits=10, blank=True, null=True)
    BudgetedEvent_percent_ref = models.ForeignKey('self', on_delete=models.CASCADE, blank=True,
                                                  null=True)
    account_source = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='b_account_source',
                                       blank=True, null=True)
    account_destination = models.ForeignKey(Account, on_delete=models.CASCADE,
                                            related_name='b_account_destination',
                                            blank=True, null=True)
    cat1 = models.ForeignKey(Cat1, on_delete=models.CASCADE,
                             verbose_name='Category')
    cat2 = models.ForeignKey(Cat2, on_delete=models.CASCADE,
                             verbose_name='Subcategory')
    description = models.CharField(max_length=200, default='Description')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, blank=True, null=True)
    budget_only = models.BooleanField('only for budgeting, no actual expense planned', default=False)  # is this useful?
    isrecurring = models.BooleanField('Is this a recurring event?', default=True)
    repeat_start = models.DateField('date of the first event')
    repeat_stop = models.DateField('date of the last event, optional', blank=True, null=True)
    nb_iteration = models.IntegerField('number of repetitions, null if not applicable', blank=True,
                                       null=True)  # is this implementable on complex patterns?
    repeat_interval_days = models.IntegerField('period in days, 0 if not applicable', default=0)
    repeat_interval_years = models.IntegerField('period in years, 0 if not applicable', default=0)
    repeat_interval_months = models.IntegerField('period in months, 0 if not applicable', default=0)
    repeat_interval_weeks = models.IntegerField('period in weeks, 0 if not applicable', default=0)

    ######################################
    # binary masks are ALWAYS APPLICABLE #
    ######################################

    repeat_months_mask = models.IntegerField(
        'binary mask of applicable months. Always Applicable jan=1 feb=2 mar=4 ... dec=2048 ALL=4095',
        default=4095)
    repeat_dayofmonth_mask = models.IntegerField(
        'binary mask of applicable month days. Always Applicable ALL=2147483647', default=2147483647
    )
    repeat_weekofmonth_mask = models.IntegerField('binary mask of applicable month week. Always Applicable ALL=15',
                                                  default=63)

    repeat_weekday_mask = models.IntegerField('binary mask of applicable week day. Always Applicable ALL=127',
                                              default=127)
    # Mon=1, Tue=2,Wed=4, Thu=8, Fri=16, Sat=32, Sun=64, all=127
    # workweek=31   weekend=96

    def __str__(self):
        return self.description

    def get_absolute_url(self):
        return reverse('budgetdb:details_be', kwargs={'pk': self.pk})

    def checkDate(self, dateCheck):
        # verifies if the event happens on the dateCheck. should handle all the recurring patterns
        # not before first event
        if dateCheck < self.repeat_start:
            return False
        # same day OK
        elif self.repeat_start == dateCheck:
            return True
        # not the same day and no recursion
        elif self.repeat_start != dateCheck \
                and self.isrecurring is False:
            return False
        # applying masks
        elif (1 << dateCheck.weekday()) & self.repeat_weekday_mask == 0:
            return False
        elif (1 << (dateCheck.month-1)) & self.repeat_months_mask == 0:
            return False
        elif (1 << (dateCheck.day-1)) & self.repeat_dayofmonth_mask == 0:
            return False
        elif (1 << int((dateCheck.day-1) / 7)) & self.repeat_weekofmonth_mask == 0:
            return False
        # not after last event
        elif self.repeat_stop is not None \
                and dateCheck > self.repeat_stop:
            return False
        # if day interval is used, check if the difference is a repeat of interval
        elif self.repeat_interval_days != 0 \
                and (dateCheck - self.repeat_start).days % self.repeat_interval_days != 0:
            return False
        # if year interval is used, check if the difference is a repeat of interval.
        # Days and months must match
        elif self.repeat_interval_years != 0 and \
                ((dateCheck.day != self.repeat_start.day) or (dateCheck.month != self.repeat_start.month)
                 or (dateCheck.year - self.repeat_start.year) % self.repeat_interval_years != 0):
            return False
        # if month interval is used, check if the difference is a repeat of interval. Days must match
        elif self.repeat_interval_months != 0 and \
                ((dateCheck.day != self.repeat_start.day) or
                 (dateCheck.month - self.repeat_start.month) % self.repeat_interval_months != 0):
            return False
        # if weeks interval is used, check if the difference is a repeat of interval. Weekday must match
        elif self.repeat_interval_weeks != 0 and \
                (dateCheck.weekday() != self.repeat_start.weekday() or
                 ((dateCheck - self.repeat_start).days / 7) % self.repeat_interval_weeks == 0):
            return False
        else:
            return True

    def listPotentialTransactionDates(self, n=20, begin_interval=datetime.date.today(), interval_length_months=12):
        calendar = MyCalendar.objects.filter(db_date__gte=begin_interval, db_date__lte=begin_interval+relativedelta(months=interval_length_months))
        event_date_list = []
        i = n
        for day in calendar:
            if (self.checkDate(day.db_date)):
                event_date_list.append(day.db_date)
                i -= 1
                if (i == 0):
                    break
        return event_date_list

    def listNextTransactions(self, n=20, begin_interval=datetime.date.today(), interval_length_months=12):
        transactions = Transaction.objects.filter(BudgetedEvent_id=self.id)
        transactions = transactions.filter(date_actual__gt=begin_interval)
        end_date = begin_interval + relativedelta(months=interval_length_months)
        transactions = transactions.filter(date_actual__lte=end_date)[:n]
        return transactions

    def createTransactions(self, n=20, begin_interval=datetime.date.today(), interval_length_months=12):
        transaction_dates = self.listPotentialTransactionDates(n=n, begin_interval=begin_interval, interval_length_months=interval_length_months)
        for date in transaction_dates:
            new_transaction = Transaction.objects.create(date_planned=date,
                                                         date_actual=date,
                                                         amount_actual=self.amount_planned,
                                                         description=self.description,
                                                         BudgetedEvent_id=self.id,
                                                         account_destination=self.account_destination_id,
                                                         account_source=self.account_source,
                                                         cat1=self.cat1,
                                                         cat2=self.cat2,
                                                         vendor=self.vendor
                                                         )
            new_transaction.save()
            # Needs a lot more work with these interval management  #######
            self.generated_interval_stop = date


class Statement (models.Model):
    class Meta:
        verbose_name = 'Statement'
        verbose_name_plural = 'Statements'

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='statement_account')
    balance = models.DecimalField('Statement balance', decimal_places=2, max_digits=10, default=Decimal('0.0000'))
    statement_date = models.DateField('date of the statement')
    statement_due_date = models.DateField('date where payment is due', blank=True, null=True)
    comment = models.CharField(max_length=200)
    payment_transaction = models.ForeignKey('Transaction', on_delete=models.CASCADE, related_name='payment_transaction',
                                            blank=True, null=True)

    def __str__(self):
        return self.comment
