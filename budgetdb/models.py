import datetime
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.db.models.functions import Cast, Coalesce


class MyBoolMap(models.IntegerField):
    def db_type(self, connection):
        return 'integer'

    def rel_db_type(self, connection):
        return 'integer'


class MyCalendar (models.Model):
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
            # print(self.get_amount_frequency_display())
            return self.amount
        elif self.amount_frequency == 'W':
            print('weekly')
            return self.amount/7
        elif self.amount_frequency == 'M':
            print('monthly')
            return self.amount/30
        elif self.amount_frequency == 'Y':
            print('yearly')
            return self.amount/365
        else:
            print('nothing')
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

    AccountHost = models.ForeignKey(AccountHost, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Vendor(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class BudgetedEvent(models.Model):
    # description of budgeted events
    class Meta:
        verbose_name = 'Budgeted Event'
        verbose_name_plural = 'Budgeted Events'

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
    budget_only = models.BooleanField('only for budgeting, no actual expense planned', default=False)
    isrecurring = models.BooleanField('Is this a recurring event?', default=True)  # is this useful?
    repeat_start = models.DateField('date of the first event')
    repeat_stop = models.DateField('date of the last event, optional', blank=True, null=True)
    nb_iteration = models.IntegerField('number of repetitions, null if not applicable', blank=True,
                                       null=True)  # is this implementable on complex patterns?
    repeat_interval_days = models.IntegerField('period in days, 0 if not applicable', default=0)
    repeat_interval_years = models.IntegerField('period in years, 0 if not applicable', default=0)
    repeat_interval_months = models.IntegerField('period in months, 0 if not applicable', default=0)
    repeat_interval_weeks = models.IntegerField('period in weeks, 0 if not applicable', default=0)

    # binary masks are ALWAYS APPLICABLE
    months_mask = MyBoolMap(default=4095)

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

    def __str__(self):
        return self.description

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


# description of a transaction.  Can be linked to a budgeted event or not
class Transaction(models.Model):
    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'

    BudgetedEvent = models.ForeignKey(BudgetedEvent, on_delete=models.CASCADE, blank=True,
                                      null=True)
    BudgetedEvent_index = models.IntegerField(
        'event index, nth repetition of that budgeted event', blank=True, null=True
    )  # is this really needed?
    date_planned = models.DateField('planned date', blank=True, null=True)
    # not modifiable if linked to a budgeted event -- HOW?
    # not sure what option is better.  Just use date planned to match the budgeted event or use the index?
    # index could be hard to calculate for complex repetition patterns...
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

    def __str__(self):
        return self.description


class AccountAudit(models.Model):
    class Meta:
        verbose_name = 'Account audit point'
        verbose_name_plural = 'Account audit points'
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='audit_account')
    audit_date = models.DateField('date of the audit')
    audit_amount = models.DecimalField('audit amount', decimal_places=2, max_digits=10, default=Decimal('0.0000'))
    comment = models.CharField(max_length=200)


class Statement (models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='statement_account')
    balance = models.DecimalField('Statement balance', decimal_places=2, max_digits=10, default=Decimal('0.0000'))
    statement_date = models.DateField('date of the statement')
    statement_due_date = models.DateField('date where payment is due', blank=True, null=True)
    comment = models.CharField(max_length=200)
    payment_transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, blank=True, null=True)


class BitmapWeeksPerMonth(models.Model):
    bit1 = models.BooleanField('1st', default=True)
    bit2 = models.BooleanField('2nd', default=True)
    bit3 = models.BooleanField('3rd', default=True)
    bit4 = models.BooleanField('4th', default=True)
    bit5 = models.BooleanField('5th', default=True)
    budgeted_event = models.OneToOneField(BudgetedEvent, on_delete=models.CASCADE)

    def __str__(self):
        return 1*self.bit1 + 2*self.bit2 + 4*self.bit3 + 8*self.bit4 + 16*self.bit5


class BitmapWeekdays(models.Model):
    bit1 = models.BooleanField('Mondays', default=True)
    bit2 = models.BooleanField('Tuesdays', default=True)
    bit3 = models.BooleanField('Wednesdays', default=True)
    bit4 = models.BooleanField('Thursdays', default=True)
    bit5 = models.BooleanField('Fridays', default=True)
    bit6 = models.BooleanField('Saturdays', default=True)
    bit7 = models.BooleanField('Sundays', default=True)
    budgeted_event = models.OneToOneField(BudgetedEvent, on_delete=models.CASCADE)

    def __str__(self):
        return 1*self.bit1 + 2*self.bit2 + 4*self.bit3 + 8*self.bit4 + 16*self.bit5 + 32*self.bit6 + 64*self.bit7


