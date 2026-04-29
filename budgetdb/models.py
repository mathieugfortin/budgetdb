from crum import get_current_user
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager 
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist, ValidationError
from django.core.mail import EmailMessage
from django.db import models, transaction
from django.db.models import Sum, Q, Window, F
from django.db.models.functions import Cast, Coalesce, ExtractMonth, ExtractYear, RowNumber, TruncMonth
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.translation import gettext_lazy as _
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.urls import reverse

from .tokens import account_activation_token


class MyMeta(models.Model):
    class Meta:
        abstract = True

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)


class CustomUserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""
    use_in_migrations = True
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault("is_active", True)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault("is_active", True)

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name']
    username = None
    email = models.EmailField('email address', unique=True)
    friends = models.ManyToManyField("User", related_name='friends_users')
    email_verified = models.BooleanField('Email Verified', default=False, null=False)
    objects = CustomUserManager()
    
    def __str__(self):
        return self.email

    def send_verify_email(self):
        if not self.email_verified:
            user = self.first_name
            email = self.email
            subject = "Verify Email"
            message = render_to_string('budgetdb/user/email_validation_message.html', {
                'user': user,
                'domain': 'https://budget.patatemagique.biz/',
                'uid':urlsafe_base64_encode(force_bytes(self.pk)),
                'token':account_activation_token.make_token(self),
            })
            email = EmailMessage(
                subject, message, to=[email]
            )
            email.content_subtype = 'html'
            email.send()


class BaseManager(models.Manager):
    deleted_filter = "active_only"  # active_only - deleted_only - all
     
    def for_user(self, user=None):
        user = user or get_current_user()
        qs = super().get_queryset()
        qs = self.apply_lifecycle_filter(qs)

        if not user or user.is_anonymous:
            return qs.none()
        qs = self.apply_permission_filters(qs, user)
        return qs
        
    def get_queryset(self):
        return self.for_user(get_current_user())

    def apply_lifecycle_filter(self, qs):
        if self.deleted_filter == "active_only":
            return qs.filter(is_deleted=False)  
        elif self.deleted_filter == "deleted_only":
            return qs.filter(is_deleted=True)
        else: # self.deleted_filter == "all"
            return qs
        
    def apply_permission_filters(self, qs, user):
        is_owner = Q(owner=user)
        is_admin = Q(users_admin=user)
        is_system = Q(system_object=True)
        # Default permission logic (shared by both)
        return qs.filter(is_system | is_owner | is_admin).distinct()


class AdminManager(BaseManager):
    deleted_filter = "active_only"  # active_only - deleted_only - all


class ViewerManager(BaseManager):
    deleted_filter = "active_only"  # active_only - deleted_only - all

    def apply_permission_filters(self, qs, user):
        is_system = Q(system_object=True)
        is_owner = Q(owner=user)
        is_admin = Q(users_admin=user)
        is_viewer = Q(users_view=user)
        return qs.filter(is_system | is_owner | is_admin | is_viewer).distinct()


class ViewerDeletedManager(BaseManager):
    deleted_filter = "deleted_only"  # active_only - deleted_only - all

    def apply_permission_filters(self, qs, user):
        is_owner = Q(owner=user)
        is_admin = Q(users_admin=user)
        is_viewer = Q(users_view=user)
        return qs.filter(is_owner | is_admin | is_viewer).distinct()


class BaseTransactionManager(BaseManager):
    # Default settings that subclasses can override
    deleted_filter = "active_only"  # active_only - deleted_only - all
    permission_type = 'view' # 'view' or 'admin'
    require_all_accounts = False # False = OR, True = AND

    def apply_permission_filters(self, qs, user):
        from .models import Account

        if self.permission_type == 'admin':
            permitted_accounts = Account.admin_objects.for_user(user)
        else:
            permitted_accounts = Account.view_objects.for_user(user)

        # 3. Combine using AND (&) or OR (|)
        if self.require_all_accounts:
            source_invalid = Q(account_source__isnull=False) & ~Q(account_source__in=permitted_accounts)
            dest_invalid = Q(account_destination__isnull=False) & ~Q(account_destination__in=permitted_accounts)
            return qs.exclude(source_invalid).exclude(dest_invalid)        
        else:
            # Lax: You must own at least one side.
            return qs.filter(Q(account_source__in=permitted_accounts) | Q(account_destination__in=permitted_accounts))


class TransactionViewerManager(BaseTransactionManager):
    deleted_filter = "active_only"  # active_only - deleted_only - all
    permission_type = 'view'
    require_all_accounts = False


class TransactionDeletedViewerManager(BaseTransactionManager):
    deleted_filter = "deleted_only"  # active_only - deleted_only - all
    permission_type = 'view'
    require_all_accounts = False


class TransactionViewerAllManager(BaseTransactionManager):
    deleted_filter = "all"  # active_only - deleted_only - all
    permission_type = 'view'
    require_all_accounts = False


class TransactionAdminManager(BaseTransactionManager):
    deleted_filter = "active_only"  # active_only - deleted_only - all
    permission_type = 'admin'
    require_all_accounts = True # Strict check: Admin of both sides


class ClassOwner(models.Model):
    class Meta:
        abstract = True

    owner = models.ForeignKey("User", on_delete=models.CASCADE, blank=False, null=False,
                              related_name='object_owner_%(app_label)s_%(class)s')
    
    def save(self, *args, **kwargs):
        user = get_current_user()
        if user and not user.pk:
            user = None
        if not self.pk and self._state.adding:
            self.owner = user
        super(ClassOwner, self).save(*args, **kwargs)


class UserPermissions(ClassOwner):
    class Meta:
        abstract = True

    # groups_admin = models.ManyToManyField(Group, related_name='g_can_mod_%(app_label)s_%(class)s', blank=True)
    # groups_view = models.ManyToManyField(Group, related_name='g_can_view_%(app_label)s_%(class)s', blank=True)
    users_admin = models.ManyToManyField("User", related_name='users_full_access_%(app_label)s_%(class)s', blank=True)
    users_view = models.ManyToManyField("User", related_name='users_view_access_%(app_label)s_%(class)s', blank=True)
    objects = models.Manager()  # The default manager.
    view_objects = ViewerManager()
    view_deleted_objects = ViewerDeletedManager()
    admin_objects = AdminManager()
    system_object = models.BooleanField(default=False)

    def can_edit(self):
        user = get_current_user()
        if self.owner == user:
            return True
        if self.system_object:
            return False
        if user is None:
            return False
        if self.users_admin.filter(pk=user.pk).exists():
            return True
        return False

    def can_view(self):
        if self.system_object:
            return True
        user = get_current_user()
        if self.owner == user:
            return True
        if user is None:
            return False
        if self.users_admin.filter(pk=user.pk).exists():
            return True
        if self.users_view.filter(pk=user.pk).exists():
            return True
        return False


