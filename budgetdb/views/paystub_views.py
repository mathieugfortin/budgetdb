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


# Added matched_tx_ids to the parameters
def process_mapping_line(mapping, profile, pay_date, tokens, engine, matched_tx_ids=None, commit=False, paystub_id=None, manual_jt_id=None):
    """ Compares extracted PDF data against the DB to propose an action or save, depending on commit.  """
    
    # Initialize the set if not provided
    if matched_tx_ids is None:
        matched_tx_ids = set()

    if mapping.is_date_line or mapping.is_header or mapping.is_ignored:
        if commit:
            return None # Commit view can just ignore this
        return {
            'type': 'INFO', 
            'category': 'Metadata', 
            'val': 0, 
            'ignore_in_math': True,
            'label': mapping.line_keyword 
        }

    final_amount = engine.calculate_mapped_value(mapping, tokens)
    target_source_account = None
    discovered_jt = None
    target_destination_account = mapping.destination_account or profile.pay_account

    if mapping.entry_type == mapping.EntryType.DEDUCTION:
        target_destination_account = None or mapping.destination_account
        target_source_account = profile.pay_account
         
    category = mapping.category.name if mapping.category else "No Category"

    if mapping.is_net_pay:
        existing_tx = Transaction.admin_objects.filter(
            date_actual=pay_date,
            account_source=profile.pay_account,
            cat2=Cat2.objects.get(name='transfer',system_object=True)
        ).exclude(id__in=matched_tx_ids).first()
        
        cat2 = Cat2.objects.get(name='transfer',system_object=True)
        category = cat2.name
        if existing_tx:
            target_destination_account = existing_tx.account_destination or profile.checking_account
        else:
            target_destination_account = profile.checking_account
        target_source_account = profile.pay_account
    else:    
        cat2=mapping.category
        existing_tx = Transaction.objects.filter(
            account_source=target_source_account,
            date_actual=pay_date,
            cat2=cat2
        ).exclude(id__in=matched_tx_ids).first()

    action = {
        'mapping_id': mapping.id,
        'category': category,
        'destination_account': target_destination_account,
        'source_account': target_source_account,
        'val': final_amount,
        'color_class': 'text-danger' if final_amount < 0 else 'text-success',
        'paystub_id':paystub_id,
    }

    if existing_tx:
        # Mark this transaction as "claimed" so duplicate lines don't grab it again
        matched_tx_ids.add(existing_tx.id)
        
        direct_jts = list(existing_tx.joined_transactions.values('id', 'name'))
        event_jts = []
        if hasattr(existing_tx, 'budgetedevent') and existing_tx.budgetedevent:
            event_jts = list(existing_tx.budgetedevent.joined_transactions.values('id', 'name'))

        all_potential_jts = {jt['id']: jt for jt in direct_jts + event_jts}.values()
        
        action.update({'potential_jts': list(all_potential_jts)})

        if round(float(existing_tx.amount_actual), 2) != round(float(final_amount), 2):
            action.update({
                'type': 'UPDATE',
                'old_val': existing_tx.amount_actual,
                'tx_id': existing_tx.id
            })
        else:
            action.update({
                'type': 'MATCH',
                'tx_id': existing_tx.id
            })
    else:
        action.update({'type': 'CREATE'})

    if commit:
        final_jt = JoinedTransactions.admin_objects.get(id=manual_jt_id) if manual_jt_id else discovered_jt
        unique_note = f"Imported: {mapping.line_keyword}"

        if existing_tx:
            existing_tx.amount_actual = Decimal(format(final_amount, ".2f"))
            existing_tx.comment = f"Updated via: {mapping.line_keyword}"
            existing_tx.receipt=True
            existing_tx.paystub_id=paystub_id
            existing_tx.save()
            tx = existing_tx
        else:
            currency = target_source_account.currency if target_source_account else target_destination_account.currency
            cat1 = cat2.cat1 if cat2 else None

            tx = Transaction.objects.create(
                date_actual=pay_date,
                amount_actual=Decimal(format(final_amount, ".2f")),
                account_source=target_source_account,
                account_destination=target_destination_account,
                cat1=cat1,
                cat2=cat2,
                receipt=True,
                currency=currency,
                comment=f"Created via: {mapping.line_keyword}",
                description=mapping.line_keyword,
                paystub_id=paystub_id
            )
            # Add new tx to the exclusion set so subsequent duplicates don't falsely match it!
            matched_tx_ids.add(tx.id) 
        
        if final_jt:
            if not final_jt.transactions.filter(pk=tx.pk).exists():
                if not (tx.budgetedevent and final_jt.budgetedevents.filter(pk=tx.budgetedevent.pk).exists()):
                    final_jt.transactions.add(tx)
        return tx

    return action



def get_grouped_actions(profile, pay_date, engine):
    sections = []
    current_section = {"header": "General", "actions": []}
    all_discovered_jts = {}
    
    # Mathematical counters
    running_total = 0 # Sum of all earnings/deductions
    reported_net_pay = 0 # The value of the specific 'Net Pay' line
    
    # 1. Get all your saved rules
    mappings = PaystubMapping.admin_objects.filter(profile=profile).order_by('line_sequence')
    matched_tx_ids = set()
    # 2. Get the actual PDF data from the engine
    pdf_active_map = engine.get_active_mappings() # Assuming you added this to Engine

    for mapping in mappings:
        if mapping.is_header:
            if current_section["actions"]:
                sections.append(current_section)
            current_section = {"header": mapping.line_keyword, "actions": []}
            continue
        # 3. Pull the tokens for this line
        tokens =  pdf_active_map.get(mapping.line_keyword)
        if tokens and not mapping.is_ignored:
            if mapping.is_date_line:
                    continue
            action = process_mapping_line(mapping, profile, pay_date, tokens, engine)
            # Add any JTs found in this line to the master list
            for jt in action.get('potential_jts', []):
                all_discovered_jts[jt['id']] = jt['name']

            current_section["actions"].append(action)
            if mapping.is_net_pay:
                reported_net_pay = action['val']
            else:
                running_total += action['val']

            # --- THE MATH PART ---
            # If this is the 'Net Pay' line, we store it separately to compare
            if getattr(mapping, 'is_net_pay', False): 
                reported_net_pay = action['val']
            else:
                # Add/Subtract this line from our calculated total
                running_total += action['val']

    # Push the final section
    sections.append(current_section)
    
    # 4. Final Verification
    # Is what we calculated == what the PDF says was deposited?
    is_balanced = round(running_total, 2) == round(reported_net_pay, 2)

    return sections, is_balanced, running_total, reported_net_pay, all_discovered_jts


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
        engine.sync_mappings_with_db(profile)
        unmapped = engine.get_unmapped_keys(profile)
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
    unmapped_keys = engine.get_unmapped_keys(profile)

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
    pay_date = engine.find_pay_date(profile)

    # get_grouped_actions handles the logic of matching mappings to tokens
    sections, is_balanced, total_mapped, net_pay, all_jts = get_grouped_actions(
        profile, pay_date, engine
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
                process_mapping_line(
                    mapping, engine.profile, pay_date, tokens, engine, 
                    paystub_id=paystub_id,
                    manual_jt_id=joined_tx.id, 
                    commit=True
                )

        messages.success(request, "Paystub finalized successfully.")
        return redirect('budgetdb:transaction_list_view', filter_type='account', pk=profile.pay_account.pk, date1=pay_date,date2=pay_date)
