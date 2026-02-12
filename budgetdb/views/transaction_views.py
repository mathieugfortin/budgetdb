from django import forms

from django.forms.models import modelformset_factory, inlineformset_factory, formset_factory
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError, ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.safestring import mark_safe
from django.views.generic import ListView, CreateView, UpdateView, View, DetailView
from budgetdb.utils import Calendar, serialize_ofx, analyze_ofx_serialized_data
from budgetdb.views import MyUpdateView, MyCreateView, MyDetailView, MyListView
from budgetdb.tables import JoinedTransactionsListTable, TransactionListTable
from budgetdb.models import Cat1, Transaction, Cat2, BudgetedEvent, Vendor, Account, AccountCategory, Preference
from budgetdb.models import JoinedTransactions, AccountBalanceDB
from budgetdb.forms import TransactionFormFull, TransactionFormShort, JoinedTransactionsForm, TransactionFormSet, JoinedTransactionConfigForm
from budgetdb.forms import TransactionModalForm, TransactionOFXImportForm
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Button
from crispy_forms.layout import Layout, Div
from ofxparse import OfxParser
from decimal import *
from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalCreateView
from crum import get_current_user
import json

###################################################################################################################
# Transactions


class TransactionDetailView(MyDetailView):
    model = Transaction
    template_name = 'budgetdb/transaction_detail.html'


class TransactionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Transaction
    template_name = 'budgetdb/transaction_form.html'
    form_class = TransactionFormFull
    task = 'Update'
    user = None

    def test_func(self):
        try:
            view_object = self.model.view_all_objects.get(pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist:
            raise PermissionDenied
        return view_object.can_edit()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.user = get_current_user()
        kwargs['task'] = self.task
        kwargs['user'] = self.user
        return kwargs

    def get_context_data(self, **kwargs):
        self.user = get_current_user()
        context = super().get_context_data(**kwargs)
        preference = get_object_or_404(Preference, user=self.user)
        context['currency'] = preference.currency_prefered.id
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        return form


def TransactionDelete(request, pk):
    model = Transaction
    try:
        delete_object = model.view_objects.get(pk=self.kwargs.get('pk'))
    except ObjectDoesNotExist:
        raise PermissionDenied
    if delete_object.can_edit():
        if request.method == 'POST':
            delete_object.soft_delete()
    else:
        raise PermissionDenied
    return redirect('/')


class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    template_name = 'budgetdb/transaction_form.html'
    form_class = TransactionFormFull
    task = 'Create'
    user = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.user = get_current_user()
        kwargs['task'] = self.task
        kwargs['user'] = self.user
        return kwargs

    def get_context_data(self, **kwargs):
        self.user = get_current_user()
        context = super().get_context_data(**kwargs)
        preference = get_object_or_404(Preference, user=self.user)
        context['currency'] = preference.currency_prefered.id
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        return form

    def get_success_url(self):
        return reverse('budgetdb:details_transaction', kwargs={'pk': self.object.id})


class TransactionCreateViewFromDateAccount(LoginRequiredMixin, CreateView):
    model = Transaction
    template_name = 'budgetdb/transaction_modal_form.html'
    form_class = TransactionFormFull
    task = 'Create'
    user = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.user = get_current_user()
        kwargs['task'] = self.task
        kwargs['user'] = self.user
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form_date = self.kwargs.get('date')
        if form_date is None:
            form_date = date.today().strftime("%Y-%m-%d")
        try:
            account = Account.admin_objects.get(pk=self.kwargs.get('account_pk'))
        except ObjectDoesNotExist:
            raise PermissionDenied
        form.initial['date_actual'] = form_date
        form.initial['account_source'] = account
        form.helper.form_method = 'POST'
        return form


def load_payment_transaction(request):
    account_id = request.GET.get('account')
    transactions = Transaction.admin_objects.filter(account_destination=account_id,).order_by('date_actual')
    return render(request, 'budgetdb/get_payment_transaction_dropdown_list.html', {'transactions': transactions})


class TransactionCreateModal(LoginRequiredMixin, UserPassesTestMixin, BSModalCreateView):
    model = Transaction
    template_name = 'budgetdb/transaction_modal_form.html'
    form_class = TransactionModalForm
    task = 'Create'
    user = None
    account = None

    def test_func(self):
        try:
            self.account = Account.admin_objects.get(pk=self.kwargs.get('accountpk'))
        except ObjectDoesNotExist:
            raise PermissionDenied
        return True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.user = get_current_user()
        kwargs['task'] = self.task
        kwargs['user'] = self.user
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        preference = get_object_or_404(Preference, user=self.user)
        context['currency'] = preference.currency_prefered.id
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form_date = self.kwargs.get('date')
        if form_date is None:
            form_date = date.today().strftime("%Y-%m-%d")
        preference = get_object_or_404(Preference, user=self.user)
        form.initial['date_actual'] = form_date
        form.initial['account_source'] = self.account
        form.initial['currency'] = preference.currency_prefered.id
        form.initial['amount_actual_foreign_currency'] = Decimal(0)
        form.initial['audit'] = False
        form.helper.form_method = 'POST'
        return form

    def form_valid(self, form):
        pass
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.GET.get("next", self.request.META.get("HTTP_REFERER", "/")
        )


class TransactionModalUpdate(LoginRequiredMixin, UserPassesTestMixin, BSModalUpdateView):
    model = Transaction
    template_name = 'budgetdb/transaction_modal_form.html'
    form_class = TransactionModalForm
    task = 'Update'
    success_message = 'Success: Transaction was updated.'
    user = None

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs.get('pk'))
        return view_object.can_edit()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.user = get_current_user()
        kwargs['audit'] = False
        kwargs['task'] = self.task
        kwargs['user'] = self.user
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        preference = get_object_or_404(Preference, user=self.user)
        context['currency'] = preference.currency_prefered.id
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        return form

    def form_valid(self, form):
        pass
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.GET.get('next', self.request.META.get('HTTP_REFERER', '/')
        )