class BaseSoftDelete(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey("User", null=True, blank=True, on_delete=models.CASCADE, related_name='deleted_by_%(app_label)s_%(class)s')

    class Meta:
        abstract = True

    def soft_delete(self):
        if self.is_deleted:
            return
        if self.can_edit():
            self.is_deleted = True
            user = get_current_user()
            if user and not user.is_anonymous:
                self.deleted_by = user
            self.deleted_at = timezone.now()
            self.save()

    def soft_undelete(self):
        if not self.is_deleted:
            return
        if self.can_edit():
            self.is_deleted = False
            self.deleted_by = None
            self.deleted_at = None
            self.save()

    def delete(self, *args, **kwargs):
        self.soft_delete()


class Preference(models.Model):
    COLOR_MODE = {
        "light": "Light",
        "dark": "Dark",
    }
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    slider_start = models.DateField(blank=True)
    slider_stop = models.DateField(blank=True)
    timeline_stop = models.DateField(blank=True, null=True)
    timeline_start = models.DateField(blank=True, null=True)
    statement_buffer_before = models.IntegerField('days before statement date in transactionlist view', default=36)
    statement_buffer_after = models.IntegerField('days after statement date in transactionlist view', default=0)
    currencies = models.ManyToManyField("Currency", related_name="currencies")
    currency_prefered = models.ForeignKey("Currency",
                                          on_delete=models.DO_NOTHING,
                                          related_name="currency_prefered"
                                          )
    favorite_accounts = models.ManyToManyField("Account", related_name="favorites", blank=True)
    theme = models.CharField('Color Mode',max_length=15, choices=COLOR_MODE, default='Dark')
    # add ordre of listing, old first/ new first

    def save(self, *args, **kwargs):

        super(Preference, self).save(*args, **kwargs)


class Messages(models.Model):
    MESSAGE_TYPE = {
        "tutorial": "Tutorial",
    }
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=2000)
    message_type = models.CharField('Type',max_length=15, choices=MESSAGE_TYPE, default='Tutorial')


class Invitation(MyMeta, BaseSoftDelete, ClassOwner):
    class Meta:
        verbose_name = 'Invitation'
        verbose_name_plural = 'Invitations'
        ordering = ['email']

    email = models.EmailField(max_length=254, blank=False, null=False)
    accepted = models.BooleanField(default=False)
    rejected = models.BooleanField(default=False)


    def __str__(self):
        return self.email

    def get_absolute_url(self):
        return reverse('budgetdb:list_invitation')

    def send_invite_email(self):
        template = 'budgetdb/user/email_share_message.html'
        subject = "Budget Sharing"
        try:
            invited_user = User.objects.get(email=self.email)
        except ObjectDoesNotExist:
            template = 'budgetdb/user/email_invitation_message.html'
            subject = "Budget Invitation"

        email = self.email
        # current_site = Site.objects.get_current()

        message = render_to_string(template, {
            # 'request': request,
            'inviter': self.owner,
            'email': self.email,
            'domain': 'https://budget.patatemagique.biz',
        })
        email = EmailMessage(
            subject, message, to=[email]
        )
        email.content_subtype = 'html'
        email.send()


class AccountBalanceDB(models.Model):
    class Meta:
        # This makes the "Filter by account AND date" lightning fast
        unique_together = ('account', 'db_date') 
        indexes = [
            models.Index(fields=['account', 'db_date']),
        ]
    db_date = models.DateField() 
    account = models.ForeignKey("Account", on_delete=models.CASCADE, related_name="balances", blank=True, null=True)
    
    # Inputs
    audit = models.DecimalField('audited amount', decimal_places=2, max_digits=15, blank=True, null=True)
    is_audit = models.BooleanField('override of the account balance', default=False)
    
    # Calculated Fields
    delta = models.DecimalField('relative change', decimal_places=2, max_digits=15, default=Decimal('0.00'), blank=False, null=False,)
    balance = models.DecimalField('balance for the day', decimal_places=2, max_digits=15, default=Decimal('0.00'), blank=False, null=False,)
    
    # State Flags
    balance_is_dirty = models.BooleanField('If there is a new transaction for this day, the balance is not reliable', default=False)

    def __str__(self):
        return f'{self.account.name} - {self.db_date.strftime("%Y-%m-%d")} - {self.balance}'

    def save(self, *args, **kwargs):
        if self.is_audit and self.audit is not None:
            self.balance = self.audit
            
        super().save(*args, **kwargs)


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
        ordering = ['priority', 'name']

    name = models.CharField(max_length=200)
    name_short = models.CharField(max_length=10)
    symbol = models.CharField(max_length=5)
    priority = models.IntegerField("priority", blank=True)

    def __str__(self):
        return self.name


class AccountReport():
    def __init__(self,
                 accountname=None,
                 accountpk=None,
                 isaccountparent=True,
                 year=None,
                 month=None,
                 deposits=None,
                 withdrawals=None,
                 dividends=None,
                 balance_end=None,
                 rate=None,
                 interests=None):
        self.year = year
        self.month = month
        self.deposits = Decimal(0.00) if deposits is None else deposits
        self.withdrawals = Decimal(0.00) if withdrawals is None else withdrawals
        self.dividends = Decimal(0.00) if dividends is None else dividends
        self.balance_end = Decimal(0.00) if balance_end is None else balance_end
        self.rate = Decimal(0.00) if rate is None else rate
        self.interests = Decimal(0.00) if interests is None else interests
        self.accountname = '' if accountname is None else accountname
        self.accountpk = accountpk
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


