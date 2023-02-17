# import datetime
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal, InvalidOperation
from django.db import models
from django.utils import timezone
from django.db.models.functions import Cast, Coalesce
from django.db.models import Sum, Q
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from crum import get_current_user


class User(AbstractUser):
    invited = models.ManyToManyField("User", related_name='invited_users')
    friends = models.ManyToManyField("User", related_name='friends_users')


class ViewerManager(models.Manager):
    def get_queryset(self):
        user = get_current_user()
        qs = super().get_queryset()
        owned = qs.filter(owner=user)
        admins = qs.filter(users_admin=user)
        viewers = qs.filter(users_view=user)
        qs = owned | admins | viewers
        return qs


class TransactionViewerManager(models.Manager):
    def get_queryset(self):
        user = get_current_user()
        qs = super().get_queryset()
        view_accounts = Account.view_objects.all()
        ok_source = qs.filter(account_source__in=view_accounts)
        ok_dest = qs.filter(account_destination__in=view_accounts)
        qs = ok_source | ok_dest
        return qs


class TransactionAdminManager(models.Manager):
    def get_queryset(self):
        user = get_current_user()
        qs = super().get_queryset()
        view_accounts = Account.admin_objects.all()
        ok_source = qs.filter(account_source__in=view_accounts)
        ok_dest = qs.filter(account_destination__in=view_accounts)
        qs = ok_source | ok_dest
        return qs


class AdminManager(models.Manager):
    def get_queryset(self):
        user = get_current_user()
        qs = super().get_queryset()
        owned = qs.filter(owner=user)
        admins = qs.filter(users_admin=user)
        return owned | admins


class UserPermissions(models.Model):
    class Meta:
        abstract = True

    owner = models.ForeignKey("User", on_delete=models.CASCADE, blank=False, null=False,
                              related_name='object_owner_%(app_label)s_%(class)s')
    # groups_admin = models.ManyToManyField(Group, related_name='g_can_mod_%(app_label)s_%(class)s', blank=True)
    # groups_view = models.ManyToManyField(Group, related_name='g_can_view_%(app_label)s_%(class)s', blank=True)
    users_admin = models.ManyToManyField("User", related_name='users_full_access_%(app_label)s_%(class)s', blank=True)
    users_view = models.ManyToManyField("User", related_name='users_view_access_%(app_label)s_%(class)s', blank=True)
    objects = models.Manager()  # The default manager.
    view_objects = ViewerManager()
    admin_objects = AdminManager()

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user and not user.pk:
            user = None
        if not self.pk and self._state.adding:
            self.owner = user
        super(UserPermissions, self).save(*args, **kwargs)

    def can_edit(self):
        user = get_current_user()
        if self.owner == user:
            return True
        if self.users_admin.filter(pk=user.pk).exists():
            return True
        return False

    def can_view(self):
        user = get_current_user()
        if self.owner == user:
            return True
        if self.users_admin.filter(pk=user.pk).exists():
            return True
        if self.users_view.filter(pk=user.pk).exists():
            return True
        return False


class BaseSoftDelete(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True)
    deleted_by = models.ForeignKey("User", null=True, on_delete=models.CASCADE, related_name='deleted_by_%(app_label)s_%(class)s')

    class Meta:
        abstract = True

    def soft_delete(self, user_id=None):
        if self.is_deleted:
            return
        self.is_deleted = True
        self.deleted_by = user_id
        self.deleted_at = timezone.now()
        self.save()

    def soft_undelete(self, user_id=None):
        if not self.is_deleted:
            return
        self.is_deleted = False
        self.deleted_by = None
        self.deleted_at = None
        self.save()