def import_ofx_view(request):
    # --- STEP 4: FINAL CONFIRMATION (Save to DB) ---
    if request.method == 'POST' and 'confirm_import' in request.POST:
        import_data = request.session.get('ofx_import_data')
        account_id = request.session.get('ofx_account_id')
        to_import_indices = [int(i) for i in request.POST.getlist('import_idx')]

        if not import_data or not account_id:
            messages.error(request, "Session expired. Please re-upload.")
            return redirect('budgetdb:upload_transactions_OFX')

        account = Account.objects.get(id=account_id)

        transactions_to_create = []
        for idx in to_import_indices:
            data = import_data[idx]
            # budgetdb/views/transaction_views.py
            # Create the instance in memory
            if data["status"] == "match":
                matched = Transaction.admin_objects.get(pk=data["existing_id"])
                matched.fit_id = data['fit_id']
                matched.comment = f'imported description: {data['description'][:180]}'
                matched.save()
            else:
                new_tx = Transaction(
                    account_source=account,
                    amount_actual=Decimal(str(data['amount'])),
                    date_actual=data['date'],
                    description=data['description'][:200], # Ensure it fits char limit
                    currency=account.currency,
                    fit_id=data['fit_id'],
                    vendor_id=data['vendor_id']
                )
                transactions_to_create.append(new_tx)

        if transactions_to_create:
            # bulk_create is fast but skips .save() and .full_clean()
            Transaction.objects.bulk_create(transactions_to_create)
            # Find the earliest date in the imported batch
            earliest_date = min(t.date_actual for t in transactions_to_create)
            latest_date = max(t.date_actual for t in transactions_to_create)
            
            # Mark parent/account balances as dirty from that date forward
            AccountBalanceDB.objects.filter(
                account=account,
                db_date__gte=earliest_date
            ).update(balance_is_dirty=True)
            messages.success(request, f"Successfully imported {len(transactions_to_create)} transactions.")

        # Clean up session
        del request.session['ofx_import_data']
        del request.session['ofx_account_id']
        if transactions_to_create:
            return redirect('budgetdb:list_account_activity_period', pk=account.pk, date1=earliest_date, date2=latest_date)
        else:
            return redirect('budgetdb:list_account_activity', pk=account.pk)

    # --- STEP 3: LIVE SIGN FLIP (Ajax-like update to session) ---
    if request.method == 'POST' and 'flip_now' in request.POST:
        import_data = request.session.get('ofx_import_data')
        account = Account.objects.get(id=request.session.get('ofx_account_id'))
        
        # Flip data in session
        for item in import_data:
            item['amount'] = float(item['amount']) * -1
        
        # Save preference to account permanently
        account.ofx_flip_sign = not account.ofx_flip_sign
        account.save()
        
        request.session['ofx_import_data'] = import_data
        messages.info(request, "Signs flipped and preference saved.")
        return render(request, 'budgetdb/transaction_import_preview.html', {'transactions': import_data, 'account': account})

    # --- STEP 2: ACCOUNT IDENTIFICATION (After Mapping Template) ---
    if request.method == 'POST' and 'identify_account' in request.POST:
        account = Account.objects.get(id=request.POST.get('identify_account'))
        
        if request.POST.get('save_id') == 'on':
            account.ofx_acct_id = request.session.get('pending_ofx_acct_id')
            account.ofx_org = request.session.get('pending_ofx_org')
            account.ofx_fid = request.session.get('pending_ofx_fid')
            account.save()
            
        # Analyze the serialized data now that we have an account context
        serialized_list = request.session.get('ofx_serialized_list')
        data = analyze_ofx_serialized_data(serialized_list, account)
        # Pass a flag to the template to show the "Verify" UI only if needed
        show_verify_signage_ui = (account.ofx_flip_sign is None)

        request.session['ofx_import_data'] = data
        request.session['ofx_account_id'] = account.id
        return render(request, 'budgetdb/transaction_import_preview.html', {'transactions': data, 'account': account, 'show_verify_signage_ui': show_verify_signage_ui})

    # --- STEP 1: INITIAL UPLOAD ---
    if request.method == 'POST' and 'ofx_file' in request.FILES:
        try:
            ofx = OfxParser.parse(request.FILES['ofx_file'])
            ofx_id = ofx.account.number
            org = ofx.institution.organization if hasattr(ofx, 'institution') else ""
            fid = ofx.institution.fid if hasattr(ofx, 'institution') else ""

            account = Account.objects.filter(ofx_acct_id=ofx_id, ofx_org=org, ofx_fid=fid).first()
            serialized_list, _, _ = serialize_ofx(ofx, account)

            if account:
                # Account known: Go straight to preview
                data = analyze_ofx_serialized_data(serialized_list, account)
                request.session['ofx_import_data'] = data
                request.session['ofx_account_id'] = account.id
                return render(request, 'budgetdb/transaction_import_preview.html', {'transactions': data, 'account': account})
            else:
                # Account unknown: Go to mapping
                request.session['pending_ofx_acct_id'] = ofx_id
                request.session['pending_ofx_org'] = org
                request.session['pending_ofx_fid'] = fid
                request.session['ofx_serialized_list'] = serialized_list
                return render(request, 'budgetdb/account_ofx_mapping.html', {
                    'acct_id': ofx_id, 'org': org, 'accounts': Account.admin_objects.all()
                })
        except Exception as e:
            messages.error(request, f"Parse error: {str(e)}")

    # DEFAULT: Show upload form
    return render(request, 'budgetdb/transaction_import_ofx.html', {'form': TransactionOFXImportForm()})