class Account(MyMeta, BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = _('Account')
        verbose_name_plural = _('Accounts')
        ordering = ['account_host__name', 'name']

    SUM_CHILDREN = 'SUM'
    PARENT_OVERRIDE = 'OVR'
    CALC_CHOICES = [
        (SUM_CHILDREN, 'Strict Sum of Children'),
        (PARENT_OVERRIDE, 'Parent Audit Overrides (Hybrid)'),
    ]
    calc_mode = models.CharField(max_length=3, choices=CALC_CHOICES, default=SUM_CHILDREN)
    ofx_acct_id = models.CharField(max_length=100, blank=True, null=True, help_text="Bank's ACCTID from OFX")  # <ACCTID>
    ofx_org = models.CharField(max_length=50, blank=True, null=True) # <ORG>
    ofx_fid = models.CharField(max_length=50, blank=True, null=True) # <FID>
    ofx_flip_sign = models.BooleanField(default=False, help_text="Check if outflows are positive in OFX")
    ofx_flip_sign_set = models.BooleanField(default=False, help_text="don't ask user for flip sign")

    date_open = models.DateField('date opened', blank=False, null=False, default='2018-01-01')
    date_closed = models.DateField('date closed', blank=True, null=True)
    account_host = models.ForeignKey(AccountHost, on_delete=models.CASCADE)
    account_parent = models.ForeignKey("Account", on_delete=models.CASCADE, blank=True, null=True, related_name='account_children')
    name = models.CharField(max_length=200)
    currency = models.ForeignKey("Currency", on_delete=models.DO_NOTHING, blank=False, null=False)
    account_number = models.CharField(max_length=200, blank=True)
    comment = models.CharField("Comment", max_length=200, blank=True, null=True)
    TFSA = models.BooleanField('Account is a TFSA for canadian fiscal considerations', default=False)
    RRSP = models.BooleanField('Account is a RRSP for canadian fiscal considerations', default=False)
    unit_price = models.BooleanField('Do we keep unit quantity and cost per for this account', default=False)

    def __str__(self):
        user = get_current_user()
        preference = Preference.objects.get(user=user.id)
        star = ""
        if preference.favorite_accounts.filter(favorites=preference.id, id=self.pk):
            star = "★ "
        if user == self.owner:
            return star + self.account_host.name + " - " + self.name
        else:
            return star + self.account_host.name + " - " + self.owner.first_name.capitalize() + " - " + self.name

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        # save original values, when model is loaded from database,
        # in a separate attribute on the model
        instance._loaded_values = dict(zip(field_names, values))
        
        return instance

    @property
    def full_display_name(self):
        if self.owner.name == "user":
            return f"{self.account_host.name} - {self.name}"
        return f"{self.account_host.name} - ({self.owner.name}) - {self.name}"

    @property
    def implied_unit_price(self):
        if self.unit_price and self.total_units > 0:
            return self.latest_balance / self.total_units
        return None

    def ensure_records_exist(self, target_date):
        """Checks if records exist up to target_date; creates them if not."""
        balances = self.balances.order_by('db_date').first()
        first_record = balances.db_date if balances else None
        # if there are balances missing at the start
        new_rows = []
        if first_record and first_record > self.date_open:
            current_date = self.date_open
            new_rows.append(AccountBalanceDB(
                    account=self,
                    db_date=self.date_open - timedelta(days=1),
                    balance=Decimal('0.00'),
                    audit=Decimal('0.00'),
                    is_audit=True,
                    balance_is_dirty=False 
                ))
            while current_date < first_record:
                new_rows.append(AccountBalanceDB(
                    account=self,
                    db_date=current_date,
                    balance_is_dirty=True # New rows are always dirty until first calculation
                ))
                current_date += timedelta(days=1)
        #if there are balances missing at the end or none before target_date
        last_record = self.balances.order_by('db_date').last()
        start_from = last_record.db_date + timedelta(days=1) if last_record else self.date_open
        current_date = start_from
        if start_from <= target_date:
            # if there are no balances, set the day before account openning at 0       
            if not last_record:
                new_rows.append(AccountBalanceDB(
                    account=self,
                    db_date=self.date_open - timedelta(days=1),
                    balance=Decimal('0.00'),
                    audit=Decimal('0.00'),
                    is_audit=True,
                    balance_is_dirty=False 
                ))

            while current_date <= target_date:
                new_rows.append(AccountBalanceDB(
                    account=self,
                    db_date=current_date,
                    balance_is_dirty=True # New rows are always dirty until first calculation
                ))
                current_date += timedelta(days=1)

        if new_rows:
            AccountBalanceDB.objects.bulk_create(new_rows)

    def get_balances(self, start_date, end_date):
        # Use an atomic block to prevent partial 'Clean' states
        with transaction.atomic():
            self.tree_balances_needed_cleaning(start_date, end_date)
        return AccountBalanceDB.objects.filter(
            account=self,
            db_date__gte=start_date,
            db_date__lte=end_date
        ).order_by('db_date')

    def get_balance(self, date):
        with transaction.atomic():
            self.tree_balances_needed_cleaning(date,date)
        return AccountBalanceDB.objects.get(account=self, db_date=date)

    def save(self, *args, **kwargs):
        ############
        ######### when saving and parent change, old and new parents needs to be reset
        ################

        # Convert string dates to date objects if necessary
        if isinstance(self.date_open, str):
            self.date_open = datetime.strptime(self.date_open, '%Y-%m-%d').date()
        if isinstance(self.date_closed, str):
            self.date_closed = datetime.strptime(self.date_closed, '%Y-%m-%d').date()

        if self._state.adding is True:
            super(Account, self).save(*args, **kwargs)            
        else:
            # Safely get old values; default to current values if _loaded_values is missing
            loaded = getattr(self, '_loaded_values', {})
            old_date_closed = loaded.get('date_closed', self.date_closed)

            super(Account, self).save(*args, **kwargs)            
            if self.date_closed != None and (old_date_closed is None or self.date_closed < old_date_closed):
                #remove unused balances 
                AccountBalanceDB.objects.filter(account=self,db_date__gt=self.date_closed).delete()

    def get_absolute_url(self):
        return reverse('budgetdb:list_account_simple')

    def build_yearly_report_unit(self, year):
        start_date = date(year, 1, 1)
        account_list = Account.objects.filter(account_parent_id=self.pk, is_deleted=False).exclude(date_closed__lt=start_date)
        previous_day = start_date + timedelta(days=-1)

        accountsReport = []
        for account in account_list:
            account_report = account.build_yearly_report_unit(year)
            accountsReport.append(account_report)

        if account_list.first() is None:
            # if it's a account without children, return a report with 12 months + total
            account_report = []
            balance_beginning = self.get_balance(previous_day)
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
            reports_totals_monthly = [AccountReport(accountname=self.name, accountpk=self.pk) for i in range(13)]
            for account_report in accountsReport:
                # do not add parent accounts to the totals
                if account_report[0].isaccountparent:
                    continue
                for month in range(13):
                    reports_totals_monthly[month].addAccountFormonth(account_report[month])
                try:
                    reports_totals_monthly[month].rate = 100 * (reports_totals_monthly[month].interests
                                                                / (reports_totals_monthly[month].balance_end - reports_totals_monthly[month].interests))
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
            start_date = date(year-1, 12, 31)
            end_date = date(year, 12, 31)
        else:
            start_date = date(year, month, 1)
            end_date = start_date + relativedelta(day=+31)

        balance_end = self.get_balance(end_date)
        transactions = Transaction.view_objects.filter(date_actual__gt=start_date, date_actual__lte=end_date, is_deleted=False,)
        deposits = transactions.filter(account_destination=self, audit=False).aggregate(Sum('amount_actual'))['amount_actual__sum']
        withdrawals = transactions.filter(account_source=self, audit=False).aggregate(Sum('amount_actual'))['amount_actual__sum']
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
                                    accountpk=self.pk,
                                    isaccountparent=False,
                                    )
        return reportmonth

    def build_report_with_balance(self, start_date, end_date):
        events = Transaction.view_objects.filter(date_actual__gt=start_date,
                                                 date_actual__lte=end_date,
                                                 is_deleted=False).order_by('date_actual', '-verified', 'audit','-id')
        childrens = self.account_children.filter(is_deleted=False)
        account_list = Account.objects.filter(id=self.pk, is_deleted=False) | childrens
        events = events.filter(account_destination__in=account_list) | events.filter(account_source__in=account_list)
        # balance = Decimal(Account.view_objects.get(id=self.pk).get_balance(start_date))
        balance = Decimal(self.get_balance(start_date))
        for event in events:
            amount = Decimal(0.00)
            event.account_view_id = self.pk
            if event.audit is True:
                balance = event.amount_actual
                if childrens.count() > 0:
                    total_with_children = Decimal(self.get_balance(event.date_actual))
                    event.calc_amount = str(event.amount_actual) + "$"
                    event.audit_amount = str(total_with_children) + "$"
                else:
                    event.calc_amount = str(event.amount_actual) + "$"
                    event.audit_amount = str(event.amount_actual) + "$"
                # event.viewname = f'{event._meta.app_label}:details_transaction_Audit'
            elif not (event.budget_only is True and event.date_actual <= date.today()):
                if event.account_destination_id == self.pk:
                    amount += event.amount_actual
                if event.account_source_id == self.pk:
                    amount -= event.amount_actual
                balance = balance + amount
                event.calc_amount = str(amount) + "$"
                # event.viewname = f'{event._meta.app_label}:details_transaction'
            event.balance = balance
            event.save()
            # checking if the event is part of a joinedTransaction
            if event.joined_transactions.first() is not None:
                event.joinedtransaction = event.joined_transactions.first()
            elif event.budgetedevent is not None:
                if event.budgetedevent.joined_transactions.first() is not None:
                    event.joinedtransaction = event.budgetedevent.joined_transactions.first()
        return events

    def leaf_balances_needed_cleaning(self, start_date, end_date):
        # after this is run, the interval start_date, end_date is clean
        # return False if the balances were not dirty and were not modified
        # return True if the balances were dirty and were modified

        closest_audit = AccountBalanceDB.objects.filter(account=self, db_date__lte=start_date, is_audit=True).order_by('-db_date').first()
        first_dirty = AccountBalanceDB.objects.filter(account=self, db_date__gte=closest_audit.db_date, db_date__lte=end_date,balance_is_dirty=True).order_by('db_date').first()

        if first_dirty is not None:
            self.build_balances_leaf(first_dirty.db_date, end_date)
            return True
        else:
            return False

    def tree_balances_needed_cleaning(self, start_date, end_date=None):
        # after this is run, the interval start_date, end_date is clean
        # return False if the balances were not dirty and were not modified
        # return True if the balances were dirty and were modified
        self.ensure_records_exist(end_date if end_date else start_date)
        child_accounts = Account.objects.filter(account_parent=self, is_deleted=False)
        
        # did *anything* in the subtree change?
        for child in child_accounts:
            child.tree_balances_needed_cleaning(start_date, end_date)

        first_dirty_record = self.balances.filter(
            balance_is_dirty=True,
            db_date__lte=end_date
        ).order_by('db_date').first()

        # everything is clean in our range
        if not first_dirty_record or first_dirty_record.db_date > end_date:
            return False

        first_dirty_date = first_dirty_record.db_date

        if not child_accounts.exists():
            self.build_balances_leaf(first_dirty_date, end_date)
        else:
            self.build_balances_tree(first_dirty_date, end_date)
        return True

    def build_balances_leaf(self, first_dirty_date, end_date):
        """
        Recalculates running balances for a range.
        """
        # 1. Find the starting balance (the day before our first dirty record)
        day_before = first_dirty_date - relativedelta(days=1)
        starting_balance = AccountBalanceDB.objects.filter(
            account=self, 
            db_date=day_before
        ).values_list('balance', flat=True).first() or Decimal('0.00')

        # 2. Get all records that need cleaning
        to_clean = AccountBalanceDB.objects.filter(
            account=self, 
            db_date__gte=first_dirty_date, 
            db_date__lte=end_date
        ).order_by('db_date')

        # 3. Perform the Running Total
        # Note: SQL Window function could be used here but a single loop that saves at the end is fine.
        current_running_balance = starting_balance
        
        for record in to_clean:
            if record.is_audit:
                # FIREWALL: The audit is the new truth. 
                # We ignore the previous math and the current delta.
                current_running_balance = record.audit
            else:
                # NORMAL: Math continues as usual.
                current_running_balance += record.delta

            record.balance = current_running_balance
            record.balance_is_dirty = False
        
        # 4. Bulk update the results back to the DB in one go
        AccountBalanceDB.objects.bulk_update(to_clean, ['balance', 'balance_is_dirty'])

    def build_balances_tree(self, start_date, end_date, calc_mode=None):
        if not calc_mode:
            calc_mode=self.calc_mode

        day_before_start = start_date - timedelta(days=1)
        # Get the sum of all children, grouped by date, in a single SQL hit
        child_data = AccountBalanceDB.objects.filter(
            account__account_parent=self,
            db_date__gte=day_before_start,
            db_date__lte=end_date
        ).values('db_date').annotate(
            day_balance=Sum('balance'),
            day_delta=Sum('delta'),
            day_audit=Sum('audit'),
            day_audit_count=Sum('audit')
        ).order_by('db_date')

        totals_map = {
            item['db_date']: {
                'balance': item['day_balance'] or Decimal('0.00'),
                'delta': item['day_delta'] or Decimal('0.00'),
                'audit': item['day_audit'],
                'audit_count': item['day_audit_count'],
            } for item in child_data
        }
        
        # 3. Fetch the parent records we need to update
        parent_records = AccountBalanceDB.objects.filter(
            account=self,
            db_date__gte=day_before_start,
            db_date__lte=end_date
        ).order_by('db_date')
        
        day_before_record = parent_records.filter(db_date=day_before_start).first()
        parent_records = parent_records.exclude(db_date=day_before_start)

        parent_audit=False
        running_balance=Decimal('0.00')

        if calc_mode == Account.PARENT_OVERRIDE:
            #check if there is a running parent audit
            before_data = totals_map.get(day_before_start, {'balance': Decimal('0.00')})
            if day_before_record.balance != before_data['balance']:
                parent_audit=True
                running_balance=day_before_record.balance

            # 4. Map the data in the parent
            for p_record in parent_records:
                data = totals_map.get(p_record.db_date, {'balance': 0, 'delta': 0, 'audit': 0, 'audit_count':0})
                if parent_audit and data['audit_count'] and data['audit_count'] > 0:
                    parent_audit = False
                if parent_audit:
                    running_balance = running_balance + data['delta']
                    p_record.balance = running_balance
                else:    
                    p_record.balance = data['balance']
                if p_record.is_audit:
                    parent_audit=True
                    p_record.balance = p_record.audit
                    running_balance =  p_record.audit
                
                p_record.delta = data['delta']                
                p_record.balance_is_dirty = False
        else:
            for p_record in parent_records:
                data = totals_map.get(p_record.db_date, {'balance': 0, 'delta': 0, 'audit': 0, 'audit_count':0})        
                p_record.balance = data['balance']
                p_record.delta = data['delta'] 
                p_record.balance_is_dirty = False                

        # 5. Bulk save back to the database
        AccountBalanceDB.objects.bulk_update(parent_records, ['balance', 'balance_is_dirty', 'delta'])


