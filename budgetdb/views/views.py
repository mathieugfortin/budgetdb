from django.http import HttpResponse, HttpResponseRedirect
from django_addanother.views import CreatePopupMixin, UpdatePopupMixin
from django.forms import ModelForm
from django.shortcuts import get_object_or_404, render
from django.views.generic import ListView, CreateView, UpdateView, View, TemplateView, DetailView
from django.urls import reverse, reverse_lazy
from django.utils.safestring import mark_safe
from dal import autocomplete
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from budgetdb.models import Cat1, Transaction, Cat2, BudgetedEvent, Vendor, Account, AccountCategory, MyCalendar
from budgetdb.utils import Calendar
import pytz
from decimal import *
from chartjs.views.lines import BaseLineChartView
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field


class FirstGraph(TemplateView):
    template_name = 'budgetdb/firstgraph.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        begin = self.request.GET.get('begin', None)
        end = self.request.GET.get('end', None)
        accountcategoryID = self.request.GET.get('ac', None)

        if accountcategoryID is not None:
            accountcategory = AccountCategory.objects.filter(id=accountcategoryID)
            context['accountcategory'] = accountcategory
        accountcategories = AccountCategory.objects.all()

        context['accountcategories'] = accountcategories

        if end is None or end == 'None':
            end = date.today()
        else:
            end = datetime.strptime(end, "%Y-%m-%d").date()

        if begin is None or begin == 'None':
            begin = end + relativedelta(months=-1)
        else:
            begin = datetime.strptime(begin, "%Y-%m-%d").date()

        context['begin'] = begin.strftime("%Y-%m-%d")
        context['end'] = end.strftime("%Y-%m-%d")
        mydate = date.today()
        context['now'] = mydate.strftime("%Y-%m-%d")
        mydate = date.today() + relativedelta(months=-1)
        context['monthago'] = mydate.strftime("%Y-%m-%d")
        mydate = date.today() + relativedelta(months=-3)
        context['3monthsago'] = mydate.strftime("%Y-%m-%d")
        mydate = date.today() + relativedelta(months=-12)
        context['yearago'] = mydate.strftime("%Y-%m-%d")
        mydate = date.today() + relativedelta(months=-1)
        context['inamonth'] = mydate.strftime("%Y-%m-%d")
        mydate = date.today() + relativedelta(months=-3)
        context['in3months'] = mydate.strftime("%Y-%m-%d")
        mydate = date.today() + relativedelta(months=-12)
        context['inayear'] = mydate.strftime("%Y-%m-%d")

        context['ac'] = accountcategoryID
        return context


class FirstGraphJSON(BaseLineChartView):
    x_labels = []
    data = []
    line_labels = []

    def get_labels(self):
        return self.x_labels

    def get_providers(self):
        return self.line_labels

    def get_data(self):
        return self.data

    def get_context_data(self, **kwargs):
        begin = self.request.GET.get('begin', None)
        end = self.request.GET.get('end', None)
        accountcategoryID = self.request.GET.get('ac', None)

        if accountcategoryID is None or accountcategoryID == 'None':
            accounts = Account.objects.all()
        else:
            accounts = Account.objects.filter(account_categories=accountcategoryID)

        self.line_labels = []  # Account names
        self.x_labels = []  # Dates
        self.data = [[] for i in range(accounts.count())]  # balances data points

        for day in MyCalendar.objects.filter(db_date__gte=begin, db_date__lte=end).order_by('db_date'):
            self.x_labels.append(f'{day}')

        account_counter = 0
        for account in accounts:
            self.line_labels.append(account.name)
            balances = account.build_balance_array(begin, end)
            for day in balances:
                self.data[account_counter].append(day.balance)

            account_counter += 1

        context = super().get_context_data(**kwargs)
        return context


