from django.views.generic import ListView, CreateView, UpdateView, View, TemplateView, DetailView
from budgetdb.models import Cat1, Transaction, Cat2, Statement, Vendor, Account
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from decimal import *


class StatementListView(ListView):
    model = Statement
    context_object_name = 'statement_list'

    def get_queryset(self):
        return Statement.objects.filter(deleted=False).order_by('account', 'statement_date')


class StatementDetailView(DetailView):
    model = Statement
    template_name = 'budgetdb/statement_detail.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        pk = self.kwargs['pk']
        # Add in a QuerySet of all the books
        included_transactions = Transaction.objects.filter(deleted=False, statement=pk).order_by('date_actual')
        
        context['included_transactions'] = included_transactions
        return context


class StatementUpdate(UpdateView):
    # template_name = 'budgetdb/statementmod_form.html'
    model = Statement
    fields = (
            'account',
            'statement_date',
            'balance',
            'statement_due_date',
            'comment',
            'payment_transaction',
            'deleted',
        )

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form


class StatementCreate(CreateView):
    # template_name = 'budgetdb/statementmod_form.html'
    model = Statement
    fields = (
            'account',
            'statement_date',
            'balance',
            'minimum_payment',
            'statement_due_date',
            'comment',
            'payment_transaction',
            'deleted',
        )

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        return form