class AccountCategory(MyMeta, BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Account Category'
        verbose_name_plural = 'Account Categories'
        ordering = ['name']
    accounts = models.ManyToManyField(Account, related_name='account_categories')
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budgetdb:list_accountcategory')


class MyCalendar(models.Model):
    class Meta:
        verbose_name = 'Calendar'
        verbose_name_plural = 'Calendars'

    db_date = models.DateField('date', unique=True)  #
    year = models.IntegerField('year')  #
    month = models.IntegerField('month')  # 1 to 12
    day = models.IntegerField('day')  # 1 to 31
    quarter = models.IntegerField('quarter')  # 1 to 4
    week = models.IntegerField('week')  # 1 to 52/53
    day_name = models.CharField('Day name EN', max_length=9)  # 'Monday'...
    month_name = models.CharField('Month Name EN', max_length=9)  # 'January'..
    holiday_flag = models.BooleanField('Holiday Flag', default=False)
    weekend_flag = models.BooleanField('Weekend Flag', default=False)
    event = models.CharField('Event name', max_length=50)

    def __str__(self):
        return f'{self.db_date.year}-{self.db_date.month}-{self.db_date.day}'


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
        ordering = ['name']
    name = models.CharField(max_length=200)
    date_open = models.DateField('date opened', blank=True, null=True)
    date_closed = models.DateField('date closed', blank=True, null=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budgetdb:list_cattype')

    def get_month_total(self, targetdate):
        # improvement: how do we deal with account currencies ?
        start = date(targetdate.year,targetdate.month,1)
        end = date(targetdate.year,targetdate.month+1,1)
        cat1s = Cat1.view_objects.filter(cattype=self)
        cat2s = Cat2.view_objects.filter(cattype=self)
        accounts = Account.admin_objects.all()
        transactions = Transaction.view_objects.filter(date_actual__gte=start, date_actual__lt=end)
 
        cat1onlytransact = transactions.filter(cat1__in=cat1s,cat2__isnull=True) # .aggregate(Sum('amount_actual')).get('amount_actual__sum')
        cat2transact = transactions.filter(cat2__in=cat2s) # .aggregate(Sum('amount_actual')).get('amount_actual__sum')
        type_transactions = cat1onlytransact | cat2transact
        total = (type_transactions.aggregate(Sum('amount_actual')).get('amount_actual__sum') or Decimal('0.00'))
        # total = (cat1onlytransact or Decimal('0.00')) + (cat2transact or Decimal('0.00'))
        
        return total

    def get_total(self, targetdate):
        # improvement: how do we deal with account currencies ?
        start = date(targetdate.year,1,1)
        end = date(targetdate.year,12,31)
        cat1s = Cat1.view_objects.filter(cattype=self)
        cat2s = Cat2.view_objects.filter(cattype=self)
        transactions = Transaction.view_objects.filter(date_actual__gte=start, date_actual__lt=end)
 
        cat1onlytransact = transactions.filter(cat1__in=cat1s,cat2__isnull=True) # .aggregate(Sum('amount_actual')).get('amount_actual__sum')
        cat2transact = transactions.filter(cat2__in=cat2s) # .aggregate(Sum('amount_actual')).get('amount_actual__sum')
        type_transactions = cat1onlytransact | cat2transact
        total = (type_transactions.aggregate(Sum('amount_actual')).get('amount_actual__sum') or Decimal('0.00'))
        # total = (cat1onlytransact or Decimal('0.00')) + (cat2transact or Decimal('0.00'))
        
        return total

    def get_totals(self, start, end):
        # improvement: how do we deal with account currencies ?
        cat2s = Cat2.view_objects.filter(cattype=self)
        transactions = Transaction.view_objects.filter(date_actual__gte=start, date_actual__lt=end,cat2__in=cat2s)
        cat1s_sums = (transactions
            .annotate(total=Sum('amount_actual'))
            .order_by('-total')
        )
        return cat1s_sums

    def get_monthly_totals(self, start, end):
        # improvement: how do we deal with account currencies ?
        cat2s = Cat2.view_objects.filter(cattype=self)
        transactions = Transaction.view_objects.filter(
            date_actual__gte=start, 
            date_actual__lt=end,
            cat2__in=cat2s
        ).annotate(month=TruncMonth('date_actual'))
        cat1s_sums = (transactions
            .values('month') # Use the relationship path
            .annotate(total=Sum('amount_actual'))
            .order_by('-total')
        )
        return cat1s_sums

    def get_cat1_totals(self, start, end):
        # improvement: how do we deal with account currencies ?
        cat2s = Cat2.view_objects.filter(cattype=self)
        transactions = Transaction.view_objects.filter(date_actual__gte=start, date_actual__lt=end,cat2__in=cat2s)
        cat1s_sums = (transactions
            .values('cat1_id', 'cat1__name') # Use the relationship path
            .annotate(total=Sum('amount_actual'))
            .order_by('-total')
        )
        return cat1s_sums        

    def get_cat1_monthly_totals(self, start, end):
        # improvement: how do we deal with account currencies ?
        cat2s = Cat2.view_objects.filter(cattype=self)
        transactions = Transaction.view_objects.filter(
            date_actual__gte=start, 
            date_actual__lt=end,
            cat2__in=cat2s
        ).annotate(month=TruncMonth('date_actual'))
        cat1s_sums = (transactions
            .values('cat1_id', 'cat1__name', 'month') # Use the relationship path
            .annotate(total=Sum('amount_actual'))
            .order_by('-total')
        )
        return cat1s_sums

    def get_cat2_totals(self, cat1, start, end):
        # improvement: how do we deal with account currencies ?
        cat2s = Cat2.view_objects.filter(cattype=self, cat1=cat1)
        transactions = Transaction.view_objects.filter(date_actual__gte=start, date_actual__lte=end,cat2__in=cat2s, cat1=cat1)
        cat2s_sums = (transactions
            .values('cat2_id', 'cat2__name') # Use the relationship path
            .annotate(total=Sum('amount_actual'))
            .order_by('-total')
        )
        return cat2s_sums

    def get_cat2_monthly_totals(self, cat1, start, end):
        # improvement: how do we deal with account currencies ?
        cat2s = Cat2.view_objects.filter(cattype=self, cat1=cat1)
        transactions = Transaction.view_objects.filter(
            date_actual__gte=start, 
            date_actual__lt=end,
            cat1=cat1,
            cat2__in=cat2s
        ).annotate(month=TruncMonth('date_actual'))
        cat2s_sums = (transactions
            .values('cat2_id', 'cat2__name', 'month') # Use the relationship path
            .annotate(total=Sum('amount_actual'))
            .order_by('-total')
        )
        return cat2s_sums


class Cat1(BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']
    name = models.CharField(max_length=200)
    catbudget = models.ForeignKey('CatBudget', on_delete=models.CASCADE,
                                  blank=True, null=True)
    cattype = models.ForeignKey(CatType, on_delete=models.CASCADE)
    date_open = models.DateField('date opened', blank=True, null=True)
    date_closed = models.DateField('date closed', blank=True, null=True)
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budgetdb:list_cat1')


class Cat2(BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Sub-Category'
        verbose_name_plural = 'Sub-Categories'
        ordering = ['name']
    cat1 = models.ForeignKey(Cat1, on_delete=models.CASCADE)
    cattype = models.ForeignKey(CatType, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    catbudget = models.ForeignKey(CatBudget, on_delete=models.CASCADE, blank=True, null=True)
    unit_price = models.BooleanField('Do we keep unit quantity and cost per for this subcategory', default=False)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budgetdb:details_cat1', kwargs={'pk': self.cat1.pk})


class PaystubProfile(BaseSoftDelete, UserPermissions):
    name = models.CharField(max_length=100, help_text="e.g., Bell Canada Mgmt")
    pay_account = models.ForeignKey('Account', on_delete=models.CASCADE, related_name='pay_sources')
    checking_account = models.ForeignKey('Account', on_delete=models.CASCADE, related_name='pay_destinations')

    # Date Extraction Rules
    date_section = models.CharField(max_length=100, help_text="e.g., BANK Account number")
    date_keyword = models.CharField(max_length=100, help_text="e.g., 2026/")
    date_index = models.IntegerField(default=2)

    def get_absolute_url(self):
        return reverse('budgetdb:home')


class PaystubMapping(BaseSoftDelete, UserPermissions):
    class EntryType(models.TextChoices):
        INCOME = '1.0', 'Income (+)'
        DEDUCTION = '-1.0', 'Deduction (-)'
        # Easy to add more later, e.g.:
        # INFORMATIONAL = '0.0', 'Info Only'
    profile = models.ForeignKey(PaystubProfile, on_delete=models.CASCADE, related_name='mappings')
    section_name = models.CharField(max_length=100)
    line_keyword = models.CharField(max_length=100)
    line_sequence = models.IntegerField(default=0, help_text="Order of the line in the document")
    category = models.ForeignKey('Cat2', on_delete=models.SET_NULL, null=True, blank=True)
    column_indices = models.CharField(max_length=20, default="-1")
    
    is_header = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_date_line = models.BooleanField(default=False)
    is_ignored = models.BooleanField(default=False)
    is_net_pay = models.BooleanField(default=False)
    is_pass_through  = models.BooleanField(default=False)
    token_count = models.IntegerField(default=0, help_text="number of token for this line")

    entry_type = models.CharField(
        max_length=10,
        choices=EntryType.choices,
        default=EntryType.INCOME,
        help_text="Determines if the value adds to or subtracts from the total."
    )
    destination_account = models.ForeignKey(
        'Account', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='paystub_mappings'
    )
    def get_indices(self):
        if not self.column_indices or self.column_indices == "-1":
            return []
        return self.column_indices.split(',')

    def __str__(self):
        return f'{self.section_name} - {self.category}'

    @property
    def keyword_label(self):
        """Returns 'Regular Pay [3]' as 'Regular Pay'"""
        if not self.line_keyword:
            return ""
        # rsplit from the right, exactly once
        parts = self.line_keyword.rsplit(' [', 1)
        return parts[0]

    @property
    def token_suffix(self):
        """Returns the [n] part for small badges/tooltips"""
        if ' [' in self.line_keyword:
            return f"{self.line_keyword.rsplit(' [')[1].rsplit(']')[0]}"
        return ""


class Vendor(BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'
        ordering = ['name']
    name = models.CharField(max_length=200)
    OFX_name = models.CharField('Bank import key', max_length=200, blank=True, null=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budgetdb:list_vendor')


class BaseEvent(models.Model):
    class Meta:
        abstract = True
    account_source = models.ForeignKey(Account, on_delete=models.CASCADE,
                                       blank=True, null=True, related_name='%(class)s_account_source')
    account_destination = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='%(class)s_account_destination', blank=True, null=True
    )
    amount_planned = models.DecimalField(
        'planned amount', decimal_places=2, max_digits=10, blank=True, null=True
    )

    currency = models.ForeignKey("Currency", on_delete=models.DO_NOTHING, blank=False, null=False)
    amount_planned_foreign_currency = models.DecimalField(
        'original amount', decimal_places=2, max_digits=10, blank=True, null=True
    )
    description = models.CharField('Description', max_length=200)
    comment = models.CharField('Comment', max_length=200, blank=True, null=True)
    ismanual = models.BooleanField('Manual Intervention?', default=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, blank=True, null=True)
    budget_only = models.BooleanField(
        'Budget only, counts as 0 after today',
        default=False,
    )
    joined_order = models.IntegerField('position in a joined transaction', blank=True,
                                       null=True)
    cat1 = models.ForeignKey(Cat1, on_delete=models.CASCADE, blank=True, null=True,
                             verbose_name='Category', related_name='%(class)s_category')
    cat2 = models.ForeignKey(Cat2, on_delete=models.CASCADE, blank=True, null=True,
                             verbose_name='Sub-Category', related_name='%(class)s_subcategory')

    def can_edit(self):
        user = get_current_user()
        if not user or user.is_anonymous:
            return False
        
        # Check both accounts. If an account exists, user MUST be able to edit it.
        # Logic: If account exists, user must have edit rights.
        if self.account_source and not self.account_source.can_edit():
            return False
        if self.account_destination and not self.account_destination.can_edit():
            return False        
        
        return True

    def can_view(self):
        user = get_current_user()
        if not user or user.is_anonymous:
            return False

        # A user can view a transaction if they can view EITHER account.
        # This matches your Manager's "source_ok | dest_ok" logic.
        if self.account_source and self.account_source.can_view():
            return True
        if self.account_destination and self.account_destination.can_view():
            return True
        
        return False


class Template(MyMeta, BaseSoftDelete, BaseEvent, UserPermissions):
    class Meta:
        verbose_name = 'Template'
        verbose_name_plural = 'Templates'

    def __str__(self):
        return f'{self.vendor} - {self.description}'

    def get_absolute_url(self):
        return reverse('budgetdb:list_template')


class Transaction(MyMeta, BaseSoftDelete, BaseEvent):
    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        constraints = [
            models.UniqueConstraint(
                fields=['account_source', 'fit_id'], 
                condition=models.Q(is_deleted=False),
                name='unique_fit_id_per_account'
            )
        ]
    objects = models.Manager()  # The default manager.
    view_objects = TransactionViewerManager()
    view_deleted_objects = TransactionDeletedViewerManager()
    view_all_objects = TransactionViewerAllManager()
    admin_objects = TransactionAdminManager()

    budgetedevent = models.ForeignKey("BudgetedEvent", on_delete=models.CASCADE, blank=True, null=True)
    date_planned = models.DateField('planned date', blank=True, null=True)
    date_actual = models.DateField('date of the transaction')
    amount_actual = models.DecimalField('Amount', decimal_places=2, max_digits=10, default=Decimal('0.00'))
    amount_actual_foreign_currency = models.DecimalField('original amount', decimal_places=2, max_digits=10, default=Decimal('0.00'))
    #Fuel_L = models.DecimalField('Fuel quantity', decimal_places=3, max_digits=7, blank=True, null=True)
    #Fuel_price = models.DecimalField('Fuel cost per', decimal_places=3, max_digits=5, blank=True, null=True)
    Unit_QTY = models.DecimalField('Quantity', decimal_places=4, max_digits=9, blank=True, null=True)
    Unit_price = models.DecimalField('Price per', decimal_places=4, max_digits=9, blank=True, null=True)
    statement = models.ForeignKey("Statement", on_delete=models.CASCADE, blank=True, null=True, related_name="transactions")
    verified = models.BooleanField('Verified in a statement', default=False)
    audit = models.BooleanField('Audit', default=False)
    receipt = models.BooleanField('Checked with receipt', default=False)
    fit_id = models.CharField(max_length=255, null=True, blank=True)
    fit_id_transfer = models.CharField(max_length=255, null=True, blank=True)
    paystub_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f'{self.description} - {self.date_actual}'

    def get_absolute_url(self):
        return reverse('budgetdb:details_transaction', kwargs={'pk': self.pk})

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        # save original values, when model is loaded from database,
        # in a separate attribute on the model
        instance._loaded_values = dict(zip(field_names, values))
        
        return instance

    @property
    def joined_transaction_id(self):
        """Returns the ID of the related joined transaction if one exists."""
        if self.budgetedevent:
            first_event = self.budgetedevent.joined_transactions.first()
            if first_event:
                return first_event.id
        
        first_tx = self.joined_transactions.first()
        if first_tx:
            return first_tx.id
            
        return None

    def clean(self):
        super().clean()

        # Audit must have an amount
        if self.audit and self.amount_actual is None:
            raise ValidationError({
                'amount_actual': _('An audited transaction must have an actual amount.')
            })
            
        # Prevent transfers to the same account
        if self.account_source == self.account_destination and self.account_source is not None:
            raise ValidationError(
                _('Source and destination accounts cannot be the same.')
            )

        # 3. Ensure dates aren't in the far future (optional sanity check)
        if self.date_actual and self.date_actual > date.today() + relativedelta(years=5):
            raise ValidationError({'date_actual': _('Date is too far in the future.')})

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.can_edit():
            # don't save an audit if there is already one on the same day on the same account
            if self.audit:
                existing_audits = Transaction.objects.filter(
                    date_actual=self.date_actual,
                    account_source=self.account_source,
                    audit=True,
                    is_deleted=False
                ).exclude(pk=self.pk)
                if existing_audits.exists():
                    return

            # Capture the "old" state before we save
            is_new = self.pk is None
            old_date = getattr(self, '_loaded_values', {}).get('date_actual')
            old_src = getattr(self, '_loaded_values', {}).get('account_source_id')
            old_dest = getattr(self, '_loaded_values', {}).get('account_destination_id')

            super().save(*args, **kwargs)
            # 3. Trigger the Sync
            from budgetdb.services import LedgerService
            LedgerService.sync_transaction(self, is_new, old_date, old_src, old_dest)

    def soft_delete(self):
        super().soft_delete()
        if self.verified and self.statement:
            self.statement.verified_lock = False
            self.statement.save()


class BaseRecurring(models.Model):
    class Meta:
        abstract = True
    repeat_start = models.DateField('date of the first event')
    repeat_stop = models.DateField('date of the last event, optional', blank=True, null=True)
    nb_iteration = models.IntegerField('number of repetitions, null if N/A', blank=True,
                                       null=True)  # is this implementable on complex patterns?

    repeat_interval_days = models.IntegerField('period in days, 0 if N/A', default=0)
    repeat_interval_years = models.IntegerField('period in years, 0 if N/A', default=0)
    repeat_interval_months = models.IntegerField('period in months, 0 if N/A', default=0)
    repeat_interval_weeks = models.IntegerField('period in weeks, 0 if N/A', default=0)

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

    def listPotentialTransactionDates(self, n=20, begin_interval=date.today(), interval_length_months=60):
        calendar = MyCalendar.objects.filter(db_date__gte=begin_interval, db_date__lte=begin_interval+relativedelta(months=interval_length_months))
        event_date_list = []
        i = n
        for day in calendar:
            if (self.checkDate(day.db_date)):
                # skip existing transactions
                if not Transaction.objects.filter(budgetedevent=self, date_planned=day.db_date).exists():
                    event_date_list.append(day.db_date)
                    i -= 1
                    if (i == 0):
                        break
        return event_date_list

    def listNextTransactions(self, n=20, begin_interval=date.today(), interval_length_months=60):
        transactions = Transaction.view_objects.filter(budgetedevent_id=self.pk)
        transactions = transactions.filter(date_actual__gt=begin_interval)
        end_date = begin_interval + relativedelta(months=interval_length_months)
        transactions = transactions.filter(date_actual__lte=end_date).order_by('date_actual')[:n]
        return transactions

    def listLinkedTransactions(self, n=20, begin_interval=date.today(), interval_length_months=60):
        transactions = Transaction.view_all_objects.filter(budgetedevent_id=self.pk)
        transactions = transactions.filter(date_actual__gt=begin_interval)
        end_date = begin_interval + relativedelta(months=interval_length_months)
        transactions = transactions.filter(date_actual__lte=end_date).order_by('date_actual')[:n]
        return transactions

    def listPreviousTransaction(self, n=20, begin_interval=date.today(), interval_length_months=60):
        transactions = Transaction.view_objects.filter(budgetedevent_id=self.pk)
        transactions = transactions.filter(date_actual__lt=begin_interval)
        end_date = begin_interval - relativedelta(months=interval_length_months)
        transactions = transactions.filter(date_actual__gt=end_date).order_by('-date_actual')[:n]
        return transactions


class BudgetedEvent(MyMeta, BaseSoftDelete, BaseEvent, BaseRecurring, UserPermissions):
    # description of budgeted events
    class Meta:
        verbose_name = 'Budgeted Event'
        verbose_name_plural = 'Budgeted Events'
    generated_interval_start = models.DateField('begining of the generated events interval', blank=True, null=True)
    generated_interval_stop = models.DateField('end of the generated events interval', blank=True, null=True)
    percent_planned = models.DecimalField('percent of another event.  say 10% of pay goes to RRSP',
                                          decimal_places=2, max_digits=10, blank=True, null=True)
    budgetedevent_percent_ref = models.ForeignKey('self', on_delete=models.CASCADE, blank=True,
                                                  null=True)
    isrecurring = models.BooleanField('Is this a recurring event?', default=True)

    def __str__(self):
        return self.description

    def get_absolute_url(self):
        return reverse('budgetdb:details_be', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        super(BudgetedEvent, self).save(*args, **kwargs)
        self.deleteUnverifiedTransaction()
        if self.is_deleted is False:
            self.createTransactions()
        super(BudgetedEvent, self).save(*args, **kwargs)

    def isGenerateNeeded(self):
        if self.generated_interval_stop is None:
            transaction_dates = self.listPotentialTransactionDates(n=1)
        else:
            transaction_dates = self.listPotentialTransactionDates(n=1, begin_interval=self.generated_interval_stop,)

        if len(transaction_dates) == 0:
            return False
        else:    
            return True

    def createTransactions(self, n=400, begin_interval=None, interval_length_months=60, slider_stop=None):
        if begin_interval is None:
            begin_interval = self.repeat_start

        # make sure we generate at least up to the end of the timeline
        user = get_current_user()
        preference = Preference.objects.get(user=user.id)
        if slider_stop is None:
            slider_stop = preference.timeline_stop
        default_slider_stop = begin_interval + relativedelta(months=interval_length_months)
        if default_slider_stop < slider_stop:
            delta = default_slider_stop - slider_stop
            interval_length_months += 1 - round(delta.days / 30)

        transaction_dates = self.listPotentialTransactionDates(n=n,
                                                               begin_interval=begin_interval,
                                                               interval_length_months=interval_length_months,
                                                               )
        if transaction_dates:
            self.generated_interval_start = transaction_dates[0]
        else:
            return

        for date in transaction_dates:
            if Transaction.objects.filter(budgetedevent=self, date_planned=date).exists():
                # transaction already exists
                continue
            new_transaction = Transaction.objects.create(date_planned=date,
                                                         date_actual=date,
                                                         amount_actual=self.amount_planned,
                                                         amount_planned=self.amount_planned,
                                                         ismanual=self.ismanual,
                                                         description=self.description,
                                                         budgetedevent_id=self.pk,
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
        # don't delete is self is none, it's a new BE creation
        if self.pk is not None:
            transactions = Transaction.view_objects.filter(budgetedevent=self.pk, verified=False, receipt=False)
            transactions.delete()
            self.generated_interval_start = None
            self.generated_interval_stop = None

    def lastTransactionDate(self):
        transactions = Transaction.view_objects.filter(budgetedevent=self.pk)
        last_transaction = transactions.order_by('-date_actual').first()
        if last_transaction is None:
            return "No Transaction"
        else:
            return last_transaction.date_actual


class Statement (MyMeta, BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Statement'
        verbose_name_plural = 'Statements'
        ordering = ['-statement_date']
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='statement_account')
    balance = models.DecimalField('Statement balance', decimal_places=2, max_digits=10, default=Decimal('0.00'))
    minimum_payment = models.DecimalField('Minimum Payment', decimal_places=2, max_digits=10, default=Decimal('0.00'))
    statement_date = models.DateField('date of the statement')
    statement_due_date = models.DateField('Payment due date', blank=True, null=True)
    comment = models.CharField(max_length=200, blank=True, null=True)
    payment_transaction = models.ForeignKey('Transaction', on_delete=models.CASCADE, related_name='payment_transaction',
                                            blank=True, null=True)
    verified_lock = models.BooleanField('Total is good, all transactions verified, lock status', default=False)

    def __str__(self):
        # return self.account.name + " " + self.statement_date.strftime('%Y-%m-%d')
        return f'{self.statement_date.strftime('%Y-%m-%d')} - {self.account.name} - {self.account.currency.symbol}{self.balance:,.2f}'

    def get_absolute_url(self):
        return reverse('budgetdb:details_statement', kwargs={'pk': self.pk})

    @property
    def is_balanced(self):
        # Check for annotated value first
        annotated_sum = getattr(self, 'calculated_total', None)
        if annotated_sum is not None:
            return self.balance == annotated_sum

        # Manual fallback calculation
        txs = self.transaction_set.filter(is_deleted=False)

        sum_in = txs.filter(account_destination=self.account).aggregate(
            total=Sum('amount_actual'))['total'] or 0
        sum_out = txs.filter(account_source=self.account).aggregate(
            total=Sum('amount_actual'))['total'] or 0
        
        return self.balance == (sum_in - sum_out)


class JoinedTransactions(MyMeta, BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Joined Transactions'
        verbose_name_plural = 'Joined Transactions'
    name = models.CharField(max_length=200)
    comment = models.CharField(max_length=200, blank=True, null=True)
    transactions = models.ManyToManyField(Transaction, related_name='joined_transactions') #was transactions
    budgetedevents = models.ManyToManyField(BudgetedEvent, related_name='joined_transactions') #was budgeted_events
    isrecurring = models.BooleanField('Is this a recurring event?', default=True)
