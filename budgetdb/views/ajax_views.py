
import json
import threading
import calendar

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, Submit
from crum import get_current_user
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
#from decimal import *
from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models import Case, Value, When, Sum, F, DecimalField, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView
from django.views.generic.base import RedirectView
from django.views.decorators.http import require_POST, require_GET
from budgetdb.decorators import login_required_ajax
from django_tables2 import SingleTableView  
from rest_framework import serializers

# from budgetdb
from budgetdb.forms import *
from budgetdb.models import *
from budgetdb.tables import *
from budgetdb.tokens import account_activation_token
from budgetdb.scheduler import run_extend_ledgers


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ('vendor',
                  'description',
                  'account_source',
                  'account_destination',
                  'amount_planned',
                  'currency',
                  'amount_planned_foreign_currency',
                  'ismanual',
                  'budget_only',
                  'cat1',
                  'cat2',
                  )


@login_required_ajax
@require_POST
def PreferenceSetIntervalJSON(request):
    # NOT SAFE
    slider_start = request.POST.get("begin_interval", None)
    slider_stop = request.POST.get("end_interval", None)
    preference = Preference.objects.get(user=request.user.id)
    if slider_start:
        preference.slider_start = datetime.strptime(slider_start, "%Y-%m-%d")
    if slider_stop:
        preference.slider_stop = datetime.strptime(slider_stop, "%Y-%m-%d")
    preference.save()
    return HttpResponse(status=200)

@login_required_ajax
@require_POST
def TransactionVerifyToggleJSON(request):
    # NOT SAFE
    transaction_ID = request.POST.get("transaction_id", None)
    if transaction_ID:
        transaction = get_object_or_404(Transaction, pk=transaction_ID)
    else:
        return HttpResponse(status=404)
    if transaction.can_edit() is False:
        return HttpResponse(status=401)
    transaction.verified = not transaction.verified
    transaction.save()
    return HttpResponse(status=200)

@login_required_ajax
@require_POST
def TransactionReceiptToggleJSON(request):
    # NOT SAFE
    transaction_ID = request.POST.get("transaction_id", None)
    if transaction_ID:
        transaction = get_object_or_404(Transaction, pk=transaction_ID)
    else:
        return HttpResponse(status=404)
    if transaction.can_edit() is False:
        return HttpResponse(status=401)
    transaction.receipt = not transaction.receipt
    transaction.save()
    return HttpResponse(status=200)

@login_required_ajax
@require_POST
def update_transaction_categoryJSON(request):
    # NOT SAFE
    tx_id = request.POST.get('transaction_id')
    cat_level = request.POST.get('cat_level')
    cat_id = request.POST.get('category_id') or None

    if not all([tx_id, cat_level]):
        return JsonResponse({'error': 'Missing data'}, status=400)

    transaction = get_object_or_404(Transaction.view_objects, pk=tx_id)
    if not transaction.can_edit():
        return JsonResponse({'error': "permission problems"}, status=403)
    
    if cat_level == '1':
        if cat_id is None:
            transaction.cat1 = None
            transaction.cat2 = None # Reset child if parent changes
            transaction.save()
            return JsonResponse({'status': 'success', 'message': 'Category updated'})
        elif Cat1.admin_objects.filter(id=cat_id).exists():
            transaction.cat1_id = cat_id
            transaction.cat2 = None # Reset child if parent changes
            transaction.save()
            return JsonResponse({'status': 'success', 'message': 'Category updated'})
    else:
        if Cat2.admin_objects.filter(id=cat_id).exists():
            transaction.cat2_id = cat_id
            transaction.save()
            return JsonResponse({'status': 'success', 'message': 'Category updated'})
        elif cat_id is None:
            transaction.cat2 = None
            transaction.save()
            return JsonResponse({'status': 'success', 'message': 'Category updated'})
        
    return JsonResponse({'error': 'data error'}, status=500)

@login_required_ajax
@require_GET
def GetCat2AdminListJSON(request):
    # NOT SAFE, sanitize cat1_id input
    cat1_id = request.GET.get('cat1_id')
    # Filter Cat2 models that have cat1 as a parent
    cat2s = Cat2.admin_objects.filter(cat1=cat1_id).values('id', 'name')
    return JsonResponse({'cat2s': list(cat2s)})    

