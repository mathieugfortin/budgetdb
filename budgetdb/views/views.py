from datetime import date, datetime
from decimal import *
import json

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, Submit
from crum import get_current_user
from dateutil.relativedelta import relativedelta
# from django import forms
from django.apps import apps
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
# from django.forms import ModelForm
from django.db.models import Case, Value, When
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.views.generic import (CreateView, DetailView,  # , FormView
                                  ListView, TemplateView, UpdateView)
from django.views.generic.base import RedirectView
# from bootstrap_modal_forms.generic import BSModalCreateView

from django_tables2 import SingleTableView  # , SingleTableMixin
from rest_framework import serializers

# from budgetdb.utils import Calendar
from budgetdb.forms import *
from budgetdb.models import *
from budgetdb.tables import *
from budgetdb.tokens import account_activation_token


# colors stolen from django chart js library
COLORS = [
    (202, 201, 197),  # Light gray
    (171, 9, 0),  # Red
    (166, 78, 46),  # Light orange
    (255, 190, 67),  # Yellow
    (163, 191, 63),  # Light green
    (122, 159, 191),  # Light blue
    (140, 5, 84),  # Pink
    (166, 133, 93),  # Light brown
    (75, 64, 191),  # Red blue
    (237, 124, 60),  # orange
]


def next_color(color_list=COLORS):
    step = 0
    while True:
        for color in color_list:
            yield list(map(lambda base: (base + step) % 256, color))
        step += 197


def PreferenceSetIntervalJSON(request):
    slider_start = request.POST.get("begin_interval", None)
    slider_stop = request.POST.get("end_interval", None)
    preference = Preference.objects.get(user=request.user.id)
    if slider_start:
        preference.slider_start = datetime.strptime(slider_start, "%Y-%m-%d")
    if slider_stop:
        preference.slider_stop = datetime.strptime(slider_stop, "%Y-%m-%d")
    preference.save()
    return HttpResponse(status=200)


