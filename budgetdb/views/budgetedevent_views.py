from django.views.generic import ListView, CreateView, UpdateView, View, TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from budgetdb.models import Cat1, Transaction, Cat2, BudgetedEvent, Vendor, Account, AccountCategory
from budgetdb.forms import BudgetedEventForm
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from decimal import *


class budgetedEventsListView(LoginRequiredMixin, ListView):
    model = BudgetedEvent
    context_object_name = 'budgetedevent_list'

    def get_queryset(self):
        return BudgetedEvent.view_objects.order_by('description')


class BudgetedEventDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = BudgetedEvent

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs.get('pk'))
        return view_object.can_view()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        budgetedEvent = BudgetedEvent.objects.get(pk=self.kwargs.get('pk'))
        editable = budgetedEvent.can_edit()

        # context['vendor_list'] = Vendor.view_objects.filter(is_deleted==False)
        # context['cat1_list'] = Cat1.view_objects.filter(is_deleted=False)
        # context['cat2_list'] = Cat2.view_objects.filter(is_deleted=False)
        context['editable'] = editable
        begin_interval = datetime.today().date() + relativedelta(months=-6)
        context['next_transactions'] = budgetedEvent.listNextTransactions(n=60, begin_interval=begin_interval, interval_length_months=60)
        return context


class BudgetedEventUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    template_name = 'budgetdb/budgetedevent_form.html'
    model = BudgetedEvent
    form_class = BudgetedEventForm

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs.get('pk'))
        return view_object.can_edit()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form


class BudgetedEventCreate(LoginRequiredMixin, CreateView):
    # template_name = 'budgetdb/budgetedeventmod_form.html'
    model = BudgetedEvent
    fields = (
            'description',
            'amount_planned',
            'cat1',
            'cat2',
            'ismanual',
            'repeat_start',
            'repeat_stop',
            'vendor',
            'account_source',
            'account_destination',
            'budget_only',
            'isrecurring',
            'repeat_interval_days',
            'repeat_interval_weeks',
            'repeat_interval_months',
            'repeat_interval_years',
        )

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        return form


class BudgetedEventCreateFromTransaction(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    # template_name = 'budgetdb/budgetedeventmod_form.html'
    model = BudgetedEvent
    fields = (
            'description',
            'amount_planned',
            'cat1',
            'cat2',
            'ismanual',
            'repeat_start',
            'repeat_stop',
            'vendor',
            'account_source',
            'account_destination',
            'budget_only',
            'isrecurring',
            'repeat_interval_days',
            'repeat_interval_weeks',
            'repeat_interval_months',
            'repeat_interval_years',
        )

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs.get('pk'))
        return view_object.can_edit()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        transaction_id = self.kwargs.get('transaction_id')
        transaction = Transaction.objects.get(id=transaction_id)
        form.initial['description'] = transaction.description
        form.initial['amount_planned'] = transaction.amount_actual
        form.initial['cat1'] = transaction.cat1
        form.initial['cat2'] = transaction.cat2
        form.initial['ismanual'] = transaction.ismanual
        form.initial['repeat_start'] = transaction.date_actual
        form.initial['vendor'] = transaction.vendor
        form.initial['account_source'] = transaction.account_source
        form.initial['account_destination'] = transaction.account_destination
        form.initial['isrecurring'] = True

        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        return form


class BudgetedEventCreateView(LoginRequiredMixin, CreateView):
    model = BudgetedEvent
    form_class = BudgetedEventForm
    success_url = reverse_lazy('budgetdb:list_be')


def BudgetedEventSubmit(request):
    description = request.POST.get('description')
    amount_planned = Decimal(request.POST.get('amount_planned'))
    cat1_id = int(request.POST.get('cat1'))
    cat2_id = int(request.POST.get('cat2'))
    repeat_start = datetime.strptime(request.POST.get('repeat_start'), "%Y-%m-%d").date()
    if request.POST.get('repeat_stop') == '':
        repeat_stop = None
    else:
        repeat_stop = datetime.strptime(request.POST.get('repeat_stop'), "%Y-%m-%d").date()

    if request.POST.get('vendor') == '':
        vendor_id = None
    else:
        vendor_id = int(request.POST.get('vendor'))

    if request.POST.get('account_source') == '':
        account_source_id = None
    else:
        account_source_id = int(request.POST.get('account_source'))

    if request.POST('account_destination') == '':
        account_destination_id = None
    else:
        account_destination_id = int(request.POST.get('account_destination'))

    if request.POST.get('budget_only') == 'on':
        budget_only = True
    else:
        budget_only = False
    if request.POST.get('isrecurring') == 'on':
        isrecurring = True
    else:
        isrecurring = False
    if request.POST.get('ismanual') == 'on':
        ismanual = True
    else:
        ismanual = False
    repeat_interval_days = int(request.POST.get('repeat_interval_days'))
    repeat_interval_weeks = int(request.POST.get('repeat_interval_weeks'))
    repeat_interval_months = int(request.POST.get('repeat_interval_months'))
    repeat_interval_years = int(request.POST.get('repeat_interval_years'))
    new_budgetedevent = BudgetedEvent.objects.create(description=description,
                                                     amount_planned=amount_planned,
                                                     cat1_id=cat1_id,
                                                     cat2_id=cat2_id,
                                                     ismanual=ismanual,
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