@login_required_ajax
@require_GET
def GetPreferenceJSON(request):
    preference = Preference.objects.get(user=request.user.id)
    
    if preference.timeline_start is None or preference.timeline_stop is None:
        if preference.timeline_start is None:
            preference.timeline_start = Transaction.view_objects.all().order_by("date_actual").first().date_actual
        if preference.timeline_stop is None:
            preference.timeline_stop = Transaction.view_objects.all().order_by("date_actual").last().date_actual
        preference.save()

    if preference.slider_start is None or preference.slider_stop is None:
        if preference.slider_start is None:
            preference.slider_start = Transaction.view_objects.all().order_by("date_actual").first().date_actual
        if preference.slider_stop is None:
            preference.slider_stop = Transaction.view_objects.all().order_by("date_actual").last().date_actual
        preference.save()

    data = {
        'slider_start': preference.slider_start,
        'slider_stop': preference.slider_stop,
        'timeline_start': preference.timeline_start,
        'timeline_stop': preference.timeline_stop,
    }
    return JsonResponse(data, safe=False)

@login_required
@require_POST
def update_theme_preference(request):
    theme = request.POST.get('theme')
    if theme in ['light', 'dark']:
        get_current_user().preference_set.update(theme=theme)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required_ajax
@require_GET
def GetAccountViewListJSON(request):
    queryset = Account.view_objects.all().order_by("name")

    array = []
    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)

@login_required_ajax
@require_GET
def GetAccountTransactionListURLJSON(request):
    preference = Preference.objects.get(user=request.user.id)
    accounts = Account.view_objects.all()
    accounts = accounts.annotate(
        favorite=Case(
            When(favorites=preference.id, then=Value(True)),
            default=Value(False),
        )
    )
    accounts = accounts.order_by("-favorite", "account_host", "name")

    data = []
    for acc in accounts:
        namestring = ""
        if acc.favorite:
            namestring = namestring + "☆ "
        namestring = namestring + acc.account_host.name
        if acc.owner != get_current_user():
            namestring = namestring + " - " + acc.owner.first_name.capitalize()
        namestring = namestring + " - " + acc.name
        data.append({
            'name': acc.name,
            'url': reverse('budgetdb:list_account_transactions', kwargs={'pk': acc.pk})
        })
    return JsonResponse(data, safe=False)

@login_required_ajax
@require_GET
def GetAccountCatTimelineURLsJSON(request):
    categories = AccountCategory.view_objects.all().order_by("name")
    base_url = reverse('budgetdb:timeline_chart')
    
    data = []
    for cat in categories:
        data.append({
            'name': cat.name,
            # Construct the URL with the query parameter ?ac=PK
            'url': f"{base_url}?ac={cat.pk}"
        })
    return JsonResponse(data, safe=False)

@login_required_ajax
@require_GET
def GetAccountHostViewListJSON(request):
    queryset = AccountHost.view_objects.all().order_by("name")

    array = []
    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)

@login_required_ajax
@require_GET
def GetVendorListJSON(request):
    queryset = Vendor.view_objects.all().order_by("name")

    array = []
    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)

@login_required_ajax
@require_GET
def GetCat1ListURLJSON(request):
    cats = Cat1.view_objects.all().order_by("name")
    data = [{
        'name': c.name,
        'url': reverse('budgetdb:transaction_list_view', kwargs={'filter_type': 'cat1', 'pk': c.pk})
    } for c in cats]
    return JsonResponse(data, safe=False)    

@login_required_ajax
@require_GET
def GetCatTypePieURLsJSON(request):
    cats = CatType.view_objects.all().order_by("name")
    data = [{
        'name': c.name,
        'url': reverse('budgetdb:cattype_pie', kwargs={'cat_type_pk': c.pk})
    } for c in cats]
    return JsonResponse(data, safe=False)  

@login_required_ajax
@require_GET
def GetCatTypeBarURLsJSON(request):
    cats = CatType.view_objects.all().order_by("name")
    data = [{
        'name': c.name,
        'url': reverse('budgetdb:cattype_bar', kwargs={'cat_type_pk': c.pk})
    } for c in cats]
    return JsonResponse(data, safe=False) 

@login_required_ajax
@require_GET
def GetCatTypeByCat1sTotalsJSON(request):
    form = CatType_begin_end_ValForm(request.GET, user=request.user)

    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=403) # 403 because it's often a permission issue    
    
    cattype = form.cleaned_data['cattype_obj']
    begin = form.cleaned_data['begin']
    end = form.cleaned_data['end']

    cattype = CatType.view_objects.get(pk=cattype.pk)

    cat1s_sums = cattype.get_cat1_totals(begin,end)

    chart_data = []
    for cat in cat1s_sums:
        chart_data.append({
            'value': float(cat['total'] or 0),
            'name': cat['cat1__name'],
            'cat1_id': cat['cat1_id']  
        })
    return JsonResponse({'data': chart_data, 'cattype_name': cattype.name})

