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
            return format_html(f"Shared with {users.first().username.capitalize()}")
        elif nb_users == 2:
            return format_html(f"Shared with {users.first().username.capitalize()} and {users.last().username.capitalize()}")
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
        fields = ("description", "lastTransactionDate")
        attrs = {"class": "table table-hover table-striped"}
        # per_page = 30

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


class FriendListTable(tables.Table):
    class Meta:
        model = Friend
        fields = ("email",)
        attrs = {"class": "table table-hover table-striped"}
        # per_page = 30


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
