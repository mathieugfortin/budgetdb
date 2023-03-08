# from django_addanother.views import CreatePopupMixin, UpdatePopupMixin
from django.core.exceptions import PermissionDenied
from django import forms
from django.apps import apps
from django.forms import ModelForm
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, View, TemplateView, DetailView, FormView
from django.views.generic.base import RedirectView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import login
from dal import autocomplete
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from budgetdb.models import *
from budgetdb.utils import Calendar
from budgetdb.forms import *
from budgetdb.tables import *
from decimal import *
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Button
from crum import get_current_user
from bootstrap_modal_forms.generic import BSModalCreateView
from django_tables2 import SingleTableView, SingleTableMixin

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
    preference = Preference.objects.get(user=request.user.id)
    if start_interval:
        preference.start_interval = datetime.strptime(start_interval, "%Y-%m-%d")
    if end_interval:
        preference.end_interval = datetime.strptime(end_interval, "%Y-%m-%d")
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
    transactions = Transaction.view_objects.all().order_by("date_actual")

    if (preference.min_interval_slider is None):
        start_slider = transactions.first().date_actual
    else:
        start_slider = preference.min_interval_slider

    if (preference.max_interval_slider is None):
        stop_slider = transactions.last().date_actual
    else:
        stop_slider = preference.max_interval_slider

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
    queryset = Account.view_objects.all().order_by("account_host", "name")

    array = []
    for entry in queryset:
        namestring = entry.account_host.name
        if entry.owner != get_current_user():
            namestring = namestring + " - " + entry.owner.username.capitalize()
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
    cats = Cat1.view_objects.all()

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


def timeline2JSON(request):
    if request.user.is_authenticated is False:
        return JsonResponse({}, status=401)
    accountcategoryID = request.GET.get('ac', None)

    if accountcategoryID is None or accountcategoryID == 'None':
        accounts = Account.view_objects.all().order_by('account_host', 'name')
    else:
        accounts = Account.view_objects.filter(account_categories=accountcategoryID).order_by('account_host', 'name')

    preference = get_object_or_404(Preference, user=request.user.id)
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
        if account.can_view() is False:
            continue
        if account.date_closed is not None:
            if account.date_closed < begin:
                continue
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
        cat_type_pk = self.kwargs.get('cat_type_pk')
        cattype = CatType.view_objects.get(pk=cat_type_pk)
        begin = self.request.GET.get('begin', None)
        end = self.request.GET.get('end', None)
        preference = Preference.objects.get(user=self.request.user.id)

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.model._meta.verbose_name
        context["task"] = self.task
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', self.task, css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Cancel', css_class='btn-secondary',
                              onclick="javascript:history.back();"))
        return form


class MyDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
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
            context["title"] = f'{self.model._meta.verbose_name} List'
        if self.create is True:
            context['add_url'] = reverse(f'budgetdb:create_{self.model._meta.model_name.lower()}')
        else:
            context['add_url'] = None
        context["create"] = self.create
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
            account.balance = account.balance_by_EOD(datetime.today())
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
        preference = get_object_or_404(Preference, id=user.id)
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


class CatTypeUpdateView(MyUpdateView):
    model = CatType
    form_class = CatTypeForm


class CatTypeCreateView(MyCreateView):
    model = CatType
    form_class = CatTypeForm


###################################################################################################################
# Friend


class FriendListView(MyListView):
    model = Friend
    title = 'Pending Invites'
    table_class = FriendListTable

    def get_queryset(self):
        return self.model.view_objects.all().order_by('email')


class FriendCreateView(MyCreateView):
    model = Friend
    form_class = FriendForm


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

    def get_object(self, queryset=None):
        statement = super().get_object(queryset=queryset)
        statement.editable = statement.can_edit()
        statement.included_transactions = Transaction.view_objects.filter(statement=statement).order_by('date_actual')
        transactions_sum = 0
        for transaction in statement.included_transactions:
            transactions_sum += transaction.amount_actual
        statement.transactions_sum = transactions_sum
        statement.error = transactions_sum - statement.balance
        min_date = statement.statement_date - relativedelta(months=2)
        statement.possible_transactions = Transaction.view_objects.filter(account_source=statement.account,
                                                                          date_actual__lte=statement.statement_date,
                                                                          date_actual__gt=min_date,
                                                                          statement__isnull=True,
                                                                          audit=False
                                                                          ).order_by('date_actual')
        transactions_sumP = 0
        for transaction in statement.possible_transactions:
            transactions_sumP += transaction.amount_actual
        statement.transactions_sumP = transactions_sumP
        return statement


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
###################################################################################################################


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = 'budgetdb/index.html'


class AccountTransactionListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
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
        pk = self.kwargs.get('pk')
        preference = Preference.objects.get(user=self.request.user.id)
        year = preference.end_interval.year
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


class AccountTransactionListView2(UserPassesTestMixin, MyListView):
    model = Account
    table_class = AccountActivityListTable
    # template_name = 'budgetdb/AccountTransactionListView.html'

    def test_func(self):
        view_object = get_object_or_404(self.model, pk=self.kwargs.get('pk'), is_deleted=False)
        return view_object.can_view()

    def handle_no_permission(self):
        raise PermissionDenied

    def get_queryset(self):
        pk = self.kwargs.get('pk')
        preference = Preference.objects.get(user=self.request.user.id)
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
        pk = self.kwargs.get('pk')
        preference = Preference.objects.get(user=self.request.user.id)
        year = preference.end_interval.year
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


###################################################################################################################
# User Management

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
        # julie = User.objects.get(username='julie')
        # julie.set_password('etpatatietpatata')
        # julie.save()
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Log in', css_class='btn-primary'))
        return form


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
                start_interval=start,
                end_interval=stop,
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
