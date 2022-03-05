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
    template_name = 'budgetdb/transaction_popup_form.html'
    form_class = TransactionFormFull


class JoinedTransactionsDetailView(LoginRequiredMixin, DetailView):
    model = JoinedTransactions
    template_name = 'budgetdb/joinedtransactions_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs['pk']
        date = self.kwargs['date']
        transactions = JoinedTransactions.objects.get(deleted=False, pk=pk).transactions.filter(deleted=False)
        transactiondate = datetime.strptime(date, "%Y-%m-%d").date()
        for budgetedevent in JoinedTransactions.objects.get(deleted=False, pk=pk).budgetedevents.filter(deleted=False):
            transactions = transactions | Transaction.objects.filter(deleted=False, budgetedevent=budgetedevent, date_actual=transactiondate)

        context['transactions'] = transactions
        return context


class JoinedTransactionsUpdateView(LoginRequiredMixin, UpdateView):
    model = JoinedTransactions
    form_class = JoinedTransactionsForm
    template_name = 'budgetdb/joinedtransactions_form.html'

    def post(self, request, *args, **kwargs):
        return super().post(request, args, kwargs)

    def clean(self):
        return super().clean(self)

    def form_invalid(self, form):
        return super().form_invalid(form)

    def form_valid(self, form):
        context = self.get_context_data()
        transactions = context['formset']
        # pk = kwargs.pop('pk', None)
        # self.object = form.save()
        # transactions.clean()
        if transactions.is_valid():
            for transaction in transactions:
                # the form empties fields that are not included in the form.  There must be a better way...
                tosave = Transaction.objects.get(pk=transaction.fields['id'].initial)
                for field in transaction.changed_data:
                    if field == 'budgetedevent':
                        pass
                    else:
                        setattr(tosave, field, transaction.cleaned_data[field])
                tosave.save()
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
        # I want to show individual deleted transactions but not when the whole budgetedevent is deleted
        transactions = joinedtransaction.transactions.all()
        transactiondate = datetime.strptime(date, "%Y-%m-%d").date()
        firstbudgetedevent = joinedtransaction.budgetedevents.filter(deleted=False).order_by('joined_order').first()
        nextrecurrence = firstbudgetedevent.listNextTransactions(n=1, begin_interval=transactiondate).first()
        previousrecurrence = firstbudgetedevent.listPreviousTransaction(n=1, begin_interval=transactiondate).first()
        for budgetedevent in joinedtransaction.budgetedevents.filter(deleted=False):
            transactions = transactions | Transaction.objects.filter(budgetedevent=budgetedevent, date_actual=transactiondate)
        transactions = transactions.order_by('joined_order')
        transactionFormSet = modelformset_factory(Transaction, form=TransactionFormShort, exclude=(), extra=0)
        # transactionFormSet = inlineformset_factory(JoinedTransactions, Transaction, form=TransactionFormShort, exclude=(), extra=0)
        formset = transactionFormSet(queryset=transactions,)
        formsetPost = transactionFormSet(self.request.POST, queryset=transactions)
        # self.form.helper = FormHelper()
        if self.request.POST:
            context['formset'] = TransactionFormSet(self.request.POST, queryset=transactions, initial=transactions)
            # check if formset is valid here?
        else:
            context['formset'] = TransactionFormSet(queryset=transactions)
        context['joinedtransaction'] = joinedtransaction
        context['helper'] = context.get('form').helper
        context['pdate'] = previousrecurrence.date_actual.strftime("%Y-%m-%d")
        context['ndate'] = nextrecurrence.date_actual.strftime("%Y-%m-%d")
        context['transactiondate'] = transactiondate.strftime("%Y-%m-%d")
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
