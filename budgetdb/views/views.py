# from django_addanother.views import CreatePopupMixin, UpdatePopupMixin
from django.core.exceptions import PermissionDenied
from django import forms
from django.apps import apps
from django.forms import ModelForm
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, View, TemplateView, DetailView
from django.views.generic.base import RedirectView
from django.urls import reverse, reverse_lazy
from django.utils.safestring import mark_safe
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import login
from dal import autocomplete
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from budgetdb.models import Cat1, Transaction, Cat2, BudgetedEvent, Vendor, Account, AccountCategory, MyCalendar, User
from budgetdb.models import JoinedTransactions, CatSums, CatType, AccountHost, Preference, AccountPresentation
from budgetdb.utils import Calendar
from budgetdb.forms import UserSignUpForm, PreferenceForm, AccountForm, AccountHostForm, AccountCategoryForm
import pytz
from decimal import *
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field
from crispy_forms.layout import Layout, Submit, Button, Field, Fieldset, ButtonHolder, Div, LayoutObject, TEMPLATE_PACK, HTML, Hidden
from crum import get_current_user


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
    start_interval = request.POST.get("begin_interval", None)
    end_interval = request.POST.get("end_interval", None)
    preference = Preference.objects.get(pk=request.user.id)
    if start_interval:
        preference.start_interval = datetime.strptime(start_interval, "%Y-%m-%d")
    if end_interval:
        preference.end_interval = datetime.strptime(end_interval, "%Y-%m-%d")
    preference.save()
    return HttpResponse(status=200)


def TransactionVerifyToggleJSON(request):
    transaction_ID = request.POST.get("transaction_id", None)
    if transaction_ID:
        transaction = Transaction.objects.get(pk=transaction_ID)
        transaction.verified = not(transaction.verified)
    transaction.save()
    return HttpResponse(status=200)


def TransactionReceiptToggleJSON(request):
    transaction_ID = request.POST.get("transaction_id", None)
    if transaction_ID:
        transaction = Transaction.objects.get(pk=transaction_ID)
        transaction.receipt = not(transaction.receipt)
    transaction.save()
    return HttpResponse(status=200)


def PreferenceGetJSON(request):
    preference = Preference.objects.get(pk=request.user.id)
    transactions = Transaction.objects.filter(is_deleted=False).order_by("date_actual")

    start_slider = preference.min_interval_slider
    stop_slider = preference.max_interval_slider
    if (preference.min_interval_slider is None):
        start_slider = transactions.first().date_actual
    if (preference.max_interval_slider is None):
        stop_slider = transactions.last().date_actual

    data = {
        'start_interval': preference.start_interval,
        'end_interval': preference.end_interval,
        'begin_data': start_slider,
        'end_data': stop_slider,
        # 'begin_data': transactions.first().date_actual,
        # 'end_data': transactions.last().date_actual,
    }

    return JsonResponse(data, safe=False)