class Preference(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_interval = models.DateField(blank=True)
    end_interval = models.DateField(blank=True)
    max_interval_slider = models.DateField(blank=True, null=True)
    min_interval_slider = models.DateField(blank=True, null=True)
    currencies = models.ManyToManyField("Currency", related_name="currencies")
    currency_prefered = models.ForeignKey("Currency", on_delete=models.DO_NOTHING, related_name="currency_prefered")
    # add ordre of listing, old first/ new first


class AccountBalances(models.Model):
    db_date = models.DateField(blank=True)
    account = models.ForeignKey("Account", on_delete=models.DO_NOTHING, blank=True, null=True)
    audit = models.DecimalField(
        'audited amount',
        decimal_places=2,
        max_digits=10,
        blank=True,
        null=True,
        )
    delta = models.DecimalField(
        'relative change for the day',
        decimal_places=2,
        max_digits=10,
        blank=True,
        null=True,
        )
    balance = models.DecimalField(
        'balance for the day',
        decimal_places=2,
        max_digits=10,
        blank=True,
        null=True,
        )

    class Meta:
        managed = False
        db_table = 'budgetdb_accounttotal'


class AccountHost(BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Financial Institution'
        verbose_name_plural = 'Financial Institutions'
        ordering = ['name']

    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budgetdb:list_accounthost')


class Currency(models.Model):
    class Meta:
        verbose_name = 'Currency'
        verbose_name_plural = 'Currencies'
        ordering = ['priority']

    name = models.CharField(max_length=200)
    name_short = models.CharField(max_length=10)
    symbol = models.CharField(max_length=5)
    priority = models.IntegerField("priority", blank=True)

    def __str__(self):
        return self.name


class AccountPresentation(BaseSoftDelete):
    class Meta:
        managed = False
        db_table = 'budgetdb_account_presentation'

    id = models.BigIntegerField(primary_key=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    account_host = models.ForeignKey(AccountHost, on_delete=models.DO_NOTHING)
    account_parent = models.ForeignKey("Account", on_delete=models.DO_NOTHING, blank=True, null=True)
    name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=200, blank=True)
    childrens = models.CharField(max_length=200, blank=True, null=True)
    parent = models.CharField(max_length=200, blank=True, null=True)
    owner = models.ForeignKey("User", on_delete=models.DO_NOTHING, blank=False, null=False,
                              related_name='object_owner_%(app_label)s_%(class)s')


class AccountReport():
    def __init__(self, accountname=None, accountid=None, isaccountparent=True, year=None, month=None, deposits=None, withdrawals=None, dividends=None, balance_end=None, rate=None, interests=None):
        self.year = year
        self.month = month
        self.deposits = Decimal(0.00) if deposits is None else deposits
        self.withdrawals = Decimal(0.00) if withdrawals is None else withdrawals
        self.dividends = Decimal(0.00) if dividends is None else dividends
        self.balance_end = Decimal(0.00) if balance_end is None else balance_end
        self.rate = Decimal(0.00) if rate is None else rate
        self.interests = Decimal(0.00) if interests is None else interests
        self.accountname = '' if accountname is None else accountname
        self.accountid = accountid
        self.isaccountparent = isaccountparent

    def addmonthYearly(self, monthreport):
        self.deposits += monthreport.deposits
        self.withdrawals += monthreport.withdrawals
        self.dividends += monthreport.dividends
        self.balance_end = monthreport.balance_end
        self.rate = ((((self.rate/Decimal(100)) + Decimal(1)) * ((monthreport.rate/Decimal(100)) + Decimal(1))) - Decimal(1))*Decimal(100)
        self.interests += monthreport.interests

    def addAccountFormonth(self, monthreport):
        self.deposits += monthreport.deposits
        self.withdrawals += monthreport.withdrawals
        self.dividends += monthreport.dividends
        self.balance_end += monthreport.balance_end
        self.interests += monthreport.interests
        self.rate = (self.interests / (self.balance_end - self.interests))*Decimal(100)


class Account(BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'
        ordering = ['account_host__name', 'name']

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    date_open = models.DateField('date opened', blank=True, null=True)
    date_closed = models.DateField('date closed', blank=True, null=True)
    account_host = models.ForeignKey(AccountHost, on_delete=models.CASCADE)
    account_parent = models.ForeignKey("Account", on_delete=models.CASCADE, blank=True, null=True, related_name='account_children')
    name = models.CharField(max_length=200)
    currency = models.ForeignKey("Currency", on_delete=models.DO_NOTHING, blank=False, null=False)
    account_number = models.CharField(max_length=200, blank=True)
    comment = models.CharField("Comment", max_length=200, blank=True, null=True)
    TFSA = models.BooleanField('Account is a TFSA for canadian fiscal considerations', default=False)
    RRSP = models.BooleanField('Account is a RRSP for canadian fiscal considerations', default=False)

    def __str__(self):
        return self.account_host.name + " - " + self.name

    def get_absolute_url(self):
        return reverse('budgetdb:list_account_simple')

    def balance_by_EOD(self, dateCheck):

        audit_today = Transaction.objects.filter(account_source_id=self.id, date_actual=dateCheck, audit=True, is_deleted=False).order_by('-date_actual')[:1]
        if audit_today.count() == 1:
            return audit_today.first().amount_actual

        balance = Decimal(0.00)

        childrens = self.account_children.all()
        if childrens.count() > 0:
            for children in childrens:
                balance += children.balance_by_EOD(dateCheck)
            return balance

        closestAudit = Transaction.objects.filter(account_source_id=self.id, date_actual__lte=dateCheck, audit=True, is_deleted=False).order_by('-date_actual')[:1]
        if closestAudit.count() == 0:
            balance = Decimal(0.00)
            events = Transaction.objects.filter(date_actual__lte=dateCheck, is_deleted=False)
        else:
            balance = Decimal(closestAudit.first().amount_actual)
            events = Transaction.objects.filter(date_actual__gt=closestAudit.first().date_actual, date_actual__lte=dateCheck, is_deleted=False)

        events = events.filter(account_source_id=self.id) | events.filter(account_destination_id=self.id)

        for event in events:
            amount = Decimal(0.00)
            if event.audit is True:
                balance = event.amount_actual
            elif not (event.budget_only is True and event.date_actual <= date.today()):
                if event.account_destination_id == self.id:
                    balance += event.amount_actual
                if event.account_source_id == self.id:
                    balance -= event.amount_actual

        return balance

    def build_yearly_report_unit(self, year):
        start_date = datetime(year, 1, 1)
        account_list = Account.objects.filter(account_parent_id=self.id, is_deleted=False).exclude(date_closed__lt=start_date)
        previous_day = start_date + timedelta(days=-1)

        accountsReport = []
        for account in account_list:
            account_report = account.build_yearly_report_unit(year)
            accountsReport.append(account_report)

        if account_list.first() is None:
            # if it's a account without children, return a report with 12 months + total
            account_report = []
            balance_beginning = self.balance_by_EOD(previous_day)
            report_account_year = AccountReport(isaccountparent=False)
            for month in range(12):
                report_current_month = self.build_report(year, month+1, balance_beginning)
                report_account_year.addmonthYearly(report_current_month)
                account_report.append(report_current_month)
                balance_beginning = report_current_month.balance_end
            account_report.append(report_account_year)
            accountsReport = account_report
        else:
            # if the account has childrens, it can't have direct transactions, just sum the childrens
            # add a check so as to not add parent accounts
            reports_totals_monthly = [AccountReport(accountname=self.name, accountid=self.id) for i in range(13)]
            for account_report in accountsReport:
                # do not add parent accounts to the totals
                if account_report[0].isaccountparent:
                    continue
                for month in range(13):
                    reports_totals_monthly[month].addAccountFormonth(account_report[month])
                try:
                    reports_totals_monthly[month].rate = 100 * (reports_totals_monthly[month].interests / (reports_totals_monthly[month].balance_end - reports_totals_monthly[month].interests))
                except (InvalidOperation):
                    reports_totals_monthly[month].rate = 0
            accountsReport.append(reports_totals_monthly)
        return accountsReport

    def build_yearly_report(self, year):
        account_report = self.build_yearly_report_unit(year)
        accountsReport = []
        # if there is only one account in the report,
        # put it in a list so that the template can iterate over it
        # this is a really ugly test, find something better
        if len(account_report) == 13:
            accountsReport.append(account_report)
        else:
            accountsReport = account_report

        return accountsReport

    def build_report(self, year, month=None, balance_beginning=None):
        if month is None:
            start_date = datetime(year-1, 12, 31)
            end_date = datetime(year, 12, 31)
        else:
            start_date = datetime(year, month, 1)
            end_date = start_date + relativedelta(day=+31)

        balance_end = self.balance_by_EOD(end_date)
        transactions = Transaction.objects.filter(date_actual__gt=start_date, date_actual__lte=end_date, is_deleted=False,)
        deposits = transactions.filter(account_destination=self, audit=False, is_deleted=False).aggregate(Sum('amount_actual'))['amount_actual__sum']
        withdrawals = transactions.filter(account_source=self, audit=False, is_deleted=False).aggregate(Sum('amount_actual'))['amount_actual__sum']
        if withdrawals is None:
            withdrawals = Decimal(0)
        if deposits is None:
            deposits = Decimal(0)
        dividends = Decimal(0)
        interests = Decimal(0)
        rate = Decimal(0)
        if balance_beginning is not None and balance_beginning != 0:
            interests = balance_end - balance_beginning - deposits + withdrawals - dividends
            rate = (interests / balance_beginning) * Decimal(100)
        reportmonth = AccountReport(year=year,
                                    month=month,
                                    balance_end=balance_end,
                                    deposits=deposits,
                                    accountname=self.name,
                                    withdrawals=withdrawals,
                                    interests=interests,
                                    rate=rate,
                                    accountid=self.id,
                                    isaccountparent=False,
                                    )
        return reportmonth

    def build_report_with_balance(self, start_date, end_date):
        events = Transaction.view_objects.filter(date_actual__gt=start_date, date_actual__lte=end_date, is_deleted=False).order_by('date_actual', 'audit')
        childrens = self.account_children.filter(is_deleted=False)
        account_list = Account.objects.filter(id=self.id, is_deleted=False) | childrens
        events = events.filter(account_destination__in=account_list) | events.filter(account_source__in=account_list)
        # balance = Decimal(Account.view_objects.get(id=self.id).balance_by_EOD(start_date))
        balance = Decimal(self.balance_by_EOD(start_date))
        for event in events:
            amount = Decimal(0.00)
            if event.audit is True:
                balance = event.amount_actual
                if childrens.count() > 0:
                    total_with_children = Decimal(self.balance_by_EOD(event.date_actual))
                    event.calc_amount = str(event.amount_actual) + "$"
                    event.audit_amount = str(total_with_children) + "$"
                else:
                    event.calc_amount = str(event.amount_actual) + "$"
                    event.audit_amount = str(event.amount_actual) + "$"
                # event.viewname = f'{event._meta.app_label}:details_transaction_Audit'
            elif not (event.budget_only is True and event.date_actual <= date.today()):
                if event.account_destination_id == self.id:
                    amount += event.amount_actual
                if event.account_source_id == self.id:
                    amount -= event.amount_actual
                balance = balance + amount
                event.calc_amount = str(amount) + "$"
                # event.viewname = f'{event._meta.app_label}:details_transaction'
            event.balance = str(balance) + "$"
            # checking if the event is part of a joinedTransaction
            if event.transactions.first() is not None:
                event.joinedtransaction = event.transactions.first()
            elif event.budgetedevent is not None:
                if event.budgetedevent.budgeted_events.first() is not None:
                    event.joinedtransaction = event.budgetedevent.budgeted_events.first()
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
                f"    AND (t.account_source_id={self.id} OR t.account_destination_id={self.id}) AND t.audit = 0 AND t.is_deleted = 0 " \
                f"LEFT JOIN budgetdb.budgetdb_transaction ta ON c.db_date = ta.date_actual " \
                f"    AND ta.audit = 1 AND ta.account_source_id = {self.id} AND ta.is_deleted = 0 " \
                f"WHERE c.db_date BETWEEN '{start_date}' AND '{end_date}' " \
                f"GROUP BY c.db_date " \
                f"ORDER BY c.db_date "

        # get children account data
        childaccounts = Account.view_objects.filter(account_parent_id=self.id, is_deleted=False)
        childcount = childaccounts.count()
        # is this all done with DB queries?  Can I do it all in memory?
        if (childcount > 0):  # If children, account is virtual, only check childrens
            dailybalances = MyCalendar.objects.filter(db_date__gt=start_date, db_date__lte=end_date)
            childbalances = []
            # get the balances for the subaccounts
            for childaccount in childaccounts:
                childbalance = childaccount.build_balance_array(start_date, end_date)
                childbalances.append(childbalance)
            index = 0
            for day in dailybalances:
                # If the parent account has an audit, do not add the child accounts.
                # good for the audited day but next day probably won't be OK...
                day.balance = Decimal(0.00)
                for i in range(childcount):
                    day.balance += childbalances[i][index].balance
                index += 1
        else:  # no children, calculate account
            # fetch audits and deltas
            dailybalances = AccountBalances.objects.raw(sqlst)

            # add the balances
            previous_day = start_date + relativedelta(days=-1)
            balance = self.balance_by_EOD(previous_day)
            for day in dailybalances:
                if day.audit is not None:
                    balance = day.audit
                else:
                    if day.delta is not None:
                        balance += day.delta
                day.balance = balance

        return dailybalances


class AccountCategory(BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Account Category'
        verbose_name_plural = 'Account Categories'
        ordering = ['name']

    accounts = models.ManyToManyField(Account, related_name='account_categories')
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budgetdb:list_accountcategory')


class CatSums(models.Model):
    cat1 = models.ForeignKey("Cat1", on_delete=models.DO_NOTHING)
    cattype = models.ForeignKey("CatType", on_delete=models.DO_NOTHING)
    cat2 = models.ForeignKey("Cat2", on_delete=models.DO_NOTHING)
    month = models.IntegerField("month", blank=True)
    total = models.DecimalField('balance for the day', decimal_places=2, max_digits=10,
                                blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'budgetdb_cattotals'

    def build_cat1_totals_array(self, start_date, end_date):
        # don't do the sql = thing in prod
        sqlst = f"SELECT " \
                f"row_number() OVER () as id, " \
                f"t.cat1_id, " \
                f"c2.cattype_id AS cattype_id, " \
                f"sum(t.amount_actual) AS total " \
                f"FROM budgetdb.budgetdb_transaction t " \
                f"JOIN budgetdb.budgetdb_cat1 c1 ON t.cat1_id = c1.id " \
                f"JOIN budgetdb.budgetdb_cat2 c2 ON t.cat2_id = c2.id " \
                f"WHERE t.date_actual BETWEEN '{start_date}' AND '{end_date}' " \
                f'AND t.cat1_id IS NOT Null ' \
                f"GROUP BY t.cat1_id, c2.cattype_id "  \
                f"ORDER BY c1.name "

        print(sqlst)
        cat1_totals = CatSums.objects.raw(sqlst)

        return cat1_totals

    def build_cat2_totals_array(self, start_date, end_date):
        # don't do the sql = thing in prod
        sqlst = f"SELECT " \
                f"row_number() OVER () as id, " \
                f"t.cat1_id, " \
                f"t.cat2_id, " \
                f"c2.cattype_id AS cattype_id, " \
                f"sum(t.amount_actual) AS total " \
                f"FROM budgetdb.budgetdb_transaction t " \
                f"JOIN budgetdb.budgetdb_cat1 c1 ON t.cat1_id = c1.id " \
                f"JOIN budgetdb.budgetdb_cat2 c2 ON t.cat2_id = c2.id " \
                f"WHERE t.date_actual BETWEEN '{start_date}' AND '{end_date}' " \
                f'AND t.cat1_id IS NOT Null ' \
                f"GROUP BY t.cat1_id, c2.cattype_id, t.cat2_id "  \
                f"ORDER BY c1.name "

        print(sqlst)
        cat1_totals = CatSums.objects.raw(sqlst)

        return cat1_totals

    def build_monthly_cat1_totals_array(self, start_date, end_date, cat_id):
        # don't do the sql = thing in prod
        sqlst = f"SELECT " \
                f"row_number() OVER () as id, " \
                f"t.cat1_id, " \
                f"year(t.date_actual) AS year, " \
                f"month(t.date_actual) AS month, " \
                f"c2.cattype_id AS cattype_id, " \
                f"sum(t.amount_actual) AS total " \
                f"FROM budgetdb.budgetdb_transaction t " \
                f"JOIN budgetdb.budgetdb_cat1 c1 ON t.cat1_id = c1.id " \
                f"JOIN budgetdb.budgetdb_cat2 c2 ON t.cat2_id = c2.id " \
                f"WHERE t.date_actual BETWEEN '{start_date}' AND '{end_date}' " \
                f"AND t.cat1_id = '{cat_id}' " \
                f"GROUP BY t.cat1_id, c2.cattype_id, month(t.date_actual) "  \
                f"ORDER BY c1.name, t.date_actual "

        print(sqlst)
        cat1_totals = CatSums.objects.raw(sqlst)

        return cat1_totals

    def build_monthly_cat2_totals_array(self, start_date, end_date, cat_id):
        # don't do the sql = thing in prod
        sqlst = f"SELECT " \
                f"row_number() OVER () as id, " \
                f"t.cat2_id, " \
                f"year(t.date_actual) AS year, " \
                f"month(t.date_actual) AS month, " \
                f"c2.cattype_id AS cattype_id, " \
                f"sum(t.amount_actual) AS total " \
                f"FROM budgetdb.budgetdb_transaction t " \
                f"JOIN budgetdb.budgetdb_cat2 c2 ON t.cat2_id = c2.id " \
                f"WHERE t.date_actual BETWEEN '{start_date}' AND '{end_date}' " \
                f"AND t.cat2_id = '{cat_id}' " \
                f"GROUP BY t.cat2_id, c2.cattype_id, month(t.date_actual), year(t.date_actual) "  \
                f"ORDER BY c2.name, t.date_actual "

        print(sqlst)
        cat1_totals = CatSums.objects.raw(sqlst)

        return cat1_totals


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

    def build_year_month_array(self, start_date, end_date):
        # don't do the sql = thing in prod
        sqlst = f"SELECT distinct " \
                f"row_number() OVER () as id, " \
                f"c.year,c.month " \
                f"FROM budgetdb.budgetdb_mycalendar c " \
                f"WHERE c.db_date BETWEEN '{start_date}' AND '{end_date}' " \
                f"ORDER BY c.year, c.month "

        print(sqlst)
        dates_array = MyCalendar.objects.raw(sqlst)

        return dates_array


class CatBudget(BaseSoftDelete, UserPermissions):
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


class CatType(BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Category Type'
        verbose_name_plural = 'Categories Type'
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budgetdb:list_cattype')


class Cat1(BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    name = models.CharField(max_length=200)
    catbudget = models.ForeignKey('CatBudget', on_delete=models.CASCADE,
                                  blank=True, null=True)
    cattype = models.ForeignKey(CatType, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budgetdb:list_cat1')


class Cat2(BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Sub Category'
        verbose_name_plural = 'Sub Categories'
        ordering = ['name']

    cat1 = models.ForeignKey(Cat1, on_delete=models.CASCADE)
    cattype = models.ForeignKey(CatType, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    catbudget = models.ForeignKey(CatBudget, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budgetdb:details_cat1', kwargs={'pk': self.cat1.pk})


class Vendor(BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Account audit point'
        verbose_name_plural = 'Account audit points'
        ordering = ['name']

    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budgetdb:list_vendor')


class Transaction(BaseSoftDelete):
    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'

    objects = models.Manager()  # The default manager.
    view_objects = TransactionViewerManager()
    admin_objects = TransactionAdminManager()

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    budgetedevent = models.ForeignKey("BudgetedEvent", on_delete=models.CASCADE, blank=True,
                                      null=True)
    date_planned = models.DateField('planned date', blank=True, null=True)
    # date_planned only populated if linked to a budgeted_event
    # will break if repetition pattern of BE changes... so BE can't change if it has attached Ts
    date_actual = models.DateField('date of the transaction')
    joined_order = models.IntegerField('position in a joined transaction', blank=True,
                                       null=True)
    amount_planned = models.DecimalField(
        'planned amount', decimal_places=2, max_digits=10, blank=True, null=True
    )
    amount_actual = models.DecimalField(
        'transaction amount', decimal_places=2, max_digits=10, default=Decimal('0.00')
    )
    currency = models.ForeignKey("Currency", on_delete=models.DO_NOTHING, blank=False, null=False)
    amount_actual_foreign_currency = models.DecimalField(
        'original amount', decimal_places=2, max_digits=10, default=Decimal('0.00')
    )
    Fuel_L = models.DecimalField(
        'Fuel quantity', decimal_places=3, max_digits=7, blank=True, null=True
    )
    Fuel_price = models.DecimalField(
        'Fuel cost per', decimal_places=3, max_digits=5, blank=True, null=True
    )

    description = models.CharField('Description', max_length=200)
    comment = models.CharField('optional comment', max_length=200, blank=True, null=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, blank=True, null=True)
    cat1 = models.ForeignKey(Cat1, on_delete=models.CASCADE, blank=True, null=True)
    cat2 = models.ForeignKey(Cat2, on_delete=models.CASCADE, blank=True, null=True)
    ismanual = models.BooleanField('Is this an event that require manual intervention?', default=False)
    account_source = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='t_account_source', blank=True, null=True
    )
    account_destination = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='t_account_destination', blank=True, null=True
    )
    statement = models.ForeignKey("Statement", on_delete=models.CASCADE, blank=True, null=True)
    verified = models.BooleanField('Verified in a statement', default=False)
    audit = models.BooleanField(
        'Audit',
        default=False,
        )
    receipt = models.BooleanField(
        'Checked with receipt',
        default=False,
        )
    budget_only = models.BooleanField(
        'counts as 0 after today, only exists to simulate future expenses',
        default=False,
        )

    def __str__(self):
        return f'{self.description} - {self.date_actual}'

    def get_absolute_url(self):
        return reverse('budgetdb:details_transaction', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        if self._state.adding and self.budgetedevent is not None and self.date_planned is not None:
            if Transaction.objects.filter(budgetedevent=self.budgetedevent, date_planned=self.date_planned).exists():
                # don't save a duplicate
                pass
            else:
                super(Transaction, self).save(*args, **kwargs)
        else:
            super(Transaction, self).save(*args, **kwargs)

    def can_edit(self):
        if self.account_destination:
            if self.account_destination.can_edit():
                return True
        if self.account_source:
            if self.account_source.can_edit():
                return True
        return False

    def can_view(self):
        if self.account_destination:
            if self.account_destination.can_view():
                return True
        if self.account_source:
            if self.account_source.can_view():
                return True
        return False


class BudgetedEvent(BaseSoftDelete, UserPermissions):
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
    budgetedevent_percent_ref = models.ForeignKey('self', on_delete=models.CASCADE, blank=True,
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
    ismanual = models.BooleanField('Is this an event that require manual intervention?', default=False)
    repeat_start = models.DateField('date of the first event')
    repeat_stop = models.DateField('date of the last event, optional', blank=True, null=True)
    nb_iteration = models.IntegerField('number of repetitions, null if not applicable', blank=True,
                                       null=True)  # is this implementable on complex patterns?
    joined_order = models.IntegerField('position in a joined transaction', blank=True,
                                       null=True)
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
    repeat_weekofmonth_mask = models.IntegerField('binary mask of applicable month week. Always Applicable ALL=31',
                                                  default=63)

    repeat_weekday_mask = models.IntegerField('binary mask of applicable week day. Always Applicable ALL=127',
                                              default=127)
    # Mon=1, Tue=2,Wed=4, Thu=8, Fri=16, Sat=32, Sun=64, all=127
    # workweek=31   weekend=96

    def __str__(self):
        return self.description

    def get_absolute_url(self):
        return reverse('budgetdb:details_be', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        super(BudgetedEvent, self).save(*args, **kwargs)
        self.deleteUnverifiedTransaction()
        self.createTransactions()

    def checkDate(self, dateCheck):
        # verifies if the event happens on the dateCheck. should handle all the recurring patterns

        # https://stackoverflow.com/a/13565185
        # get close to the end of the month for any day, and add 4 days 'over'
        next_month = dateCheck.replace(day=28) + relativedelta(days=4)
        # subtract the number of remaining 'overage' days to get last day of current month,
        # or said programattically said, the previous day of the first of next month
        last_day_month = next_month + relativedelta(days=-next_month.day)

        # budget only should be in the future only
        if self.budget_only is True and dateCheck < date.today():
            return False
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
        # if month interval is used, check if the difference is a repeat of interval.
        # Days must match OR must be last day of the month and planned day is after
        # *************************************************************
        elif self.repeat_interval_months != 0 and \
                (
                    (
                        dateCheck.day != self.repeat_start.day
                        and
                        (self.repeat_start.day < last_day_month.day
                         or
                         last_day_month != dateCheck)
                    )
                or
                 (dateCheck.month - self.repeat_start.month) % self.repeat_interval_months != 0):
            return False
        # if weeks interval is used, check if the difference is a repeat of interval. Weekday must match
        elif self.repeat_interval_weeks != 0 and \
                (dateCheck.weekday() != self.repeat_start.weekday() or
                 ((dateCheck - self.repeat_start).days / 7) % self.repeat_interval_weeks != 0):
            return False
        else:
            return True

    def listPotentialTransactionDates(self, n=20, begin_interval=datetime.today().date(), interval_length_months=12):
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

    def listNextTransactions(self, n=20, begin_interval=datetime.today().date(), interval_length_months=60):
        transactions = Transaction.objects.filter(budgetedevent_id=self.id, is_deleted=False)
        transactions = transactions.filter(date_actual__gt=begin_interval)
        end_date = begin_interval + relativedelta(months=interval_length_months)
        transactions = transactions.filter(date_actual__lte=end_date).order_by('date_actual')[:n]
        return transactions

    def listPreviousTransaction(self, n=20, begin_interval=datetime.today().date(), interval_length_months=60):
        transactions = Transaction.objects.filter(budgetedevent_id=self.id, is_deleted=False)
        transactions = transactions.filter(date_actual__lt=begin_interval)
        end_date = begin_interval - relativedelta(months=interval_length_months)
        transactions = transactions.filter(date_actual__gt=end_date).order_by('-date_actual')[:n]
        return transactions

    def createTransactions(self, n=400, begin_interval=None, interval_length_months=60):
        if begin_interval is None:
            begin_interval = self.repeat_start
        transaction_dates = self.listPotentialTransactionDates(n=n, begin_interval=begin_interval, interval_length_months=interval_length_months)
        if transaction_dates:
            self.generated_interval_start = transaction_dates[0]
        else:
            return

        for date in transaction_dates:
            new_transaction = Transaction.objects.create(date_planned=date,
                                                         date_actual=date,
                                                         amount_actual=self.amount_planned,
                                                         amount_planned=self.amount_planned,
                                                         ismanual=self.ismanual,
                                                         description=self.description,
                                                         budgetedevent_id=self.id,
                                                         account_destination=self.account_destination,
                                                         account_source=self.account_source,
                                                         cat1=self.cat1,
                                                         cat2=self.cat2,
                                                         vendor=self.vendor,
                                                         budget_only=self.budget_only,
                                                         joined_order=self.joined_order,
                                                         currency_id=1,
                                                         amount_actual_foreign_currency=0,
                                                         )
            new_transaction.save()
            # Needs a lot more work with these interval management  #######
            self.generated_interval_stop = date

    def deleteUnverifiedTransaction(self):
        # don't delete if it's verified in a statement
        # don't delete if it's verified with a receipt
        # don't delete if it's flagged as deleted
        transactions = Transaction.objects.filter(budgetedevent=self.id, verified=False, is_deleted=False, receipt=False)
        transactions.delete()
        self.generated_interval_start = None
        self.generated_interval_stop = None


class Statement (BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Statement'
        verbose_name_plural = 'Statements'

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='statement_account')
    balance = models.DecimalField('Statement balance', decimal_places=2, max_digits=10, default=Decimal('0.0000'))
    minimum_payment = models.DecimalField('Minimum Payment', decimal_places=2, max_digits=10, default=Decimal('0.0000'))
    statement_date = models.DateField('date of the statement')
    statement_due_date = models.DateField('date where payment is due', blank=True, null=True)
    comment = models.CharField(max_length=200, blank=True, null=True)
    payment_transaction = models.ForeignKey('Transaction', on_delete=models.CASCADE, related_name='payment_transaction',
                                            blank=True, null=True)

    def __str__(self):
        return self.account.name + " " + self.statement_date.strftime('%Y-%m-%d')

    def get_absolute_url(self):
        return reverse('budgetdb:details_statement', kwargs={'pk': self.pk})


class Recurring(models.Model):
    # description of budgeted events
    class Meta:
        verbose_name = 'Recurring'
        verbose_name_plural = 'Recurring'

    generated_interval_start = models.DateTimeField('begining of the generated events interval', blank=True, null=True)
    generated_interval_stop = models.DateTimeField('end of the generated events interval', blank=True, null=True)
    repeat_start = models.DateField('date of the first event')
    repeat_stop = models.DateField('date of the last event, optional', blank=True, null=True)
    nb_iteration = models.IntegerField('number of repetitions, null if not applicable', blank=True,
                                       null=True)  # is this implementable on complex patterns?
    repeat_interval_days = models.IntegerField('period in days, 0 if not applicable', default=0)
    repeat_interval_years = models.IntegerField('period in years, 0 if not applicable', default=0)
    repeat_interval_months = models.IntegerField('period in months, 0 if not applicable', default=0)
    repeat_interval_weeks = models.IntegerField('period in weeks, 0 if not applicable', default=0)

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

    def checkDate(self, dateCheck):
        # verifies if the event happens on the dateCheck. should handle all the recurring patterns

        # https://stackoverflow.com/a/13565185
        # get close to the end of the month for any day, and add 4 days 'over'
        next_month = dateCheck.replace(day=28) + relativedelta(days=4)
        # subtract the number of remaining 'overage' days to get last day of current month,
        # or said programattically said, the previous day of the first of next month
        last_day_month = next_month + relativedelta(days=-next_month.day)

        # not before first event
        if dateCheck < self.repeat_start:
            return False
        # same day OK
        elif self.repeat_start == dateCheck:
            return True
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
        # if month interval is used, check if the difference is a repeat of interval.
        # Days must match OR must be last day of the month and planned day is after
        # *************************************************************
        elif self.repeat_interval_months != 0 and \
                (
                    (
                        dateCheck.day != self.repeat_start.day
                        and
                        (self.repeat_start.day < last_day_month.day
                         or
                         last_day_month != dateCheck)
                    )
                or
                 (dateCheck.month - self.repeat_start.month) % self.repeat_interval_months != 0):
            return False
        # if weeks interval is used, check if the difference is a repeat of interval. Weekday must match
        elif self.repeat_interval_weeks != 0 and \
                (dateCheck.weekday() != self.repeat_start.weekday() or
                 ((dateCheck - self.repeat_start).days / 7) % self.repeat_interval_weeks != 0):
            return False
        else:
            return True

    def listNextTransactions(self, n=20, begin_interval=datetime.today().date(), interval_length_months=60):
        transactions = Transaction.objects.filter(budgetedevent_id=self.id, is_deleted=False)
        transactions = transactions.filter(date_actual__gt=begin_interval)
        end_date = begin_interval + relativedelta(months=interval_length_months)
        transactions = transactions.filter(date_actual__lte=end_date).order_by('date_actual')[:n]
        return transactions

    def listPreviousTransactions(self, n=20, begin_interval=datetime.today().date(), interval_length_months=60):
        transactions = Transaction.objects.filter(budgetedevent_id=self.id, is_deleted=False)
        transactions = transactions.filter(date_actual__lte=begin_interval)
        end_date = begin_interval + relativedelta(months=-interval_length_months)
        transactions = transactions.filter(date_actual__gt=end_date).order_by('date_actual')[:n]
        return transactions


class JoinedTransactions(BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Joined Transactions'
        verbose_name_plural = 'Joined Transactions'

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=200)
    comment = models.CharField(max_length=200, blank=True, null=True)
    transactions = models.ManyToManyField(Transaction, related_name='transactions')
    budgetedevents = models.ManyToManyField(BudgetedEvent, related_name='budgeted_events')
    isrecurring = models.BooleanField('Is this a recurring event?', default=True)
    recurring = models.ForeignKey(Recurring, on_delete=models.CASCADE, null=True)
