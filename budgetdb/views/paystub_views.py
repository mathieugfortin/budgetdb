# paystub_views.py
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
from django.db.models import Case, Value, When, Sum, F, DecimalField, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.dateparse import parse_date
from django.views.generic import ListView, CreateView, UpdateView, View, DetailView
from budgetdb.utils import PaystubEngine
from budgetdb.tables import JoinedTransactionsListTable, TransactionListTable
from budgetdb.models import Cat1, Transaction, Cat2, BudgetedEvent, Vendor, Account, AccountCategory, Preference
from budgetdb.models import JoinedTransactions, PaystubMapping, PaystubProfile
from budgetdb.forms import PaystubUploadForm, MappingRowForm, BaseMappingFormSet


from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Button
from crispy_forms.layout import Layout, Div
from ofxparse import OfxParser
from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalCreateView, BSModalDeleteView
import json
from urllib.parse import urlparse, urlunparse

import pdfplumber
import re


def paystub_PDF_import(request, profile_id=None):
    if profile_id:
        profile = PaystubProfile.admin_objects.get(id=profile_id)
    else:        
        if PaystubProfile.admin_objects.all().count()==1:
            profile = PaystubProfile.admin_objects.all().first()
        else:
            # add logic to ask for a profile
            profile = PaystubProfile.admin_objects.all().first()

    # --- PDF UPLOAD ---
    if request.method == "POST" and request.FILES.get('paystub_pdf'):
        uploaded_file = request.FILES['paystub_pdf']
        engine = PaystubEngine(uploaded_file, profile=profile)
        request.session['raw_paystub_text'] = engine.raw_text
        engine.sync_mappings_with_db()
        unmapped = engine.get_unmapped_keys()
        if unmapped:
            return redirect('budgetdb:paystub_edit_mappings', profile_id=profile.id)
        else:
            return redirect('budgetdb:paystub_confirm_import', profile_id=profile.id)

    # --- DEFAULT: PDF FILE SELECTION SCREEN ---
    return render(request, 'budgetdb/paystub_pdf_read.html', {
        'upload_form': PaystubUploadForm(),
        'step': 'upload'
    })


def paystub_edit_mappings(request, profile_id):
    profile = get_object_or_404(PaystubProfile, id=profile_id)
    raw_text = request.session.get('raw_paystub_text')
    engine = PaystubEngine(raw_text, profile=profile)

    # Get the unified data
    active_map = engine.get_active_mappings()
    active_mapping_keys = list(active_map.keys())
    preference = Preference.objects.get(user=request.user.id)
    accounts = Account.admin_objects.all().annotate(
        favorite=Case(
            When(favorites=preference.id, then=Value(True)),
            default=Value(False),
        )
    ).order_by("-favorite", "account_host", "name")

    # Fetch only the mappings present in THIS PDF
    queryset = PaystubMapping.objects.filter(
        profile=profile,
        line_keyword__in=active_mapping_keys
    ).order_by('line_sequence')

    MappingFormSet = modelformset_factory(
        PaystubMapping, 
        form=MappingRowForm, 
        formset=BaseMappingFormSet, 
        extra=0
    )

    if request.method == "POST":
        formset = MappingFormSet(request.POST, queryset=queryset, live_tokens=active_map)
        if formset.is_valid():
            formset.save()
            return redirect('budgetdb:paystub_confirm_import', profile_id=profile.id)
    else:
        # Initial GET request
        formset = MappingFormSet(queryset=queryset, live_tokens=active_map)
    unmapped_keys = engine.get_unmapped_keys()

    return render(request, 'budgetdb/paystub_mapping_editor.html', {
        'formset': formset,
        'profile': profile,
        'unmapped_keys': unmapped_keys,
        'accounts': accounts,
        'step': 'mapping',
        'live_tokens_map': engine.get_token_dict(), # For debug/UI if needed
    })

def paystub_confirm_import(request, profile_id):
    profile = get_object_or_404(PaystubProfile, id=profile_id)
    raw_text = request.session.get('raw_paystub_text')
    
    engine = PaystubEngine(raw_text, profile=profile)
    pay_date = engine.find_pay_date()

    # get_grouped_actions handles the logic of matching mappings to tokens
    sections, is_balanced, total_mapped, net_pay, all_jts = engine.get_grouped_actions(
        pay_date
    )

    return render(request, 'budgetdb/paystub_import_check.html', {
        'sections': sections,
        'is_balanced': is_balanced,
        'step': 'confirm',
        'profile':profile,
        'pay_date':pay_date,
        'all_discovered_jts':all_jts
    })


@transaction.atomic
def commit_paystub(request):
    if request.method == "POST":
        # 1. Pull data from the POST bundle
        pay_date = request.POST.get('pay_date')
        manual_jt_id = request.POST.get('manual_jt_id')
        raw_text = request.session.get('raw_paystub_text')
        profile_id = request.POST.get('profile_id')
        paystub_id = f'{pay_date}-{profile_id}'
        matched_tx_ids = set()
        
        # 2. Get our container (The JoinedTransactions)
        if manual_jt_id:
            # We use the one the Recap page found
            joined_tx = JoinedTransactions.admin_objects.get(id=manual_jt_id)
        else:
            # Nothing was found in the recap, create a fresh one
            joined_tx = JoinedTransactions.objects.create(
                name=f"Paystub - {pay_date}",
                owner=request.user
            )

        # 3. Process the lines using our shared helper
        profile = None
        if profile_id:
            # We use the one the Recap page found
            profile = PaystubProfile.admin_objects.get(id=profile_id)
       
        engine = PaystubEngine(raw_text, profile=profile) # Rebuild engine from session text
        pdf_active_map = engine.get_active_mappings()
        mappings = PaystubMapping.objects.filter(profile=profile).order_by('line_sequence')

        for mapping in mappings:
            # Skip ignored/headers
            if mapping.is_ignored or mapping.is_header:
                continue

            tokens = pdf_active_map.get(mapping.line_keyword)   
           
            if tokens:
                # Call the helper with commit=True
                # It will use 'joined_tx' to link everything up
                engine.process_mapping_line(
                    mapping, pay_date, tokens, 
                    matched_tx_ids=matched_tx_ids,
                    paystub_id=paystub_id,
                    manual_jt_id=joined_tx.id, 
                    commit=True
                )

        messages.success(request, "Paystub finalized successfully.")
        base_url = reverse('budgetdb:transaction_list_view', kwargs={'filter_type':'account', 'pk': profile.pay_account.pk})
        params = urlencode({'start': pay_date, 'end': pay_date})
        return redirect(f"{base_url}?{params}")
        