###################################################################################################################
# Audits

class TransactionAuditCreateModalViewFromDateAccount(LoginRequiredMixin, UserPassesTestMixin, BSModalCreateView):
    model = Transaction
    template_name = 'budgetdb/transaction_modal_form.html'
    form_class = TransactionModalForm
    task = 'Create'
    user = None
    account = None

    def test_func(self):
        self.account = get_object_or_404(Account, pk=self.kwargs.get('accountpk'))
        return self.account.can_edit()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.user = get_current_user()
        kwargs['audit'] = True
        kwargs['task'] = self.task
        kwargs['user'] = self.user
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form_date = self.kwargs.get('date')
        form_amount = self.kwargs.get('amount')
        if form_date is None:
            form_date = date.today().strftime("%Y-%m-%d")
            form.initial['description'] = f'Ajustement du marché'
        else:
            form.initial['description'] = f'Confirmation de solde'
            form_amount = form_amount.replace('N','-',1)
            length = len(form_amount)
            clean_amount = form_amount[:length-2] + '.' + form_amount[-2:]
            form.initial['amount_actual'] = clean_amount
        preference = get_object_or_404(Preference, user=self.user)
        form.initial['date_actual'] = form_date
        form.initial['account_source'] = self.account
        form.initial['audit'] = True
        form.initial['verified'] = True
        form.initial['currency'] = preference.currency_prefered
        form.initial['amount_actual_foreign_currency'] = Decimal(0)

        form.helper.form_method = 'POST'
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        preference = get_object_or_404(Preference, user=self.user)
        context['currency'] = preference.currency_prefered.id
        return context

    def get_success_url(self):
        return reverse('budgetdb:list_account_activity', kwargs={'pk': self.account.pk})