@login_required_ajax
@require_GET
def GetCatTypeByCat2sTotalsJSON(request):
    form = CatType_Cat1_begin_end_ValForm(request.GET, user=request.user)

    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=403) # 403 because it's often a permission issue    
    
    cattype = form.cleaned_data['cattype_obj']
    cat1 = form.cleaned_data.get('cat1_obj') # Might be None
    begin = form.cleaned_data['begin']
    end = form.cleaned_data['end']

    cat2s_sums = cattype.get_cat2_totals(cat1, begin, end)

    chart_data = []
    for cat in cat2s_sums:
        chart_data.append({
            'value': float(cat['total']),
            'name': cat['cat2__name'],
            'cat2_id': cat['cat2_id']  
        })

    return JsonResponse({'data': chart_data, 'title': f'{cattype.name} - {cat1.name}'})

@login_required_ajax
@require_GET
def GetCatTypeByCat1sMonthlyTotalsJSON(request):
    form = CatType_begin_end_ValForm(request.GET, user=request.user)

    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=403) # 403 because it's often a permission issue    
    
    cattype = form.cleaned_data['cattype_obj']
    begin = form.cleaned_data['begin']
    end = form.cleaned_data['end']

    raw_data = cattype.get_cat1_monthly_totals(begin,end)
    months = sorted(list(set(item['month'].strftime('%Y-%m') for item in raw_data)))

    categories = sorted(list(set(item['cat1__name'] for item in raw_data)))

    # Create a series for each category
    series_list = []
    for cat in categories:
        cat_series = {
            "name": cat,
            "type": "bar",
    #        "stack": "total", # This makes it a stacked bar
            "data": []
        }
        # For every month in the range, find the value or 0
        for m in months:
            val = next((float(x['total']) for x in raw_data 
                        if x['month'].strftime('%Y-%m') == m 
                        and x['cat1__name'] == cat), 0)
            cat_series["data"].append(val)
        series_list.append(cat_series)

    total_data = []
    for m in months:
        # Sum up all totals for this month
        m_total = sum(float(x['total']) for x in raw_data if x['month'].strftime('%Y-%m') == m)
        total_data.append(m_total)
    series_list.append({
        "name": "Total Monthly",
        "type": "line",
        "data": total_data,
        "smooth": True,
        "lineStyle": { "width": 4, "type": "dashed" },
        "symbol": "circle",
        "symbolSize": 8,
        "color": "#ffc107" # High contrast color
    })

    return JsonResponse({
        "months": months,
        "series": series_list,
        "title": f"Monthly {cattype.name} Trends"
    })

@login_required_ajax
@require_GET
def load_cat2(request):
    cat1_id = request.GET.get('cat1')
    cat2s = Cat2.admin_objects.filter(cat1=cat1_id).order_by('name')
    return render(request, 'budgetdb/subcategory_dropdown_list_options.html', {'cat2s': cat2s})

@login_required_ajax
@require_GET
def get_template(request):
    vendor_id = request.GET.get('vendor_id')
    template = get_object_or_404(Template, vendor=vendor_id)
    response = TemplateSerializer(instance=template)
    return JsonResponse(response.data, safe=False)

@login_required_ajax
def ledger_status_view(request):
    if request.method == "POST":
        # Check for the trigger in JSON body or POST params
        # (Since it's a modal, we'll likely send a simple POST)
        thread = threading.Thread(target=run_extend_ledgers)
        thread.start()
        return JsonResponse({
            'status': 'Running',
            'message': 'Ledger extension started.'
        })

    # For a GET request (when opening the modal)
    context = {
        'last_run': cache.get('ledger_task_last_run'),
        'status': cache.get('ledger_task_status', 'Idle'),
    }
    return JsonResponse(context)

@login_required_ajax
@require_GET
def load_cat2_unit_price(request):
    cat2_id = request.GET.get('cat2')
    if cat2_id != '' and cat2_id is not None:
        unitprice = Cat2.admin_objects.get(id=cat2_id).unit_price
        return JsonResponse({"unitprice": unitprice}, safe=False)
    else:
        return JsonResponse({"unitprice": False}, safe=False)

@login_required_ajax
@require_GET
def load_account_unit_price(request):
    account_id = request.GET.get('account')
    if account_id != '' and account_id is not None:
        unitprice = Account.admin_objects.get(id=account_id).unit_price
        return JsonResponse({"unitprice": unitprice}, safe=False)
    else:
        return JsonResponse({"unitprice": False}, safe=False)

@login_required_ajax
@require_GET
def load_cat2_stock(request):
    cat2_id = request.GET.get('cat2')
    if cat2_id != '' and cat2_id is not None:
        unitprice = Cat2.admin_objects.get(id=cat2_id).unit_price
        return JsonResponse({"unitprice": unitprice}, safe=False)
    else:
        return JsonResponse({"unitprice": False}, safe=False)
