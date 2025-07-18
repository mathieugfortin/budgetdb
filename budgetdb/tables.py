import django_tables2 as tables
from budgetdb.models import *
from django.utils.html import format_html
from django.urls import reverse
from crum import get_current_user


class MySharingColumns(tables.Table):
    access_rights = tables.Column(verbose_name='Access', orderable=False, empty_values=())
    shared = tables.Column(verbose_name='Shared', orderable=False, empty_values=())

    def render_access_rights(self, value, record):
        if record.owner.id == get_current_user().id:
            return format_html("Owner")
        if record.can_edit() is True:
            return format_html("Read/Write")
        else:
            return format_html("Read Only")

    def render_shared(self, value, record):
        users = record.users_admin.all().exclude(id=get_current_user().id)
        users = users | record.users_view.all().exclude(id=get_current_user().id)
        users = users.distinct()
        nb_users = users.count()
        if nb_users == 0:
            return format_html("")
        elif nb_users == 1:
            return format_html(f"Shared with {users.first().first_name.capitalize()}")
        elif nb_users == 2:
            return format_html(f"Shared with {users.first().first_name.capitalize()} and {users.last().first_name.capitalize()}")
        else:
            return format_html(f"Shared with {nb_users} users")


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

        return format_html(categories)


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

class AccountActivityListTable(tables.Table):
    addtransaction = tables.Column(verbose_name='', orderable=False, empty_values=())
    date_actual = tables.Column(verbose_name='Date',
                                attrs={"td": {"class": "min"}},
                                order_by=("date_actual", 'audit','-verified', '-id')
                                )
    recurencelinks = tables.Column(verbose_name='Repeat', orderable=False, empty_values=(), attrs={"th": {"class": "d-none d-md-table-cell"},"td": {"class": "min d-none d-md-table-cell"}})
    amount_actual = tables.Column(verbose_name='$', orderable=False)
    description = tables.Column(orderable=False)
    mybalance = tables.Column(verbose_name='Balance', orderable=False, empty_values=())
    verified = tables.Column(verbose_name='verif', attrs={"th": {"class": "d-none d-sm-table-cell"},"td": {"class": "min d-none d-sm-table-cell"}}, orderable=False)
    statement = tables.Column(verbose_name='Statement', attrs={"th": {"class": "d-none d-xl-table-cell"},"td": {"class": "d-none d-xl-table-cell"}}, orderable=False)
    receipt = tables.Column(verbose_name='Receipt', attrs={"th": {"class": "d-none d-sm-table-cell"},"td": {"class": "min d-none d-sm-table-cell"}}, orderable=False)
    cat1 = tables.Column(attrs={"th": {"class": "d-none d-lg-table-cell"},"td": {"class": "d-none d-lg-table-cell"}}, orderable=False)
    cat2 = tables.Column(attrs={"th": {"class": "d-none d-lg-table-cell"},"td": {"class": "d-none d-lg-table-cell"}}, orderable=False)
    addaudit = tables.Column(verbose_name='Audit', orderable=False, empty_values=(), attrs={"th": {"class": "d-none d-md-table-cell"},"td": {"class": "min d-none d-md-table-cell"}})
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
        super().__init__(*args, **kwargs)

    def render_statement(self, record):
        field = ''
        if record.statement is not None:
            reverse_url = reverse("budgetdb:details_statement", kwargs={"pk": record.statement.id})
            field = field + (f'<a class="btn btn-outline-primary btn-sm" '
                f'href="{reverse_url}">'
                f'{record.statement}'
                f'</a>')
        return format_html(field)

    def render_receipt(self, record):
        if record.audit:
            return format_html('')
        if record.receipt is True:
            field = (f'<span class="material-symbols-outlined RECEIPT" onclick="togglereceiptT({record.id})" id="R{record.id}"></span>' )
        else:
            field = (f'<span class="material-symbols-outlined NORECEIPT" onclick="togglereceiptT({record.id})" id="R{record.id}"></span>' )
        return format_html(field)

    def render_verified(self, record):
        if record.audit:
            return format_html('')
        if record.verified is True:
            field = (f'<span class="material-symbols-outlined VERIFIED" onclick="toggleverifyT({record.id})" id="V{record.id}"></span>' )
        else:
            field = (f'<span class="material-symbols-outlined UNVERIFIED" onclick="toggleverifyT({record.id})" id="V{record.id}"></span>' )
        return format_html(field)

    def render_recurencelinks(self, value, record):
        field = ''        
        if record.budgetedevent is not None:
            reverse_url = reverse("budgetdb:update_be", kwargs={"pk": record.budgetedevent.id})
            field = field + (f'<a href="{reverse_url}" '
                f'title="Edit the recurring event">'
                f'<span class="material-symbols-outlined">manufacturing</span>'
                f'</a>')
            reverse_url = reverse("budgetdb:details_be", kwargs={"pk": record.budgetedevent.id})
            field = field + (f'<a href='
                f'"{reverse_url}" '
                f'title="view the recurring event">'
                f'<span class="material-symbols-outlined">list</span>'
                f'</a>')
        return format_html(field)

    def render_description(self, value, record):
        field = ''
        if record.vendor is not None:
            field = field + (f'<button type="button" '
                f'class="update-transaction btn btn-sm"> '
                f'{record.vendor}'
                f'</button>')
        reverse_url = reverse("budgetdb:account_listview_update_transaction_modal", kwargs={"pk": record.id,
                                                                                            "accountpk": self.account.pk})
        field = field + (f'<button type="button" '
            f'class="update-transaction btn btn-secondary btn-sm" '
            f'data-form-url="{reverse_url}">'
            f'{record.description}'
            f'</button>')

        show_currency = False
        if record.account_destination is not None:
            if record.account_destination.currency != record.currency:
                show_currency = True
        if record.account_source is not None:
            if record.account_source.currency != record.currency:
                show_currency = True
        if show_currency:
            field = field + (f'<button type="button" '
                f'class="btn btn-info btn-sm" >'
                f'{record.amount_actual_foreign_currency} '
                f'{record.currency.name_short} '
                f'</button>')
        if record.Unit_price is not None:
            field = field + (f'<button type="button" '
                f'class="btn btn-sm" >'
                f'{record.Unit_price:.2f}{record.currency.symbol}/unit '
                f'</button>')
        joinedtransaction = None
        if record.budgetedevent is not None:
            joinedtransaction = record.budgetedevent.budgeted_events.first()
        if joinedtransaction is None:
            joinedtransaction = record.transactions.first()

        if joinedtransaction is not None:
            reverse_url = reverse("budgetdb:update_joinedtransactions",
                                     kwargs={"pk": joinedtransaction.id,
                                             "datep": record.date_planned.strftime("%Y-%m-%d"),
                                             "datea": record.date_actual.strftime("%Y-%m-%d"),
                                            }
                                    )
            field = field + (f'<a href='
                f'"{reverse_url}" '
                f'title="Edit the joined transactions">'
                f'<span class="material-symbols-outlined"><span class="material-symbols-outlined">dynamic_feed</span></span>'
                f'</a>')

        if record.account_destination is not None and record.account_destination != self.account:
            reverse_url = reverse("budgetdb:list_account_activity",
                                       kwargs={"pk": record.account_destination.id,}
                                       )
            field = field + (
                f'<a href='
                f'"{reverse_url}" '
                f'class="btn btn-info btn-sm" role="button"> '
                f'<span class="material-symbols-outlined" style="vertical-align: -8px;">keyboard_double_arrow_right</span>'
                f'{record.account_destination}'
                f'</a>')
        if record.account_source is not None and record.account_source != self.account:
            reverse_url = reverse("budgetdb:list_account_activity",
                                       kwargs={"pk": record.account_source.id,}
                                       )
            field = field + (
                f'<a href='
                f'"{reverse_url}" '
                f'class="btn btn-info btn-sm" role="button"> '
                f'<span class="material-symbols-outlined" style="vertical-align: -8px;">keyboard_double_arrow_left</span>'
                f'{record.account_source}'
                f'</a>')
  
        return format_html(field)

    def render_date_actual(self, value):
        # strftime("%Y-%m-%d")
        return format(value.strftime("%Y-%m-%d"))

    def render_amount_actual(self, value, record):
        if record.audit:
            return format_html('')
        if not (record.budget_only is True and record.date_actual <= date.today()):
            if record.account_source == self.account:
                value = value * -1
        else:
            return format_html('')         
        return format_html(f'{value}{self.account_currency_symbol}')

    def render_mybalance(self, value, record):
        if record.audit:
            return format_html('')
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
            return format_html(f'{balance}{self.account_currency_symbol}') 
        else:
            pass

    def render_addtransaction(self, value, record):
        reverse_url = reverse("budgetdb:create_transaction_from_date_account_modal",
                              kwargs={"accountpk": self.account.pk,
                                      "date": record.date_actual.strftime("%Y-%m-%d"),
                                      }
                             )
        return format_html(f'<button  type="button" '
                           f'title="Add a transaction for this day"'
						   f'class="update-transaction btn btn-link btn-sm" data-form-url="{reverse_url}">'
                           f'<span class="material-symbols-outlined">add_circle</span>'
                           f'</button>'
                           )

    def render_addaudit(self, value, record):
        if record.audit:
            return format_html(f'{record.amount_actual}{self.account_currency_symbol}')        
        balance_str = get_balance_token(self.linebalance)
        reverse_url = reverse("budgetdb:list_account_activity_create_audit_from_account",
                              kwargs={"accountpk": self.account.pk,
                                      "date": record.date_actual.strftime("%Y-%m-%d"),
                                      "amount": balance_str,
                                      }
                             )
        return format_html(f'<button  type="button" '
                           f'title="Confirm account balance for this day"'
						   f'class="update-transaction btn btn-link btn-sm" data-form-url="{reverse_url}">'
                           f'<span class="material-symbols-outlined">add_circle</span>'
                           f'</button>'
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
            # return format_html('<div class="alert alert-danger" role="alert">{}</div>', value)
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
        return format_html(status)

    def render_email(self, value, record):
        user = get_current_user()
        if record.email == user.email:
            label = f'<a href="mailto: {record.owner.email}">From {record.owner.first_name}</a>'
        else:
            label = f'<a href="mailto: {record.email}">To {record.email}</a>'
        return format_html(label)


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

    class Meta:
        model = Statement
        fields = ("account_host", "account", "statement_date",)
        attrs = {"class": "table table-hover table-striped"}
        # per_page = 30

    def render_account_host(self, value, record):
        return format_html(f'<a href="{reverse("budgetdb:accounthost_max_redirect", kwargs={"pk": record.account.account_host.id})}">{record.account.account_host.name}</a>')

    def render_account(self, value, record):
        return format_html(f'<a href="{reverse("budgetdb:account_max_redirect", kwargs={"pk": record.account.id})}">{record.account.name}</a>')

    def render_statement_date(self, value, record):
        return format_html(f'<a href="{reverse("budgetdb:details_statement", kwargs={"pk": record.id})}">{record.statement_date}</a>')


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
