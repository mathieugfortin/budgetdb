from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.db import models
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.translation import gettext_lazy as _
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.db.models.functions import Cast, Coalesce
from django.db.models import Sum, Q
from django.db.models.functions import (
     ExtractMonth,
     ExtractYear,
 )
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager #, Group
# from django.contrib.sites.models import Site
from crum import get_current_user
from django.template.loader import render_to_string
from .tokens import account_activation_token
from django.core.exceptions import ValidationError

class MyMeta(models.Model):
    class Meta:
        abstract = True

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
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
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name']
    username = None
    email = models.EmailField('email address', unique=True)
    friends = models.ManyToManyField("User", related_name='friends_users')
    email_verified = models.BooleanField('Email Verified', default=False, null=False)

    def __str__(self):
        return self.email

    def send_verify_email(self):
        if not self.email_verified:
            user = self.first_name
            email = self.email
            # current_site = Site.objects.get_current()
            subject = "Verify Email"
            message = render_to_string('budgetdb/email_validation_message.html', {
                # 'request': request,
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


class ViewerManager(models.Manager):
    def get_queryset(self):
        user = get_current_user()
        qs = super().get_queryset()
        qs = qs.filter(is_deleted=False)
        owned = qs.filter(owner=user)
        admins = qs.filter(users_admin=user)
        viewers = qs.filter(users_view=user)
        qs = owned | admins | viewers
        return qs


class ViewerDeletedManager(models.Manager):
    def get_queryset(self):
        user = get_current_user()
        qs = super().get_queryset()
        qs = qs.filter(is_deleted=True)
        owned = qs.filter(owner=user)
        admins = qs.filter(users_admin=user)
        viewers = qs.filter(users_view=user)
        qs = owned | admins | viewers
        return qs


class AdminManager(models.Manager):
    def get_queryset(self):
        user = get_current_user()
        qs = super().get_queryset()
        qs = qs.filter(is_deleted=False)
        owned = qs.filter(owner=user)
        admins = qs.filter(users_admin=user)
        return owned | admins


class TransactionViewerManager(models.Manager):
    def get_queryset(self):
        user = get_current_user()
        qs = super().get_queryset()
        qs = qs.filter(is_deleted=False)
        view_accounts = Account.view_objects.all()
        ok_source = qs.filter(account_source__in=view_accounts)
        ok_dest = qs.filter(account_destination__in=view_accounts)
        qs = ok_source | ok_dest
        return qs


class TransactionDeletedViewerManager(models.Manager):
    def get_queryset(self):
        user = get_current_user()
        qs = super().get_queryset()
        qs = qs.filter(is_deleted=True)
        view_accounts = Account.view_objects.all()
        ok_source = qs.filter(account_source__in=view_accounts)
        ok_dest = qs.filter(account_destination__in=view_accounts)
        qs = ok_source | ok_dest
        return qs


class TransactionViewerAllManager(models.Manager):
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
        qs = qs.filter(is_deleted=False)
        admin_accounts = Account.admin_objects.all()
        ok_source = qs.filter(account_source__in=admin_accounts)
        ok_dest = qs.filter(account_destination__in=admin_accounts)
        qs = ok_source | ok_dest
        return qs


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

    # groups_admin = models.ManyToManyField(Group, related_name='g_can_mod_%(app_label)s_%(class)s', blank=True)
    # groups_view = models.ManyToManyField(Group, related_name='g_can_view_%(app_label)s_%(class)s', blank=True)
    users_admin = models.ManyToManyField("User", related_name='users_full_access_%(app_label)s_%(class)s', blank=True)
    users_view = models.ManyToManyField("User", related_name='users_view_access_%(app_label)s_%(class)s', blank=True)
    objects = models.Manager()  # The default manager.
    view_objects = ViewerManager()
    view_deleted_objects = ViewerDeletedManager()
    admin_objects = AdminManager()

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
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey("User", null=True, blank=True, on_delete=models.CASCADE, related_name='deleted_by_%(app_label)s_%(class)s')

    class Meta:
        abstract = True

    def soft_delete(self):
        if self.is_deleted:
            return
        self.is_deleted = True
        self.deleted_by = get_current_user()
        self.deleted_at = timezone.now()
        self.save()

    def soft_undelete(self):
        if not self.is_deleted:
            return
        self.is_deleted = False
        self.deleted_by = get_current_user()
        self.deleted_at = None
        self.save()


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
        template = 'budgetdb/email_share_message.html'
        subject = "Budget Sharing"
        try:
            invited_user = User.objects.get(email=self.email)
        except ObjectDoesNotExist:
            template = 'budgetdb/email_invitation_message.html'
            subject = "Budget Invitation"

        email = self.email
        # current_site = Site.objects.get_current()

        message = render_to_string(template, {
            # 'request': request,
            'inviter': self.owner,
            'email': self.email,
            'domain': 'https://budget.patatemagique.biz/',
        })
        email = EmailMessage(
            subject, message, to=[email]
        )
        email.content_subtype = 'html'
        email.send()


class AccountBalanceDB(models.Model):
    db_date = models.DateField(blank=True)
    account = models.ForeignKey("Account", on_delete=models.CASCADE, blank=True, null=True)
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
        blank=False,
        null=False,
        default=Decimal('0.00'),
        )
    balance = models.DecimalField(
        'balance for the day',
        decimal_places=2,
        max_digits=10,
        blank=False,
        null=False,
        default=Decimal('0.00'),
        )
    balance_is_dirty = models.BooleanField('If there is a new transaction for this day, the balance is not reliable', default=False)
    is_audit = models.BooleanField('override of the account balance', default=False)

    def __str__(self):
        return self.account.name + " - " + self.db_date.strftime("%Y-%m-%d")

    def save(self, *args, **kwargs):
        # Ensure db_date is a date object for math
        if isinstance(self.db_date, str):
            self.db_date = datetime.strptime(self.db_date, '%Y-%m-%d').date()

        if self.balance_is_dirty:
            if self.account.account_parent:
                AccountBalanceDB.objects.filter(
                    account=self.account.account_parent, 
                    db_date=self.db_date
                ).update(balance_is_dirty=True)

        if self.is_audit:
            target_date = self.db_date - timedelta(days=1)
            try:
                # previous = AccountBalanceDB.objects.get(account=self.account, db_date=target_date).balance


                # Use .filter().first() to avoid DoesNotExist exceptions
                prev_record = AccountBalanceDB.objects.filter(
                    account=self.account, 
                    db_date=self.db_date - timedelta(days=1)
                ).first()
                previous_bal = prev_record.balance if prev_record else Decimal('0.00')
            except ObjectDoesNotExist:
                previous_bal = Decimal('0.00')
            # If audit is set, delta is the gap between audit and yesterday
            if self.audit is not None:
                self.delta = self.audit - previous_bal
                self.balance = self.audit

        super(AccountBalanceDB, self).save(*args, **kwargs)
    
    def set_delta_and_dirty(self):
        self.balance_is_dirty = True
        audit = Transaction.objects.filter(account_source=self.account,date_actual=self.db_date, is_deleted=False, audit=True).first()
        if audit is not None:
            previous = AccountBalanceDB.objects.get(account=self.account, db_date=self.db_date - timedelta(days=1))
            self.audit = audit.amount_actual
            self.balance = self.audit
            self.is_audit = True
            self.delta = self.audit - previous.balance
        else:
            self.audit = None
            self.is_audit = False
            sum_destination = Transaction.objects.filter(account_destination=self.account,date_actual=self.db_date, is_deleted=False, audit=False).aggregate(Sum('amount_actual'))
            sum_source = Transaction.objects.filter(account_source=self.account,date_actual=self.db_date, is_deleted=False, audit=False).aggregate(Sum('amount_actual'))
            self.delta = (sum_destination.get('amount_actual__sum') or Decimal('0.00')) - (sum_source.get('amount_actual__sum') or Decimal('0.00'))
        self.save()


class AccountHost(BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Financial Institution'
        verbose_name_plural = 'Financial Institutions'
        ordering = ['name']

    user_permissions = models.OneToOneField(to=UserPermissions, parent_link=True, on_delete=models.CASCADE, related_name='accounthost_permissions_child')
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
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'
        ordering = ['account_host__name', 'name']

    user_permissions = models.OneToOneField(to=UserPermissions, parent_link=True, on_delete=models.CASCADE, related_name='account_permissions_child')

    ofx_acct_id = models.CharField(max_length=100, blank=True, null=True, help_text="Bank's ACCTID from OFX")  # <ACCTID>
    ofx_org = models.CharField(max_length=50, blank=True, null=True) # <ORG>
    ofx_fid = models.CharField(max_length=50, blank=True, null=True) # <FID>
    ofx_flip_sign = models.BooleanField(default=False, help_text="Check if outflows are positive in OFX")

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

    def new_balances(self, begin, end):
        # Ensure begin is a date object, not a string
        if isinstance(begin, str):
            begin = datetime.strptime(begin, '%Y-%m-%d').date()
        # Ensure end is a date object
        if isinstance(end, str):
            end = datetime.strptime(end, '%Y-%m-%d').date()

        existing_objects = AccountBalanceDB.objects.filter(account=self)
        balances_to_create = []
        
        if existing_objects.exists():
            last_object = existing_objects.latest('db_date')
            date_cursor = last_object.db_date
            if date_cursor > end:
                return()
            new_balance=last_object.balance
            new_balance_is_dirty=True
        else:
            date_cursor = begin - timedelta(days=1)
            balances_to_create.append(
                AccountBalanceDB(
                    account=self,
                    db_date=date_cursor,
                    audit=Decimal('0.00'),
                    balance=Decimal('0.00'),
                    is_audit=True,
                    balance_is_dirty=False
                )
            )
            new_balance=Decimal('0.00')
            new_balance_is_dirty=False

        date_cursor = date_cursor + timedelta(days=1)
        while date_cursor <= end:
            balances_to_create.append(
                AccountBalanceDB(
                    account=self,
                    db_date=date_cursor,
                    balance=new_balance,
                    is_audit=False,
                    balance_is_dirty=new_balance_is_dirty
                )
            )
            date_cursor = date_cursor + timedelta(days=1)
        if balances_to_create:
            AccountBalanceDB.objects.bulk_create(balances_to_create)
        if new_balance_is_dirty and self.account_parent is not None:
            AccountBalanceDB.objects.filter(account=self.account_parent,db_date__range=(begin, end)).update(balance_is_dirty=True)

    def check_balances(self, end):
        # verify if balances exist up to a given date.  create them if thy do not exist
        last_balance = AccountBalanceDB.objects.filter(account=self).latest('db_date')
        last_date = last_balance.db_date
        if end > last_date:
            self.new_balances(last_date,end)

    def save(self, *args, **kwargs):
        # Convert string dates to date objects if necessary
        if isinstance(self.date_open, str):
            self.date_open = datetime.strptime(self.date_open, '%Y-%m-%d').date()
        if isinstance(self.date_closed, str):
            self.date_closed = datetime.strptime(self.date_closed, '%Y-%m-%d').date()

        if self._state.adding is True:
            super(Account, self).save(*args, **kwargs)            
            #new account, need to create balances and set first one
            if self.date_closed is None:
                end_generate = date.today() + relativedelta(years=3)
            else:
                end_generate = self.date_closed
            self.new_balances(self.date_open,end_generate)
            
        else:
            # Safely get old values; default to current values if _loaded_values is missing
            loaded = getattr(self, '_loaded_values', {})
            old_date_open = loaded.get('date_open', self.date_open)
            old_date_closed = loaded.get('date_closed', self.date_closed)

            super(Account, self).save(*args, **kwargs)
            if self.date_open < old_date_open:
                #add earlier balances and add an audit just before the old date_open to keep the balances
                new_audit_date = old_date_open - timedelta(days=1)
                self.new_balances(self.date_open,new_audit_date)
                new_audit = AccountBalanceDB.objects.get(account=self.account,db_date=new_audit_date)
                new_audit.audit = self.get_balance(old_date_open) 
                new_audit.is_audit=True
                new_audit.delta = new_audit.audit
                new_audit.save()
            elif self.date_open > old_date_open:
                #remove unused balances and add an audit just before the new date_open
                new_audit_date = self.date_open - timedelta(days=1)
                new_audit = AccountBalanceDB.objects.get(account=self.account,db_date=new_audit_date)
                new_audit = self.get_balance(self.date_open)
                new_audit.is_audit=True
                new_audit.delta = new_audit.audit
                new_audit.save()
                unused_balances = AccountBalanceDB.objects.filter(account=self.account,db_date__lt=self.new_audit_date).delete()
            if self.date_closed != None and self.date_closed > old_date_closed:
                #add later balances
                self.new_balances(old_date_closed,self.date_closed)
                new_dirty = AccountBalanceDB.objects.get(account=self.account,db_date=new_audit_date)
                new_audit.balance_is_dirty=True
                new_audit.save()
            elif self.date_closed != None and self.date_closed < old_date_closed:
                #remove unused balances 
                unused_balances = AccountBalanceDB.objects.filter(account=self.account,db_date__gt=self.date_closed).delete()

    def get_absolute_url(self):
        return reverse('budgetdb:list_account_simple')

    def balance_by_EOD(self, dateCheck):

        audit_today = Transaction.view_objects.filter(account_source_id=self.pk, date_actual=dateCheck, audit=True).order_by('-date_actual')[:1]
        if audit_today.count() == 1:
            return audit_today.first().amount_actual

        balance = Decimal(0.00)

        childrens = self.account_children.all()
        if childrens.count() > 0:
            for children in childrens:
                balance += children.balance_by_EOD(dateCheck)
            return balance

        closestAudit = Transaction.view_objects.filter(account_source_id=self.pk, date_actual__lte=dateCheck, audit=True).order_by('-date_actual')[:1]
        if closestAudit.count() == 0:
            balance = Decimal(0.00)
            events = Transaction.view_objects.filter(date_actual__lte=dateCheck)
        else:
            balance = Decimal(closestAudit.first().amount_actual)
            events = Transaction.view_objects.filter(date_actual__gt=closestAudit.first().date_actual, date_actual__lte=dateCheck)

        events = events.filter(account_source_id=self.pk) | events.filter(account_destination_id=self.pk)

        for event in events:
            amount = Decimal(0.00)
            if event.audit is True:
                balance = event.amount_actual
            elif not (event.budget_only is True and event.date_actual <= date.today()):
                if event.account_destination_id == self.pk:
                    balance += event.amount_actual
                if event.account_source_id == self.pk:
                    balance -= event.amount_actual

        return balance

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

        balance_end = self.balance_by_EOD(end_date)
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
        # balance = Decimal(Account.view_objects.get(id=self.pk).balance_by_EOD(start_date))
        balance = Decimal(self.balance_by_EOD(start_date))
        for event in events:
            amount = Decimal(0.00)
            event.account_view_id = self.pk
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
            if event.transactions.first() is not None:
                event.joinedtransaction = event.transactions.first()
            elif event.budgetedevent is not None:
                if event.budgetedevent.budgeted_events.first() is not None:
                    event.joinedtransaction = event.budgetedevent.budgeted_events.first()
        return events

    def leaf_balances_needed_cleaning(self, start_date, end_date):
        # after this is run, the interval start_date, end_date is clean
        # return False if the balances were not dirty and were not modified
        # return True if the balances were dirty and were modified

        closest_audit = AccountBalanceDB.objects.filter(account=self, db_date__lte=start_date, is_audit=True).order_by('-db_date').first()
        first_dirty = AccountBalanceDB.objects.filter(account=self, db_date__gte=closest_audit.db_date, db_date__lte=end_date,balance_is_dirty=True).order_by('db_date').first()

        if first_dirty is not None:
            self.build_balances_leaf(first_dirty.db_date, end_date)
            # that function needs to dirty end_date+1 if it modifies balances ########################
            return True
        else:
            return False

    def tree_balances_needed_cleaning(self, start_date, end_date=None):
        # after this is run, the interval start_date, end_date is clean
        # return False if the balances were not dirty and were not modified
        # return True if the balances were dirty and were modified

        if end_date is None:
            end_date = start_date

        if end_date < self.date_open:
            return False

        if self.date_closed is not None and start_date > self.date_closed:
            return False

        if self.date_closed is not None and end_date > self.date_closed :
            end_date = self.date_closed

        if start_date < self.date_open:
            start_date = self.date_open


        children_needed_cleaning = False
        if self.id >= 500:
            None
        closest_parent_audit = AccountBalanceDB.objects.filter(account=self, db_date__lte=start_date, is_audit=True).order_by('-db_date').first()
        first_parent_dirty = AccountBalanceDB.objects.filter(account=self, db_date__gte=closest_parent_audit.db_date, db_date__lte=end_date,balance_is_dirty=True).order_by('db_date').first()
        if first_parent_dirty is not None:
            start_date = first_parent_dirty.db_date
        childaccounts = Account.view_objects.filter(account_parent_id=self.pk, is_deleted=False)
        if (childaccounts.count() > 0):
            # this is a parent, clean child accounts
            for child in childaccounts:
                # call recursively, a child could have childrens
                if child.tree_balances_needed_cleaning(start_date, end_date) is True:
                    children_needed_cleaning = True
        else:
            # This is a leaf, clean it
            if self.leaf_balances_needed_cleaning(start_date, end_date) is True:
                return True
            else:
                return False

        if children_needed_cleaning is True or first_parent_dirty is not None:
            self.build_balances_tree(start_date, end_date)
            return True

    def build_balances_leaf(self, first_dirty_date, end_date):    
        last_clean_date = first_dirty_date - timedelta(days=1)
        if self.id >= 500:
            None
        last_clean_balance = AccountBalanceDB.objects.get(account=self, db_date=last_clean_date)
        previous_day_balance = last_clean_balance.balance
        balances = AccountBalanceDB.objects.filter(account=self, db_date__gte=first_dirty_date, db_date__lte=end_date).order_by('db_date')
        for balance in balances:
            if balance.is_audit or (balance.audit is not None and balance.audit != decimal('0.0')):
                balance.balance = balance.audit
                balance.is_audit = True
                balance.delta = balance.audit - previous_day_balance
            else:
                balance.balance = previous_day_balance + balance.delta
            balance.balance_is_dirty = False
            previous_day_balance = balance.balance
            balance.save()
        # we updated balances, the next day is now dirty
        new_dirty_date = end_date + timedelta(days=1)
        new_dirty_day = AccountBalanceDB.objects.get(account=self, db_date=new_dirty_date)
        if new_dirty_day.is_audit is False:
            new_dirty_day.balance_is_dirty = True
            new_dirty_day.save()

    def build_balances_tree(self, first_dirty_date, end_date):
        last_clean_date = first_dirty_date - timedelta(days=1)
        try:
            last_clean_day = AccountBalanceDB.objects.get(account=self, db_date=last_clean_date)
            previous_day = last_clean_day.balance
        except ObjectDoesNotExist:
            previous_day = Decimal('0.00')
        days = AccountBalanceDB.objects.filter(account=self, db_date__gte=first_dirty_date, db_date__lte=end_date).order_by('db_date')
        

        childaccounts = Account.view_objects.filter(account_parent_id=self.pk, is_deleted=False)        
        childrens_delta = AccountBalanceDB.objects.filter(account__in=childaccounts, db_date__gte=first_dirty_date, db_date__lte=end_date).values('db_date').annotate(Sum('delta'))
        for day in days:
            if day.is_audit or day.audit is not None:
                day.balance = day.audit
                day.is_audit = True
                day.delta = day.audit - previous_day
            else:
                day.balance = (previous_day 
                                + day.delta 
                                + childrens_delta.get(db_date=day.db_date).get('delta__sum')
                                )
            day.balance_is_dirty = False
            previous_day = day.balance
            day.save()

        # we updated balances, the next day is now dirty
        new_dirty_date = end_date + timedelta(days=1)
        new_dirty_day = AccountBalanceDB.objects.get(account=self, db_date=new_dirty_date)
        if new_dirty_day.is_audit is False:
            new_dirty_day.balance_is_dirty = True
            new_dirty_day.save()

    def get_balances(self, start_date, end_date):
        self.tree_balances_needed_cleaning(start_date, end_date)
        return AccountBalanceDB.objects.filter(account=self, db_date__gte=start_date, db_date__lte=end_date).order_by('db_date')

    def get_balance(self, date):
        self.tree_balances_needed_cleaning(date,date)
        return AccountBalanceDB.objects.get(account=self, db_date=date)

    def force_deltas(self):
        balances = AccountBalanceDB.objects.filter(account=self)
        for balance in balances:
            balance.set_delta_and_dirty()


class AccountCategory(MyMeta, BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Account Category'
        verbose_name_plural = 'Account Categories'
        ordering = ['name']

    user_permissions = models.OneToOneField(to=UserPermissions, parent_link=True, on_delete=models.CASCADE, related_name='accountcategory_permissions_child')
    accounts = models.ManyToManyField(Account, related_name='account_categories')
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

    user_permissions = models.OneToOneField(to=UserPermissions, parent_link=True, on_delete=models.CASCADE, related_name='catbudget_permissions_child')
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

    user_permissions = models.OneToOneField(to=UserPermissions, parent_link=True, on_delete=models.CASCADE, related_name='cattype_permissions_child')
    name = models.CharField(max_length=200)
    date_open = models.DateField('date opened', blank=True, null=True)
    date_closed = models.DateField('date closed', blank=True, null=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budgetdb:list_cattype')

    def get_month_total(self, targetdate):
        start = date(targetdate.year,targetdate.month,1)
        end = date(targetdate.year,targetdate.month+1,1)
        cat1s = Cat1.view_objects.filter(cattype=self)
        cat2s = Cat2.view_objects.filter(cattype=self)
        accounts = Account.admin_objects.all()
        transactions = Transaction.view_objects.filter(date_actual__gte=start, date_actual__lt=end,account_destination__in=accounts)
        transactions = transactions | Transaction.view_objects.filter(date_actual__gte=start, date_actual__lt=end,account_source__in=accounts)
        # zbrocoli not dealing with account currencies
        cat1onlytransact = transactions.filter(cat1__in=cat1s,cat2__isnull=True) # .aggregate(Sum('amount_actual')).get('amount_actual__sum')
        cat2transact = transactions.filter(cat2__in=cat2s) # .aggregate(Sum('amount_actual')).get('amount_actual__sum')
        type_transactions = cat1onlytransact | cat2transact
        total = (type_transactions.aggregate(Sum('amount_actual')).get('amount_actual__sum') or Decimal('0.00'))
        # total = (cat1onlytransact or Decimal('0.00')) + (cat2transact or Decimal('0.00'))
        
        return total

    def get_cat1_totals(self, start, end):
        cat1s = Cat1.view_objects.filter(cattype=self)
        accounts = Account.view_objects.all()
        transactions = Transaction.view_objects.filter(date_actual__gte=start, date_actual__lt=end,account_destination__in=accounts,cat1__in=cat1s)
        transactions = transactions | Transaction.view_objects.filter(date_actual__gte=start, date_actual__lt=end,account_source__in=accounts,cat1__in=cat1s)
        # zbrocoli not dealing with account currencies
        cat1s_sums = transactions.values('cat1_id').annotate(Sum('amount_actual'))
        return cat1s_sums

    def get_cat1_monthly_totals(self, start, end):
        cat1s = Cat1.view_objects.filter(cattype=self)
        accounts = Account.view_objects.all()
        transactions = Transaction.view_objects.filter(date_actual__gte=start, date_actual__lt=end,account_destination__in=accounts,cat1__in=cat1s)
        transactions = transactions | Transaction.view_objects.filter(date_actual__gte=start, date_actual__lt=end,account_source__in=accounts,cat1__in=cat1s)
        # zbrocoli not dealing with account currencies
        transactions = transactions.annotate(month=ExtractMonth('date_actual'),year=ExtractYear('date_actual'))
        cat1s_sums = transactions.values('cat1_id','month','year').annotate(Sum('amount_actual'))
        return cat1s_sums


class Cat1(BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    user_permissions = models.OneToOneField(to=UserPermissions, parent_link=True, on_delete=models.CASCADE, related_name='cat1_permissions_child')
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

    user_permissions = models.OneToOneField(to=UserPermissions, parent_link=True, on_delete=models.CASCADE, related_name='cat2_permissions_child')
    cat1 = models.ForeignKey(Cat1, on_delete=models.CASCADE)
    cattype = models.ForeignKey(CatType, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    catbudget = models.ForeignKey(CatBudget, on_delete=models.CASCADE, blank=True, null=True)
    unit_price = models.BooleanField('Do we keep unit quantity and cost per for this subcategory', default=False)
    
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budgetdb:details_cat1', kwargs={'pk': self.cat1.pk})


class Vendor(BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'
        ordering = ['name']

    user_permissions = models.OneToOneField(to=UserPermissions, parent_link=True, on_delete=models.CASCADE, related_name='vendor_permissions_child')
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
        if self.account_destination:
            if self.account_destination.can_edit() is False:
                return False
        if self.account_source:
            if self.account_source.can_edit() is False:
                return False
        return True

    def can_view(self):
        if self.account_destination:
            if self.account_destination.can_view() is False:
                return False
        if self.account_source:
            if self.account_source.can_view() is False:
                return False
        return True


class Template(MyMeta, BaseSoftDelete, BaseEvent, UserPermissions):
    class Meta:
        verbose_name = 'Template'
        verbose_name_plural = 'Templates'

    user_permissions = models.OneToOneField(to=UserPermissions, parent_link=True, on_delete=models.CASCADE, related_name='template_permissions_child')

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
    statement = models.ForeignKey("Statement", on_delete=models.CASCADE, blank=True, null=True)
    verified = models.BooleanField('Verified in a statement', default=False)
    audit = models.BooleanField('Audit', default=False)
    receipt = models.BooleanField('Checked with receipt', default=False)
    balance = models.DecimalField('Balance', decimal_places=2, max_digits=10, blank=True, null=True)
    fit_id = models.CharField(max_length=255, null=True, blank=True)

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
        
    def clean(self):
        super().clean()
        
        # 1. Audit must have an amount
        if self.audit and self.amount_actual is None:
            raise ValidationError({
                'amount_actual': _('An audited transaction must have an actual amount.')
            })
            
        # 2. Prevent transfers to the same account
        if self.account_source == self.account_destination and self.account_source is not None:
            raise ValidationError(
                _('Source and destination accounts cannot be the same.')
            )

        # 3. Ensure dates aren't in the far future (optional sanity check)
        if self.date_actual and self.date_actual > date.today() + relativedelta(years=5):
            raise ValidationError({'date_actual': _('Date is too far in the future.')})

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.can_edit() is True:
            if self.audit is True:
                if Transaction.objects.filter(date_actual=self.date_actual,account_source=self.account_source,audit=True,is_deleted=False).exclude(pk=self.pk).count() > 0:
                    # don't save an audit if there is already one on the same day on the same account
                    return
            super(Transaction, self).save(*args, **kwargs)
            
            dirties = None
            if hasattr(self,'_loaded_values') is False:
                old_source = None
                old_destination = None
                old_date = self.date_actual
            else:
                old_source = self._loaded_values.get('account_source_id')
                old_destination = self._loaded_values.get('account_destination_id')
                old_date = self._loaded_values.get('date_actual')
            
            if old_date != self.date_actual:
                #If the date changed, get the old accounts, old date
                account_filter = [old_destination,
                                  old_source,
                                  ]
                dirties = AccountBalanceDB.objects.filter(account__in=account_filter, db_date=old_date)
                # and new accounts, new date
                account_filter = [self.account_source,
                                  self.account_destination
                                  ]
                dirties = dirties | AccountBalanceDB.objects.filter(account__in=account_filter, db_date=self.date_actual)
            else:
                #same date, old and new for the same date
                account_filter = [old_destination,
                                  old_source,
                                  self.account_source,
                                  self.account_destination
                                  ]
                dirties = AccountBalanceDB.objects.filter(account__in=account_filter, db_date=self.date_actual)

            for dirty in dirties:
                dirty.set_delta_and_dirty()


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

    user_permissions = models.OneToOneField(to=UserPermissions,
                                            parent_link=True,
                                            on_delete=models.CASCADE,
                                            related_name='budgetedevent_permissions_child'
                                            )
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

    user_permissions = models.OneToOneField(to=UserPermissions, parent_link=True, on_delete=models.CASCADE, related_name='statement_permissions_child')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='statement_account')
    balance = models.DecimalField('Statement balance', decimal_places=2, max_digits=10, default=Decimal('0.00'))
    minimum_payment = models.DecimalField('Minimum Payment', decimal_places=2, max_digits=10, default=Decimal('0.00'))
    statement_date = models.DateField('date of the statement')
    statement_due_date = models.DateField('date where payment is due', blank=True, null=True)
    comment = models.CharField(max_length=200, blank=True, null=True)
    payment_transaction = models.ForeignKey('Transaction', on_delete=models.CASCADE, related_name='payment_transaction',
                                            blank=True, null=True)

    def __str__(self):
        # return self.account.name + " " + self.statement_date.strftime('%Y-%m-%d')
        return f'{self.statement_date.strftime('%Y-%m-%d')} - {self.account.name} - {self.account.currency.symbol}{self.balance:,.2f}'

    def get_absolute_url(self):
        return reverse('budgetdb:details_statement', kwargs={'pk': self.pk})


class JoinedTransactions(MyMeta, BaseSoftDelete, UserPermissions):
    class Meta:
        verbose_name = 'Joined Transactions'
        verbose_name_plural = 'Joined Transactions'

    user_permissions = models.OneToOneField(to=UserPermissions, parent_link=True, on_delete=models.CASCADE, related_name='joinedtransactions_permissions_child')
    name = models.CharField(max_length=200)
    comment = models.CharField(max_length=200, blank=True, null=True)
    transactions = models.ManyToManyField(Transaction, related_name='transactions')
    budgetedevents = models.ManyToManyField(BudgetedEvent, related_name='budgeted_events')
    isrecurring = models.BooleanField('Is this a recurring event?', default=True)