def GetAccountViewListJSON(request):
    queryset = Account.view_objects.filter(is_deleted=False)
    queryset = queryset.order_by("name")

    array = []

    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetAccountCatViewListJSON(request):
    queryset = AccountCategory.view_objects.filter(is_deleted=False)
    queryset = queryset.order_by("name")

    array = []

    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetAccountHostViewListJSON(request):
    queryset = AccountHost.view_objects.filter(is_deleted=False)
    queryset = queryset.order_by("name")

    array = []

    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetVendorListJSON(request):
    queryset = Vendor.objects.filter(is_deleted=False)
    queryset = queryset.order_by("name")

    array = []

    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetCat1ListJSON(request):
    queryset = Cat1.objects.filter(is_deleted=False)
    queryset = queryset.order_by("name")

    array = []

    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetCatTypeListJSON(request):
    queryset = CatType.objects.filter(is_deleted=False)
    queryset = queryset.order_by("name")

    array = []

    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetCat1TotalPieChartData(request):
    begin = request.GET.get('begin', None)
    end = request.GET.get('end', None)
    cat_type_pk = request.GET.get('ct', None)
    cattype = CatType.objects.get(pk=cat_type_pk)
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

    begin = request.GET.get('begin', None)
    end = request.GET.get('end', None)
    cat_type_pk = request.GET.get('ct', None)
    cattype = CatType.objects.get(pk=cat_type_pk)
    cat1_pk = request.GET.get('cat1', None)
    cat1 = Cat1.objects.get(pk=cat1_pk)
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
    beginstr = request.GET.get('begin', None)
    endstr = request.GET.get('end', None)
    cat_type_pk = request.GET.get('ct', None)
    cattype = CatType.objects.get(pk=cat_type_pk)
    cats = Cat1.objects.filter(is_deleted=False)

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
        cat_totals = cat1sums.build_monthly_cat1_totals_array(beginstr, endstr, cat.id)
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
    beginstr = request.GET.get('begin', None)
    endstr = request.GET.get('end', None)
    cat_type_pk = request.GET.get('ct', None)
    cattype = CatType.objects.get(pk=cat_type_pk)
    cat1_pk = request.GET.get('cat1', None)
    cat1 = Cat1.objects.get(pk=cat1_pk)

    cats = Cat2.objects.filter(cat1=cat1, is_deleted=False)

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


def timeline2JSON(request):
    accountcategoryID = request.GET.get('ac', None)

    if accountcategoryID is None or accountcategoryID == 'None':
        accounts = Account.objects.filter(is_deleted=False).order_by('name')
    else:
        accounts = Account.objects.filter(is_deleted=False, account_categories=accountcategoryID).order_by('name')

    preference = Preference.objects.get(pk=request.user.id)
    begin = preference.start_interval
    end = preference.end_interval

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
        color = next(colors)
        balances = account.build_balance_array(begin, end)
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
            'label': account.name,
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
        cat_type_pk = self.kwargs['cat_type_pk']
        cattype = CatType.objects.get(pk=cat_type_pk)

        begin = self.request.GET.get('begin', None)
        end = self.request.GET.get('end', None)
        preference = Preference.objects.get(pk=self.request.user.id)

        if end is None or end == 'None':
            end = preference.end_interval
        else:
            end = datetime.strptime(end, "%Y-%m-%d")

        if begin is None or begin == 'None':
            begin = preference.start_interval
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
        cat_type_pk = self.kwargs['cat_type_pk']
        cattype = CatType.objects.get(pk=cat_type_pk)
        begin = self.request.GET.get('begin', None)
        end = self.request.GET.get('end', None)
        preference = Preference.objects.get(pk=self.request.user.id)

        if end is None or end == 'None':
            end = preference.end_interval
        else:
            end = datetime.strptime(end, "%Y-%m-%d")

        if begin is None or begin == 'None':
            begin = preference.start_interval
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

        # beginstr = self.request.GET.get('begin', None)
        # endstr = self.request.GET.get('end', None)
        accountcategoryID = self.request.GET.get('ac', None)

        if accountcategoryID is not None and accountcategoryID != 'None':
            accountcategory = AccountCategory.objects.get(id=accountcategoryID)
            context['accountcategory'] = accountcategory

        accountcategories = AccountCategory.objects.filter(is_deleted=False)
        context['accountcategories'] = accountcategories

        # preference = Preference.objects.get(pk=self.request.user.id)
        # if endstr is None or endstr == 'None':
        #     end = preference.end_interval
        # else:
        #     end = datetime.strptime(endstr, "%Y-%m-%d")

        # if beginstr is None or beginstr == 'None':
        #     begin = preference.start_interval
        # else:
        #     begin = datetime.strptime(beginstr, "%Y-%m-%d")

        # context['begin'] = begin.strftime("%Y-%m-%d")
        # context['end'] = end.strftime("%Y-%m-%d")
        # mydate = date.today()
        # context['now'] = mydate.strftime("%Y-%m-%d")
        # mydate = date.today() + relativedelta(months=-1)
        # context['monthago'] = mydate.strftime("%Y-%m-%d")
        # mydate = date.today() + relativedelta(months=-3)
        # context['3monthsago'] = mydate.strftime("%Y-%m-%d")
        # mydate = date.today() + relativedelta(months=-12)
        # context['yearago'] = mydate.strftime("%Y-%m-%d")
        # mydate = date.today() + relativedelta(months=1)
        # context['inamonth'] = mydate.strftime("%Y-%m-%d")
        # mydate = date.today() + relativedelta(months=3)
        # context['in3months'] = mydate.strftime("%Y-%m-%d")
        # mydate = date.today() + relativedelta(months=12)
        # context['inayear'] = mydate.strftime("%Y-%m-%d")

        context['ac'] = accountcategoryID
        return context


