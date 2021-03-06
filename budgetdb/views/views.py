from django_addanother.views import CreatePopupMixin, UpdatePopupMixin
from django.forms import ModelForm
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import ListView, CreateView, UpdateView, View, TemplateView, DetailView
from django.urls import reverse, reverse_lazy
from django.utils.safestring import mark_safe
from dal import autocomplete
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from budgetdb.models import Cat1, Transaction, Cat2, BudgetedEvent, Vendor, Account, AccountCategory, MyCalendar, CatSums, CatType, AccountHost, Preference, AccountPresentation
from budgetdb.utils import Calendar
import pytz
from decimal import *
# from chartjs.views.lines import BaseLineChartView
# from chartjs.views.pie import HighChartDonutView, HighChartPieView
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field

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


def PreferenceGetJSON(request):
    preference = Preference.objects.get(pk=request.user.id)
    transactions = Transaction.objects.all().order_by("date_actual")

    data = {
        'start_interval': preference.start_interval,
        'end_interval': preference.end_interval,
        'begin_data': transactions.first().date_actual,
        'end_data': transactions.last().date_actual,
    }

    return JsonResponse(data, safe=False)


def GetAccountListJSON(request):
    queryset = Account.objects.all()
    queryset = queryset.order_by("name")

    array = []

    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetAccountCatListJSON(request):
    queryset = AccountCategory.objects.all()
    queryset = queryset.order_by("name")

    array = []

    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetAccountHostListJSON(request):
    queryset = AccountHost.objects.all()
    queryset = queryset.order_by("name")

    array = []

    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetVendorListJSON(request):
    queryset = Vendor.objects.all()
    queryset = queryset.order_by("name")

    array = []

    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetCat1ListJSON(request):
    queryset = Cat1.objects.all()
    queryset = queryset.order_by("name")

    array = []

    for entry in queryset:
        array.append([{"pk": entry.pk}, {"name": entry.name}])

    return JsonResponse(array, safe=False)


def GetCatTypeListJSON(request):
    queryset = CatType.objects.all()
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
    # dailybalances = AccountBalances.objects.raw(sqlst)
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

    # dailybalances = AccountBalances.objects.raw(sqlst)
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
    cats = Cat1.objects.filter()

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

    cats = Cat2.objects.filter(cat1=cat1)

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
        accounts = Account.objects.all().order_by('name')
    else:
        accounts = Account.objects.filter(account_categories=accountcategoryID).order_by('name')

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

        accountcategories = AccountCategory.objects.all()
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
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Account.objects.none()

        qs = Account.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class AutocompleteCat1(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Cat1.objects.none()

        qs = Cat1.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class AutocompleteCat2(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Cat2.objects.none()

        qs = Cat2.objects.all()
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
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Vendor.objects.none()

        qs = Vendor.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class Cat1DetailView(DetailView):
    model = Cat1
    template_name = 'budgetdb/cat1_detail.html'


class Cat1UpdateView(UpdateView):
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


class Cat2UpdateView(UpdateView):
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


class CatTypeUpdateView(UpdateView):
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


class VendorUpdateView(UpdateView):
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


class AccountUpdateView(UpdateView):
    model = Account
    fields = (
        'name',
        'account_host',
        'account_parent',
        'account_number',
        )

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form


class AccountCatUpdateView(UpdateView):
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
        form.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))
        return form


class AccountHostUpdateView(UpdateView):
    model = AccountHost
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


class Cat2DetailView(DetailView):
    model = Cat2
    template_name = 'budgetdb/cat2_detail.html'


class CatTypeDetailView(DetailView):
    model = CatType
    template_name = 'budgetdb/cattype_detail.html'


class VendorDetailView(DetailView):
    model = Vendor
    template_name = 'budgetdb/vendor_detail.html'


class AccountDetailView(DetailView):
    model = Account
    template_name = 'budgetdb/account_detail.html'


class AccountHostDetailView(DetailView):
    model = AccountHost
    template_name = 'budgetdb/accounthost_detail.html'


class IndexView(ListView):
    template_name = 'budgetdb/index.html'
    context_object_name = 'categories_list'

    def get_queryset(self):
        return Cat1.objects.order_by('name')


