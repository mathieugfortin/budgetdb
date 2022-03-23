from django.views.generic import ListView, CreateView, UpdateView, View, TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from budgetdb.models import Cat1, Transaction, Cat2, BudgetedEvent, Vendor, Account, AccountCategory
from budgetdb.models import JoinedTransactions
from budgetdb.forms import TransactionFormFull, TransactionFormShort, JoinedTransactionsForm, TransactionFormSet
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
    account_source = forms.ModelChoiceField(queryset=Account.admin_objects.order_by('name'))
    model = Transaction

    fields = [
            'description',
            'users_view',
            'users_admin',
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
        account = Account.admin_objects.get(id=account_id)
        form.initial['date_actual'] = date
        form.initial['account_source'] = account
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        return form


class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    # template_name = 'budgetdb/crispytest.html'
    template_name = 'budgetdb/transaction_form.html'
    # template_name = 'budgetdb/transaction_popup_form.html'
    form_class = TransactionFormFull

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form


class TransactionUpdatePopupView(LoginRequiredMixin, UpdateView):
    model = Transaction
    template_name = 'budgetdb/transaction_popup_form.html'
    form_class = TransactionFormFull

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form


class JoinedTransactionsDetailView(LoginRequiredMixin, DetailView):
    model = JoinedTransactions
    template_name = 'budgetdb/joinedtransactions_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs['pk']
        date = self.kwargs['date']
        joinedtransaction = JoinedTransactions.objects.get(pk=pk)
        transactions = joinedtransaction.transactions.all()
        transactiondate = datetime.strptime(date, "%Y-%m-%d").date()
        firstbudgetedevent = joinedtransaction.budgetedevents.filter(deleted=False).order_by('joined_order').first()
        nextrecurrence = firstbudgetedevent.listNextTransactions(n=1, begin_interval=transactiondate).first().date_actual.strftime("%Y-%m-%d")
        previousrecurrence = firstbudgetedevent.listPreviousTransaction(n=1, begin_interval=transactiondate).first().date_actual.strftime("%Y-%m-%d")
        for budgetedevent in joinedtransaction.budgetedevents.filter(deleted=False):
            transactions = transactions | Transaction.objects.filter(budgetedevent=budgetedevent, date_actual=transactiondate)
        transactions = transactions.order_by('joined_order')
        context['joinedtransaction'] = joinedtransaction
        context['transactions'] = transactions
        context['pdate'] = previousrecurrence
        context['ndate'] = nextrecurrence
        context['transactiondate'] = date
        return context


class JoinedTransactionsUpdateView(LoginRequiredMixin, UpdateView):
    model = JoinedTransactions
    form_class = JoinedTransactionsForm
    template_name = 'budgetdb/joinedtransactions_form.html'

    def form_valid(self, form):
        context = self.get_context_data()
        transactions = context['formset']

        if transactions.is_valid():
            transactions.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('budgetdb:details_joined_transaction', kwargs={'pk': self.kwargs['pk'], 'date': self.kwargs['date']})

    def get_form_kwargs(self):
        kwargs = super(JoinedTransactionsUpdateView, self).get_form_kwargs()
        kwargs.update(self.kwargs)
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs['pk']
        date = self.kwargs['date']
        joinedtransaction = JoinedTransactions.objects.get(pk=pk)
        transactions = joinedtransaction.transactions.all()
        transactiondate = datetime.strptime(date, "%Y-%m-%d").date()
        # I want to show individual deleted transactions but not when the whole budgetedevent is deleted
        firstbudgetedevent = joinedtransaction.budgetedevents.filter(deleted=False).order_by('joined_order').first()
        nextrecurrence = firstbudgetedevent.listNextTransactions(n=1, begin_interval=transactiondate).first().date_actual.strftime("%Y-%m-%d")
        previousrecurrence = firstbudgetedevent.listPreviousTransaction(n=1, begin_interval=transactiondate).first().date_actual.strftime("%Y-%m-%d")
        for budgetedevent in joinedtransaction.budgetedevents.filter(deleted=False):
            transactions = transactions | Transaction.objects.filter(budgetedevent=budgetedevent, date_actual=transactiondate)
        transactions = transactions.order_by('joined_order')
        if self.request.POST:
            context['formset'] = TransactionFormSet(self.request.POST, queryset=transactions)
        else:
            context['formset'] = TransactionFormSet(queryset=transactions)
        context['joinedtransaction'] = joinedtransaction
        context['pdate'] = previousrecurrence
        context['ndate'] = nextrecurrence
        context['transactiondate'] = date
        return context


class JoinedTransactionCreateView(LoginRequiredMixin, CreateView):
    ArticleFormSet = formset_factory(JoinedTransactions)


class TransactionDetailView(LoginRequiredMixin, DetailView):
    model = Transaction
    template_name = 'budgetdb/transact_detail.html'


def saveTransaction(request, transaction_id):
    return HttpResponse("You're working on transaction %s." % transaction_id)


class TransactionListView(LoginRequiredMixin, ListView):
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


class TransactionUnverifiedListView(LoginRequiredMixin, ListView):
    # Patate rebuild this without calendar to gain speed
    model = Transaction
    template_name = 'budgetdb/transaction_list.html'
    context_object_name = 'transaction_list'

    def get_queryset(self):
        today = date.today()
        transactions = Transaction.objects.filter(deleted=0, verified=0, audit=0, date_actual__lt=today).order_by('date_actual')
        return transactions

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Past Unverified Transactions'
        return context


class TransactionManualListView(LoginRequiredMixin, ListView):
    # Patate rebuild this without calendar to gain speed
    model = Transaction
    template_name = 'budgetdb/transaction_list.html'
    context_object_name = 'transaction_list'

    def get_queryset(self):
        inamonth = (date.today() + relativedelta(months=+1)).strftime("%Y-%m-%d")
        transactions = Transaction.objects.filter(deleted=0, verified=0, ismanual=1, date_actual__lt=inamonth).order_by('date_actual')
        return transactions

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Upcoming Manual Transactions'
        return context


class TransactionCalendarView(LoginRequiredMixin, ListView):
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