class AutocompleteAccount(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Account.objects.none()

        qs = Account.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class AutocompleteCat1(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Cat1.objects.none()

        qs = Cat1.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class AutocompleteCat2(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Cat2.objects.none()

        qs = Cat2.objects.all()
        category = self.forwarded.get('cat1', None)

        if category:
            qs = qs.filter(cat1=category)

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


def load_cat2(request):
    cat1_id = request.GET.get('cat1')
    cat2s = Cat2.objects.filter(cat1=cat1_id).order_by('name')
    return render(request, 'budgetdb/subcategory_dropdown_list_options.html', {'cat2s': cat2s})


class AutocompleteVendor(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Vendor.objects.none()

        qs = Vendor.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class Cat1DetailView(DetailView):
    model = Cat1
    template_name = 'budgetdb/cat1_detail.html'


class Cat1UpdateView(UpdateView):
    model = Cat1
    fields = ('name',)

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form


class Cat2UpdateView(UpdateView):
    model = Cat2
    fields = ('name',)

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form


class VendorUpdateView(UpdateView):
    model = Vendor
    fields = ('name',)

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form


class AccountUpdateView(UpdateView):
    model = Account
    fields = (
        'name',
        'AccountHost',
        'account_number',
        )

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form


class Cat2DetailView(DetailView):
    model = Cat2
    template_name = 'budgetdb/cat2_detail.html'


class VendorDetailView(DetailView):
    model = Vendor
    template_name = 'budgetdb/vendor_detail.html'


class AccountDetailView(DetailView):
    model = Account
    template_name = 'budgetdb/account_detail.html'


class IndexView(ListView):
    template_name = 'budgetdb/index.html'
    context_object_name = 'categories_list'

    def get_queryset(self):
        return Cat1.objects.order_by('name')


class Cat1ListView(ListView):
    model = Cat1
    context_object_name = 'categories_list'

    def get_queryset(self):
        return Cat1.objects.order_by('name')


class Cat2ListView(ListView):
    model = Cat2
    context_object_name = 'categories_list'

    def get_queryset(self):
        return Cat2.objects.order_by('name')


class AccountListView(ListView):
    model = Account
    context_object_name = 'account_list'

    def get_queryset(self):
        return Account.objects.all().order_by('name')


class VendorListView(ListView):
    model = Vendor
    context_object_name = 'vendor_list'

    def get_queryset(self):
        return Vendor.objects.order_by('name')


class AccountperiodicView(ListView):
    model = Account
    template_name = 'budgetdb/AccountperiodicView.html'

    def get_queryset(self):
        pk = self.kwargs['pk']
        begin = self.request.GET.get('begin', None)
        end = self.request.GET.get('end', None)
        if begin is None:
            end = date.today()
            begin = end + relativedelta(months=-1)
        events = Account.objects.get(id=pk).build_report_with_balance(begin, end)
        return events

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs['pk']
        begin = self.request.GET.get('begin', None)
        end = self.request.GET.get('end', None)
        if end is None:
            end = date.today()
        if begin is None:
            begin = end + relativedelta(months=-1)

        context['account_list'] = Account.objects.all()
        context['begin'] = begin
        context['end'] = end
        context['pk'] = pk
        context['now'] = date.today()
        context['month'] = date.today() + relativedelta(months=-1)
        context['3month'] = date.today() + relativedelta(months=-3)
        context['account_name'] = Account.objects.get(id=pk).name
        return context


class Cat1CreateView(CreateView):
    model = Cat1
    fields = ['name']

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        return form


class AccountCreateView(CreateView):
    model = Account
    fields = ['name', 'AccountHost', 'account_number']

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        return form


class Cat2Create(CreateView):
    model = Cat2
    fields = ['name', 'cat1']

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.layout = Layout(
           Field('cat1', type="hidden"),
           Field('name', type="")
           )
        cat1_id = self.kwargs['cat1_id']
        cat1 = Cat1.objects.get(id=cat1_id)
        form.initial['cat1'] = cat1
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        return form


class VendorCreate(CreatePopupMixin, CreateView):
    model = Vendor
    fields = ['name']

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        return form