def TransactionVerifyToggleJSON(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
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


def TransactionReceiptToggleJSON(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
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


def PreferenceGetJSON(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    preference = Preference.objects.get(user=request.user.id)
    
    if (preference.timeline_start is None or preference.timeline_stop is None):
        transactions = Transaction.view_objects.all().order_by("date_actual")
        preference.timeline_start = preference.timeline_start or transactions.first().date_actual
        preference.timeline_stop = preference.timeline_stop or transactions.last().date_actual
        preference.save()

    data = {
        'slider_start': preference.slider_start,
        'slider_stop': preference.slider_stop,
        'timeline_start': preference.timeline_start,
        'timeline_stop': preference.timeline_stop,
        # 'begin_data': transactions.first().date_actual,
        # 'end_data': transactions.last().date_actual,
    }

    return JsonResponse(data, safe=False)


def GetAccountViewListJSON(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    queryset = Account.view_objects.all().order_by("name")

    array = []
    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetAccountDetailedViewListJSON(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)

    preference = Preference.objects.get(user=request.user.id)
    queryset = Account.view_objects.all()
    queryset = queryset.annotate(
        favorite=Case(
            When(favorites=preference.id, then=Value(True)),
            default=Value(False),
        )
    )
    queryset = queryset.order_by("-favorite", "account_host", "name")

    array = []
    for entry in queryset:
        namestring = ""
        if entry.favorite:
            namestring = namestring + "☆ "
        namestring = namestring + entry.account_host.name
        if entry.owner != get_current_user():
            namestring = namestring + " - " + entry.owner.first_name.capitalize()
        namestring = namestring + " - " + entry.name
        array.append([{"pk": entry.pk}, {"name": namestring}])

    return JsonResponse(array, safe=False)


def GetAccountCatViewListJSON(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    queryset = AccountCategory.view_objects.all().order_by("name")

    array = []
    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetAccountHostViewListJSON(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    queryset = AccountHost.view_objects.all().order_by("name")

    array = []
    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetVendorListJSON(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    queryset = Vendor.view_objects.all().order_by("name")

    array = []
    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetCat1ListJSON(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    queryset = Cat1.view_objects.all().order_by("name")

    array = []
    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetCatTypeListJSON(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    queryset = CatType.view_objects.all().order_by("name")

    array = []
    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetCat1TotalPieChartData(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    begin = request.GET.get('begin', None)
    end = request.GET.get('end', None)
    cat_type_pk = request.GET.get('ct', None)
    cattype = CatType.view_objects.get(pk=cat_type_pk)
    colors = next_color()
    color_list = []

    labels = []  # categories
    data = []  # totals
    indexes = []  # cat1_ids

    cat1sums = CatSums()
    cat_totals = cat1sums.build_cat1_totals_array(begin, end)

    for cat in cat_totals:
        if cat.cattype_id == cattype.id:
            labels.append(cat.cat1.name)
            data.append(cat.total)
            indexes.append(cat.cat1_id)
            color = next(colors)
            color_list.append(f"rgba({color[0]}, {color[1]}, {color[2]}, 1)")

    data = {
        'type': 'doughnut',
        'options': {'responsive': True},
        'data': {
            'datasets': [{
                    'data': data,
                    'indexes': indexes,
                    'backgroundColor': color_list,
                    'label': cattype.name
            }],
            'labels': labels
        },
    }

    return JsonResponse(data, safe=False)


def GetCat2TotalPieChartData(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    begin = request.GET.get('begin', None)
    end = request.GET.get('end', None)
    cat_type_pk = request.GET.get('ct', None)
    cattype = CatType.view_objects.get(pk=cat_type_pk)
    cat1_pk = request.GET.get('cat1', None)
    cat1 = Cat1.view_objects.get(pk=cat1_pk)
    colors = next_color()
    color_list = []
    labels = []  # categories
    data = []  # totals

    cat2sums = CatSums()
    cat_totals = cat2sums.build_cat2_totals_array(begin, end)

    for cat in cat_totals:
        if cat.cattype_id == cattype.id and cat.cat1 == cat1:
            labels.append(cat.cat2.name)
            data.append(cat.total)
            color = next(colors)
            color_list.append(f"rgba({color[0]}, {color[1]}, {color[2]}, 1)")

    data = {
        'type': 'doughnut',
        'options': {'responsive': True},
        'data': {
            'datasets': [{
                    'data': data,
                    'backgroundColor': color_list,
                    'label': f'{cattype.name} - {cat1.name}'
            }],
            'labels': labels
        },
    }

    return JsonResponse(data, safe=False)


def GetCat1TotalBarChartData(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    beginstr = request.GET.get('begin', None)
    endstr = request.GET.get('end', None)
    cat_type_pk = request.GET.get('ct', None)
    cattype = CatType.view_objects.get(pk=cat_type_pk)
    cats = Cat1.view_objects.filter(cattype=cattype)

    if endstr is not None and endstr != 'None':
        end = datetime.strptime(endstr, "%Y-%m-%d").date()

    if beginstr is not None and beginstr != 'None':
        begin = datetime.strptime(beginstr, "%Y-%m-%d").date()

    labels = []  # months
    datasets = []
    colors = next_color()
    indexdict = {}

    i = date(begin.year, begin.month, 1)
    nbmonths = 0
    while i <= end:
        labels.append(i.strftime("%B"))
        indexdict[f'{i.strftime("%Y-%m")}'] = nbmonths
        i = i + relativedelta(months=1)
        nbmonths += 1

    for cat in cats:
        data = [None] * nbmonths
        cat1sums = CatSums()
        #cat_totals = cat1sums.build_monthly_cat1_totals_array(beginstr, endstr, cat.id)
        transactions = Transaction.objects.filter(date_actual__gte=begin,date_actual__lte=end,is_deleted=False,cat1__in=cats)
        cat1_totals = transactions.values('cat1').annotate(Sum('amount_actual'))
        color = next(colors)
        empty = True
        for total in cat1_totals:
            if total.cattype_id == cattype.id:
                empty = False
                index = indexdict[f'{total.year}-{total.month:02d}']
                data[index] = total.total
        if empty is False:
            dataset = {
                'label': cat.name,
                'data': data,
                'index': cat.id,
                'borderColor': f"rgba({color[0]}, {color[1]}, {color[2]}, 1)",
                'backgroundColor': f"rgba({color[0]}, {color[1]}, {color[2]}, 0.5)",
            }
            datasets.append(dataset)

    bardata = {
        'type': 'bar',
        'data': {
            'labels': labels,
            'datasets': datasets
        }
    }
    return JsonResponse(bardata, safe=False)


def GetCat2TotalBarChartData(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    beginstr = request.GET.get('begin', None)
    endstr = request.GET.get('end', None)
    cat_type_pk = request.GET.get('ct', None)
    cattype = CatType.view_objects.get(pk=cat_type_pk)
    cat1_pk = request.GET.get('cat1', None)
    cat1 = Cat1.view_objects.get(pk=cat1_pk)

    cats = Cat2.view_objects.filter(cat1=cat1)

    if endstr is not None and endstr != 'None':
        end = datetime.strptime(endstr, "%Y-%m-%d").date()

    if beginstr is not None and beginstr != 'None':
        begin = datetime.strptime(beginstr, "%Y-%m-%d").date()

    labels = []  # months
    datasets = []
    colors = next_color()
    indexdict = {}

    i = date(begin.year, begin.month, 1)
    nbmonths = 0
    while i <= end:
        labels.append(i.strftime("%B"))
        indexdict[f'{i.strftime("%Y-%m")}'] = nbmonths
        i = i + relativedelta(months=1)
        nbmonths += 1

    for cat in cats:
        data = [None] * nbmonths
        cat2sums = CatSums()
        cat_totals = cat2sums.build_monthly_cat2_totals_array(beginstr, endstr, cat.id)
        color = next(colors)
        empty = True
        for total in cat_totals:
            if total.cattype_id == cattype.id:
                empty = False
                index = indexdict[f'{total.year}-{total.month:02d}']
                data[index] = total.total
        if empty is False:
            dataset = {
                'label': cat.name,
                'data': data,
                'borderColor': f"rgba({color[0]}, {color[1]}, {color[2]}, 1)",
                'backgroundColor': f"rgba({color[0]}, {color[1]}, {color[2]}, 0.5)",
            }
            datasets.append(dataset)

    bardata = {
        'type': 'bar',
        'data': {
            'labels': labels,
            'datasets': datasets
        },
        'options': {
            'scales': {
                'yAxes': [{
                    'ticks': {
                        'beginAtZero': True
                    }
                }]
            }
        }
    }

    return JsonResponse(bardata, safe=False)


def load_cat2(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    cat1_id = request.GET.get('cat1')
    cat2s = Cat2.admin_objects.filter(cat1=cat1_id).order_by('name')
    return render(request, 'budgetdb/subcategory_dropdown_list_options.html', {'cat2s': cat2s})


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


def get_template(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    vendor_id = request.GET.get('vendor_id')
    template = get_object_or_404(Template, vendor=vendor_id)
    response = TemplateSerializer(instance=template)
    return JsonResponse(response.data, safe=False)


def load_cat2_fuel(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    cat2_id = request.GET.get('cat2')
    if cat2_id != '' and cat2_id is not None:
        isfuel = Cat2.admin_objects.get(id=cat2_id).fuel
        return JsonResponse({"isfuel": isfuel}, safe=False)
    else:
        return JsonResponse({"isfuel": False}, safe=False)


def timeline2JSON(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    accountcategoryID = request.GET.get('ac', None)

    if accountcategoryID is None or accountcategoryID == 'None':
        accounts = Account.view_objects.all().order_by('account_host', 'name')
    else:
        accounts = Account.view_objects.filter(account_categories=accountcategoryID).order_by('account_host', 'name')

    preference = get_object_or_404(Preference, user=request.user.id)
    begin = preference.slider_start
    end = preference.slider_stop

    colors = next_color()

    datasets = []  # lines
    labels = []  # Dates

    dates = MyCalendar.objects.filter(db_date__gte=begin, db_date__lte=end).order_by('db_date')
    index_today = None
    i = 0
    for day in dates:
        labels.append(f'{day}')
        if day.db_date == date.today():
            index_today = i
        i += 1

    nb_days = len(labels)
    linetotaldata = [Decimal(0.00)] * nb_days
    for account in accounts:
        if account.can_view() is False:
            continue
        if account.date_closed is not None:
            if account.date_closed < begin:
                continue
        color = next(colors)
        # balances = account.build_balance_array(begin, end)
        balances = account.get_balances(begin, end)
        linedata = []
        i = 0
        for day in balances:
            linetotaldata[i] += day.balance
            linedata.append(day.balance)
            i += 1
        linedict = {
            "backgroundColor": f"rgba({color[0]}, {color[1]}, {color[2]}, 0.5)",
            "borderColor": f"rgba({color[0]}, {color[1]}, {color[2]}, 1)",
            "pointBackgroundColor": f"rgba({color[0]}, {color[1]}, {color[2]}, 1)",
            "pointBorderColor": "#fff",
            'data': linedata,
            'label': f'{account.account_host} - {account.name}',
            'name': account.name,
            'index': account.id,
            'cubicInterpolationMode': 'monotone',
        }
        datasets.append(linedict)

    linedict = {
        "backgroundColor": f"rgba(0,0,0, 0.5)",
        "borderColor": f"rgba(0,0,0, 1)",
        "pointBackgroundColor": f"rgba(0,0,0, 1)",
        "pointBorderColor": "#fff",
        'data': linetotaldata,
        'label': 'TOTAL',
        'name': 'TOTAL',
        'index': None,
        'cubicInterpolationMode': 'monotone',
    }
    # datasets.append(linedict)

    data = {
        'datasets': datasets,
        'labels': labels,
        'index_today': index_today
    }

    return JsonResponse(data, safe=False)


class CatTotalPieChart(TemplateView):
    template_name = 'budgetdb/cattype_pie_chart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cat_type_pk = self.kwargs.get('cat_type_pk')
        cattype = CatType.view_objects.get(pk=cat_type_pk)

        begin = self.request.GET.get('begin', None)
        end = self.request.GET.get('end', None)
        preference = Preference.objects.get(user=self.request.user.id)

        if end is None or end == 'None':
            end = preference.slider_stop
        else:
            end = datetime.strptime(end, "%Y-%m-%d")

        if begin is None or begin == 'None':
            begin = preference.slider_start
        else:
            begin = datetime.strptime(begin, "%Y-%m-%d")

        context['begin'] = begin.strftime("%Y-%m-%d")
        context['end'] = end.strftime("%Y-%m-%d")

        context['cattype'] = cattype.id
        return context


class CatTotalBarChart(TemplateView):
    template_name = 'budgetdb/cattype_bar_chart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cat_type_pk = self.kwargs.get('cat_type_pk')
        cattype = CatType.view_objects.get(pk=cat_type_pk)
        begin = self.request.GET.get('begin', None)
        end = self.request.GET.get('end', None)
        preference = Preference.objects.get(user=self.request.user.id)

        if end is None or end == 'None':
            end = preference.slider_stop
        else:
            end = datetime.strptime(end, "%Y-%m-%d")

        if begin is None or begin == 'None':
            begin = preference.slider_start
        else:
            begin = datetime.strptime(begin, "%Y-%m-%d")

        context['begin'] = begin.strftime("%Y-%m-%d")
        context['end'] = end.strftime("%Y-%m-%d")

        context['cattype'] = cattype.id
        return context


class timeline2(TemplateView):
    template_name = 'budgetdb/timeline2.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        accountcategoryID = self.request.GET.get('ac', None)

        if accountcategoryID is not None:
            accountcategory = get_object_or_404(AccountCategory, pk=accountcategoryID)
            if not accountcategory.can_view():
                raise PermissionDenied
            context['accountcategory'] = accountcategory
        else:
            context['accountcategory'] = None

        accountcategories = AccountCategory.view_objects.all()
        context['accountcategories'] = accountcategories

        context['ac'] = accountcategoryID
        return context


###################################################################################################################
###################################################################################################################
# Generic classes


class ObjectMaxRedirect(RedirectView):
    permanent = False
    model = ''

    def get_redirect_url(*args, **kwargs):
        pk = kwargs.get('pk')
        model_name = args[0].model
        model = apps.get_model('budgetdb', model_name)
        try:
            redirect_object = model.view_objects.get(pk=pk)
        except ObjectDoesNotExist:
            raise PermissionDenied
        viewname = 'budgetdb:'
        if redirect_object.can_edit():
            viewname = viewname + 'update_' + model_name.lower()
            return reverse_lazy(viewname, kwargs={'pk': pk})
        if redirect_object.can_view():
            viewname = viewname + 'details_' + model_name.lower()
            return reverse_lazy(viewname, kwargs={'pk': pk})
        raise PermissionDenied


class MyUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    template_name = 'budgetdb/generic_form.html'
    task = 'Update'
    contains_currency = False
    contains_cat = False
    contains_account = False

    def test_func(self):
        try:
            view_object = self.model.view_objects.get(pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist:
            raise PermissionDenied
        return view_object.can_edit()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.model._meta.verbose_name
        context["task"] = self.task
        context["contains_currency"] = self.contains_currency
        context["contains_cat"] = self.contains_cat
        context["contains_account"] = self.contains_account
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', self.task, css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        form.helper.add_input(Submit('delete', 'Delete', css_class='btn-danger'))
        return form


class MyCreateView(LoginRequiredMixin, CreateView):
    template_name = 'budgetdb/generic_form.html'
    task = 'Create'
    contains_currency = False
    contains_cat = False
    contains_account = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.model._meta.verbose_name
        context["task"] = self.task
        context["contains_currency"] = self.contains_currency
        if self.contains_currency:
            user = get_current_user()
            preference = Preference.objects.get(user=user.id)
            context["currency"] = preference.currency_prefered.id
        context["contains_cat"] = self.contains_cat
        context["contains_account"] = self.contains_account
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', self.task, css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        return form


class MyDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    task = 'View'
    url = ''
    title = ''

    def test_func(self):
        try:
            view_object = self.model.view_objects.get(pk=self.kwargs.get('pk'))
        except ObjectDoesNotExist:
            raise PermissionDenied
        return view_object.can_view()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_object(self, queryset=None):
        my_object = super().get_object(queryset=queryset)
        my_object.editable = my_object.can_edit()
        return my_object

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.model._meta.verbose_name
        context["task"] = self.task
        context["url"] = self.url
        context["title"] = self.title
        return context        


class MyListView(LoginRequiredMixin, SingleTableView):
    template_name = 'budgetdb/generic_list.html'
    create = True
    url = ''
    title = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.title != '':
            context["title"] = self.title
        else:
            context["title"] = f'{self.model._meta.verbose_name_plural} List'
        if self.create is True:
            context['add_url'] = reverse(f'budgetdb:create_{self.model._meta.model_name.lower()}')
        else:
            context['add_url'] = None
        context["create"] = self.create
        return context


class MyNotificationLoggedin(LoginRequiredMixin, TemplateView):
    template_name = 'budgetdb/notification.html'
    notification_message = ''
    notification_title = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notification_title'] = self.notification_title
        context['notification_message'] = self.notification_message
        return context


class MyNotificationLoggedout(TemplateView):
    template_name = 'budgetdb/notification.html'
    notification_message = ''
    notification_title = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notification_title'] = self.notification_title
        context['notification_message'] = self.notification_message
        return context


def echartOptionTimeline2JSON(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    title = ''
    preference = get_object_or_404(Preference, user=request.user.id)
    begin = preference.slider_start
    end = preference.slider_stop
    accountcategoryID = request.GET.get('ac', None)
    period = request.GET.get('period', None)
    if period == 'nextmonth':
        begin = datetime.today()
        end = begin + timedelta(days=40)
    if accountcategoryID  == 'favorites':
        accounts = preference.favorite_accounts.all()
    elif accountcategoryID is None or accountcategoryID == 'None':
        accounts = Account.view_objects.all().order_by('account_host', 'name')
        title = 'All'
    else:
        try:
            accountcategory = AccountCategory.view_objects.get(pk=accountcategoryID)
        except ObjectDoesNotExist:
            raise PermissionDenied
        title = accountcategory.name
        accounts = Account.view_objects.filter(account_categories=accountcategory.pk).order_by('account_host', 'name')




    series = []  # lines
    x_axis = []  # Dates, x axis
    series_label = []  # series label

    dates = MyCalendar.objects.filter(db_date__gte=begin, db_date__lte=end).order_by('db_date')
    index_today = None
    i = 0
    for day in dates:
        x_axis.append(f'{day.db_date}')
        if day.db_date == date.today():
            index_today = i
        i += 1
    if index_today is not None:
        vert_line =  {
                'type': 'line',
                'silent': 'true',
                
                'markLine': {
                    'symbol': 'circle',
                    'lineStyle': {
                        'color': 'rgb(255,0,0)',
                        'type': 'solid',
                    },
                    'data': [
                    {
                        'name': 'Today',
                        'xAxis': date.today(),
                    }
                    ]
                }
                }
        series.append(vert_line)

    nb_days = len(x_axis)
    linetotaldata = [Decimal(0.00)] * nb_days
    for account in accounts:
        if account.can_view() is False:
            continue
        if account.date_closed is not None:
            if account.date_closed < begin:
                continue
        series_label.append(f'{account}')
        balances = account.get_balances(begin, end)
        linedata = []
        i = 0
        for day in balances:
            linetotaldata[i] += day.balance
            linedata.append(day.balance)
            i += 1
        linedict = {
            'name': f'{account}',
            'type': 'line',
            'smooth': 'true',
            'areaStyle': {},
            'symbol': account.currency.symbol,  # doesn't work...
            'data': linedata,
        }
        series.append(linedict)




    # datasets.append(linedict)
    data = {
        'title': {
                'text': title
                },
        'legend': {
                'data': series_label,
                'type': 'scroll',
                'orient': 'vertical',
                'right': '10',
                'top': '20',
                'bottom': '20',
            },
        'grid': {
            'left': '1%',
            'right': '2%',
            'bottom': '2%',
            'containLabel': 'true'
        },
       # 'tooltip': {
        #    'trigger': 'axis',
         #   'valueFormatter': '(value) => "$" + value.toFixed(2)'
            #'formatter': 'callback'
        #},
        'dataZoom': [
            {
            'type': 'inside',
            'start': 0,
            'end': 100,
            },
        ],
        'markLine': {
            'data': [ 
                { 'name': 'bang', 
                'xAxis': '2024-01-28' } 
            ]
        },
        'xAxis': {
            'boundaryGap': 'false',
            'data': x_axis,
           # 'type': 'time',
        },
        'yAxis': {
            'type': 'value'
        },
        'series': series
    }

    return JsonResponse(data, safe=False)


class EChartTimelineView(LoginRequiredMixin, TemplateView):
    # template_name = 'budgetdb/echart_template.html'
    template_name = 'budgetdb/echart_template_json.html'
    echart_title = 'Account Timeline'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        accountcategoryID = self.request.GET.get('ac', None)

        if accountcategoryID is not None:
            accountcategory = get_object_or_404(AccountCategory, pk=accountcategoryID)
            if not accountcategory.can_view():
                raise PermissionDenied
            context['accountcategory'] = accountcategory
        else:
            context['accountcategory'] = None

        accountcategories = AccountCategory.view_objects.all()
        context['accountcategories'] = accountcategories
        context['ac'] = accountcategoryID
        context['echart_title'] = self.echart_title
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'budgetdb/dashboard.html'
    title = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        messages = Messages.objects.filter(message_type='tutorial')

        context['messages'] = messages
        context['title'] = 'Dashboard'
        return context


###################################################################################################################
###################################################################################################################
# Account


class AccountListViewSimple(MyListView):
    model = Account
    table_class = AccountListTable

    def get_queryset(self):
        return self.model.view_objects.all().order_by('account_host__name', 'name')


class AccountDetailView(MyDetailView):
    model = Account


class AccountSummaryView(LoginRequiredMixin, ListView):
    model = Account
    template_name = 'budgetdb/account_list_summary.html'

    def get_queryset(self):
        accounts = Account.view_objects.all().order_by('account_host__name', 'name')
        accounts = accounts.exclude(date_closed__lt=datetime.today())
        return accounts

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        decorated = []
        for account in self.object_list:
            account.balance = account.get_balance(datetime.today()).balance
            if account.owner != get_current_user():
                account.nice_name = f'{account.account_host} - {account.owner} - {account.name}'
            else:
                account.nice_name = f'{account.account_host} - {account.name}'
            decorated.append(account)
        context['decorated'] = decorated
        return context


class AccountYearReportDetailView(MyDetailView):
    model = Account
    template_name = 'budgetdb/account_yearreportview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        year = self.kwargs.get('year')
        # context['account_list'] = Account.objects.all().order_by('name')
        context['pk'] = pk
        context['year'] = year
        context['nyear'] = year + 1
        context['pyear'] = year - 1
        context['account_name'] = Account.objects.get(id=pk).name
        context['reports'] = Account.objects.get(pk=pk).build_yearly_report(year)
        return context


class AccountCatYearReportDetailView(MyDetailView):
    model = AccountCategory
    template_name = 'budgetdb/account_yearreportview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        year = self.kwargs.get('year')
        # context['account_list'] = Account.objects.all().order_by('name')
        context['pk'] = pk
        context['year'] = year
        context['account_name'] = Account.objects.get(id=pk).name
        context['reports'] = Account.objects.get(pk=pk).build_yearly_report(year)
        return context


class AccountUpdateView(MyUpdateView):
    model = Account
    form_class = AccountForm


class AccountCreateView(MyCreateView):
    model = Account
    form_class = AccountForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = get_current_user()
        preference = get_object_or_404(Preference, user=user)
        form.initial['currency'] = preference.currency_prefered
        return form

###################################################################################################################
# AccountCategories


class AccountCatListView(MyListView):
    model = AccountCategory
    table_class = AccountCategoryListTable

    def get_queryset(self):
        return self.model.view_objects.all().order_by('name')


class AccountCatDetailView(MyDetailView):
    model = AccountCategory

    def get_object(self, queryset=None):
        category = super().get_object(queryset=queryset)
        category.editable = category.can_edit()
        category.my_accounts = category.accounts.filter(is_deleted=False)
        return category


class AccountCatUpdateView(MyUpdateView):
    model = AccountCategory
    form_class = AccountCategoryForm


class AccountCatCreateView(MyCreateView):
    model = AccountCategory
    form_class = AccountCategoryForm


###################################################################################################################
# AccountHost


class AccountHostListView(MyListView):
    model = AccountHost
    table_class = AccountHostListTable

    def get_queryset(self):
        return self.model.view_objects.all().order_by('name')


class AccountHostDetailView(MyDetailView):
    model = AccountHost
    context_object_name = 'accounthost'
    template_name = 'budgetdb/accounthost_detail.html'


class AccountHostUpdateView(MyUpdateView):
    model = AccountHost
    form_class = AccountHostForm


class AccountHostCreateView(MyCreateView):
    model = AccountHost
    form_class = AccountHostForm

###################################################################################################################
# Cat1


class Cat1ListView(MyListView):
    model = Cat1
    table_class = Cat1ListTable

    def get_queryset(self):
        return self.model.view_objects.all().order_by('name')


class Cat1DetailView(MyDetailView):
    model = Cat1
    template_name = 'budgetdb/cat1_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cat1 = get_object_or_404(self.model, pk=self.kwargs.get('pk'))
        cat2s = Cat2.view_objects.filter(cat1=cat1)
        context['cat2s'] = cat2s
        return context


class Cat1UpdateView(MyUpdateView):
    model = Cat1
    form_class = Cat1Form


class Cat1CreateView(MyCreateView):
    model = Cat1
    form_class = Cat1Form

###################################################################################################################
# Cat2


class Cat2ListView(MyListView):
    model = Cat2
    table_class = Cat2ListTable
    create = False

    def get_queryset(self):
        return self.model.view_objects.all().order_by('cat1', 'name')


class Cat2DetailView(MyDetailView):
    model = Cat2
    template_name = 'budgetdb/cat2_detail.html'


class Cat2UpdateView(MyUpdateView):
    model = Cat2
    form_class = Cat2Form


class Cat2CreateView(MyCreateView):
    model = Cat2
    form_class = Cat2Form

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(self.kwargs)
        return kwargs

    def form_valid(self, form):
        return super().form_valid(form)


###################################################################################################################
# CatType


class CatTypeListView(MyListView):
    model = CatType
    table_class = CatTypeListTable

    def get_queryset(self):
        return self.model.view_objects.all().order_by('name')


class CatTypeDetailView(MyDetailView):
    model = CatType
    template_name = 'budgetdb/cattype_detail.html'


def CatTypeMonthJSON(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)

    today = date.today()
    series = []
    total = Decimal('0.00')
    i = 1
    param = request.GET.get(f'pk{i}', None)    
    while param is not None:
        id = param
        sign = 1
        cattype = None
        if id[0] == '-':
            sign = -1
            id = id.replace('-','',1)
        try:
            cattype = CatType.view_objects.get(pk=id)
            value = sign * cattype.get_month_total(today)
            total = total + value
            linedict = {
                'name': cattype.name,
                'type': 'bar',
                'smooth': 'true',
                'data': [value],
            }
            series.append(linedict)
        except ObjectDoesNotExist:
            continue
        
        i = i + 1
        param = request.GET.get(f'pk{i}', None)    


    linedict = {
                'name': 'balance',
                'type': 'bar',
                'smooth': 'true',
                'data': [total],
            }
    series.append(linedict)

    month_name = today.strftime("%B")


    data = {
 
        "tooltip": {
            "trigger": 'axis',
            "axisPointer": {
         "type": 'shadow' 
            }
        },
        'xAxis': {
            'type': 'value',
            'position': 'top',
            'splitLine': {
                'lineStyle': {
                    'type': 'dashed'
                }
            }
        },
        'yAxis': {
            'type': 'category',
            'show': False,
            'data': [month_name]
        },
        'series': series
    
    }
    return JsonResponse(data, safe=False)


class CatTypeUpdateView(MyUpdateView):
    model = CatType
    form_class = CatTypeForm


class CatTypeCreateView(MyCreateView):
    model = CatType
    form_class = CatTypeForm


###################################################################################################################
# Invitation


class InvitationListView(MyListView):
    model = Invitation
    title = 'Pending Invites'
    table_class = InvitationListTable

    def get_queryset(self):
        user = get_current_user()
        my_invitations = self.model.objects.filter(owner=user).order_by('email')
        received_invitations = self.model.objects.filter(email=user.email)
        return my_invitations | received_invitations


class InvitationCreateView(MyCreateView):
    model = Invitation
    form_class = InvitationForm

    def form_valid(self, form):
        invite = form.save()
        invite.send_invite_email()
        return redirect('budgetdb:home')


class InvitationAcceptView(UserPassesTestMixin, MyNotificationLoggedin):
    notification_message = 'Sharing enabled'
    notification_title = 'Sharing enabled'
    invitation = None
    user = None
    invitee = None
    inviter = None

    def test_func(self):
        self.user = get_current_user()
        try:
            self.invitation = Invitation.objects.get(pk=self.kwargs.get('pk'))
            self.inviter = self.invitation.owner
        except ObjectDoesNotExist:
            return False
        try:
            self.invitee = User.objects.get(email=self.invitation.email)
        except ObjectDoesNotExist:
            pass

        if self.user == self.inviter:
            return True
        elif self.user == self.invitee:
            return True
        else:
            return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.invitee is not None:
            self.invitee.friends.add(self.inviter)
            self.inviter.friends.add(self.invitee)
            self.invitation.accepted = True
            self.invitation.rejected = False
            self.invitation.save()
        return context


class InvitationRejectView(UserPassesTestMixin, MyNotificationLoggedin):
    notification_message = 'Sharing disabled'
    notification_title = 'Sharing disabled'
    invitation = None
    user = None
    invitee = None
    inviter = None

    def test_func(self):
        self.user = get_current_user()
        try:
            self.invitation = Invitation.objects.get(pk=self.kwargs.get('pk'))
            self.inviter = self.invitation.owner
        except ObjectDoesNotExist:
            return False

        try:
            self.invitee = User.objects.get(email=self.invitation.email)
        except ObjectDoesNotExist:
            pass

        if self.user == self.inviter:
            return True
        elif self.user == self.invitee:
            return True
        else:
            return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        self.invitation.rejected = True
        self.invitation.accepted = False
        self.invitation.save()
        if self.invitee is not None:
            # remove existing rights
            self.invitee.friends.remove(self.inviter)
            self.inviter.friends.remove(self.invitee)
            objects_with_rights = UserPermissions.objects.filter(users_admin__in=[self.inviter,self.invitee])
            for myobject in objects_with_rights:
                myobject.users_admin.remove(self.invitee)
                myobject.users_admin.remove(self.inviter)
            objects_with_rights = UserPermissions.objects.filter(users_view__in=[self.inviter,self.invitee])
            for myobject in objects_with_rights:
                myobject.users_view.remove(self.invitee)
                myobject.users_view.remove(self.inviter)
        return context


###################################################################################################################
# Vendor


class VendorListView(MyListView):
    model = Vendor
    table_class = VendorListTable

    def get_queryset(self):
        return self.model.view_objects.all().order_by('name')


class VendorDetailView(MyDetailView):
    model = Vendor
    template_name = 'budgetdb/vendor_detail.html'


class VendorUpdateView(MyUpdateView):
    model = Vendor
    form_class = VendorForm


class VendorCreateView(MyCreateView):
    model = Vendor
    form_class = VendorForm


###################################################################################################################
# Statement


class StatementListView(MyListView):
    model = Statement
    table_class = StatementListTable

    def get_queryset(self):
        return self.model.view_objects.all().order_by('-statement_date', 'account')


class StatementDetailView(MyDetailView):
    model = Statement
    template_name = 'budgetdb/statement_detail.html'
    date_min = None
    date_max = None

    def get_object(self, queryset=None):
        statement = super().get_object(queryset=queryset)
        statement.editable = statement.can_edit()
        # statement.included_transactions = Transaction.view_objects.filter(statement=statement).order_by('date_actual')
        self.date_min = statement.statement_date - timedelta(days=35)
        self.title = f'Statement {statement.statement_date} for {statement.account}'
        statement.included_transactions = statement.transaction_set.filter(is_deleted=False).order_by('date_actual')
        if statement.included_transactions.count() > 0:
            first_transaction_date = statement.included_transactions.first().date_actual
            if first_transaction_date < self.date_min:
                self.date_min = first_transaction_date
            
        sum_from = statement.included_transactions.filter(account_source=statement.account).aggregate(Sum('amount_actual')).get('amount_actual__sum')
        sum_to = statement.included_transactions.filter(account_destination=statement.account).aggregate(Sum('amount_actual')).get('amount_actual__sum')
        
        # switching sign because the CC balance is positive in the statement even if it's a debt
        transactions_sum = - (sum_to or Decimal('0.00')) + (sum_from or Decimal('0.00'))
        
        statement.transactions_sum = transactions_sum
        statement.error = transactions_sum - statement.balance
        if statement.error < 0:
            statement.errorsign = '-'
            statement.error = -statement.error
        
        self.date_max = statement.statement_date
        statement.possible_transactions = Transaction.admin_objects.filter(account_source=statement.account,
                                                                          date_actual__lte=self.date_max,
                                                                          date_actual__gt=self.date_min,
                                                                          statement__isnull=True,
                                                                          audit=False
                                                                          ).order_by('date_actual')

        transactions_sumP = statement.possible_transactions.aggregate(Sum('amount_actual')).get('amount_actual__sum')
        statement.transactions_sumP = transactions_sumP
        return statement

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["date1"] = self.date_min
        context["date2"] = self.date_max
        return context  


class StatementAddTransactionsRedirectView(RedirectView):
    permanent = False

    def get_redirect_url(*args, **kwargs):
        pk = kwargs.get('pk')
        model = Statement
        try:
            statement = model.admin_objects.get(pk=pk)
        except ObjectDoesNotExist:
            raise PermissionDenied
        min_date = statement.statement_date - relativedelta(days=40)
        possible_transactions = Transaction.admin_objects.filter(account_source=statement.account,
                                                                date_actual__lte=statement.statement_date,
                                                                date_actual__gt=min_date,
                                                                statement__isnull=True,
                                                                audit=False
                                                                ).update(statement=pk)


        viewname = 'budgetdb:'
        viewname = viewname + 'details_' + model._meta.model_name
        return reverse_lazy(viewname, kwargs={'pk': pk})


class StatementUpdateView(LoginRequiredMixin, UpdateView):
    model = Statement
    form_class = StatementForm
    task = 'Update'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', self.task, css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        form.helper.add_input(Submit('delete', 'Delete', css_class='btn-danger'))
        return form


class StatementCreateView(LoginRequiredMixin, CreateView):
    model = Statement
    form_class = StatementForm
    task = 'Create'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', self.task, css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        return form

###################################################################################################################
# Template


class TemplateListView(MyListView):
    model = Template
    table_class = TemplateListTable

    def get_queryset(self):
        return self.model.view_objects.all().order_by('vendor')


class TemplateDetailView(MyDetailView):
    model = Template
    template_name = 'budgetdb/template_detail.html'


class TemplateUpdateView(MyUpdateView):
    model = Template
    form_class = TemplateForm
    contains_currency = True
    contains_cat = True
    contains_account = True


class TemplateCreateView(MyCreateView):
    model = Template
    form_class = TemplateForm
    contains_currency = True
    contains_cat = True
    contains_account = True


###################################################################################################################
###################################################################################################################


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = 'budgetdb/index.html'


class AccountTransactionListViewOLD(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Account
    template_name = 'budgetdb/AccountTransactionListView.html'

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs.get('pk'), is_deleted=False)
        return view_object.can_view()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_queryset(self):
        pk = self.kwargs.get('pk')
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

        events = Account.objects.get(id=pk).build_report_with_balance(begin, end)
        return events

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        preference = Preference.objects.get(user=self.request.user.id)
        year = preference.slider_stop.year
        decorated = []
        for transaction in self.object_list:
            transaction.show_currency = False
            if transaction.account_destination is not None:
                if transaction.account_destination.currency != transaction.currency:
                    transaction.show_currency = True
            if transaction.account_source is not None:
                if transaction.account_source.currency != transaction.currency:
                    transaction.show_currency = True
            decorated.append(transaction)
        context['pk'] = pk
        context['year'] = year
        context['decorated'] = decorated
        context['account_name'] = Account.objects.get(id=pk).name
        return context


class AccountTransactionListView(UserPassesTestMixin, MyListView):
    model = Account
    table_class = AccountActivityListTable
    template_name = 'budgetdb/account_transactions_list.html'
    begin = None
    end = None
    year = None
    create = False
    account = None
    # SingleTableView.table_pagination = False

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs.get('pk'), is_deleted=False)
        return view_object.can_view()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
       
        context['pk'] = self.account.pk
        context['year'] = self.year
        context['account_name'] = self.account
        return context

    def get_table_kwargs(self):
       return {
           'account_view': self.account.pk,
           'begin': self.begin,
           'end': self.end,
       }

    def get_queryset(self):
        pk = self.kwargs.get('pk')
        preference = Preference.objects.get(user=self.request.user.id)
        date1 = self.kwargs.get('date1')
        date2 = self.kwargs.get('date2')
        if date1 is not None and date2 is not None:
            self.begin = datetime.strptime(date1, "%Y-%m-%d").date()
            self.end = datetime.strptime(date2, "%Y-%m-%d").date()
            preference.slider_start = self.begin
            preference.slider_stop = self.end
            preference.save() 
        else:
            self.begin = preference.slider_start
            self.end = preference.slider_stop
        self.year = preference.slider_stop.year
        self.account = Account.objects.get(pk=pk)
        self.title = self.account.name

        childaccounts = Account.view_objects.filter(account_parent_id=pk, is_deleted=False)
        accounts = childaccounts | Account.view_objects.filter(pk=pk)
        events_source = Transaction.view_objects.filter(account_source__in=accounts,date_actual__gte=self.begin,date_actual__lte=self.end)
        events_destination = Transaction.view_objects.filter(account_destination__in=accounts,date_actual__gte=self.begin,date_actual__lte=self.end)
        return events_source | events_destination


###################################################################################################################
# User Management

class UserVerifyEmailView(MyNotificationLoggedin):
    notification_message = 'Verification email sent'
    notification_title = 'Verification email sent'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_current_user()
        user.send_verify_email()
        return context


class UserVerifiedEmailView(MyNotificationLoggedout):
    notification_message = 'Email address verified, welcome'
    notification_title = 'Email verified'


class UserVerifiedEmailBadLinkView(MyNotificationLoggedout):
    notification_message = 'Verification link is invalid'
    notification_title = 'Verification failed'


class UserVerifyLinkView(RedirectView):
    permanent = False
    
    def get_redirect_url(*args, **kwargs):
        uidb64 = kwargs.get('uidb64')
        token = kwargs.get('token')
        user = None

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except(TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        if user is not None and account_activation_token.check_token(user, token):
            user.email_verified = True
            user.save()
            return reverse_lazy('budgetdb:email_verified')  
        else:
            return reverse_lazy('budgetdb:email_verified_bad_link')


class UserSignupView(CreateView):
    model = User
    form_class = UserSignUpForm
    template_name = 'budgetdb/user_form.html'

    def form_valid(self, form):
        user = form.save()
        preference = Preference.objects.create(
            user=user,
            slider_start=datetime.today().date()-relativedelta(months=6),
            slider_stop=datetime.today().date()+relativedelta(months=6),
            timeline_start=datetime.today().date()-relativedelta(months=6),
            timeline_stop=datetime.today().date()+relativedelta(months=6),
            currency_prefered = Currency.objects.get(name_short='CAD')
            )
        preference.save()
        user.send_verify_email()
        login(self.request, user)
        return redirect('budgetdb:home')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        email = self.kwargs.get('email')
        if email is not None:
            form.initial['email'] = email
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Sign Up!', css_class='btn-primary'))
        return form


class UserLoginView(auth_views.LoginView):
    model = User
    template_name = 'budgetdb/login.html'

    def form_valid(self, form):
        login(self.request, form.get_user())
        return redirect('budgetdb:home')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # julie = User.objects.get(first_name='julie')
        # julie.set_password('etpatatietpatata')
        # julie.save()
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Log in', css_class='btn-primary'))
        return form


class UserPasswordUpdateView(LoginRequiredMixin, auth_views.PasswordChangeView):
    model = User
    form_class = PasswordChangeForm
    success_url = reverse_lazy('budgetdb:home')
    template_name = 'budgetdb/generic_form.html'

    def get_form_kwargs(self):
        kwargs = super(auth_views.PasswordChangeView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        if self.request.method == 'POST':
            kwargs['data'] = self.request.POST
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Change Password', css_class='btn-primary'))
        return form

    

    def form_valid(self, form):
        form.save()
        update_session_auth_hash(self.request, form.user)        
        return super(auth_views.PasswordChangeView, self).form_valid(form) 


class PreferencesUpdateView(LoginRequiredMixin, UpdateView):

    model = Preference
    form_class = PreferenceForm

    def get_object(self):
        user = get_current_user()
        try:
            preference = Preference.objects.get(user=user)
        except Preference.DoesNotExist:
            transactions = Transaction.view_objects.all().order_by("date_actual")
            start = transactions.first().date_actual
            stop = transactions.last().date_actual
            preference = Preference.objects.create(
                user=user,
                slider_start=start,
                slider_stop=stop,
                begin_data=start,
                end_data=stop
                )
            preference.save()
        return preference

    def get_success_url(self):
        return reverse('budgetdb:home')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form
