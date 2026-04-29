import django_tables2 as tables
from budgetdb.models import *
from decimal import Decimal
from django.utils.html import format_html
from django.urls import reverse
from crum import get_current_user
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

class MySharingColumns(tables.Table):
    access_rights = tables.Column(verbose_name='Access', orderable=False, empty_values=())
    shared = tables.Column(verbose_name='Shared', orderable=False, empty_values=())

    def render_access_rights(self, value, record):
        if record.owner.id == get_current_user().id:
            return _('Owner')
        if record.can_edit() is True:
            return _('Read/Write')
        else:
            return _('Read Only')

    def render_shared(self, value, record):
        users = record.users_admin.all().exclude(id=get_current_user().id)
        users = users | record.users_view.all().exclude(id=get_current_user().id)
        users = users.distinct()
        nb_users = users.count()
    
        if nb_users == 0:
            return _("Not shared")
        elif nb_users == 1:
            first_name = users.first().first_name.capitalize()
            return format_html(
                _("Shared with {name}"),
                name=first_name
            )
        elif nb_users == 2:
            # Get the first two names
            names = [u.first_name.capitalize() for u in users[:2]]
            return format_html(
                _("Shared with {name1} and {name2}"),
                name1=names[0],
                name2=names[1]
            )
        else:  # Case: Many
            first_name = users.first().first_name.capitalize()
            others_count = user_count - 1
            return format_html(
                _("Shared with {name} and {count} others"),
                name=first_name,
                count=others_count
    )


class AccountListTable(MySharingColumns, tables.Table):
    category = tables.Column(verbose_name='Category', orderable=False, empty_values=())

    class Meta:
        model = Account
        fields = ("account_host", "name", "account_parent", "category")
        attrs = {"class": "table table-hover table-striped"}
        # per_page = 30

    def render_name(self, value, record):
        return format_html('<a href="{}">{}</a>',
                           reverse('budgetdb:account_max_redirect', kwargs={'pk': record.id}),
                           value, record.name)

    def render_account_host(self, value, record):
        return format_html('<a href="{}">{}</a>',
                           reverse('budgetdb:accounthost_max_redirect', kwargs={'pk': record.account_host_id}),
                           value, record.account_host)

    def render_account_parent(self, value, record):
        if record.account_parent is not None:
            return format_html('<a href="{}">{}</a>',
                               reverse('budgetdb:account_max_redirect', kwargs={'pk': record.account_parent_id}),
                               value, record.account_parent)
        return ""

    def render_category(self, value, record):

        categories = ''
        for category in record.account_categories.filter(is_deleted=False):
            if categories != '':
                categories += f' / '
            categories += f'<a href={reverse("budgetdb:account_max_redirect", kwargs={"pk": category.id})}>{category.name}</a>'

        return mark_safe(categories)


def set_class_transaction(record):
    row_class = ''
    if record.audit == 1:
        row_class = 'AUDIT '
    if record.budgetedevent_id is not None:
        row_class = row_class + 'BUDGET '
    if record.verified:
        row_class = row_class + 'VERIFIED '
    else:
        row_class = row_class + 'UNVERIFIED '
    if record.ismanual:
        row_class = row_class + 'MANUAL '
    if record.receipt:
        row_class = row_class + 'RECEIPT '
    else:
        row_class = row_class + 'NORECEIPT'
    return row_class

def get_balance_token(balance):
    balance_str = ''
    if balance is None:
        return '0'
    if balance < 0:
        balance_str = 'N'
    balance_str = balance_str + str(abs(balance)).replace('.','',1)
    return balance_str

# 1. Hidden on vertical phones, shows on landscape phones and up
HIDE_ON_VERTICAL_PHONE = {
    "th": {"class": "d-none d-sm-table-cell"},
    "td": {"class": " d-none d-sm-table-cell"}
}

# 2. Hidden on all phones, shows on Tablets and up
HIDE_ON_PHONE = {
    "th": {"class": "d-none d-md-table-cell"},
    "td": {"class": " d-none d-md-table-cell"}
}

