import django_tables2 as tables
from budgetdb.models import *
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


class AccountActivityListTable(tables.Table):
    addtransaction = tables.TemplateColumn(
        template_name="budgetdb/table2_columns/_transaction_list_render_addtransaction.html",
        orderable=False, 
        empty_values=(),
        verbose_name='',
        attrs={"td": {"class": "description-column"}}
    )
    date_actual = tables.Column(
        verbose_name='Date',
        attrs={"td": {"class": "min"}},
        order_by=("date_actual", 'audit','-verified', '-id')
    )
    amount_actual = tables.Column(verbose_name='$', orderable=False)
    mybalance = tables.Column(verbose_name='Balance', orderable=False, empty_values=(), attrs=HIDE_ON_PHONE)
    statement = tables.TemplateColumn(    
        template_name="budgetdb/table2_columns/_transaction_list_render_statement.html",
        verbose_name='Statement',
        attrs=SHOW_DESKTOP_ONLY,
        orderable=False
    )
    description = tables.TemplateColumn(
        template_name="budgetdb/table2_columns/_transaction_list_render_description.html",
        orderable=False, 
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
        orderable=False,
        empty_values=()
    )
    cat2 = tables.TemplateColumn(
        template_name="budgetdb/table2_columns/_transaction_list_render_cat2.html",
        verbose_name='Sub-Cat',
        attrs=SHOW_DESKTOP_ONLY,
        orderable=False,
        empty_values=()
    )
    receipt = tables.TemplateColumn(
        template_name="budgetdb/table2_columns/_transaction_list_render_receipt.html",
        verbose_name='Receipt',
        attrs=HIDE_ON_VERTICAL_PHONE,
        orderable=False
    )
    verified = tables.TemplateColumn(
        template_name="budgetdb/table2_columns/_transaction_list_render_verified.html",
        verbose_name='Verif',
        attrs=HIDE_ON_VERTICAL_PHONE,
        orderable=False
    )
    addaudit = tables.Column(verbose_name='Audit', orderable=False, empty_values=(), attrs=HIDE_ON_PHONE)

    view_account_id = None
    account = None
    account_currency_symbol = ''
    previous_date = None
    previous_balance = None
    previous_amount = None
    previous_source = None
    linebalance = None

    class Meta:
        model = Transaction
        fields = ("addtransaction", "date_actual", "statement", "description", "recurencelinks",
                  "cat1", "cat2", "amount_actual", "verified", "receipt", "mybalance", "addaudit")
        attrs = {"class": "table table-hover"}
        order_by = ("-date_actual")
        per_page = 150
        row_attrs = {
            "id": lambda record: f'T{record.pk}',
            "class": lambda record: set_class_transaction(record)
        }
    
    def __init__(self, *args, **kwargs):  
        view_account_id = kwargs.pop('account_view') 
        self.account = Account.view_objects.get(pk=view_account_id)
        self.begin = kwargs.pop('begin') 
        self.end = kwargs.pop('end') 
        self.account_currency_symbol = self.account.currency.symbol
        self.balances = self.account.get_balances(self.begin, self.end)
        self.request = kwargs.pop("request", None)
        self.all_cat1s = list(Cat1.admin_objects.all())
        #############################################################################################################
        # Logic: Only show balance if we are sorted by date (descending or ascending)
        # self.order_by is a tuple, e.g., ('-date_actual',)
        
        # is_date_sorted = any('date_actual' in s for s in self.order_by)
        # if not is_date_sorted:
          #   self.columns.hide('mybalance')
        super().__init__(*args, **kwargs)

    def render_date_actual(self, value):
        # strftime("%Y-%m-%d")
        return format(value.strftime("%Y-%m-%d"))

    def render_amount_actual(self, value, record):
        if record.audit:
            return mark_safe("")
        if not (record.budget_only is True and record.date_actual <= date.today()):
            if record.account_source == self.account:
                value = value * -1
        else:
            return mark_safe("")         
        return format_html('{amount}{symbol}',
            amount=value,
            symbol=self.account_currency_symbol)

    def render_mybalance(self, value, record):
        if record.audit:
            return mark_safe("")
        if self.order_by[0] == '-date_actual':
            balance = self.balances.get(db_date=record.date_actual).balance
            if self.previous_date is None or self.previous_date != record.date_actual:
                self.previous_date = record.date_actual
                self.previous_amount = record.amount_actual
                self.previous_balance = balance
                self.previous_source = record.account_source
            else:
                if self.previous_source == self.account:
                    balance = self.previous_balance + self.previous_amount
                else:
                    balance = self.previous_balance - self.previous_amount
                self.previous_amount = record.amount_actual
                self.previous_balance = balance
                self.previous_source = record.account_source
            self.linebalance = balance
            return format_html('{amount}{symbol}',
                    amount=balance,
                    symbol=self.account_currency_symbol) 
        else:
            pass

    def render_addaudit(self, value, record):
        if record.audit:
            return format_html('{amount}{symbol}',
                                amount=record.amount_actual,
                                symbol=self.account_currency_symbol)        

        balance_str = get_balance_token(self.linebalance)
        reverse_url = reverse("budgetdb:list_account_activity_create_audit_from_account",
                              kwargs={"accountpk": self.account.pk,
                                      "date": record.date_actual.strftime("%Y-%m-%d"),
                                      "amount": balance_str,
                                      }
                             )
        return format_html('<button  type="button" '
                           'title="Confirm account balance for this day"'
						   'class="update-transaction btn btn-link btn-sm" data-form-url="{url}">'
                           '<span class="material-symbols-outlined">add_circle</span>'
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
    reconciled = tables.Column(empty_values=(), verbose_name="Reconciled")
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
                return format_html('<b style="color: green;">OK but {} transactions are not verified', unverified_count)
            else:
                return mark_safe('<b style="color: green;">OK All verified</b>')
        delta = record.balance - total
        formatted_delta = "{:.2f}".format(delta)
        return format_html('<b style="color: red;">Total: {} Delta: {}{}</b>',total, formatted_delta,record.account.currency.symbol)

    def render_verified_lock(self, value, record):
        if value:
            icon = "lock"
            tooltip = "Click to Unlock"
            css_class = "lock-icon-verified"
        else:
            icon = "lock_open"
            tooltip = "Click to Verify"
            css_class = "lock-icon-unverified"
        
        toggle_url = reverse('budgetdb:toggleverifystatement_json', kwargs={'pk': record.pk})
        return format_html(
            '''
            <style>
                .lock-wrapper {{ transition: transform 0.2s; display: inline-block; }}
                .lock-wrapper:hover {{ transform: scale(1.2); cursor: pointer; }}
                .lock-icon-verified {{ 
                    display: inline-flex; align-items: center; justify-content: center; 
                    background-color: #2e7d32; color: white; border-radius: 50%; 
                    width: 30px; height: 30px; font-size: 18px; 
                }}
                .lock-icon-unverified {{ 
                    color: #9e9e9e; font-size: 30px; vertical-align: middle; 
                }}
            </style>
            <a href="{0}" title="{1}" class="lock-wrapper">
                <span class="material-symbols-outlined {2}">{3}</span>
            </a>
            ''',
            toggle_url,
            tooltip,
            css_class,
            icon
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
