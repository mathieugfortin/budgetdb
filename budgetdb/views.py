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
from .models import Cat1, Transaction, Cat2, BudgetedEvent, Vendor, Account, AccountCategory
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
        accountcategoryID = self.request.GET.get('ac', None)
        if accountcategoryID is not None:
            accountcategory = AccountCategory.objects.filter(id=accountcategoryID)
            context['accountcategory'] = accountcategory
        accountcategories = AccountCategory.objects.all()

        context['accountcategories'] = accountcategories
        context['begin'] = begin
        context['end'] = end
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

        if begin is None:
            end = date.today()
            begin = end + relativedelta(months=-1)

        if accountcategoryID is None or accountcategoryID == 'None':
            accounts = Account.objects.all()
        else:
            accounts = Account.objects.filter(account_categories=accountcategoryID)

        self.line_labels = []
        self.x_labels = []
        self.data = [[] for i in range(accounts.count())]
        account_counter = 0
        for account in accounts:
            balance = account.balance_by_EOD3(begin)
            balances_array = account.build_balance_array(begin, end)
            self.line_labels.append(account.name)
            for day in balances_array:
                if account_counter == 0:
                    self.x_labels.append(day.db_date)

                if day.audit is not None:
                    balance = day.audit
                else:
                    if day.delta is not None:
                        balance += day.delta

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
        begin_interval =datetime.today().date() + relativedelta(months=-12)
        context['next_transactions'] = BudgetedEvent.objects.get(id=pk).listNextTransactions(n=10, begin_interval=begin_interval, interval_length_months=18)
        return context


class IndexView(ListView):
    template_name = 'budgetdb/index.html'
    context_object_name = 'categories_list'

    def get_queryset(self):
        return Cat1.objects.order_by('name')


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
        return BudgetedEvent.objects.order_by('description')


class TransactionListView(ListView):
    # Patate rebuild this without calendar to gain speed
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


def BudgetedEventSubmit(request):
    description = request.POST['description']
    amount_planned = Decimal(request.POST['amount_planned'])
    cat1_id = int(request.POST['cat1'])
    cat2_id = int(request.POST['cat2'])
    repeat_start = datetime.strptime(request.POST['repeat_start'], "%Y-%m-%d").date()
    if request.POST['repeat_stop'] == '':
        repeat_stop = None
    else:
        repeat_stop = datetime.strptime(request.POST['repeat_stop'], "%Y-%m-%d").date()

    if request.POST['vendor'] == '':
        vendor_id = None
    else:
        vendor_id = int(request.POST['vendor'])

    if request.POST['account_source'] == '':
        account_source_id = None
    else:
        account_source_id = int(request.POST['account_source'])

    if request.POST['account_destination'] == '':
        account_destination_id = None
    else:
        account_destination_id = int(request.POST['account_destination'])

    if request.POST.get('budget_only') == 'on':
        budget_only = True
    else:
        budget_only = False
    if request.POST.get('isrecurring') == 'on':
        isrecurring = True
    else:
        isrecurring = False
    repeat_interval_days = int(request.POST['repeat_interval_days'])
    repeat_interval_weeks = int(request.POST['repeat_interval_weeks'])
    repeat_interval_months = int(request.POST['repeat_interval_months'])
    repeat_interval_years = int(request.POST['repeat_interval_years'])
    new_budgetedevent = BudgetedEvent.objects.create(description=description,
                                                     amount_planned=amount_planned,
                                                     cat1_id=cat1_id,
                                                     cat2_id=cat2_id,
                                                     repeat_start=repeat_start,
                                                     repeat_stop=repeat_stop,
                                                     vendor_id=vendor_id,
                                                     account_source_id=account_source_id,
                                                     account_destination_id=account_destination_id,
                                                     budget_only=budget_only,
                                                     isrecurring=isrecurring,
                                                     repeat_interval_days=repeat_interval_days,
                                                     repeat_interval_weeks=repeat_interval_weeks,
                                                     repeat_interval_months=repeat_interval_months,
                                                     repeat_interval_years=repeat_interval_years
                                                     )
    new_budgetedevent.save()
    new_budgetedevent.createTransactions()
    return HttpResponseRedirect(reverse('budgetdb:list_be'))


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