class AutocompleteAccount(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Account.objects.none()

        qs = Account.view_objects.filter(is_deleted=False)

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class AutocompleteCat1(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Cat1.objects.none()

        qs = Cat1.view_objects.filter(is_deleted=False)

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class AutocompleteCat2(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Cat2.objects.none()

        qs = Cat2.view_objects.filter(is_deleted=False)
        category = self.forwarded.get('cat1', None)

        if category:
            qs = qs.filter(cat1=category)

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


def load_cat2(request):
    cat1_id = request.GET.get('cat1')
    cat2s = Cat2.objects.filter(cat1=cat1_id).order_by('name')
    return render(request, 'budgetdb/subcategory_dropdown_list_options.html', {'cat2s': cat2s})


class AutocompleteVendor(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Vendor.objects.none()

        qs = Vendor.view_objects.filter(is_deleted=False)

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class Cat1DetailView(LoginRequiredMixin, DetailView):
    model = Cat1
    template_name = 'budgetdb/cat1_detail.html'


class Cat1UpdateView(LoginRequiredMixin, UpdateView):
    model = Cat1
    fields = (
        'name',
        'cattype',
    )

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form


class Cat2UpdateView(LoginRequiredMixin, UpdateView):
    model = Cat2
    fields = (
        'name',
        'cattype',
        )

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form


class CatTypeUpdateView(LoginRequiredMixin, UpdateView):
    model = CatType
    fields = (
        'name',
        )

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form


class PreferencesUpdateView(LoginRequiredMixin, UpdateView):
    model = Preference
    form_class = PreferenceForm

    def get_object(self):
        user = get_current_user()
        try:
            preference = Preference.objects.get(user=user)
        except Preference.DoesNotExist:
            transactions = Transaction.objects.filter(is_deleted=False).order_by("date_actual")
            start = transactions.first().date_actual
            stop = transactions.last().date_actual
            preference = Preference.objects.create(
                user=user,
                start_interval=start,
                end_interval=stop,
                begin_data=start,
                end_data=stop
                )
            preference.save()
        return preference

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form


class VendorUpdateView(LoginRequiredMixin, UpdateView):
    model = Vendor
    fields = ('name',)

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form


class ObjectMaxRedirect(RedirectView):
    permanent = False
    model = ''

    def get_redirect_url(*args, **kwargs):
        pk = kwargs['pk']
        model_name = args[0].model
        model = apps.get_model('budgetdb', model_name)
        redirect_object = get_object_or_404(model, pk=pk)
        viewname = 'budgetdb:'
        if redirect_object.can_edit():
            viewname = viewname + 'update_' + model_name.lower()
            return reverse_lazy(viewname, kwargs={'pk': pk})
        if redirect_object.can_view():
            viewname = viewname + 'details_' + model_name.lower()
            return reverse_lazy(viewname, kwargs={'pk': pk})
        raise PermissionDenied


# Account


class AccountListViewSimple(LoginRequiredMixin, ListView):
    model = Account
    context_object_name = 'account_list'
    template_name = 'budgetdb/account_list_simple.html'

    def get_queryset(self):
        accounts = Account.view_objects.filter(is_deleted=False).order_by('name')
        for account in accounts:
            account.my_categories = AccountCategory.view_objects.filter(accounts=account)
        return accounts


class AccountDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Account
    template_name = 'budgetdb/account_detail.html'

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs['pk'])
        return view_object.can_view()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_object(self, queryset=None):
        host = super(AccountDetailView, self).get_object(queryset=queryset)
        host.editable = host.can_edit()
        return host


class AccountUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Account
    template_name = 'budgetdb/generic_form.html'
    form_class = AccountForm

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs['pk'])
        return view_object.can_edit()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = 'Account'
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        form.helper.add_input(Submit('delete', 'Delete', css_class='btn-danger'))
        return form


class AccountCreateView(LoginRequiredMixin, CreateView):
    model = Account
    template_name = 'budgetdb/generic_form.html'
    form_class = AccountForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = 'Account'
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        return form


# AccountCategories


class AccountCatListView(LoginRequiredMixin, ListView):
    model = AccountCategory
    context_object_name = 'accountcat_list'

    def get_queryset(self):
        return AccountCategory.view_objects.filter(is_deleted=False).order_by('name')


class AccountCatDetailView(LoginRequiredMixin, DetailView):
    model = AccountCategory

    def get_queryset(self):
        account_categories = AccountCategory.view_objects.filter(is_deleted=False).order_by('name')
        for categorie in account_categories:
            categorie.editable = categorie.can_edit()
        return account_categories


class AccountCatUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = AccountCategory
    template_name = 'budgetdb/generic_form.html'
    form_class = AccountCategoryForm

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs['pk'])
        return view_object.can_edit()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        form.helper.add_input(Submit('delete', 'Delete', css_class='btn-danger'))
        return form


# AccountHost


class AccountHostListView(LoginRequiredMixin, ListView):
    model = AccountHost
    context_object_name = 'account_host_list'

    def get_queryset(self):
        qs = AccountHost.view_objects.filter(is_deleted=False).order_by('name')
        return qs


class AccountHostDetailView(LoginRequiredMixin, DetailView):
    model = AccountHost
    context_object_name = 'accounthost'
    template_name = 'budgetdb/accounthost_detail.html'
    fields = [
            'name',
            ]

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs['pk'])
        return view_object.can_view()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_object(self, queryset=None):
        host = super().get_object(queryset=queryset)
        host.editable = host.can_edit()
        return host


class AccountHostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = AccountHost
    template_name = 'budgetdb/generic_form.html'
    form_class = AccountHostForm

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs['pk'])
        return view_object.can_edit()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = 'Account Host'
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        form.helper.add_input(Submit('delete', 'Delete', css_class='btn-danger'))
        return form


class AccountHostCreateView(LoginRequiredMixin, CreateView):
    model = AccountHost
    template_name = 'budgetdb/generic_form.html'
    form_class = AccountHostForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = 'Account Host'
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        return form


class Cat2DetailView(LoginRequiredMixin, DetailView):
    model = Cat2
    template_name = 'budgetdb/cat2_detail.html'


class CatTypeDetailView(LoginRequiredMixin, DetailView):
    model = CatType
    template_name = 'budgetdb/cattype_detail.html'


class VendorDetailView(LoginRequiredMixin, DetailView):
    model = Vendor
    template_name = 'budgetdb/vendor_detail.html'


class IndexView(LoginRequiredMixin, ListView):
    template_name = 'budgetdb/index.html'
    context_object_name = 'categories_list'

    def get_queryset(self):
        return Cat1.objects.order_by('name')


class Cat1ListView(LoginRequiredMixin, ListView):
    model = Cat1
    context_object_name = 'categories_list'

    def get_queryset(self):
        return Cat1.objects.order_by('name')