# 3. Hidden on everything except large Desktop screens
SHOW_DESKTOP_ONLY = {
    "th": {"class": "d-none d-lg-table-cell"},
    "td": {"class": " d-none d-lg-table-cell"}
}


class BaseTransactionListTable(tables.Table):
    addtransaction = tables.TemplateColumn(
        template_name="budgetdb/table2_columns/_transaction_list_render_addtransaction.html",
        orderable=False, 
        empty_values=(),
        verbose_name='',
        attrs={"td": {"class": "description-column"}}
    )
    date_actual = tables.TemplateColumn(
        template_name="budgetdb/table2_columns/_transaction_list_render_date.html",
        verbose_name='Date',
        attrs={"td": {"class": "min"}},
        order_by=("date_actual", '-id')
    )
    mybalance = tables.Column(verbose_name='Balance', orderable=False, empty_values=(), attrs=HIDE_ON_PHONE)
    statement = tables.TemplateColumn(    
        template_name="budgetdb/table2_columns/_transaction_list_render_statement.html",
        verbose_name='Statement',
        attrs=SHOW_DESKTOP_ONLY,
        #orderable=False
    )
    description = tables.TemplateColumn(
        template_name="budgetdb/table2_columns/_transaction_list_render_description.html",
        #orderable=False, 
        attrs={"td": {"class": "description-column"}}
    )
    recurencelinks = tables.TemplateColumn(
        template_name="budgetdb/table2_columns/_transaction_list_render_recurencelinks.html",
        verbose_name='Repeat',
        orderable=False,
        empty_values=(),
        attrs=HIDE_ON_PHONE
    )
    cat1 = tables.TemplateColumn(
        template_name="budgetdb/table2_columns/_transaction_list_render_cat1.html",
        verbose_name='Category',
        attrs=SHOW_DESKTOP_ONLY,
        #orderable=False,
        empty_values=()
    )
    cat2 = tables.TemplateColumn(
        template_name="budgetdb/table2_columns/_transaction_list_render_cat2.html",
        verbose_name='Sub-Cat',
        attrs=SHOW_DESKTOP_ONLY,
        #orderable=False,
        empty_values=()
    )   
    amount_actual = tables.TemplateColumn(
        template_name="budgetdb/table2_columns/_transaction_list_render_amount_actual.html",
        verbose_name='$',
        #attrs=HIDE_ON_VERTICAL_PHONE,
        #orderable=False
        extra_context={'today': date.today()}
    )    
    receipt = tables.TemplateColumn(
        template_name="budgetdb/table2_columns/_transaction_list_render_receipt.html",
        verbose_name='Receipt',
        attrs=HIDE_ON_VERTICAL_PHONE,
        #orderable=False
    )
    verified = tables.TemplateColumn(
        template_name="budgetdb/table2_columns/_transaction_list_render_verified.html",
        verbose_name='Verif',
        attrs=HIDE_ON_VERTICAL_PHONE,
        #orderable=False
    )
    addaudit = tables.Column(verbose_name='Audit', orderable=False, empty_values=(), attrs=HIDE_ON_PHONE)

    account = None
 
    class Meta:
        model = Transaction
        fields = ("addtransaction", "date_actual", "statement", "description", "recurencelinks",
                  "cat1", "cat2", "amount_actual", "verified", "receipt", "mybalance", "addaudit")
        attrs = {"class": "table table-hover"}
        order_by = ('date_actual','-id')
        per_page = 150
        row_attrs = {
            "id": lambda record: f'T{record.pk}',
            "class": set_class_transaction,
            "data-txid": lambda record: record.pk,
            "data-date": lambda record: record.date_actual.strftime('%Y-%m-%d') if record.date_actual else "",
        }
    
    def __init__(self, *args, **kwargs): 
        self.filter_type = kwargs.pop('filter_type', 'account')
        self.filter_pk = kwargs.pop('filter_pk', None)
        self.begin = kwargs.pop('begin', None)
        self.end = kwargs.pop('end', None)
        self.statement = kwargs.pop('statement', None)
        self.request = kwargs.pop("request", None)
        
        self.context_object = None
        if self.filter_pk:
            model_map = kwargs.pop("model_map", None)
            if model_map:
                self.context_object = model_map[self.filter_type].view_objects.get(pk=self.filter_pk) 

        # Guard Account-specific logic
        if self.filter_type == 'account':
            self.account = self.context_object
        else:
            self.account = None

        self.all_cat1s = list(Cat1.admin_objects.all())
        
        super().__init__(*args, **kwargs)

        order_by = self.request.GET.get('sort', '') if self.request else "missing"

        # 2. Logic: If there is no sort, or if the sort is NOT on date_actual, hide the column
        is_sorted_by_date = False
        if order_by != "missing":
            # Check if the first sort key (the primary one) is date_actual (asc or desc)
            primary_sort = order_by.lstrip('-') 
            if primary_sort == '' or primary_sort == 'date_actual':
                is_sorted_by_date = True
        
        if self.filter_type != 'account':
            self.columns.hide('mybalance')
            self.columns.hide('addaudit')
            self.columns.hide('statement')
            self.columns.hide('addtransaction')
        elif not is_sorted_by_date:
            self.columns.hide('mybalance')
            self.columns.hide('addaudit')
            self.columns.hide('addtransaction')

    def render_date_actual(self, value):
        # strftime("%Y-%m-%d")
        return format(value.strftime("%Y-%m-%d"))

    def render_mybalance(self, value, record):
        balance = getattr(record, 'calculated_balance', None)
        if record.amount_actual == Decimal(2766.92):
            pass
        if not self.account or balance is None or record.audit:
            return mark_safe("")
        currency = record.account_source.currency if record.account_source else record.account_destination.currency
        return format_html('{amount}{symbol}',
            amount=balance,
            symbol=currency.symbol
        )


    def render_addaudit(self, value, record):
        if record.audit:
            return format_html('{amount}{symbol}',
                                amount=record.amount_actual,
                                symbol=record.account_source.currency.symbol)        

        balance_str = f'{record.calculated_balance}'.replace('.','')
        reverse_url = reverse("budgetdb:create_audit_transaction_from_account",
                              kwargs={"accountpk": self.account.pk,
                                      "date": record.date_actual.strftime("%Y-%m-%d"),
                                      "amount": balance_str,
                                      }
                             )
        return format_html('<button  type="button" '
                           'title="Confirm account balance for this day"'
						   'class="update-transaction btn btn-link btn-sm" data-form-url="{url}">'
                           '<span class="material-symbols-outlined" style="font-size: 18px; vertical-align: middle; display: inline-block;">add_circle</span>'
                           '</button>',
                           url=reverse_url
                           )


