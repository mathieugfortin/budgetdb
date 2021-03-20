from django.http import HttpResponse, HttpResponseRedirect
from django_addanother.views import CreatePopupMixin, UpdatePopupMixin
from django.forms import ModelForm
from django.shortcuts import get_object_or_404, render
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic import ListView, CreateView, UpdateView, View, TemplateView
from django.urls import reverse, reverse_lazy
from django.utils.safestring import mark_safe
from dal import autocomplete
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from .models import Cat1, Transaction, Cat2, BudgetedEvent, Vendor, Account
from .forms import BudgetedEventForm
from .utils import Calendar
import pytz
from decimal import *
from chartjs.views.lines import BaseLineChartView


class FirstGraph(TemplateView):
    template_name = 'budgetdb/firstgraph.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        begin = self.request.GET.get('begin', None)
        end = self.request.GET.get('end', None)
        ac = self.request.GET.get('ac', None)
        account_ID_List = [int(e) if e.isdigit() else e for e in ac.split(',')]
        accounts = Account.objects.filter(pk__in=account_ID_List)

        context['accounts'] = accounts
        context['begin'] = begin
        context['end'] = end
        context['ac'] = ac
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
        self.line_labels = []
        self.x_labels = []
        balance = 0

        begin = self.request.GET.get('begin', None)
        end = self.request.GET.get('end', None)
        ac = self.request.GET.get('ac', None)
        account_ID_List = [int(e) if e.isdigit() else e for e in ac.split(',')]

        if begin is None:
            end = date.today()
            begin = end + relativedelta(months=-1)

        accounts = Account.objects.filter(pk__in=account_ID_List)
        self.data = [[] for i in range(accounts.count())]
        account_counter = 0
        for account in accounts:
            balances_array = account.build_balance_array(begin, end)
            self.line_labels.append(account.name)
            for day in balances_array:
                if account_counter == 0:
                    self.x_labels.append(day.db_date)
                if day.audit is not None:
                    balance = day.audit
                else:
                    if day.rel is not None:
                        balance += day.rel
                self.data[account_counter].append(balance)
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


class CategoryDetailView(DetailView):
    model = Cat1
    template_name = 'budgetdb/cat1_detail.html'


class SubCategoryDetailView(DetailView):
    model = Cat2
    template_name = 'budgetdb/cat2_detail.html'


class TransactionDetailView(DetailView):
    model = Transaction
    template_name = 'budgetdb/transact_detail.html'


def saveTransaction(request, transaction_id):
    return HttpResponse("You're working on transaction %s." % transaction_id)


class BudgetedEventDetailView(DetailView):
    model = BudgetedEvent
    # queryset = BudgetedEvent.objects.all()

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        pk = self.kwargs['pk']
        # Add in a QuerySet of all the books
        context['vendor_list'] = Vendor.objects.all()
        context['cat1_list'] = Cat1.objects.all()
        context['cat2_list'] = Cat2.objects.all()
        context['next_transactions'] = BudgetedEvent.objects.get(id=pk).listNextTransactions(n=10)
        return context


class IndexView(ListView):
    template_name = 'budgetdb/index.html'
    context_object_name = 'categories_list'

    def get_queryset(self):
        return Cat1.objects.order_by('name')[:5]


class CategoryListView(ListView):
    template_name = 'budgetdb/cat_list.html'
    context_object_name = 'categories_list'

    def get_queryset(self):
        return Cat1.objects.order_by('name')


class AccountListView(ListView):
    context_object_name = 'account_list'

    def get_queryset(self):
        return Account.objects.order_by('name')




class AccountperiodicView3(ListView):
    model = Account
    template_name = 'budgetdb/AccountperiodicView3.html'

    def get_queryset(self):
        pk = self.kwargs['pk']
        begin = self.request.GET.get('begin', None)
        end = self.request.GET.get('end', None)
        if begin is None:
            end = date.today()
            begin = end + relativedelta(months=-1)
        events = Account.objects.get(id=pk).build_report_with_balance3(begin, end)
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


class budgetedEventsListView(ListView):
    model = BudgetedEvent
    context_object_name = 'budgetedevent_list'

    def get_queryset(self):
        return BudgetedEvent.objects.order_by('description')[:5]


class TransactionListView(ListView):
    model = Transaction
    context_object_name = 'calendar_list'
    template_name = 'budgetdb/calendarview_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month = self.request.GET.get('month', None)
        year = self.request.GET.get('year', None)

        # use today's date for the calendar
        if year is None:
            d = date.today()
        else:
            d = date(int(year), int(month), 1)

        # Instantiate our calendar class with today's year and date
        cal = Calendar(d.year, d.month)

        # Call the formatmonth method, which returns our calendar as a table
        html_cal = cal.formatmonthlist(withyear=True)
        context['calendar'] = mark_safe(html_cal)
        context['prev_month'] = (d + relativedelta(months=-1)).month
        context['prev_year'] = (d + relativedelta(months=-1)).year
        context['next_month'] = (d + relativedelta(months=+1)).month
        context['next_year'] = (d + relativedelta(months=+1)).year
        context['now_month'] = date.today().month
        context['now_year'] = date.today().year
        return context


class TransactionCalendarView(ListView):
    model = Transaction
    template_name = 'budgetdb/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month = self.request.GET.get('month', None)
        year = self.request.GET.get('year', None)

        # use today's date for the calendar
        if year is None:
            d = date.today()
        else:
            d = date(int(year), int(month), 1)

        # Instantiate our calendar class with today's year and date
        cal = Calendar(d.year, d.month)

        # Call the formatmonth method, which returns our calendar as a table
        html_cal = cal.formatmonth(withyear=True)
        context['calendar'] = mark_safe(html_cal)
        context['prev_month'] = (d + relativedelta(months=-1)).month
        context['prev_year'] = (d + relativedelta(months=-1)).year
        context['next_month'] = (d + relativedelta(months=+1)).month
        context['next_year'] = (d + relativedelta(months=+1)).year
        context['now_month'] = date.today().month
        context['now_year'] = date.today().year
        return context


class BudgetedEventView(UpdateView):
    model = BudgetedEvent
    form_class = BudgetedEventForm
    success_url = reverse_lazy('budgetdb:be_list')


class BudgetedEventCreateView(CreateView):
    model = BudgetedEvent
    form_class = BudgetedEventForm
    success_url = reverse_lazy('budgetdb:list_be')


class CreateCat1(CreatePopupMixin, CreateView):
    model = Cat1
    fields = ['name']


class CreateAccount(CreatePopupMixin, CreateView):
    model = Account
    fields = ['name', 'AccountHost', 'account_number']


class CreateCat2(CreatePopupMixin, CreateView):
    model = Cat2
    fields = ['name']


class CreateVendor(CreatePopupMixin, CreateView):
    model = Vendor
    fields = ['name']
