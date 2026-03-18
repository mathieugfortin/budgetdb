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
from budgetdb.models import JoinedTransactions, AccountBalanceDB, PaystubMapping, PaystubProfile
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

def process_mapping_line(mapping, profile, pay_date, tokens, engine, commit=False, manual_jt_id=None):
    """ Compares extracted PDF data against the DB to propose an action or save, depending on commit.  """

    final_amount = engine.calculate_mapped_value(mapping, tokens)
    # source is the employer but on deduction we flip it.
    target_source_account = None
    discovered_jt = None
    # 2. Determine the target account
    target_destination_account = mapping.destination_account or profile.pay_account

    if mapping.entry_type == mapping.EntryType.DEDUCTION:
        target_destination_account = None or mapping.destination_account
        target_source_account = profile.pay_account
         
    ## when mapping.is_net_pay=True, special case on transfer
    ## what happens if there is more than one value indexed for the net_pay line???
    if mapping.is_net_pay:
        existing_tx = Transaction.admin_objects.filter(
            date_actual=pay_date,
            account_source=profile.pay_account,
            #account_destination=profile.checking_account,
            cat2=Cat2.objects.get(name='transfer',system_object=True)
        ).first()
        if existing_tx:
            target_destination_account = existing_tx.account_destination or profile.checking_account
            target_source_account = profile.pay_account
    else:    
        
        # 3. Look for a collision in the DB
        # We match on Date, Category (Cat2), and Account
        existing_tx = Transaction.objects.filter(
            #Q(account_source=target_destination_account) | Q(account_destination=target_destination_account),
            account_source=target_source_account,
            date_actual=pay_date,
            cat2=mapping.category
        ).first()

    action = {
        'mapping_id': mapping.id,
        'category': mapping.category.name if mapping.category else "No Category",
        'destination_account': target_destination_account,
        'source_account': target_source_account,
        'val': final_amount,
        'color_class': 'text-danger' if final_amount < 0 else 'text-success',
    }

    if existing_tx:
        # Get all unique JTs linked directly
        direct_jts = list(existing_tx.joined_transactions.values('id', 'name'))
        
        # Get all unique JTs linked via the event
        event_jts = []
        if hasattr(existing_tx, 'budgetedevent') and existing_tx.budgetedevent:
            event_jts = list(existing_tx.budgetedevent.joined_transactions.values('id', 'name'))

        # Combine them and remove duplicates based on ID
        # This creates a list of dicts: [{'id': 1, 'name': 'Paystub Mar'}, ...]
        all_potential_jts = {jt['id']: jt for jt in direct_jts + event_jts}.values()
        
        action.update({
            'potential_jts': list(all_potential_jts)
        })

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
        final_jt = None
        if manual_jt_id:
            final_jt = JoinedTransactions.admin_objects.get(id=manual_jt_id)
        else:
            final_jt = discovered_jt
        unique_note = f"Imported: {mapping.line_keyword}"

        if existing_tx:
            # Update existing
            existing_tx.amount_actual = Decimal(format(final_amount, ".2f"))
            existing_tx.comment = f"Updated via: {mapping.line_keyword}"
            existing_tx.save() # Triggers your overloaded save()
            tx = existing_tx
        else:
            # Create new
            if target_source_account:
                currency=target_source_account.currency
            elif target_destination_account:
                currency=target_destination_account.currency

            tx = Transaction.objects.create(
                date_actual=pay_date,
                amount_actual=Decimal(format(final_amount, ".2f")),
                account_source=target_source_account,
                account_destination=target_destination_account,
                cat1=mapping.category.cat1,
                cat2=mapping.category,
                currency=currency,
                comment=f"Created via: {mapping.line_keyword}",
                description=mapping.line_keyword
            )
        
        # Linking logic.  Don't link if it's already there butyou can link on a different one
        if final_jt:
            if final_jt.transactions.filter(pk=tx.pk).exists():
                return tx
            if tx.budgetedevent and final_jt.budgetedevents.filter(pk=tx.budgetedevent.pk).exists():
                return tx
            final_jt.transactions.add(tx)
        return tx

    return action

@transaction.atomic
def commit_paystub(request):
    if request.method == "POST":
        # 1. Pull data from the POST bundle
        pay_date = request.POST.get('pay_date')
        manual_jt_id = request.POST.get('manual_jt_id')
        raw_text = request.session.get('raw_paystub_text')
        profile_id = request.POST.get('profile_id')
        
        # 2. Get our container (The JoinedTransactions)
        if manual_jt_id:
            # We use the one the Recap page found
            joined_tx = JoinedTransactions.admin_objects.get(id=manual_jt_id)
        else:
            # Nothing was found in the recap, create a fresh one
            joined_tx = JoinedTransactions.objects.create(
                name=f"Paystub - {pay_date}",
                date=pay_date,
                user=request.user
            )

        # 3. Process the lines using our shared helper
        profile = None
        if profile_id:
            # We use the one the Recap page found
            profile = PaystubProfile.admin_objects.get(id=profile_id)
       
        engine = PaystubEngine(raw_text, profile=profile) # Rebuild engine from session text
        mappings = PaystubMapping.objects.filter(profile=profile).order_by('line_sequence')
        
        for mapping in mappings:
            # Skip ignored/headers
            if mapping.is_ignored or mapping.is_header:
                continue

            pdf_data = engine.get_token_dict()   
            tokens = pdf_data.get(mapping.line_keyword) 
           
            if tokens:
                # Call the helper with commit=True
                # It will use 'joined_tx' to link everything up
                process_mapping_line(
                    mapping, engine.profile, pay_date, tokens, engine, 
                    manual_jt_id=joined_tx.id, 
                    commit=True
                )

        messages.success(request, "Paystub finalized successfully.")
        return redirect('budgetdb:home')