class AccountCategoryListTable(MySharingColumns, tables.Table):
    class Meta:
        model = AccountCategory
        fields = ("name",)
        attrs = {"class": "table table-hover table-striped"}
        # per_page = 30

    def render_name(self, value, record):
        return format_html('<a href="{}">{}</a>',
                           reverse('budgetdb:accountcategory_max_redirect', kwargs={'pk': record.id}),
                           value, record.name)


class AccountHostListTable(MySharingColumns, tables.Table):
    class Meta:
        model = AccountHost
        fields = ("name",)
        attrs = {"class": "table table-hover table-striped"}
        # per_page = 30

    def render_name(self, value, record):
        return format_html('<a href="{}">{}</a>',
                           reverse('budgetdb:accounthost_max_redirect', kwargs={'pk': record.id}),
                           value, record.name)


class BudgetedEventListTable(MySharingColumns, tables.Table):
    lastTransactionDate = tables.Column(verbose_name='Last planned transaction', orderable=False)

    class Meta:
        model = BudgetedEvent
        fields = ("description", "lastTransactionDate", "account_source", "account_destination")
        attrs = {"class": "table table-hover table-striped"}
        per_page = 50

    def render_description(self, value, record):
        return format_html('<a href="{}">{}</a>',
                           reverse('budgetdb:details_be', kwargs={'pk': record.id}),
                           value, record.description)

    def render_lastTransactionDate(self, value, record):
        if value == "No Transaction":
            return format_html('<button type="button" class="btn btn-danger">{}</button>', value)
        else:
            return format_html('{}', value)