class Cat2ListView(LoginRequiredMixin, ListView):
    model = Cat2
    context_object_name = 'categories_list'

    def get_queryset(self):
        return Cat2.objects.order_by('name')


class AccountSummaryView(LoginRequiredMixin, ListView):
    model = Account
    context_object_name = 'account_list'
    template_name = 'budgetdb/account_list_detailed.html'

    def get_queryset(self):
        accountps = AccountPresentation.objects.filter(is_deleted=False)

        for accountp in accountps:
            account = Account.objects.get(id=accountp.id)
            balance = account.balance_by_EOD(datetime.today())
            categories = account.account_categories.filter(is_deleted=False)
            accountp.account_cat = ''
            i = 0
            for category in categories:
                if i:
                    accountp.account_cat += f', '
                accountp.account_cat += category.name
                i += 1
            accountp.balance = balance
        return accountps


class VendorListView(LoginRequiredMixin, ListView):
    model = Vendor
    context_object_name = 'vendor_list'

    def get_queryset(self):
        return Vendor.objects.order_by('name')


class CatTypeListView(LoginRequiredMixin, ListView):
    model = CatType
    context_object_name = 'cattype_list'

    def get_queryset(self):
        return CatType.objects.order_by('name')


class AccountListActivityView(LoginRequiredMixin, ListView):
    model = Account
    template_name = 'budgetdb/AccountListActivityView.html'

    def get_queryset(self):
        pk = self.kwargs['pk']
        preference = Preference.objects.get(pk=self.request.user.id)
        begin = preference.start_interval
        end = preference.end_interval

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
        pk = self.kwargs['pk']
        context['account_list'] = Account.objects.filter(is_deleted=False).order_by('name')
        context['pk'] = pk
        context['account_name'] = Account.objects.get(id=pk).name
        return context


class Cat1CreateView(LoginRequiredMixin, CreateView):
    model = Cat1
    fields = [
        'name',
        'cattype',
        ]

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        return form


class UserSignupView(CreateView):
    model = User
    form_class = UserSignUpForm
    template_name = 'budgetdb/user_form.html'

    def form_valid(self, form):
        user = form.save()
        preference = Preference.objects.create(
            user=user,
            start_interval=datetime.today().date()-relativedelta(months=6),
            end_interval=datetime.today().date()+relativedelta(months=6),
            min_interval_slider=datetime.today().date()-relativedelta(months=6),
            max_interval_slider=datetime.today().date()+relativedelta(months=6)
            )
        preference.save()
        login(self.request, user)
        return redirect('budgetdb:home')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Sign Up!', css_class='btn-primary'))
        return form


class UserLoginView(LoginView):
    model = User
    template_name = 'budgetdb/login.html'

    def form_valid(self, form):
        login(self.request, form.get_user())
        return redirect('budgetdb:home')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # julie = User.objects.get(username='Julie')
        # julie.set_password('letmein')
        # julie.save()
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Log in', css_class='btn-primary'))
        return form


class AccountCatCreateView(LoginRequiredMixin, CreateView):
    model = AccountCategory
    fields = (
        'name',
        'accounts',
        )

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        return form


class CatTypeCreateView(LoginRequiredMixin, CreateView):
    model = CatType
    fields = [
        'name',
        ]

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        return form


class Cat2CreateView(LoginRequiredMixin, CreateView):
    model = Cat2
    fields = [
        'name',
        'cat1',
        'cattype',
        ]

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.layout = Layout(
           Field('cat1', type="hidden"),
           Field('name', type=""),
           Field('cattype', type="")
           )
        cat1_id = self.kwargs['cat1_id']
        cat1 = Cat1.objects.get(id=cat1_id)
        form.initial['cat1'] = cat1
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        return form


class VendorCreateView(LoginRequiredMixin, CreateView):
    model = Vendor
    fields = ['name']

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        return form