class Cat1ListView(ListView):
    model = Cat1
    context_object_name = 'categories_list'

    def get_queryset(self):
        return Cat1.objects.order_by('name')


class Cat2ListView(ListView):
    model = Cat2
    context_object_name = 'categories_list'

    def get_queryset(self):
        return Cat2.objects.order_by('name')


class AccountSummaryView(ListView):
    model = Account
    context_object_name = 'account_list'
    template_name = 'budgetdb/account_list_detailed.html'

    def get_queryset(self):
        accountps = AccountPresentation.objects.all()

        # accounts = Account.objects.filter(account_parent=None).order_by('name')
        for accountp in accountps:
            account = Account.objects.get(id=accountp.id)
            balance = account.balance_by_EOD(datetime.today())
            categories = account.account_categories.all()
            accountp.account_cat = ''
            i = 0
            for category in categories:
                if i:
                    accountp.account_cat += f', '
                accountp.account_cat += category.name
                i += 1
            accountp.balance = balance
        return accountps


class AccountListViewSimple(ListView):
    model = Account
    context_object_name = 'account_list'
    template_name = 'budgetdb/account_list_simple.html'

    def get_queryset(self):
        accounts = Account.objects.all().order_by('name')
        for account in accounts:
            categories = account.account_categories.all()
            account.account_cat = ''
            i = 0
            for category in categories:
                if i:
                    account.account_cat += f', '
                account.account_cat += category.name
                i += 1
        return accounts


class AccountHostListView(ListView):
    model = AccountHost
    context_object_name = 'account_host_list'

    def get_queryset(self):
        return AccountHost.objects.all().order_by('name')


class VendorListView(ListView):
    model = Vendor
    context_object_name = 'vendor_list'

    def get_queryset(self):
        return Vendor.objects.order_by('name')


class CatTypeListView(ListView):
    model = CatType
    context_object_name = 'cattype_list'

    def get_queryset(self):
        return CatType.objects.order_by('name')


class AccountCatListView(ListView):
    model = AccountCategory
    context_object_name = 'accountcat_list'

    def get_queryset(self):
        return AccountCategory.objects.order_by('name')


class AccountperiodicView(ListView):
    model = Account
    template_name = 'budgetdb/AccountperiodicView.html'

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
        # beginstr = self.request.GET.get('begin', None)
        # endstr = self.request.GET.get('end', None)
        # preference = Preference.objects.get(pk=self.request.user.id)
        # if endstr is not None and endstr != 'None':
        #    end = datetime.strptime(endstr, "%Y-%m-%d")
        # else:
        #    end = preference.end_interval

        # if beginstr is not None and beginstr != 'None':
        #    begin = datetime.strptime(beginstr, "%Y-%m-%d")
        # else:
        #    begin = preference.start_interval

        context['account_list'] = Account.objects.all().order_by('name')
        # context['begin'] = begin.strftime("%Y-%m-%d")
        # context['end'] = end.strftime("%Y-%m-%d")
        context['pk'] = pk
        # context['now'] = date.today().strftime("%Y-%m-%d")
        # context['month'] = (date.today() + relativedelta(months=-1)).strftime("%Y-%m-%d")
        # context['3month'] = (date.today() + relativedelta(months=-3)).strftime("%Y-%m-%d")
        context['account_name'] = Account.objects.get(id=pk).name
        return context


class Cat1CreateView(CreateView):
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
        return form


class AccountCreateView(CreateView):
    model = Account
    fields = [
        'name',
        'account_host',
        'account_parent',
        'account_number']

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        return form


class AccountCatCreateView(CreateView):
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
        return form


class AccountHostCreateView(CreateView):
    model = AccountHost
    fields = ['name']

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        return form


class CatTypeCreate(CreateView):
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
        return form


class Cat2Create(CreateView):
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
           Field('name', type="")
           )
        cat1_id = self.kwargs['cat1_id']
        cat1 = Cat1.objects.get(id=cat1_id)
        form.initial['cat1'] = cat1
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        return form


class VendorCreate(CreatePopupMixin, CreateView):
    model = Vendor
    fields = ['name']

    def form_valid(self, form):
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.form_method = 'POST'
        form.helper.add_input(Submit('submit', 'Create', css_class='btn-primary'))
        return form
