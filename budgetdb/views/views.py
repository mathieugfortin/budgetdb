
import json
import threading
import calendar

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, Submit
from crum import get_current_user
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
#from decimal import *
from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models import Case, Value, When, Sum, F, DecimalField, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView
from django.views.generic.base import RedirectView
from django.views.decorators.http import require_POST, require_GET
from budgetdb.decorators import login_required_ajax
from django_tables2 import SingleTableView  
from rest_framework import serializers

# from budgetdb
from budgetdb.forms import *
from budgetdb.models import *
from budgetdb.tables import *
from budgetdb.tokens import account_activation_token
from budgetdb.scheduler import run_extend_ledgers


def get_majority_year(start_date, end_date):
    # If same year, return it immediately
    if start_date.year == end_date.year:
        return start_date.year
    
    year_counts = {}

    for year in range(start_date.year, end_date.year + 1):
        # Determine the start of the interval within this year
        year_start = max(start_date, date(year, 1, 1))
        # Determine the end of the interval within this year
        year_end = min(end_date, date(year, 12, 31))
        
        # Calculate days (inclusive)
        days = (year_end - year_start).days + 1
        year_counts[year] = days

    # Return the year with the maximum day count
    return max(year_counts, key=year_counts.get)


class CatTypeTotalPieChart(TemplateView):
    template_name = 'budgetdb/cattype_pie_chart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cat_type_pk = self.kwargs.get('cat_type_pk')
        cattype = CatType.view_objects.get(pk=cat_type_pk)
        cattypes = CatType.view_objects.all()

        begin = self.request.GET.get('begin', None)
        end = self.request.GET.get('end', None)
        preference = Preference.objects.get(user=self.request.user.id)

        if end is None or end == 'None':
            end = preference.slider_stop
        else:
            end = datetime.date.today()

        if begin is None or begin == 'None':
            begin = preference.slider_start
        else:
            begin = datetime.date.today()

        context['begin'] = begin.strftime("%Y-%m-%d")
        context['end'] = end.strftime("%Y-%m-%d")
        context['cattypes'] = cattypes
        context['cattype'] = cattype.id
        context['year'] = get_majority_year(begin, end)
        context['months'] =  [(i, name) for i, name in enumerate(calendar.month_name) if i != 0]
        return context


class CatTypeTotalBarChart(TemplateView):
    template_name = 'budgetdb/cattype_barchart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cat_type_pk = self.kwargs.get('cat_type_pk')
        cattype = CatType.view_objects.get(pk=cat_type_pk)
        cattypes = CatType.view_objects.all()

        begin = self.request.GET.get('begin', None)
        end = self.request.GET.get('end', None)
        preference = Preference.objects.get(user=self.request.user.id)

        if end is None or end == 'None':
            end = preference.slider_stop
        else:
            end = datetime.date.today()

        if begin is None or begin == 'None':
            begin = preference.slider_start
        else:
            begin = datetime.date.today()

        context['begin'] = begin.strftime("%Y-%m-%d")
        context['end'] = end.strftime("%Y-%m-%d")
        context['cattypes'] = cattypes
        context['cattype'] = cattype.id
        context['year'] = get_majority_year(begin, end)
        context['months'] =  [(i, name) for i, name in enumerate(calendar.month_name) if i != 0]
        
        return context


###################################################################################################################
###################################################################################################################
# Generic classes


class ObjectMaxRedirect(RedirectView):
    permanent = False
    model = ''

    def get_redirect_url(*args, **kwargs):
        pk = kwargs.get('pk')
        model_name = args[0].model
        model = apps.get_model('budgetdb', model_name)
        try:
            redirect_object = model.objects.get(pk=pk)
        except ObjectDoesNotExist:
            raise PermissionDenied
        viewname = 'budgetdb:'
        if redirect_object.can_edit():
            viewname = viewname + 'update_' + model_name.lower()
            return reverse_lazy(viewname, kwargs={'pk': pk})
        if redirect_object.can_view():
            viewname = viewname + 'details_' + model_name.lower()
            return reverse_lazy(viewname, kwargs={'pk': pk})
        raise PermissionDenied


class MyUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    template_name = 'budgetdb/generic_form.html'
    task = 'Update'
    contains_currency = False
    contains_cat = False
    contains_account = False

    def test_func(self):
        try:
            view_object = self.model.view_objects.get(pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist:
            raise PermissionDenied
        return view_object.can_edit()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.model._meta.verbose_name
        context["task"] = self.task
        context["contains_currency"] = self.contains_currency
        context["contains_cat"] = self.contains_cat
        context["contains_account"] = self.contains_account
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', self.task, css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        form.helper.add_input(Submit('delete', 'Delete', css_class='btn-danger'))
        return form


class MyCreateView(LoginRequiredMixin, CreateView):
    template_name = 'budgetdb/generic_form.html'
    task = 'Create'
    contains_currency = False
    contains_cat = False
    contains_account = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.model._meta.verbose_name
        context["task"] = self.task
        context["contains_currency"] = self.contains_currency
        if self.contains_currency:
            user = get_current_user()
            preference = Preference.objects.get(user=user.id)
            context["currency"] = preference.currency_prefered.id
        context["contains_cat"] = self.contains_cat
        context["contains_account"] = self.contains_account
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', self.task, css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        return form


class MyDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    task = 'View'
    url = ''
    title = ''

    def test_func(self):
        try:
            view_object = self.model.view_objects.get(pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist:
            raise PermissionDenied
        return view_object.can_view()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_object(self, queryset=None):
        my_object = super().get_object(queryset=queryset)
        my_object.editable = my_object.can_edit()
        return my_object

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.model._meta.verbose_name
        context["task"] = self.task
        context["url"] = self.url
        context["title"] = self.title
        return context        


class MyListView(LoginRequiredMixin, SingleTableView):
    template_name = 'budgetdb/generic_list.html'
    template_css = None
    create = True
    url = ''
    title = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.title != '':
            context["title"] = self.title
        else:
            context["title"] = f'{self.model._meta.verbose_name_plural} List'
        if self.create is True:
            context['add_url'] = reverse(f'budgetdb:create_{self.model._meta.model_name.lower()}')
        else:
            context['add_url'] = None
        context["create"] = self.create
        context["template_css"] = self.template_css
        return context


class MyNotificationLoggedin(LoginRequiredMixin, TemplateView):
    template_name = 'budgetdb/notification.html'
    notification_message = ''
    notification_title = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notification_title'] = self.notification_title
        context['notification_message'] = self.notification_message
        return context


class MyNotificationLoggedout(TemplateView):
    template_name = 'budgetdb/notification.html'
    notification_message = ''
    notification_title = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notification_title'] = self.notification_title
        context['notification_message'] = self.notification_message
        return context


class EChartTimelineView(LoginRequiredMixin, TemplateView):
    # template_name = 'budgetdb/echart_template.html'
    template_name = 'budgetdb/echart_template_json.html'
    echart_title = 'Account Timeline'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        accountcategoryID = self.request.GET.get('ac', None)

        if accountcategoryID is not None:
            accountcategory = get_object_or_404(AccountCategory, pk=accountcategoryID)
            if not accountcategory.can_view():
                raise PermissionDenied
            context['accountcategory'] = accountcategory
        else:
            context['accountcategory'] = None

        accountcategories = AccountCategory.view_objects.all()
        context['accountcategories'] = accountcategories
        context['ac'] = accountcategoryID
        context['echart_title'] = self.echart_title
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'budgetdb/dashboard.html'
    title = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        messages = Messages.objects.filter(message_type='tutorial')

        context['messages'] = messages
        context['title'] = 'Dashboard'
        return context


###################################################################################################################
###################################################################################################################
# Account


class AccountListViewSimple(MyListView):
    model = Account
    table_class = AccountListTable

    def get_queryset(self):
        return self.model.view_objects.all().order_by('account_host__name', 'name')


class AccountDetailView(MyDetailView):
    model = Account


class AccountSummaryView(MyListView):
    model = Account
    template_name = 'budgetdb/account/account_list_summary.html'

    def get_queryset(self):
        accounts = Account.view_objects.all().order_by('account_host__name', 'name')
        accounts = accounts.exclude(date_closed__lt=date.today())
        return accounts

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        decorated = []
        for account in self.object_list:
            account.balance = account.get_balance(date.today()).balance
            if account.owner != get_current_user():
                account.nice_name = f'{account.account_host} - {account.owner} - {account.name}'
            else:
                account.nice_name = f'{account.account_host} - {account.name}'
            decorated.append(account)
        context['decorated'] = decorated
        return context


class AccountYearReportDetailView(MyDetailView):
    model = Account
    template_name = 'budgetdb/account/account_yearreportview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        year = self.kwargs.get('year')
        # context['account_list'] = Account.objects.all().order_by('name')
        context['pk'] = pk
        context['year'] = year
        context['nyear'] = year + 1
        context['pyear'] = year - 1
        context['account_name'] = Account.objects.get(id=pk).name
        context['reports'] = Account.objects.get(pk=pk).build_yearly_report(year)
        return context


class AccountCatYearReportDetailView(MyDetailView):
    model = AccountCategory
    template_name = 'budgetdb/account/account_yearreportview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        year = self.kwargs.get('year')
        # context['account_list'] = Account.objects.all().order_by('name')
        context['pk'] = pk
        context['year'] = year
        context['account_name'] = Account.objects.get(id=pk).name
        context['reports'] = Account.objects.get(pk=pk).build_yearly_report(year)
        return context


class AccountUpdateView(MyUpdateView):
    model = Account
    form_class = AccountForm


class AccountCreateView(MyCreateView):
    model = Account
    form_class = AccountForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = get_current_user()
        preference = get_object_or_404(Preference, user=user)
        form.initial['currency'] = preference.currency_prefered
        return form

###################################################################################################################
# AccountCategories


class AccountCatListView(MyListView):
    model = AccountCategory
    table_class = AccountCategoryListTable

    def get_queryset(self):
        return self.model.view_objects.all().order_by('name')


class AccountCatDetailView(MyDetailView):
    model = AccountCategory

    def get_object(self, queryset=None):
        category = super().get_object(queryset=queryset)
        category.editable = category.can_edit()
        category.my_accounts = category.accounts.filter(is_deleted=False)
        return category


class AccountCatUpdateView(MyUpdateView):
    model = AccountCategory
    form_class = AccountCategoryForm


class AccountCatCreateView(MyCreateView):
    model = AccountCategory
    form_class = AccountCategoryForm


###################################################################################################################
# AccountHost


class AccountHostListView(MyListView):
    model = AccountHost
    table_class = AccountHostListTable

    def get_queryset(self):
        return self.model.view_objects.all().order_by('name')


class AccountHostDetailView(MyDetailView):
    model = AccountHost
    context_object_name = 'accounthost'
    template_name = 'budgetdb/account/accounthost_detail.html'


class AccountHostUpdateView(MyUpdateView):
    model = AccountHost
    form_class = AccountHostForm


class AccountHostCreateView(MyCreateView):
    model = AccountHost
    form_class = AccountHostForm

###################################################################################################################
# Cat1


class Cat1ListView(MyListView):
    model = Cat1
    table_class = Cat1ListTable

    def get_queryset(self):
        return self.model.view_objects.all().order_by('name')


class Cat1DetailView(MyDetailView):
    model = Cat1
    template_name = 'budgetdb/cat1_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cat1 = get_object_or_404(self.model, pk=self.kwargs.get('pk'))
        cat2s = Cat2.view_objects.filter(cat1=cat1)
        context['cat2s'] = cat2s
        return context


class Cat1UpdateView(MyUpdateView):
    model = Cat1
    form_class = Cat1Form


class Cat1CreateView(MyCreateView):
    model = Cat1
    form_class = Cat1Form

###################################################################################################################
# Cat2


class Cat2ListView(MyListView):
    model = Cat2
    table_class = Cat2ListTable
    create = False

    def get_queryset(self):
        return self.model.view_objects.all().order_by('cat1', 'name')


class Cat2DetailView(MyDetailView):
    model = Cat2
    template_name = 'budgetdb/cat2_detail.html'


class Cat2UpdateView(MyUpdateView):
    model = Cat2
    form_class = Cat2Form


class Cat2CreateView(MyCreateView):
    model = Cat2
    form_class = Cat2Form

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(self.kwargs)
        return kwargs

    def form_valid(self, form):
        return super().form_valid(form)


###################################################################################################################
# CatType


class CatTypeListView(MyListView):
    model = CatType
    table_class = CatTypeListTable

    def get_queryset(self):
        return self.model.view_objects.all().order_by('name')


class CatTypeDetailView(MyDetailView):
    model = CatType
    template_name = 'budgetdb/cattype_detail.html'


class CatTypeUpdateView(MyUpdateView):
    model = CatType
    form_class = CatTypeForm


class CatTypeCreateView(MyCreateView):
    model = CatType
    form_class = CatTypeForm


###################################################################################################################
# Invitation


class InvitationListView(MyListView):
    model = Invitation
    title = 'Pending Invites'
    table_class = InvitationListTable

    def get_queryset(self):
        user = get_current_user()
        my_invitations = self.model.objects.filter(owner=user).order_by('email')
        received_invitations = self.model.objects.filter(email=user.email)
        return my_invitations | received_invitations


class InvitationCreateView(MyCreateView):
    model = Invitation
    form_class = InvitationForm

    def form_valid(self, form):
        invite = form.save()
        invite.send_invite_email()
        return redirect('budgetdb:home')


class InvitationAcceptView(UserPassesTestMixin, MyNotificationLoggedin):
    notification_message = 'Sharing enabled'
    notification_title = 'Sharing enabled'
    invitation = None
    user = None
    invitee = None
    inviter = None

    def test_func(self):
        self.user = get_current_user()
        try:
            self.invitation = Invitation.objects.get(pk=self.kwargs.get('pk'))
            self.inviter = self.invitation.owner
        except ObjectDoesNotExist:
            return False
        try:
            self.invitee = User.objects.get(email=self.invitation.email)
        except ObjectDoesNotExist:
            pass

        if self.user == self.inviter:
            return True
        elif self.user == self.invitee:
            return True
        else:
            return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.invitee is not None:
            self.invitee.friends.add(self.inviter)
            self.inviter.friends.add(self.invitee)
            self.invitation.accepted = True
            self.invitation.rejected = False
            self.invitation.save()
        return context


class InvitationRejectView(UserPassesTestMixin, MyNotificationLoggedin):
    notification_message = 'Sharing disabled'
    notification_title = 'Sharing disabled'
    invitation = None
    user = None
    invitee = None
    inviter = None

    def test_func(self):
        self.user = get_current_user()
        try:
            self.invitation = Invitation.objects.get(pk=self.kwargs.get('pk'))
            self.inviter = self.invitation.owner
        except ObjectDoesNotExist:
            return False

        try:
            self.invitee = User.objects.get(email=self.invitation.email)
        except ObjectDoesNotExist:
            pass

        if self.user == self.inviter:
            return True
        elif self.user == self.invitee:
            return True
        else:
            return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        self.invitation.rejected = True
        self.invitation.accepted = False
        self.invitation.save()
        if self.invitee is not None:
            # remove existing rights
            self.invitee.friends.remove(self.inviter)
            self.inviter.friends.remove(self.invitee)
            objects_with_rights = UserPermissions.objects.filter(users_admin__in=[self.inviter,self.invitee])
            for myobject in objects_with_rights:
                myobject.users_admin.remove(self.invitee)
                myobject.users_admin.remove(self.inviter)
            objects_with_rights = UserPermissions.objects.filter(users_view__in=[self.inviter,self.invitee])
            for myobject in objects_with_rights:
                myobject.users_view.remove(self.invitee)
                myobject.users_view.remove(self.inviter)
        return context


###################################################################################################################
# PayStub

class PayStubProfileCreateView(MyCreateView):
    model = PaystubProfile
    form_class = PaystubProfileForm


###################################################################################################################
# Vendor


class VendorListView(MyListView):
    model = Vendor
    table_class = VendorListTable
    paginate_by = 15

    def get_queryset(self):
        return self.model.view_objects.all().order_by('name')


class VendorDetailView(MyDetailView):
    model = Vendor
    template_name = 'budgetdb/vendor_detail.html'


class VendorUpdateView(MyUpdateView):
    model = Vendor
    form_class = VendorForm


class VendorCreateView(MyCreateView):
    model = Vendor
    form_class = VendorForm


###################################################################################################################
# Statement


class StatementListView(MyListView):
    template_css = 'budgetdb/statement_list.css'
    model = Statement
    table_class = StatementListTable
    paginate_by = 15

    def get_queryset(self):
        pk = self.kwargs.get('pk')
        # all statements
        queryset = self.model.objects.filter(is_deleted=False)
        if pk is not None:
            # filter for one account  
            queryset = queryset.filter(account=pk)

        queryset = queryset.annotate(
            calculated_total=Sum(
                Case(
                    When(transactions__account_destination=F('account'), 
                        then=-F('transactions__amount_actual')),
                    When(transactions__account_source=F('account'), 
                        then=F('transactions__amount_actual')),
                    default=0,
                    output_field=DecimalField()
                ),
                # THIS IS THE MISSING PIECE:
                filter=Q(transactions__is_deleted=False)
            )
        )

        queryset = queryset.order_by('-statement_date', 'account') 
        return (queryset)


class StatementDetailView(MyDetailView):
    model = Statement
    template_name = 'budgetdb/statement_detail.html'
    date_min = None
    date_max = None

    def get_object(self, queryset=None):
        statement = super().get_object(queryset=queryset)
        preference = Preference.objects.get(user=self.request.user.id)
        statement.editable = statement.can_edit()
        # statement.included_transactions = Transaction.view_objects.filter(statement=statement).order_by('date_actual')
        self.date_min = statement.statement_date - timedelta(days=preference.statement_buffer_before)
        self.title = f'Statement {statement.statement_date} for {statement.account}'
        statement.included_transactions = statement.transactions.filter(is_deleted=False).order_by('date_actual')
        if statement.included_transactions.count() > 0:
            first_transaction_date = statement.included_transactions.first().date_actual
            if first_transaction_date < self.date_min:
                self.date_min = first_transaction_date
            
        sum_from = statement.included_transactions.filter(account_source=statement.account).aggregate(Sum('amount_actual')).get('amount_actual__sum')
        sum_to = statement.included_transactions.filter(account_destination=statement.account).aggregate(Sum('amount_actual')).get('amount_actual__sum')
        
        # switching sign because the CC balance is positive in the statement even if it's a debt
        transactions_sum = - (sum_to or Decimal('0.00')) + (sum_from or Decimal('0.00'))
        
        statement.transactions_sum = transactions_sum
        statement.error = transactions_sum - statement.balance
        if statement.error < 0:
            statement.errorsign = '-'
            statement.error = -statement.error
        
        self.date_max = statement.statement_date + timedelta(days=preference.statement_buffer_after)
        statement.possible_transactions = Transaction.admin_objects.filter(account_source=statement.account,
                                                                          date_actual__lte=self.date_max,
                                                                          date_actual__gt=self.date_min,
                                                                          audit=False,
                                                                          statement__isnull=True
                                                                          ) #.exclude(statement=statement).order_by('date_actual')

        statement.possible_transactions = statement.possible_transactions | Transaction.admin_objects.filter(account_source=statement.account,
                                                                          date_actual__lte=self.date_max,
                                                                          date_actual__gt=self.date_min,
                                                                          audit=False,
                                                                          verified=False
                                                                          ).exclude(statement=statement)

        statement.possible_transactions= statement.possible_transactions.order_by('date_actual')
        transactions_sumP = statement.possible_transactions.aggregate(Sum('amount_actual')).get('amount_actual__sum')
        statement.transactions_sumP = transactions_sumP
        return statement

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["date1"] = self.date_min
        context["date2"] = self.date_max
        return context  

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        selected_ids = request.POST.getlist("selected")
        if self.object.can_edit():
            Transaction.admin_objects.filter(id__in=selected_ids).update(statement=self.object)
        return redirect(self.object.get_absolute_url())


class StatementUpdateView(MyUpdateView):
    model = Statement
    form_class = StatementForm


class StatementCreateView(MyCreateView):
    model = Statement
    form_class = StatementForm
    template_name = 'budgetdb/statement_form.html'

# views.py
def StatementLockToggle(request, pk):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)

    obj = get_object_or_404(Statement, pk=pk)
    if not obj:
        return HttpResponse(status=404)
    if obj.can_edit():
        obj.verified_lock = not obj.verified_lock
        obj.save()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        return redirect('budgetdb:list_statement')
    return HttpResponse(status=401)


###################################################################################################################
# Template


class TemplateListView(MyListView):
    model = Template
    table_class = TemplateListTable

    def get_queryset(self):
        return self.model.view_objects.all().order_by('vendor')


class TemplateDetailView(MyDetailView):
    model = Template
    template_name = 'budgetdb/template_detail.html'


class TemplateUpdateView(MyUpdateView):
    model = Template
    form_class = TemplateForm
    contains_currency = True
    contains_cat = True
    contains_account = True


class TemplateCreateView(MyCreateView):
    model = Template
    form_class = TemplateForm
    contains_currency = True
    contains_cat = True
    contains_account = True


###################################################################################################################
###################################################################################################################


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = 'budgetdb/index.html'


class AccountTransactionListView(UserPassesTestMixin, MyListView):
    model = Account
    table_class = BaseTransactionListTable
    template_name = 'budgetdb/transaction/base_transactions_list.html'
    begin = None
    end = None
    year = None
    create = False
    account = None
    statement = None
    # SingleTableView.table_pagination = False

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs.get('pk'), is_deleted=False)
        return view_object.can_view()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cat1_data = list(Cat1.admin_objects.values('id', 'name'))

        context['pk'] = self.account.pk
        context['year'] = self.year
        context['account_name'] = self.account
        context['account_id'] = self.account.id
        context['account_currency_id'] = self.account.currency.id
        context['account_currency_symbol'] = self.account.currency.symbol
        context['cat1_json']= cat1_data

        return context

    def get_table_kwargs(self):
       return {
           'account_view': self.account.pk,
           'begin': self.begin,
           'end': self.end,
           'request': self.request,
           'statement': self.statement,
       }

    def get_queryset(self):
        preference = Preference.objects.get(user=self.request.user.id)
        # extract URL data
        pk = self.kwargs.get('pk')
        date1 = self.kwargs.get('date1')
        date2 = self.kwargs.get('date2')
        statement_pk = self.kwargs.get('statement_pk')
        self.account = Account.objects.get(pk=pk)
        self.title = self.account.name
        self.begin = preference.slider_start
        self.end = preference.slider_stop

        # overload preferences for a specific statement
        if statement_pk is not None:
            statement = Statement.view_objects.get(id=statement_pk)
            if statement:
                self.statement = statement.pk
                self.begin = statement.statement_date - timedelta(days=preference.statement_buffer_before)
                self.end = statement.statement_date + timedelta(days=preference.statement_buffer_after)

                #extend for late transactions
                if last_obj := Transaction.admin_objects.filter(statement=statement).order_by('date_actual').last():
                    last_date = last_obj.date_actual
                    self.end = max(self.end,last_date)

        # overload dates preferences with custom dates
        if date1 is not None and date2 is not None:
            self.begin = datetime.strptime(date1, "%Y-%m-%d").date()
            self.end = datetime.strptime(date2, "%Y-%m-%d").date()

        self.year = self.begin.year
        
        childaccounts = Account.view_objects.filter(account_parent_id=pk, is_deleted=False)
        accounts = childaccounts | Account.view_objects.filter(pk=pk)
        events_source = Transaction.view_objects.filter(account_source__in=accounts,date_actual__gte=self.begin,date_actual__lte=self.end)
        events_destination = Transaction.view_objects.filter(account_destination__in=accounts,date_actual__gte=self.begin,date_actual__lte=self.end)
        return events_source | events_destination