class BitmapMonths(models.Model):
    bit1 = models.BooleanField('Jan', default=True)
    bit2 = models.BooleanField('Feb', default=True)
    bit3 = models.BooleanField('Mar', default=True)
    bit4 = models.BooleanField('Apr', default=True)
    bit5 = models.BooleanField('May', default=True)
    bit6 = models.BooleanField('Jun', default=True)
    bit7 = models.BooleanField('Jul', default=True)
    bit8 = models.BooleanField('Aug', default=True)
    bit9 = models.BooleanField('Sep', default=True)
    bit10 = models.BooleanField('Oct', default=True)
    bit11 = models.BooleanField('Nov', default=True)
    bit12 = models.BooleanField('Dec', default=True)
    budgeted_event = models.OneToOneField(BudgetedEvent, on_delete=models.CASCADE)

    def __str__(self):
        return 1*self.bit1 + 2*self.bit2 + 4*self.bit3 + 8*self.bit4 + 16*self.bit5 + 32*self.bit6 \
               + 64*self.bit7 + 128*self.bit8 + 256*self.bit9 + 512*self.bit10 + 1024*self.bit11 + 2048*self.bit12


class BitmapDayPerMonth(models.Model):
    bit1 = models.BooleanField('1', default=True)
    bit2 = models.BooleanField('2', default=True)
    bit3 = models.BooleanField('3', default=True)
    bit4 = models.BooleanField('4', default=True)
    bit5 = models.BooleanField('5', default=True)
    bit6 = models.BooleanField('6', default=True)
    bit7 = models.BooleanField('7', default=True)
    bit8 = models.BooleanField('8', default=True)
    bit9 = models.BooleanField('9', default=True)
    bit10 = models.BooleanField('10', default=True)
    bit11 = models.BooleanField('11', default=True)
    bit12 = models.BooleanField('12', default=True)
    bit13 = models.BooleanField('13', default=True)
    bit14 = models.BooleanField('14', default=True)
    bit15 = models.BooleanField('15', default=True)
    bit16 = models.BooleanField('16', default=True)
    bit17 = models.BooleanField('17', default=True)
    bit18 = models.BooleanField('18', default=True)
    bit19 = models.BooleanField('19', default=True)
    bit20 = models.BooleanField('20', default=True)
    bit21 = models.BooleanField('21', default=True)
    bit22 = models.BooleanField('22', default=True)
    bit23 = models.BooleanField('23', default=True)
    bit24 = models.BooleanField('24', default=True)
    bit25 = models.BooleanField('25', default=True)
    bit26 = models.BooleanField('26', default=True)
    bit27 = models.BooleanField('27', default=True)
    bit28 = models.BooleanField('28', default=True)
    bit29 = models.BooleanField('29', default=True)
    bit30 = models.BooleanField('30', default=True)
    bit31 = models.BooleanField('31', default=True)
    budgeted_event = models.OneToOneField(BudgetedEvent, on_delete=models.CASCADE)

    def __str__(self):
        return 2**0*self.bit1 + 2**1*self.bit2 + 2**2*self.bit3 + 2**3*self.bit4 + 2**4*self.bit5 \
               + 2**5*self.bit6 + 2**6*self.bit7 + 2**7*self.bit8 + 2**8*self.bit9 \
               + 2**9*self.bit10 + 2**10*self.bit11 + 2**11*self.bit12 + 2**12*self.bit13 + 2**13*self.bit14 \
               + 2**14*self.bit15 + 2**15*self.bit16 + 2**16*self.bit17 + 2**17*self.bit18 + 2**18*self.bit19 \
               + 2**19*self.bit20 + 2**20*self.bit21 + 2**21*self.bit22 + 2**22*self.bit23 + 2**23*self.bit24 \
               + 2**24*self.bit25 + 2**25*self.bit26 + 2**26*self.bit27 + 2**27*self.bit28 + 2**28*self.bit29 \
               + 2 ** 29 * self.bit30 + 2 ** 30 * self.bit31


class CalendarView(models.Model):
    class Meta:
        verbose_name = 'Calendar'
        verbose_name_plural = 'Calendars'
        managed = False
        db_table = 'calendar_view'
    db_date = models.DateField()
    budgetedevent = models.ForeignKey(BudgetedEvent, on_delete=models.DO_NOTHING)
    transaction = models.ForeignKey(Transaction, on_delete=models.DO_NOTHING)
    BE_description = models.TextField()
    T_description = models.TextField()
    BE_source = models.ForeignKey(Account, on_delete=models.DO_NOTHING, related_name='cbe_account_source',
                                  blank=True, null=True)
    BE_destination = models.ForeignKey(Account, on_delete=models.DO_NOTHING,
                                       related_name='cbe_account_destination',
                                       blank=True, null=True)
    BE_ammount = models.DecimalField('Budgeted amount', decimal_places=2, max_digits=10,
                                     blank=True, null=True)
    T_source = models.ForeignKey(Account, on_delete=models.DO_NOTHING, related_name='ct_account_source',
                                 blank=True, null=True)
    T_destination = models.ForeignKey(Account, on_delete=models.DO_NOTHING,
                                      related_name='ct_account_destination',
                                      blank=True, null=True)
    T_ammount = models.DecimalField('Transaction amount', decimal_places=2, max_digits=10,
                                    blank=True, null=True)