def get_grouped_actions(profile, pay_date, engine):
    sections = []
    current_section = {"header": "General", "actions": []}
    all_discovered_jts = {}
    
    # Mathematical counters
    running_total = 0 # Sum of all earnings/deductions
    reported_net_pay = 0 # The value of the specific 'Net Pay' line
    
    # 1. Get all your saved rules
    mappings = PaystubMapping.admin_objects.filter(profile=profile).order_by('line_sequence')
    
    # 2. Get the actual PDF data from the engine
    pdf_data = engine.get_token_dict()

    for mapping in mappings:
        if mapping.is_header:
            if current_section["actions"]:
                sections.append(current_section)
            current_section = {"header": mapping.line_keyword, "actions": []}
            continue

        # 3. Pull the tokens for this line
        tokens = pdf_data.get(mapping.line_keyword)
        if tokens and not mapping.is_ignored:
            action = process_mapping_line(mapping, profile, pay_date, tokens, engine)
            # Add any JTs found in this line to the master list
            for jt in action.get('potential_jts', []):
                all_discovered_jts[jt['id']] = jt['name']

            current_section["actions"].append(action)
            if mapping.is_net_pay:
                reported_net_pay = action['val']
                # We usually want to show the Net Pay in the recap 
                # so the user can see it was parsed correctly
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

    # CRITICAL: Return all 4 values that the view is expecting
    return sections, is_balanced, running_total, reported_net_pay, all_discovered_jts


def setup_paystub_mapping(request, profile_id=None):
    preference = Preference.objects.get(user=request.user.id)
    if profile_id:
        profile = PaystubProfile.admin_objects.get(id=profile_id)
    else:        
        if PaystubProfile.admin_objects.all().count()==1:
            profile = PaystubProfile.admin_objects.all().first()
        else:
            # add logic to ask for a profile
            pass
            profile = PaystubProfile.admin_objects.all().first()

    accounts = Account.admin_objects.all().annotate(
        favorite=Case(
            When(favorites=preference.id, then=Value(True)),
            default=Value(False),
        )
    ).order_by("-favorite", "account_host", "name")

    MappingFormSet = modelformset_factory(
        PaystubMapping, 
        form=MappingRowForm, 
        formset=BaseMappingFormSet, 
        extra=0
    )
    
    # --- STEP 1: INITIAL PDF UPLOAD ---
    if request.method == "POST" and request.FILES.get('paystub_pdf'):
        uploaded_file = request.FILES['paystub_pdf']
        engine = PaystubEngine(uploaded_file, profile=profile)
        
        request.session['raw_paystub_text'] = engine.raw_text
        
        paystub_date = engine.find_pay_date(profile)
        live_tokens_map = engine.get_token_dict()
        
        # Ensure any new keywords from the PDF exist in the DB
        engine.sync_mappings_with_db(profile)

        queryset = PaystubMapping.objects.filter(
            profile=profile,
            line_keyword__in=live_tokens_map.keys()
        ).order_by('line_sequence') # Using your sequence index
        
        formset = MappingFormSet(queryset=queryset, live_tokens=live_tokens_map)

        context = {
            'formset': formset,
            'profile': profile,
            'paystub_date': paystub_date,
            'accounts': accounts,
            'step': 'mapping',
            'live_tokens_map': live_tokens_map,
        }
        return render(request, 'budgetdb/paystub_pdf_read.html', context)

    # --- STEP 2: SAVE MAPPINGS & SHOW RECAP ---
    if request.method == "POST" and 'save_mappings' in request.POST:
        raw_text = request.session.get('raw_paystub_text')

        # Re-initialize engine from session text to get token_dict back
        engine = PaystubEngine(raw_text, profile=profile)
        live_tokens_map = engine.get_token_dict()

        if not raw_text:
            messages.error(request, "Session data has expired. Please upload the PDF again.")
            return redirect('budgetdb:upload_paystub_PDF')

        # We need the same queryset as before to bind the formset correctly
        queryset = PaystubMapping.objects.filter(
            profile=profile,
            line_keyword__in=live_tokens_map.keys()
        ).order_by('id')

        profile.checking_account_id = request.POST.get('checking_account')
        profile.pay_account_id = request.POST.get('pay_account')
        profile.save()

        # Use the same 'live_tokens' map so the forms can validate the choices
        formset = MappingFormSet(request.POST, queryset=queryset, live_tokens=live_tokens_map)

        if formset.is_valid():
            formset.save()
            pay_date = engine.find_pay_date(profile)
            
            # Generate the grouped actions for the recap page
            sections, is_balanced, total_mapped, net_pay, all_discovered_jts= get_grouped_actions(
                profile, pay_date, engine
            )

            return render(request, 'budgetdb/paystub_import_check.html', {
                'sections': sections,
                'pay_date': pay_date,
                'profile': profile,
                'is_balanced': is_balanced,
                'total_mapped': total_mapped,
                'net_pay': net_pay,
                'all_discovered_jts': all_discovered_jts,
            })

        else:
            # Re-render the form with errors if it's not valid
            return render(request, 'budgetdb/paystub_pdf_read.html', {
                'formset': formset,
                'profile': profile,
                'accounts': accounts,
                'step': 'mapping',
                'live_tokens_map': live_tokens_map,
            })

    # --- DEFAULT: UPLOAD SCREEN ---
    return render(request, 'budgetdb/paystub_pdf_read.html', {
        'upload_form': PaystubUploadForm(),
        'step': 'upload'
    })