class Cat1ListTable(MySharingColumns, tables.Table):
    cattype = tables.Column(verbose_name='Category Type')

    class Meta:
        model = Cat1
        fields = ("name", "cattype", "catbudget",)
        attrs = {"class": "table table-hover table-striped"}
        # per_page = 30

    def render_name(self, value, record):
        return format_html('<a href="{}">{}</a>',
                           reverse('budgetdb:details_cat1', kwargs={'pk': record.id}),
                           value, record.name)


class Cat2ListTable(MySharingColumns, tables.Table):
    cattype = tables.Column(verbose_name='Category Type')

    class Meta:
        model = Cat2
        fields = ("name", "cat1", "cattype", "catbudget",)
        attrs = {"class": "table table-hover table-striped"}
        # per_page = 30

    def render_name(self, value, record):
        return format_html('<a href="{}">{}</a>',
                           reverse('budgetdb:cat2_max_redirect', kwargs={'pk': record.id}),
                           value, record.name)


class CatTypeListTable(MySharingColumns, tables.Table):
    class Meta:
        model = CatType
        fields = ("name",)
        attrs = {"class": "table table-hover table-striped"}
        # per_page = 30

    def render_name(self, value, record):
        return format_html('<a href="{}">{}</a>',
                           reverse('budgetdb:cattype_max_redirect', kwargs={'pk': record.id}),
                           value, record.name)


class InvitationListTable(tables.Table):
    status = tables.Column(verbose_name='Invitation Status', empty_values=(), orderable=False)
    class Meta:
        model = Invitation
        fields = ("email",)
        attrs = {"class": "table table-hover table-striped"}
        # per_page = 30
    
    def render_status(self, value, record):
        user = get_current_user()
        status = ''
        accept_URL = reverse('budgetdb:accept_invitation', kwargs={'pk':record.id})
        reject_URL = reverse('budgetdb:reject_invitation', kwargs={'pk':record.id})
        accept_button = (f'<a href="{accept_URL}" '
                         f'class="btn btn-warning btn-sm" role="button">'
                         f'grant access'
                         f'</a>'
                         )
        reject_button = (f'<a href="{reject_URL}" '
                         f'class="btn btn-success btn-sm" role="button">'
                         f'block access'
                         f'</a>'
                         )
        if record.accepted:
            status = 'Accepted  ' + reject_button
        elif record.rejected:
            status = 'Rejected  ' + accept_button
        elif record.owner == user:
            status = 'Pending  ' + reject_button
        else:
            status = accept_button + ' ' + reject_button
        return mark_safe(status)

    def render_email(self, value, record):
        user = get_current_user()
        if record.email == user.email:
            label = f'<a href="mailto: {record.owner.email}">From {record.owner.first_name}</a>'
        else:
            label = f'<a href="mailto: {record.email}">To {record.email}</a>'
        return mark_safe(label)


class JoinedTransactionsListTable(MySharingColumns, tables.Table):
    class Meta:
        model = JoinedTransactions
        fields = ("name",)
        attrs = {"class": "table table-hover table-striped"}
        # per_page = 30

    def render_name(self, value, record):
        return format_html('<a href="{}">{}</a>',
                           reverse('budgetdb:details_joinedtransactionsconfig', kwargs={'pk': record.id}),
                           value, record.name)


class TransactionListTable(tables.Table):
    class Meta:
        model = Transaction
        fields = ("date_actual", "description", "cat1", "cat2", "account_source", "account_destination", "amount_actual")
        attrs = {"class": "table table-hover table-striped"}
        # per_page = 30

    def render_description(self, value, record):
        return format_html('<a href="{}">{}</a>',
                           reverse('budgetdb:transaction_max_redirect', kwargs={'pk': record.id}),
                           value, record.description)