###################################################################################################################
# JoinedTransactions


class JoinedTransactionListView(MyListView):
    model = JoinedTransactions
    table_class = JoinedTransactionsListTable

    def get_queryset(self):
        return self.model.view_objects.all().order_by('name')


class JoinedTransactionsConfigDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = JoinedTransactions
    template_name = 'budgetdb/joinedtransactionsconfig_detail.html'
    context_object_name = 'jt'

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs.get('pk'))
        return view_object.can_view()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        joinedtransactions = JoinedTransactions.objects.get(pk=pk)
        transactions = joinedtransactions.transactions.all()
        budgetedevents = joinedtransactions.budgetedevents.all()
        context['transactions'] = transactions
        context['budgetedevents'] = budgetedevents
        return context


class JoinedTransactionsDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = JoinedTransactions
    template_name = 'budgetdb/joinedtransactions_detail.html'

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs.get('pk'))
        return view_object.can_view()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_object(self, queryset=None):
        my_object = super().get_object(queryset=queryset)
        my_object.editable = my_object.can_edit()
        return my_object

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        date = self.kwargs.get('date')
        joinedtransactions = context.get('joinedtransactions')
        transactions = joinedtransactions.transactions.filter(is_deleted=False)
        transactionPlannedDate = datetime.strptime(date, "%Y-%m-%d").date()
        firstbudgetedevent = joinedtransactions.budgetedevents.filter(is_deleted=False).order_by('joined_order').first()
        nextrecurrence = firstbudgetedevent.listNextTransactions(n=1, begin_interval=transactionPlannedDate).first().date_planned.strftime("%Y-%m-%d")
        previousrecurrence = firstbudgetedevent.listPreviousTransaction(n=1, begin_interval=transactionPlannedDate).first().date_planned.strftime("%Y-%m-%d")
        for budgetedevent in joinedtransactions.budgetedevents.filter(is_deleted=False):
            transactions = transactions | Transaction.view_objects.filter(budgetedevent=budgetedevent, date_planned=transactionPlannedDate)
        transactions = transactions.order_by('joined_order')
        transactionActualDate = transactions.first().date_actual.strftime("%Y-%m-%d")
        context['joinedtransactions'] = joinedtransactions
        context['transactions'] = transactions
        context['pdate'] = previousrecurrence
        context['ndate'] = nextrecurrence
        context['transactionPlannedDate'] = date
        context['transactionActualDate'] = transactionActualDate
        return context


class JoinedTransactionsUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = JoinedTransactions
    form_class = JoinedTransactionsForm
    template_name = 'budgetdb/joinedtransactions_form.html'

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs.get('pk'))
        return view_object.can_edit()

    def handle_no_permission(self):
        raise PermissionDenied

    def form_valid(self, form):
        context = self.get_context_data()
        transactions = context.get('formset')

        for transaction in transactions:
            if transaction.is_valid():
                transaction.instance.date_actual = form.cleaned_data.get('common_date')
                transaction.save()

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('budgetdb:details_joinedtransactions', kwargs={'pk': self.kwargs.get('pk'), 'date': self.kwargs.get('datep')})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(self.kwargs)
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel',
                                     css_class='btn-secondary',
                                     onclick="window.location.href = '{}';".format(reverse('budgetdb:details_joinedtransactions',
                                                                                           args=[self.kwargs.get('pk'),
                                                                                                 self.kwargs.get('datep')]))))
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        datep = self.kwargs.get('datep')
        datea = self.kwargs.get('datea')
        joinedtransactions = context.get('joinedtransactions')
        transactions = joinedtransactions.transactions.all()
        transactionPlannedDate = datetime.strptime(datep, "%Y-%m-%d").date()
        # I want to show individual deleted transactions but not when the whole budgetedevent is deleted
        firstbudgetedevent = joinedtransactions.budgetedevents.filter(is_deleted=False).order_by('joined_order').first()
        nextrecurrence = firstbudgetedevent.listNextTransactions(n=1, begin_interval=transactionPlannedDate).first().date_planned.strftime("%Y-%m-%d")
        previousrecurrence = firstbudgetedevent.listPreviousTransaction(n=1, begin_interval=transactionPlannedDate).first().date_planned.strftime("%Y-%m-%d")
        for budgetedevent in joinedtransactions.budgetedevents.filter(is_deleted=False):
            transactions = transactions | Transaction.view_objects.filter(budgetedevent=budgetedevent, date_planned=transactionPlannedDate)
        transactions = transactions.order_by('joined_order')
        transactionActualDate = transactions.first().date_actual.strftime("%Y-%m-%d")
        transactionsHelper = FormHelper()
        if self.request.POST:
            try:
                context['formset'] = TransactionFormSet(self.request.POST, queryset=transactions)
            except ValidationError:
                context['formset'] = None
        else:
            context['formset'] = TransactionFormSet(queryset=transactions)
            context['helper'] = transactionsHelper

        transactionsHelper.layout = Layout(
            Div(
                Div('description', css_class='form-group col-md-4  '),
                Div('users_view', css_class='form-group col-md-4  '),
                css_class='row'
            ),
        )
        context['joinedtransactions'] = joinedtransactions
        context['pdate'] = previousrecurrence
        context['ndate'] = nextrecurrence
        context['transactionPlannedDate'] = datep
        context['transactionActualDate'] = transactionActualDate

        return context


