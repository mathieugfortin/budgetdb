from crum import get_current_user
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import *
from django import forms
from django.forms.models import modelformset_factory, inlineformset_factory, formset_factory
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError, ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, QueryDict
from django.db import transaction
from django.db.models import Case, Value, When, Sum, F, DecimalField, Q, Window, OuterRef, Subquery, ExpressionWrapper, DateField
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.dateparse import parse_date
from django.views.generic import ListView, CreateView, UpdateView, View, DetailView
from budgetdb.utils import Calendar, serialize_ofx, analyze_ofx_serialized_data, PaystubEngine
from budgetdb.views import MyUpdateView, MyCreateView, MyDetailView, MyListView
from budgetdb.tables import JoinedTransactionsListTable, TransactionListTable, BaseTransactionListTable
from budgetdb.models import Cat1, Transaction, Cat2, BudgetedEvent, Vendor, Account, AccountCategory, Preference, CatType
from budgetdb.models import JoinedTransactions, AccountBalanceDB, PaystubMapping, PaystubProfile, Statement
from budgetdb.forms import TransactionFormFull, TransactionFormShort, JoinedTransactionsForm, TransactionFormSet, JoinedTransactionConfigForm
from budgetdb.forms import TransactionModalForm, TransactionOFXImportForm
from budgetdb.services import LedgerService

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Button
from crispy_forms.layout import Layout, Div
from ofxparse import OfxParser
from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalCreateView, BSModalDeleteView
import json
from urllib.parse import urlparse, urlunparse


###################################################################################################################
# Transactions

def ajax_load_transaction_payments(request):
    try:
        account_id = int(request.GET.get('account_id', 0))
    except (ValueError, TypeError):
        return JsonResponse([], safe=False)

    s_date_raw = request.GET.get('statement_date')


    if isinstance(s_date_raw, str):
        s_date = parse_date(s_date_raw)
    else:
        s_date = s_date_raw           

    transactions = Transaction.objects.none()
    if s_date_raw == '' or s_date is None:
        transactions = Transaction.admin_objects.filter(
            account_destination=account_id,
        ).order_by('date_actual')
    elif Account.admin_objects.filter(id=account_id).first():
        transactions = Transaction.admin_objects.filter(
            account_destination=account_id,
            date_actual__gt=s_date-timedelta(days=20),
            date_actual__lt=s_date+timedelta(days=90)
        ).order_by('date_actual')
    data = [{'id': t.id, 'text': f'{t.date_actual} -  {t.amount_actual} - {t.description}'} for t in transactions]
    return JsonResponse(data, safe=False)


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


class TransactionUpdatePopupView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Transaction
    template_name = 'budgetdb/transaction_modal_form.html'
    form_class = TransactionFormFull
    task = 'Update'
    user = None

    def test_func(self):
        try:
            view_object = self.model.view_objects.get(pk=self.kwargs.get('pk'))
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

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        return form


class TransactionDeleteView(BSModalDeleteView):
    model = Transaction
    template_name = 'budgetdb/transaction_delete_modal.html'
    success_message = 'Success: Transaction was deleted.'

    def post(self, request, *args, **kwargs):
        # To ensures that it triggers th oft-delete method.
        return self.delete(request, *args, **kwargs)

    def get_success_url(self):
        # Fallback to a default if the referer isn't found
        return self.request.META.get('HTTP_REFERER') or reverse_lazy('budgetdb:index')


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
    s_date = request.GET.get('statement_date')
    transactions = Transaction.admin_objects.filter(
        account_destination=account_id,
        date_actual__gt=s_date-timedelta(days=20),
        date_actual__lt=s_date+timedelta(days=90)
    ).order_by('date_actual')
    data = [{'id': t.id, 'text': f'{t.date_actual} - {t.description}'} for t in transactions]
    return JsonResponse(data, safe=False)


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
        instance = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'needs_refresh': True, 
                'scroll_date': instance.date_actual.strftime('%Y-%m-%d'),
                'transaction_id': instance.pk,
            })
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

        # Check if fields affecting balance were changed
        balance_sensitive_fields = ['amount_actual', 'date_actual', 'account_source', 'account_destination', 'is_deleted']
        is_delete_action = self.request.POST.get('delete') == 'true'
        needs_refresh = any(field in form.changed_data for field in balance_sensitive_fields) or is_delete_action
        is_ajax = self.request.headers.get('x-requested-with') == 'XMLHttpRequest'
        if is_ajax:
            instance = form.save()

            return JsonResponse({
                'success': True,
                'needs_refresh': needs_refresh,
                'transaction_id': instance.pk,
                'scroll_date': instance.date_actual.strftime('%Y-%m-%d'),
                'description': instance.description,
                'is_deleted': is_delete_action,
            })
        return super().form_valid(form)

    def get_success_url(self):
        # This keeps the full URL including existing query params (?sort=date...)
        next_url = self.request.GET.get('next') or self.request.META.get('HTTP_REFERER', '/')
        
        # 1. Deconstruct the URL
        url_parts = list(urlparse(next_url))
        
        # 2. Parse the existing query string (the 4th element in urlparse)  
        # Using QueryDict handles multiple values and encoding automatically
        query_params = QueryDict(url_parts[4], mutable=True)
        
        # 3. Update or Add the updated_id (this replaces any existing one)
        query_params['updated_id'] = self.object.pk
        
        # 4. Reconstruct the URL
        url_parts[4] = query_params.urlencode()
        return urlunparse(url_parts)