###################################################################################################################
# User Management

class UserVerifyEmailView(MyNotificationLoggedin):
    notification_message = 'Verification email sent'
    notification_title = 'Verification email sent'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_current_user()
        user.send_verify_email()
        return context


class UserVerifiedEmailView(MyNotificationLoggedout):
    notification_message = 'Email address verified, welcome'
    notification_title = 'Email verified'


class UserVerifiedEmailBadLinkView(MyNotificationLoggedout):
    notification_message = 'Verification link is invalid'
    notification_title = 'Verification failed'


class UserVerifyLinkView(RedirectView):
    permanent = False
    
    def get_redirect_url(*args, **kwargs):
        uidb64 = kwargs.get('uidb64')
        token = kwargs.get('token')
        user = None

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except(TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        if user is not None and account_activation_token.check_token(user, token):
            user.email_verified = True
            user.save()
            return reverse_lazy('budgetdb:email_verified')  
        else:
            return reverse_lazy('budgetdb:email_verified_bad_link')


class UserSignupView(CreateView):
    model = User
    form_class = UserSignUpForm
    template_name = 'budgetdb/user/user_register.html'

    def form_valid(self, form):
        user = form.save()
        preference = Preference.objects.create(
            user=user,
            slider_start=date.today()-relativedelta(months=6),
            slider_stop=date.today()+relativedelta(months=6),
            timeline_start=date.today()-relativedelta(months=6),
            timeline_stop=date.today()+relativedelta(months=6),
            currency_prefered = Currency.objects.get(name_short='CAD')
            )
        preference.save()
        user.send_verify_email()
        login(self.request, user)
        return redirect('budgetdb:home')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        email = self.kwargs.get('email')
        if email is not None:
            form.initial['email'] = email
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Sign Up!', css_class='btn-primary w-100 mt-3'))
        return form


class UserLoginView(auth_views.LoginView):
    model = User
    template_name = 'budgetdb/user/user_login.html'

    def form_valid(self, form):
        login(self.request, form.get_user())
        return redirect('budgetdb:home')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # julie = User.objects.get(first_name='julie')
        # julie.set_password('etpatatietpatata')
        # julie.save()
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Log in', css_class='btn-primary w-100 mt-3'))
        return form


class UserPasswordUpdateView(LoginRequiredMixin, auth_views.PasswordChangeView):
    model = User
    form_class = PasswordChangeForm
    success_url = reverse_lazy('budgetdb:home')
    template_name = 'budgetdb/user/user_password_update.html'

    def get_form_kwargs(self):
        kwargs = super(auth_views.PasswordChangeView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        if self.request.method == 'POST':
            kwargs['data'] = self.request.POST
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Change Password', css_class='btn-primary'))
        return form

    def form_valid(self, form):
        form.save()
        update_session_auth_hash(self.request, form.user)        
        return super(auth_views.PasswordChangeView, self).form_valid(form) 


class PreferencesUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):

    model = Preference
    form_class = PreferenceForm
    template_name = 'budgetdb/generic_form.html'
    task = 'Update'
    contains_currency = False
    contains_cat = False
    contains_account = False

    def get_object(self):
        try:
            preference = Preference.objects.get(user=self.user)
        except Preference.DoesNotExist:
            transactions = Transaction.view_objects.all().order_by("date_actual")
            start = transactions.first().date_actual
            stop = transactions.last().date_actual
            preference = Preference.objects.create(
                user=user,
                slider_start=start,
                slider_stop=stop,
                begin_data=start,
                end_data=stop
                )
            preference.save()
        return preference

    def get_success_url(self):
        return reverse('budgetdb:home')

    def test_func(self):
        self.user = get_current_user()
        try:
            self.view_object = self.model.objects.get(user=self.user)
        except ObjectDoesNotExist:
            raise PermissionDenied
        return True

    def handle_no_permission(self):
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.model._meta.verbose_name
        context["task"] = self.task
        context["contains_currency"] = self.contains_currency
        context["contains_cat"] = self.contains_cat
        context["contains_account"] = self.contains_account
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', self.task, css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        form.helper.add_input(Submit('delete', 'Delete', css_class='btn-danger'))
        return form
