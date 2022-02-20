from django.views.generic import ListView, CreateView, UpdateView, View, TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from budgetdb.models import Cat1, Transaction, Cat2, BudgetedEvent, Vendor, Account, AccountCategory
from budgetdb.models import JoinedTransactions
from budgetdb.forms import TransactionFormFull, TransactionFormShort, JoinedTransactionsForm
from django.forms.models import modelformset_factory, inlineformset_factory, formset_factory
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from decimal import *
from budgetdb.utils import Calendar
from django.utils.safestring import mark_safe
from django.forms import formset_factory
from django import forms


class TransactionCreateView(CreateView):
    account_source = forms.ModelChoiceField(queryset=Account.objects.order_by('name'))
    model = Transaction

    fields = [
            'description',
            'cat1',
            'cat2',
            'ismanual',
            'account_source',
            'account_destination',
            'statement',
            'verified',
            'receipt',
            'audit',
            'vendor',
            'amount_actual',
            'date_actual',
            'date_planned',
            'budgetedevent',
            'comment',
            ]

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        return form


class TransactionCreateViewFromDateAccount(CreateView):
    model = Transaction
    # template_name = 'budgetdb/crispytest.html'
    template_name = 'budgetdb/transaction_popup_form.html'
    form_class = TransactionFormFull

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        date = self.kwargs['date']
        account_id = self.kwargs['account_pk']
        account = Account.objects.get(id=account_id)
        form.initial['date_actual'] = date
        form.initial['account_source'] = account
        return form


class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    # template_name = 'budgetdb/crispytest.html'
    template_name = 'budgetdb/transaction_form.html'
    # template_name = 'budgetdb/transaction_popup_form.html'
    form_class = TransactionFormFull


class TransactionUpdatePopupView(LoginRequiredMixin, UpdateView):
    model = Transaction
    # template_name = 'budgetdb/crispytest.html'
    template_name = 'budgetdb/transaction_popup_form.html'
    form_class = TransactionFormFull
    # form_class = TransactionFormShort

    # def form_valid(self, form):
    #    form.instance.save()
    #    return super().form_valid(form)

    # def form_invalid(self, form):
    #    return super().form_invalid(form)


class JoinedTransactionUpdateViewMaybe(LoginRequiredMixin, UpdateView):
    model = JoinedTransactions
    form_class = JoinedTransactionsForm

    def get_form_kwargs(self):
        kwargs = super(JoinedTransactionUpdateView, self).get_form_kwargs()
        kwargs.update(self.kwargs)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(JoinedTransactionUpdateView, self).get_context_data(**kwargs)
        pk = self.kwargs['pk']
        day = self.kwargs['day']
        month = self.kwargs['month']
        year = self.kwargs['year']
        transactions = JoinedTransactions.objects.get(deleted=False, pk=pk).transactions.filter(deleted=False)
        transactiondate = datetime(year=year, month=month, day=day)
        for budgetedevent in JoinedTransactions.objects.get(deleted=False, pk=pk).budgetedevents.filter(deleted=False):
            transactions = transactions | Transaction.objects.filter(deleted=False, budgetedevent=budgetedevent, date_actual=transactiondate)

        if self.request.POST:
            context['transactions'] = TransactionsFormset(self.request.POST, instance=self.object)
        else:
            context['transactions'] = TransactionsFormset(instance=self.object)
        return context


class JoinedTransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = JoinedTransactions
    form_class = JoinedTransactionsForm

    def get_form_kwargs(self):
        kwargs = super(JoinedTransactionUpdateView, self).get_form_kwargs()
        kwargs.update(self.kwargs)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs['pk']
        day = self.kwargs['day']
        month = self.kwargs['month']
        year = self.kwargs['year']
        transactions = JoinedTransactions.objects.get(deleted=False, pk=pk).transactions.filter(deleted=False)
        transactiondate = datetime(year=year, month=month, day=day)
        for budgetedevent in JoinedTransactions.objects.get(deleted=False, pk=pk).budgetedevents.filter(deleted=False):
            transactions = transactions | Transaction.objects.filter(deleted=False, budgetedevent=budgetedevent, date_actual=transactiondate)
        transactionFormSet = modelformset_factory(
            Transaction,
            form=TransactionFormShort,
            exclude=(),
            fields=[
                'description',
                'cat1',
                'cat2',
                'account_source',
                'account_destination',
                'amount_planned',
                'amount_actual',
                'verified',
                'date_actual',
                'budgetedevent',
                'deleted',
            ]
        )
        formset = transactionFormSet(queryset=transactions)

        context['transactions'] = transactions
        context['formset'] = formset
        return context


class JoinedTransactionCreateView(LoginRequiredMixin, CreateView):
    ArticleFormSet = formset_factory(JoinedTransactions)


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
