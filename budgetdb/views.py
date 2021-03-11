from django.http import HttpResponse, HttpResponseRedirect
from django_addanother.views import CreatePopupMixin, UpdatePopupMixin
from django.forms import ModelForm
from django.shortcuts import get_object_or_404, render
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse, reverse_lazy
from django.utils.safestring import mark_safe
from dal import autocomplete
from datetime import datetime
from dateutil.relativedelta import relativedelta
from .models import Cat1, Transaction, Cat2, BudgetedEvent, Vendor, Account, CalendarView
from .forms import BudgetedEventForm
from .utils import Calendar


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
        # Add in a QuerySet of all the books
        context['vendor_list'] = Vendor.objects.all()
        context['cat1_list'] = Cat1.objects.all()
        context['cat2_list'] = Cat2.objects.all()
        return context


class IndexView(ListView):
    template_name = 'budgetdb/index.html'
    context_object_name = 'categories_list'

    def get_queryset(self):
        return Cat1.objects.order_by('name')[:5]


class budgetedEventsListView(ListView):
    model = BudgetedEvent
    context_object_name = 'budgetedevent_list'

    def get_queryset(self):
        return BudgetedEvent.objects.order_by('description')[:5]


class CalendarListView(ListView):
    model = CalendarView
    context_object_name = 'calendar_list'
    template_name = 'budgetdb/calendarview_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month = self.request.GET.get('month', None)
        year = self.request.GET.get('year', None)

        # use today's date for the calendar
        if year is None:
            d = datetime.today()
        else:
            d = datetime(int(year), int(month), 1)

        # Instantiate our calendar class with today's year and date
        cal = Calendar(d.year, d.month)

        # Call the formatmonth method, which returns our calendar as a table
        html_cal = cal.formatmonthlist(withyear=True)
        context['calendar'] = mark_safe(html_cal)
        context['prev_month'] = (d + relativedelta(months=-1)).month
        context['prev_year'] = (d + relativedelta(months=-1)).year
        context['next_month'] = (d + relativedelta(months=+1)).month
        context['next_year'] = (d + relativedelta(months=+1)).year
        context['now_month'] = datetime.today().month
        context['now_year'] = datetime.today().year
        return context


class CalendarTableView(ListView):
    model = CalendarView
    template_name = 'budgetdb/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month = self.request.GET.get('month', None)
        year = self.request.GET.get('year', None)

        # use today's date for the calendar
        if year is None:
            d = datetime.today()
        else:
            d = datetime(int(year), int(month), 1)

        # Instantiate our calendar class with today's year and date
        cal = Calendar(d.year, d.month)

        # Call the formatmonth method, which returns our calendar as a table
        html_cal = cal.formatmonth(withyear=True)
        context['calendar'] = mark_safe(html_cal)
        context['prev_month'] = (d + relativedelta(months=-1)).month
        context['prev_year'] = (d + relativedelta(months=-1)).year
        context['next_month'] = (d + relativedelta(months=+1)).month
        context['next_year'] = (d + relativedelta(months=+1)).year
        context['now_month'] = datetime.today().month
        context['now_year'] = datetime.today().year
        return context


class BudgetedEventView(UpdateView):
    model = BudgetedEvent
    form_class = BudgetedEventForm
    success_url = reverse_lazy('budgetdb:be_list')


class BudgetedEventCreateView(CreateView):
    model = BudgetedEvent
    form_class = BudgetedEventForm
    success_url = reverse_lazy('budgetdb:be_list')


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