class StatementListTable(MySharingColumns, tables.Table):
    account_host = tables.Column(verbose_name='Host', empty_values=(), orderable=False)
    reconciled = tables.Column(
        empty_values=(),
        verbose_name="Reconciled",
        orderable=False
    )
    verified_lock = tables.Column(
        orderable=True, 
        verbose_name='Verified and locked',
        empty_values=(),
    )
    class Meta:
        model = Statement
        fields = ("account_host", "account", "statement_date", "balance", "statement_due_date", "payment_transaction", "reconciled", "verified_lock")
        attrs = {"class": "table table-hover table-striped"}
        # per_page = 30

    def render_account_host(self, value, record):
        return format_html(
                    '<a href="{url}">{label}</a>',
                    url=reverse("budgetdb:accounthost_max_redirect", kwargs={"pk": record.account.account_host.id}),
                    label=record.account.account_host.name
                    )

    def render_account(self, value, record):
        return format_html(
                    '<a href="{url}">{label}</a>',
                    url=reverse("budgetdb:account_max_redirect", kwargs={"pk": record.account.id}),
                    label=record.account.name
                    )

    def render_statement_date(self, value, record):
        return format_html(
                    '<a href="{statement_url}">{label}</a> ',
                    statement_url=reverse("budgetdb:details_statement", kwargs={"pk": record.id}),
                    label=record.statement_date,
                    )

    def render_payment_transaction(self, value, record):
        return format_html('{} - {}{}',
            record.payment_transaction.date_actual,
            record.payment_transaction.account_source.currency.symbol,
            record.payment_transaction.amount_actual
            )

    def render_balance(self, value, record):
        return format_html('<b">{}{}</b>',record.balance,record.account.currency.symbol)

    def render_reconciled(self, record):
        # This looks at the virtual field we created in the View
        total = getattr(record, 'calculated_total', 0)
        if total is None:
            total = Decimal(0.00)
        if record.balance == total:
            unverified_count = Transaction.objects.filter(statement_id=record.id,verified=False,is_deleted=False).count()
            if unverified_count>0:
                return format_html('<b class="text-success-emphasis">OK but {} transactions are not verified', unverified_count)
            else:
                return mark_safe('<b class="text-success-emphasis">OK All verified</b>')
        delta = record.balance - total
        formatted_delta = "{:.2f}".format(delta)
        return format_html('<b class="text-danger-emphasis">Total: {} Delta: {}{}</b>',total, formatted_delta,record.account.currency.symbol)

    def render_verified_lock(self, value, record):
        # Calculate if the statement is ready to be locked
        is_balanced = record.balance == getattr(record, 'calculated_total', 0)
        has_unverified = Transaction.objects.filter(
            statement_id=record.id, verified=False, is_deleted=False
        ).exists() 
        
        lockable = is_balanced and not has_unverified

        if value: # Currently Locked
            icon, css_class, tooltip = "lock", "lock-icon-verified", "Click to Unlock"
        else: # Currently Unlocked
            icon = "lock_open"
            css_class = "lock-icon-unverified"
            tooltip = "Click to Lock" if lockable else "Not ready to Lock"

        # Only provide the link if it's already locked OR if it's eligible to be locked
        if value or lockable:
            toggle_url = reverse('budgetdb:togglelockstatement_json', kwargs={'pk': record.pk})
            return format_html(
                '<a href="{}" title="{}" class="lock-wrapper toggle-statement-lock">'
                '<span class="material-symbols-outlined {}">{}</span>'
                '</a>',
                toggle_url, tooltip, css_class, icon
            )
        
        # Just a dead icon if it's not ready
        return format_html(
            '<span class="material-symbols-outlined {}" title="{}">{}</span>',
            css_class, tooltip, icon
        )


class VendorListTable(MySharingColumns, tables.Table):
    class Meta:
        model = Vendor
        fields = ("name",)
        attrs = {"class": "table table-hover table-striped"}
        # per_page = 30

    def render_name(self, value, record):
        return format_html('<a href="{}">{}</a>',
                           reverse('budgetdb:vendor_max_redirect', kwargs={'pk': record.id}),
                           value, record.name)


class TemplateListTable(MySharingColumns, tables.Table):
    class Meta:
        model = Template
        fields = ("vendor", "description",)
        attrs = {"class": "table table-hover table-striped"}
        # per_page = 30

    def render_vendor(self, value, record):
        return format_html('<a href="{}">{}</a>',
                           reverse('budgetdb:template_max_redirect', kwargs={'pk': record.id}),
                           value, record.vendor)
