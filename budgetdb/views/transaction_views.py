from django.views.generic import ListView, CreateView, UpdateView, View, TemplateView, DetailView
from budgetdb.models import Cat1, Transaction, Cat2, BudgetedEvent, Vendor, Account, AccountCategory
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from decimal import *
from budgetdb.utils import Calendar
from django.utils.safestring import mark_safe


class TransactionDetailView(DetailView):
    model = Transaction
    template_name = 'budgetdb/transact_detail.html'


def saveTransaction(request, transaction_id):
    return HttpResponse("You're working on transaction %s." % transaction_id)


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