class JoinedTransactionCreateView(LoginRequiredMixin, CreateView):
    ArticleFormSet = formset_factory(JoinedTransactions)


class JoinedTransactionsConfigUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Transaction
    template_name = 'budgetdb/transaction_form.html'
    form_class = JoinedTransactionConfigForm
    task = 'Update'

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs.get('pk'))
        return view_object.can_edit()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', self.task, css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        form.helper.add_input(Submit('delete', 'Delete', css_class='btn-danger'))
        return form


def saveTransaction(request, transaction_id):
    return HttpResponse("You're working on transaction %s." % transaction_id)


class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    context_object_name = 'calendar_list'
    template_name = 'budgetdb/transaction_list_dynamic_filter.html'

    def get_queryset(self):
        preference = Preference.objects.get(user=self.request.user.id)
        begin = preference.slider_start
        end = preference.slider_stop

        beginstr = self.request.GET.get('begin', None)
        endstr = self.request.GET.get('end', None)
        if beginstr is not None:
            begin = datetime.strptime(beginstr, "%Y-%m-%d").date()
            end = begin + relativedelta(months=1)
        if endstr is not None:
            end = datetime.strptime(endstr, "%Y-%m-%d").date()
        if end < begin:
            end = begin + relativedelta(months=1)

        qs = Transaction.view_objects.filter(date_actual__gt=begin, date_actual__lte=end).order_by('date_actual', 'audit')
        return qs


###################################################################################################################
# checks

class TransactionUnverifiedListView(MyListView):
    model = Transaction
    table_class = TransactionListTable
    title = 'Past Unverified Transactions'

    def get_queryset(self):
        return self.model.view_objects.filter(is_deleted=0, verified=0, audit=0, date_actual__lt=date.today()).order_by('date_actual')

def load_manual_transactionsJSON(request):

    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    inamonth = (date.today() + relativedelta(months=+1)).strftime("%Y-%m-%d")
    transactions = Transaction.view_objects.filter(verified=0, receipt=0, ismanual=1, date_actual__lt=inamonth).order_by('date_actual')

    array = []
    for entry in transactions:
        array.append([{"pk": entry.pk}, {"date": entry.date_actual}, {"description": entry.description}, {"amount": entry.amount_actual}])

    return JsonResponse(array, safe=False)

class TransactionManualListView(MyListView):
    model = Transaction
    table_class = TransactionListTable
    title = 'Upcoming Manual Transactions'

    def get_queryset(self):
        inamonth = (date.today() + relativedelta(months=+1)).strftime("%Y-%m-%d")
        return self.model.view_objects.filter(verified=0, receipt=0, ismanual=1, date_actual__lt=inamonth).order_by('date_actual')


class TransactionDeletedListView(MyListView):
    model = Transaction
    table_class = TransactionListTable
    title = 'Deleted Transactions'

    def get_queryset(self):
        inamonth = (date.today() + relativedelta(months=+1)).strftime("%Y-%m-%d")
        return self.model.view_deleted_objects.filter(date_actual__lt=inamonth).order_by('-date_actual')


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
