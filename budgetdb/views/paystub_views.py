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
from django.http import FileResponse, Http404
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
from collections import defaultdict


from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Button
from crispy_forms.layout import Layout, Div
from ofxparse import OfxParser
from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalCreateView, BSModalDeleteView
import json
import base64
import io
from urllib.parse import urlparse, urlunparse, urlencode


import pdfplumber
import re


def stream_paystub_pdf(request):
    # Pull the base64 string from the user's session storage
    b64_string = request.session.get('raw_pdf_b64')
    
    if not b64_string:
        raise Http404("No active paystub preview available for this session.")
    
    # Decode back to raw binary bytes
    pdf_bytes = base64.b64decode(b64_string)
    
    # Stream it in-memory back to the client browser
    response = FileResponse(io.BytesIO(pdf_bytes), content_type='application/pdf')
    
    # Inline tells the browser to display it embedded, rather than forcing a download file popup
    response['Content-Disposition'] = 'inline; filename="paystub_preview.pdf"'
    return response

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

        uploaded_file.seek(0)  
        pdf_bytes = uploaded_file.read()
        b64_string = base64.b64encode(pdf_bytes).decode('utf-8')
        request.session['raw_pdf_b64'] = b64_string
        
        # 2. Reset pointer so your engine can read it if it needs to
        uploaded_file.seek(0)


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

    # Get the list of tuples
    active_map_tuples = engine.get_active_mappings()
    
    # FIX: Extract unique keys for the database query
    active_mapping_keys = list(set(key for key, tokens in active_map_tuples))
    
    # Create a flat dict for the formset preview (UI only needs 1 example per rule)
    active_map_dict = {key: tokens for key, tokens in active_map_tuples}

    preference = Preference.objects.get(user=request.user.id)
    accounts = Account.admin_objects.all().annotate(
        favorite=Case(
            When(favorites=preference.id, then=Value(True)),
            default=Value(False),
        )
    ).order_by("-favorite", "account_host", "name")

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
        formset = MappingFormSet(request.POST, queryset=queryset, live_tokens=active_map_dict)
        if formset.is_valid():
            formset.save()
            return redirect('budgetdb:paystub_confirm_import', profile_id=profile.id)
    else:
        formset = MappingFormSet(queryset=queryset, live_tokens=active_map_dict)
        
    unmapped_keys = engine.get_unmapped_keys()

    return render(request, 'budgetdb/paystub_mapping_editor.html', {
        'formset': formset,
        'profile': profile,
        'unmapped_keys': unmapped_keys,
        'accounts': accounts,
        'step': 'mapping',
        'live_tokens_map': engine.get_token_dict(), 
        'has_pdf_preview': 'raw_pdf_b64' in request.session,
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
        pay_date = request.POST.get('pay_date')
        manual_jt_id = request.POST.get('manual_jt_id')
        raw_text = request.session.get('raw_paystub_text')
        profile_id = request.POST.get('profile_id')
        paystub_id = f'{pay_date}-{profile_id}'
        matched_tx_ids = set()
        
        if manual_jt_id:
            joined_tx = JoinedTransactions.admin_objects.get(id=manual_jt_id)
        else:
            joined_tx = JoinedTransactions.objects.create(
                name=f"Paystub - {pay_date}",
                owner=request.user
            )

        profile = None
        if profile_id:
            profile = PaystubProfile.admin_objects.get(id=profile_id)
        
        engine = PaystubEngine(raw_text, profile=profile)
        
        # Get the ordered list of PDF lines (preserving duplicates)
        pdf_active_lines = engine.get_active_mappings() 
        
        # Get DB rules and map them for instant matching
        mappings = PaystubMapping.objects.filter(profile=profile)
        mapping_dict = defaultdict(list)
        for m in mappings:
            mapping_dict[m.line_keyword].append(m)

        # Loop over every physical line found in the PDF
        for key, tokens in pdf_active_lines:

            # Retrieve the list of rules for this keyword (defaults to empty list)
            rules = mapping_dict.get(key, [])

            # FIX 3: Execute EVERY rule attached to this keyword
            for mapping in rules:
                # Skip if rule says to ignore/header
                if mapping.is_ignored or mapping.is_header or mapping.is_date_line:
                    continue

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
        request.session.pop('raw_pdf_b64', None)
        return redirect(f"{base_url}?{params}")