def import_ofx_view(request):
    # --- STEP 4: FINAL CONFIRMATION (Save to DB) ---
    if request.method == 'POST' and 'confirm_import' in request.POST:
        import_data = request.session.get('ofx_import_data')
        account_id = request.session.get('ofx_account_id')
        to_import_indices = [int(i) for i in request.POST.getlist('import_idx')]

        if not import_data or not account_id:
            messages.error(request, "Session expired. Please re-upload.")
            return redirect('budgetdb:upload_transactions_OFX')

        account = Account.admin_objects.get(id=account_id)
        earliest_date = datetime(2500,1,1).date()
        latest_date = datetime(1500,1,1).date()
        show_result=False
        transactions_to_create = []
        with transaction.atomic():
            # We collect the 'existing_id' from every item in import_data that is a match
            match_ids = [
                import_data[idx]["existing_id"] 
                for idx in to_import_indices 
                if import_data[idx].get("status") == "match"
            ]
            matches_pool = {t.id: t for t in Transaction.admin_objects.filter(id__in=match_ids)}

            # 2. Setup lists for bulk updating
            updates_standard = []
            updates_transfer = []

            for idx in to_import_indices:
                data = import_data[idx]

                if data["status"] == "match":
                    matched = matches_pool.get(data["existing_id"])
                    if not matched:
                        continue

                    matched.comment = f'imported description: {data['description'][:180]}'
                    tx_date = matched.date_actual
                    #tx date can be a bit off and still match.  get it back to imported data value
                    matched_date = datetime.strptime(data['date'], "%Y-%m-%d").date()
                    #if we change the date, we need the save() handler, can't do bulk update
                    local_save = False
                    if matched.date_actual != matched_date:
                        matched.date_actual = matched_date
                        local_save=True
                    if data.get('fit_handling') == 'transfer':
                        if matched.fit_id:
                            matched.fit_id_transfer = data['fit_id']
                        else:
                            matched.fit_id = data['fit_id']
                        if local_save:
                            matched.save()
                        else:
                            updates_transfer.append(matched)
                    else:
                        matched.fit_id = data['fit_id']
                        if local_save:
                            matched.save()
                        else:
                            updates_standard.append(matched)
                else:
                    tx_date = datetime.strptime(data['date'], "%Y-%m-%d").date() 
                    if data['vendor_id']:
                        description = 'imported'
                    else:
                        description = data['description'][:200] # Ensure it fits char limit
                    
                    tx_kwargs = {
                        'account_source': account,
                        'amount_actual': Decimal(str(data['amount'])),
                        'date_actual': datetime.strptime(data['date'], "%Y-%m-%d").date(),
                        'description': description,
                        'currency': account.currency,
                        'vendor_id': data['vendor_id'],
                        'comment': f"imported description: {data['description'][:180]}"
                    }
                    if data.get('fit_handling') == 'transfer':
                        tx_kwargs['fit_id_transfer'] = data['fit_id']
                    else:
                        tx_kwargs['fit_id'] = data['fit_id']

                    transactions_to_create.append(Transaction(**tx_kwargs))

                if tx_date > latest_date:
                    latest_date = tx_date
                if tx_date < earliest_date:
                    earliest_date = tx_date

            if transactions_to_create:
                new_transactions = Transaction.objects.bulk_create(transactions_to_create)
                LedgerService.sync_transaction_list(new_transactions)
                messages.success(request, f"Successfully imported {len(new_transactions)} transactions.")
                show_result=True

            if updates_standard:
                updated_transactions = Transaction.objects.bulk_update(updates_standard, ['fit_id', 'comment'])
                LedgerService.sync_transaction_list(updates_standard)
                messages.success(request, f"Successfully updated {updated_transactions} transactions.")
                show_result=True

            if updates_transfer:
                updated_transactions = Transaction.objects.bulk_update(updates_transfer, ['fit_id', 'fit_id_transfer', 'comment'])
                LedgerService.sync_transaction_list(updates_transfer)
                messages.success(request, f"Successfully updated {updated_transactions} transfers.")
                show_result=True

        # Clean up session
        del request.session['ofx_import_data']
        del request.session['ofx_account_id']
        if show_result:
            return redirect('budgetdb:list_account_transactions_period', pk=account.pk, date1=earliest_date, date2=latest_date)
        else:
            return redirect('budgetdb:list_account_transactions', pk=account.pk)

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
        show_verify_signage_ui = not account.ofx_flip_sign_set
        messages.info(request, "Signs flipped and preference saved.")
        return render(request, 'budgetdb/transaction_import_preview.html', {'transactions': import_data, 'account': account, 'show_verify_signage_ui': show_verify_signage_ui})

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
        show_verify_signage_ui = not account.ofx_flip_sign_set

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
                show_verify_signage_ui = not account.ofx_flip_sign_set
                return render(request, 'budgetdb/transaction_import_preview.html', {'transactions': data, 'account': account, 'show_verify_signage_ui': show_verify_signage_ui})
            else:
                # Account unknown: Go to mapping
                request.session['pending_ofx_acct_id'] = ofx_id
                request.session['pending_ofx_org'] = org
                request.session['pending_ofx_fid'] = fid
                request.session['ofx_serialized_list'] = serialized_list
                return render(request, 'budgetdb/account/account_ofx_mapping.html', {
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
        return reverse('budgetdb:list_account_transactions', kwargs={'pk': self.account.pk})


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

        qs = Transaction.view_objects.filter(date_actual__gte=begin, date_actual__lte=end, audit=False).order_by('date_actual', 'audit')
        return qs


class BaseTransactionListView(UserPassesTestMixin, MyListView):
    model = Transaction
    table_class = BaseTransactionListTable
    template_name = 'budgetdb/transaction/base_transactions_list.html'
    
    # State variables
    filter_type = 'account'
    filter_model = Account
    filter_q = None

    pk = None
    begin = None
    end = None
    authorized = False
    statement = None
    context_obj = None
    statement_pk = None
    title = ""
    paginate_by = None
    model_map = {
        'account': Account,
        'cat1': Cat1,
        'cat2': Cat2,
        'cattype': CatType,
        'paystub_id': None,
    }

    def get_paginate_by(self, queryset):
        # minimize the risk of splitting a day across pages, which would break the balance calculation.
        if self.filter_type == 'account':
            return 500  
        return self.paginate_by    

    def test_func(self):
        return self.authorized

    def dispatch(self, request, *args, **kwargs):
        self.filter_type = kwargs.get('filter_type', 'account')
        self.filter_model = self.model_map.get(self.filter_type)
        self.pk = kwargs.get('pk')
        
        self.context_obj = None
        if self.filter_model:
            self.context_obj = get_object_or_404(self.filter_model, pk=self.pk, is_deleted=False)
            self.authorized = self.context_obj.can_view()
            
        # 2. Run the logic to set titles, dates, and filter_q
        self.setup_filter_context()
        
        return super().dispatch(request, *args, **kwargs)

    def setup_filter_context(self):
        """Sets up titles, dates, and the base Q object once."""
        preference = Preference.objects.get(user=self.request.user)
        self.begin = preference.slider_start
        self.end = preference.slider_stop
        
        # 1. Handle Dates from URL (Overload)
        date1 = self.kwargs.get('date1')
        date2 = self.kwargs.get('date2')
        if date1 and date2:
            self.begin = datetime.strptime(date1, "%Y-%m-%d").date()
            self.end = datetime.strptime(date2, "%Y-%m-%d").date()

        # 2. Strategy Pattern for Filter Logic
        filter_method = getattr(self, f"_setup_{self.filter_type}", self._setup_default)
        self.filter_q = filter_method(preference)

    def _setup_account(self, preference):
        self.title = self.context_obj.name
        statement_pk = self.kwargs.get('statement_pk')
        
        if statement_pk:
            statement = get_object_or_404(Statement, id=statement_pk)
            self.begin = statement.statement_date - timedelta(days=preference.statement_buffer_before)
            self.end = statement.statement_date + timedelta(days=preference.statement_buffer_after)
            
            # Use the 'last_obj' check
            if last_obj := Transaction.admin_objects.filter(statement=statement).order_by('date_actual').last():
                self.end = max(self.end, last_obj.date_actual)

        child_accounts = Account.view_objects.filter(account_parent_id=self.pk)
        accounts = child_accounts | Account.view_objects.filter(pk=self.pk)
        return Q(account_source__in=accounts) | Q(account_destination__in=accounts)

    def _setup_cat1(self, preference):
        self.title = self.context_obj.name
        return Q(cat1=self.context_obj)

    def _setup_cat2(self, preference):
        self.title = f"{self.context_obj.cat1.name} - {self.context_obj.name}"
        return Q(cat2=self.context_obj)

    def _setup_cattype(self, preference):
        self.title = self.context_obj.name
        return Q(cat1__cattype=self.context_obj) | Q(cat2__cattype=self.context_obj)

    def _setup_paystub_id(self, preference):
        date_part = self.pk.split('-')[:3] # Extracts YYYY-MM-DD
        if len(date_part) == 3:
            target_date = datetime.strptime("-".join(date_part), "%Y-%m-%d").date()
            self.begin = target_date
            self.end = target_date
        paystub = get_object_or_404(PaystubProfile, pk=self.pk.split('-')[-1], is_deleted=False)
        self.authorized = paystub.can_view() if paystub else False
        self.title = f"Paystub: {paystub.name} - {target_date}"

        return Q(paystub_id=self.pk)

    def _setup_default(self, preference):
        self.title = "Transactions"
        return Q()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_queryset(self):

        qs = Transaction.view_objects.filter(
            self.filter_q, 
            date_actual__gte=self.begin, 
            date_actual__lte=self.end
        )
        sort = self.request.GET.get('sort', 'date_actual')
        if sort == 'date_actual':
            qs = qs.order_by('date_actual', '-id')
        elif sort == '-date_actual':
            qs = qs.order_by('-date_actual', 'id')

        if self.filter_type == 'account' and 'date_actual' in sort:
            # clean up balances
            self.context_obj.get_balances(self.begin, self.end)

            # Subquery for yesterday's closing balance
            daily_balance_subquery = AccountBalanceDB.objects.filter(
                account=self.context_obj,
                db_date=OuterRef('target_ledger_date')
            ).values('balance')[:1]

            # add the previous day's date
            qs = qs.annotate(
                target_ledger_date=ExpressionWrapper(
                    F('date_actual') - timedelta(days=1), 
                    output_field=DateField()
                )
            ).annotate(
                day_start_balance=Subquery(daily_balance_subquery),
                # Calculate if money is moving in or out of THIS account
                amount_contribution=Case(
                    When(audit=True, then=Value(0)),
                    When(account_source=self.context_obj, then=-F('amount_actual')),
                    When(account_destination=self.context_obj, then=F('amount_actual')),
                    default=0,
                    output_field=DecimalField()
                )
            ).annotate(
                # Running sum within the specific day
                intra_day_run_sum=Window(
                    expression=Sum('amount_contribution'),
                    partition_by=[F('date_actual')],
                    order_by=[F('date_actual').asc(), F('id').desc()]
                )
            ).annotate(
                # The final balance column for the table
                calculated_balance=ExpressionWrapper(
                    F('day_start_balance') + F('intra_day_run_sum'),
                    output_field=DecimalField()
                )
            )
            #print(qs.query)
        return qs

        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Map the existing template variables so your old templates don't break
        context['title'] = self.title
        context['begin'] = self.begin.strftime("%Y-%m-%d") if hasattr(self.begin, 'strftime') else self.begin
        context['end'] = self.end.strftime("%Y-%m-%d") if hasattr(self.end, 'strftime') else self.end
        context['year'] = self.begin.year if self.begin else None
        context['filter_type'] = self.filter_type
        context['filter_pk'] = self.pk
        
        # If it's an account, keep the old context names for compatibility
        if self.filter_type == 'account' and self.context_obj:
            context['pk'] = self.context_obj.pk
            context['account_name'] = self.context_obj
            context['account_id'] = self.context_obj.id
            context['account_currency_symbol'] = self.context_obj.currency.symbol
            
        context['cat1s_json'] = list(Cat1.admin_objects.values('id', 'name'))
        return context


    def get_table_kwargs(self):
       return {
           'filter_type': self.filter_type,
           'filter_pk': self.pk,
           'begin': self.begin,
           'end': self.end,
           'request': self.request,
           'statement': self.statement_pk,
           'model_map': self.model_map,
       }        

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
