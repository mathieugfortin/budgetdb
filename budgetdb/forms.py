from django import forms
from django.shortcuts import get_object_or_404
from .models import User, Preference
from .models import Account, AccountCategory, AccountHost, Cat1, Cat2, CatBudget, CatType, Vendor, Statement
from .models import BudgetedEvent, Transaction, JoinedTransactions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Field, Fieldset, ButtonHolder, Div, LayoutObject, TEMPLATE_PACK, HTML, Hidden, Row, Column
from django.template.loader import render_to_string
from crispy_forms.bootstrap import AppendedText, PrependedText
from django.forms.models import modelformset_factory, inlineformset_factory, formset_factory
from datetime import datetime, date
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from crum import get_current_user
from bootstrap_modal_forms.forms import BSModalModelForm


class UserSignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email')


class UserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'email')


class Formset(LayoutObject):
    """
    Renders an entire formset, as though it were a Field.
    Accepts the names (as a string) of formset and helper as they
    are defined in the context

    Examples:
        Formset('contact_formset')
        Formset('contact_formset', 'contact_formset_helper')
    """

    template = "budgetdb/formset.html"

    def __init__(self, formset_context_name, helper_context_name=None,
                 template=None, label=None):

        self.formset_context_name = formset_context_name
        self.helper_context_name = helper_context_name

        # crispy_forms/layout.py:302 requires us to have a fields property
        self.fields = []

        # Overrides class variable with an instance level variable
        if template:
            self.template = template

    def render(self, form, form_style, context, **kwargs):
        formset = context.get(self.formset_context_name)
        helper = context.get(self.helper_context_name)
        # closes form prematurely if this isn't explicitly stated
        if helper:
            helper.form_tag = False

        context.update({'formset': formset, 'helper': helper})
        return render_to_string(self.template, context.flatten())


class DateInput(forms.DateInput):
    input_type = 'date'


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = (
            'name',
            'account_host',
            'account_parent',
            'account_number',
            'comment',
            'TFSA',
            'RRSP',
            'currency',
            'users_admin',
            'users_view',
            'date_open',
            'date_closed'
            )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        friends_ids = get_current_user().friends.values('id')
        self.helper = FormHelper()
        self.fields["users_admin"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_admin"].queryset = User.objects.filter(id__in=friends_ids,)
        self.fields["users_view"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_view"].queryset = User.objects.filter(id__in=friends_ids,)
        self.fields["account_host"].queryset = AccountHost.view_objects.all()
        self.fields["account_parent"].queryset = Account.view_objects.all()
        user = get_current_user()
        self.fields['currency'].queryset = Preference.objects.get(pk=user.id).currencies
        self.helper.layout = Layout(
            Div(
                Div('name', css_class='form-group col-md-4  '),
                Div('account_number', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div(
                Div('date_open', css_class='form-group col-md-4  '),
                Div('date_closed', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div('comment', css_class='form-group col-md-6  '),
            Div('currency', css_class='form-group col-md-4  '),
            Div(
                Div('account_host', css_class='form-group col-md-4  '),
                Div('account_parent', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div(
                Div('TFSA', css_class='form-group col-md-4  '),
                Div('RRSP', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4  '),
                Div('users_view', css_class='form-group col-md-4  '),
                css_class='row'
            ),
        )


class AccountHostForm(forms.ModelForm):
    class Meta:
        model = AccountHost
        fields = (
            'name',
            'users_admin',
            'users_view',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        friends_ids = get_current_user().friends.values('id')
        self.helper = FormHelper()
        self.helper.form_id = 'AccountHostForm'
        self.fields["users_admin"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_admin"].queryset = User.objects.filter(id__in=friends_ids,)
        self.fields["users_view"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_view"].queryset = User.objects.filter(id__in=friends_ids,)
        self.helper.layout = Layout(
            Div(
                Div('name', css_class='form-group col-md-6  '),
                css_class='row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4  '),
                Div('users_view', css_class='form-group col-md-4  '),
                css_class='row'
            ),
        )


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = (
            'name',
            'users_admin',
            'users_view',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        friends_ids = get_current_user().friends.values('id')
        self.helper = FormHelper()
        self.helper.form_id = 'AccountHostForm'
        self.fields["users_admin"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_admin"].queryset = User.objects.filter(id__in=friends_ids,)
        self.fields["users_view"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_view"].queryset = User.objects.filter(id__in=friends_ids,)
        self.helper.layout = Layout(
            Div(
                Div('name', css_class='form-group col-md-6  '),
                css_class='row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4  '),
                Div('users_view', css_class='form-group col-md-4  '),
                css_class='row'
            ),
        )


class StatementForm(forms.ModelForm):
    class Meta:
        model = Statement
        fields = (
                'account',
                'statement_date',
                'balance',
                'minimum_payment',
                'statement_due_date',
                'comment',
                'payment_transaction',
                'users_admin',
                'users_view',
            )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        friends_ids = get_current_user().friends.values('id')
        self.helper = FormHelper()
        self.helper.form_id = 'AccountHostForm'

        if 'account' in self.data:
            try:
                account_id = int(self.data.get('account'))
                self.fields['payment_transaction'].queryset = Transaction.admin_objects.filter(account_destination=account_id,).order_by('date_actual')
            except (ValueError, TypeError):
                self.fields['payment_transaction'].queryset = Transaction.objects.none()
        elif 'cat1' in self.initial:
            try:
                account_id = int(self.initial.get('account'))
                self.fields['payment_transaction'].queryset = Transaction.admin_objects.filter(account_destination=account_id,).order_by('date_actual')
            except (ValueError, TypeError):
                self.fields['payment_transaction'].queryset = Transaction.objects.none()
        else:
            self.fields['payment_transaction'].queryset = Transaction.objects.none()

        self.fields["users_admin"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_admin"].queryset = User.objects.filter(id__in=friends_ids,)
        self.fields["users_view"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_view"].queryset = User.objects.filter(id__in=friends_ids,)
        self.helper.layout = Layout(
            Div(
                Div('account', css_class='form-group col-md-6  '),
                css_class='row'
            ),
            Div(
                Div('statement_date', css_class='form-group col-md-4'),
                Div('balance', css_class='form-group col-md-2'),
                Div('minimum_payment', css_class='form-group col-md-2 '),
                Div('statement_due_date', css_class='form-group col-md-4 '),
                css_class='row'
            ),
            Div(
                Div('comment', css_class='form-group col-md-6  '),
                css_class='row'
            ),
            Div(
                Div('payment_transaction', css_class='form-group col-md-6  '),
                css_class='row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4  '),
                Div('users_view', css_class='form-group col-md-4  '),
                css_class='row'
            ),
        )


class CatTypeForm(forms.ModelForm):
    class Meta:
        model = CatType
        fields = (
            'name',
            'users_admin',
            'users_view',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        friends_ids = get_current_user().friends.values('id')
        self.helper = FormHelper()
        self.helper.form_id = 'AccountHostForm'
        self.fields["users_admin"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_admin"].queryset = User.objects.filter(id__in=friends_ids,)
        self.fields["users_view"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_view"].queryset = User.objects.filter(id__in=friends_ids,)
        self.helper.layout = Layout(
            Div(
                Div('name', css_class='form-group col-md-6  '),
                css_class='row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4  '),
                Div('users_view', css_class='form-group col-md-4  '),
                css_class='row'
            ),
        )


class AccountCategoryForm(forms.ModelForm):
    class Meta:
        model = AccountCategory
        fields = (
            'name',
            'users_admin',
            'users_view',
            'accounts',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        friends_ids = get_current_user().friends.values('id')
        self.helper = FormHelper()
        self.helper.form_id = 'AccountHostForm'
        self.fields["users_admin"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_admin"].queryset = User.objects.filter(id__in=friends_ids,)
        self.fields["users_view"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_view"].queryset = User.objects.filter(id__in=friends_ids,)
        self.fields["accounts"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["accounts"].queryset = Account.view_objects.all()
        self.helper.layout = Layout(
            Div(
                Div('name', css_class='form-group col-md-6  '),
                css_class='row'
            ),
            Div(
                Div('accounts', css_class='form-group col-md-10  '),
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4  '),
                Div('users_view', css_class='form-group col-md-4  '),
                css_class='row'
            ),
        )


class RecurringBitmaps(forms.Form):
    weekdays = [(1, 'Monday'), (2, 'Tuesday'), (4, 'Wednesday'), (8, 'Thursday'), (16, 'Friday'), (32, 'Saturday')]
    weeks = [(1, '1'), (2, '2'), (4, '3'), (8, '4'), (16, '5')]
    months = [(1, 'January'), (2, 'February'), (4, 'March'), (8, 'April'), (16, 'May'), (32, 'June'), (64, 'July'), (128, 'August'), (256, 'September'), (512, 'October'), (1024, 'November'), (2048, 'December')]
    days = [(1, '1'), (2, '2'), (4, '3'), (8, '4'), (16, '5'), (32, '6'), (64, '7'), (128, '8'),
            (256, '9'), (512, '10'), (1024, '11'), (2048, '12'), (4096, '13'), (8192, '14'), (2**14, '15'),
            (2**15, '16'), (2**16, '17'), (2**17, '18'), (2**18, '19'), (2**19, '20'), (2**20, '21'), (2**21, '22'),
            (2**22, '23'), (2**23, '24'), (2**24, '25'), (2**25, '26'), (2**26, '27'), (2**27, '28'), (2**28, '29'),
            (2**29, '30'), (2**30, '31')
            ]
    daysOfWeek = forms.MultipleChoiceField(required=False, initial=[1, 2, 4, 8, 16, 32],
                                           widget=forms.CheckboxSelectMultiple,
                                           choices=weekdays,
                                           label="Days of the week"
                                           )
    monthsOfYear = forms.MultipleChoiceField(required=False, initial=[1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048],
                                             widget=forms.CheckboxSelectMultiple,
                                             choices=months,
                                             label="Months"
                                             )
    weeksOfMonth = forms.MultipleChoiceField(required=False, initial=[1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048],
                                             widget=forms.CheckboxSelectMultiple,
                                             choices=weeks,
                                             label="Weeks of month"
                                             )
    daysOfMonth = forms.MultipleChoiceField(required=False, initial=[1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 2**12,
                                                                     2**13, 2**14, 2**15, 2**16, 2**17, 2**18, 2**19, 2**20,
                                                                     2**21, 2**22, 2**23, 2**24, 2**25, 2**26, 2**27, 2**28,
                                                                     2**29, 2**30, 2**31
                                                                     ],
                                            widget=forms.CheckboxSelectMultiple,
                                            choices=days,
                                            label="Days"
                                            )


class JoinedTransactionConfigForm(forms.ModelForm):
    pass


class BudgetedEventForm(forms.ModelForm, RecurringBitmaps):
    class Meta:
        model = BudgetedEvent
        # fields = ('__all__')
        fields = (
            'description',
            'amount_planned',
            'cat1',
            'cat2',
            'ismanual',
            'repeat_start',
            'repeat_stop',
            'vendor',
            'account_source',
            'account_destination',
            'budget_only',
            'isrecurring',
            'repeat_interval_days',
            'repeat_interval_weeks',
            'repeat_interval_months',
            'repeat_interval_years',
            'users_admin',
            'users_view',
            'repeat_months_mask',
            'repeat_dayofmonth_mask',
            'repeat_weekofmonth_mask',
            'repeat_weekday_mask',
        )

        widgets = {
            'repeat_start': forms.widgets.DateInput(attrs={'type': 'date'}),
            'repeat_stop': forms.widgets.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        friends_ids = get_current_user().friends.values('id')
        self.helper = FormHelper()
        self.helper.form_id = 'BudgetedEventForm'
        self.fields['cat1'].queryset = Cat1.admin_objects.filter(is_deleted=False)
        if 'cat1' in self.data:
            try:
                cat1 = int(self.data.get('cat1'))
                self.fields['cat2'].queryset = Cat2.admin_objects.filter(cat1=cat1, is_deleted=False)
            except (ValueError, TypeError):
                self.fields['cat2'].queryset = Cat2.objects.none()
        elif 'cat1' in self.initial:
            try:
                cat1 = int(self.initial.get('cat1'))
                self.fields['cat2'].queryset = Cat2.admin_objects.filter(cat1=cat1, is_deleted=False)
            except (ValueError, TypeError):
                self.fields['cat2'].queryset = Cat2.objects.none()
        else:
            self.fields['cat2'].queryset = Cat2.objects.none()

        self.fields['cat1'].queryset = Cat1.admin_objects.filter(is_deleted=False)
        self.fields['account_source'].queryset = Account.admin_objects.filter(is_deleted=False)
        self.fields['account_destination'].queryset = Account.admin_objects.filter(is_deleted=False)
        self.fields['vendor'].queryset = Vendor.admin_objects.filter(is_deleted=False)
        self.fields["users_admin"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_admin"].queryset = User.objects.filter(id__in=friends_ids,)
        self.fields["users_view"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_view"].queryset = User.objects.filter(id__in=friends_ids,)
        if 'repeat_weekday_mask' in self.initial:
            map = []
            for i in range(7):
                if int(self.initial.get('repeat_weekday_mask')) & 2**i > 0:
                    map.append(2**i)
            self.fields["daysOfWeek"].initial = map
            map = []
            for i in range(12):
                if int(self.initial.get('repeat_months_mask')) & 2**i > 0:
                    map.append(2**i)
            self.fields["monthsOfYear"].initial = map
            map = []
            for i in range(31):
                if int(self.initial.get('repeat_dayofmonth_mask')) & 2**i > 0:
                    map.append(2**i)
            self.fields["daysOfMonth"].initial = map
            map = []
            for i in range(5):
                if int(self.initial.get('repeat_weekofmonth_mask')) & 2**i > 0:
                    map.append(2**i)
            self.fields["weeksOfMonth"].initial = map
        full = True
        if kwargs['instance'] is not None:
            if kwargs['instance'].budgeted_events is not None:
                if kwargs['instance'].budgeted_events.first() is not None:
                    full = False
        if full:
            self.helper.layout = Layout(
                Div(
                    Div('description', css_class='form-group col-md-6  '),
                    Div('vendor', css_class='form-group col-md-4  '),
                    css_class='row'
                ),
                Div(
                    Div('cat1', css_class='form-group col-md-6  '),
                    Div('cat2', css_class='form-group col-md-6  '),
                    css_class='row'
                ),
                Div(
                    # Div('amount_planned', css_class='form-group col-md-4  '),
                    Div(PrependedText('amount_planned', '$', css_class='form-group col-md-4  ')),
                    css_class='row'
                ),
                Div(
                    Div('account_source', css_class='form-group col-md-6  '),
                    Div('account_destination', css_class='form-group col-md-6  '),
                    css_class='row'
                ),
                Div(
                    Div('budget_only', css_class='form-group col-md-4  '),
                    Div('ismanual', css_class='form-group col-md-4  '),
                    Field('isrecurring', css_class='form-group col-md-4  ', type="hidden"),
                    # css_class='row'
                ),
                Div(
                    Div('repeat_start', css_class='form-group col-md-4  '),
                    Div('repeat_stop', css_class='form-group col-md-4  '),
                    css_class='row'
                ),
                Div(
                    Div('repeat_interval_days', css_class='form-group col-md-2  '),
                    Div('repeat_interval_weeks', css_class='form-group col-md-2  '),
                    Div('repeat_interval_months', css_class='form-group col-md-2  '),
                    Div('repeat_interval_years', css_class='form-group col-md-2  '),
                    Field('repeat_weekday_mask', css_class='form-group col-md-2  ', type="hidden"),
                    Field('repeat_months_mask', css_class='form-group col-md-2  ', type="hidden"),
                    Field('repeat_dayofmonth_mask', css_class='form-group col-md-2  ', type="hidden"),
                    Field('repeat_weekofmonth_mask', css_class='form-group col-md-2  ', type="hidden"),
                    css_class='row'
                ),
                Div(
                    Div('users_admin', css_class='form-group col-md-4  '),
                    Div('users_view', css_class='form-group col-md-4  '),
                    css_class='row'
                ),
                HTML("<h4>Recurrence mask</h4>"),
                Div(
                    Div('daysOfWeek', css_class='form-group col-md-2  '),
                    Div('weeksOfMonth', css_class='form-group col-md-2  '),
                    Div('monthsOfYear', css_class='form-group col-md-2  '),
                    Div('daysOfMonth', css_class='form-group col-md-2  '),
                    css_class='row'
                ),
             )
        else:
            self.helper.layout = Layout(
                Div(
                    Div('description', css_class='form-group col-md-6  '),
                    Div('vendor', css_class='form-group col-md-4  '),
                    css_class='row'
                ),
                Div(
                    Div('cat1', css_class='form-group col-md-4  '),
                    Div('cat2', css_class='form-group col-md-4  '),
                    css_class='row'
                ),
                Div(
                    # Div('amount_planned', css_class='form-group col-md-4  '),
                    Div(PrependedText('amount_planned', '$', css_class='form-group col-sm-6    ')),
                    css_class='row'
                ),
                Div(
                    Div('account_source', css_class='form-group col-md-4  '),
                    Div('account_destination', css_class='form-group col-md-4  '),
                    css_class='row'
                ),
                Div(
                    Div('budget_only', css_class='form-group col-md-4  '),
                    Div('ismanual', css_class='form-group col-md-4  '),
                    # css_class='row'
                ),
                Div(
                    Field('repeat_interval_days', css_class='form-group col-md-2  ', type="hidden"),
                    Field('repeat_interval_weeks', css_class='form-group col-md-2  ', type="hidden"),
                    Field('repeat_interval_months', css_class='form-group col-md-2  ', type="hidden"),
                    Field('repeat_interval_years', css_class='form-group col-md-2  ', type="hidden"),
                    Field('isrecurring', css_class='form-group col-md-4  ', type="hidden"),
                    Field('repeat_start', css_class='form-group col-md-4  ', type="hidden"),
                    Field('repeat_stop', css_class='form-group col-md-4  ', type="hidden"),
                    Field('repeat_weekday_mask', css_class='form-group col-md-2  ', type="hidden"),
                    Field('repeat_months_mask', css_class='form-group col-md-2  ', type="hidden"),
                    Field('repeat_dayofmonth_mask', css_class='form-group col-md-2  ', type="hidden"),
                    Field('repeat_weekofmonth_mask', css_class='form-group col-md-2  ', type="hidden"),
                    css_class='row'
                ),
                Div(
                    Div('users_admin', css_class='form-group col-md-4  '),
                    Div('users_view', css_class='form-group col-md-4  '),
                    css_class='row'
                ),
                Div(
                    HTML("<h3><i class='fas fa-exclamation-triangle'></i>This event is part of a Joint Transaction.</h3> <h3>If you want to modify the recurrence, do it through the joint transaction</h3>"),
                    css_class='row'
                ),
            )


class Cat1Form(forms.ModelForm):
    class Meta:
        model = Cat1
        fields = (
            'name',
            'catbudget',
            'cattype',
            'users_admin',
            'users_view',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        friends_ids = get_current_user().friends.values('id')
        self.fields['cattype'].queryset = CatType.admin_objects.filter(is_deleted=False)
        self.fields['catbudget'].queryset = CatBudget.admin_objects.filter(is_deleted=False)
        self.helper = FormHelper()
        self.helper.form_id = 'Cat1Form'
        self.fields["users_admin"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_admin"].queryset = User.objects.filter(id__in=friends_ids,)
        self.fields["users_view"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_view"].queryset = User.objects.filter(id__in=friends_ids,)
        self.helper.layout = Layout(
            Div(
                Div('name', css_class='form-group col-md-6  '),
                css_class='row'
            ),
            Div(
                Div('cattype', css_class='form-group col-md-4  '),
                Div('catbudget', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4  '),
                Div('users_view', css_class='form-group col-md-4  '),
                css_class='row'
            ),
        )


class Cat2Form(forms.ModelForm):
    class Meta:
        model = Cat2
        fields = (
            'name',
            'catbudget',
            'cattype',
            'cat1',
            'users_admin',
            'users_view',
        )

    def __init__(self, *args, **kwargs):
        cat1_id = kwargs.pop('cat1_id', None)
        super().__init__(*args, **kwargs)
        friends_ids = get_current_user().friends.values('id')
        if cat1_id:
            cat1 = get_object_or_404(Cat1, pk=cat1_id)
            if cat1.can_edit():
                self.fields['cat1'].initial = cat1
        self.fields['cattype'].queryset = CatType.admin_objects.filter(is_deleted=False)
        self.fields['catbudget'].queryset = CatBudget.admin_objects.filter(is_deleted=False)
        self.helper = FormHelper()
        self.helper.form_id = 'Cat1Form'
        self.fields["users_admin"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_admin"].queryset = User.objects.filter(id__in=friends_ids,)
        self.fields["users_view"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_view"].queryset = User.objects.filter(id__in=friends_ids,)
        self.helper.layout = Layout(
            Field('cat1', type="hidden"),  # feels like allowing to modify this is a bad idea...
            Div(
                Div('name', css_class='form-group col-md-6  '),
                css_class='row'
            ),
            Div(
                Div('cattype', css_class='form-group col-md-4  '),
                Div('catbudget', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4  '),
                Div('users_view', css_class='form-group col-md-4  '),
                css_class='row'
            ),
        )


class JoinedTransactionsForm(forms.ModelForm):
    class Meta:
        model = JoinedTransactions
        fields = [
            'name',
        ]
        widgets = {
            'common_date': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'type': 'date'}
            ),
        }
    common_date = forms.DateField(required=True)

    def save(self):
        return super().save(self)

    def __init__(self, *args, **kwargs):
        pk = kwargs.pop('pk', None)
        datep = kwargs.pop('datep', None)
        datea = kwargs.pop('datea', None)
        if not datea:
            datea = datep
        super(JoinedTransactionsForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = True
        self.fields['common_date'].label = "Date of the transactions"
        self.fields['common_date'].initial = datea
        self.helper.layout = Layout(
            Hidden('name', self.initial.get('name')),
            # Field('common_date'),
            HTML("Date of the transactions"),
            Div('common_date', css_class='form-group col-md-4  '),
            # Field('name'),
            HTML("<table class='table table-hover table-sm '><tr>"),
            HTML("<th scope='col'>Description</th>"),
            # HTML("<th scope='col'>Category</th>"),
            # HTML("<th scope='col'>Subcategory</th>"),
            # HTML("<th scope='col'>Source</th>"),
            # HTML("<th scope='col'>Destination</th>"),
            HTML("<th scope='col'>Verified</th>"),
            HTML("<th scope='col'>Receipt</th>"),
            HTML("<th scope='col'>Deleted</th>"),
            HTML("<th scope='col'>Amount</th>"),
            HTML("</tr>"),
            # Fieldset('', Formset('formset', helper_context_name='helper')),
            Formset('formset', helper_context_name='helper'),
            HTML("</table>"),
        )


class TransactionFormFull(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'description',
            'vendor',
            'amount_actual',
            'currency',
            # 'date_planned',
            'cat1',
            'cat2',
            'account_source',
            'account_destination',
            'statement',
            'verified',
            'receipt',
            'Fuel_L',
            'Fuel_price',
            'date_actual',
            'budgetedevent',
            'amount_actual_foreign_currency',
            'audit',
            'ismanual',
            'is_deleted',
            'comment',
        ]
        widgets = {
            'date_actual': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'date_planned': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'type': 'date'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        user = get_current_user()

        self.fields['cat1'].queryset = Cat1.admin_objects.filter(is_deleted=False)
        self.fields['currency'].queryset = Preference.objects.get(pk=user.id).currencies

        if 'cat1' in self.data:
            try:
                cat1 = int(self.data.get('cat1'))
                self.fields['cat2'].queryset = Cat2.admin_objects.filter(cat1=cat1, is_deleted=False)
            except (ValueError, TypeError):
                self.fields['cat2'].queryset = Cat2.objects.none()
        elif 'cat1' in self.initial:
            try:
                cat1 = int(self.initial.get('cat1'))
                self.fields['cat2'].queryset = Cat2.admin_objects.filter(cat1=cat1, is_deleted=False)
            except (ValueError, TypeError):
                self.fields['cat2'].queryset = Cat2.objects.none()
        else:
            self.fields['cat2'].queryset = Cat2.objects.none()
            self.fields['currency'].initial = Preference.objects.get(pk=user.id).currency_prefered
            self.fields['currency'].data = Preference.objects.get(pk=user.id).currency_prefered

        # doublon? self.fields['cat1'].queryset = Cat1.admin_objects.filter(is_deleted=False)
        self.fields['account_source'].queryset = Account.admin_objects.filter(is_deleted=False)
        self.fields['account_destination'].queryset = Account.admin_objects.filter(is_deleted=False)
        self.fields['statement'].queryset = Statement.admin_objects.filter(is_deleted=False)
        self.fields['vendor'].queryset = Vendor.admin_objects.filter(is_deleted=False)
        self.fields['budgetedevent'].queryset = BudgetedEvent.admin_objects.filter(is_deleted=False)

        self.fields['cat1'].label = "Category"
        self.fields['cat2'].label = "Sub-Category"
        self.fields['amount_actual'].label = "Amount"

        self.helper.layout = Layout(
            Field('description'),
            Div(
                Div(PrependedText('amount_actual', '$', css_class='form-group col-sm-6    ')),
                Div('amount_actual_foreign_currency', css_class='form-group col-md-4  '),
                Div('currency', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div( 
                Div(AppendedText('Fuel_L', 'L', css_class='form-group col-sm-6   mr-0  ')),
                Div(AppendedText('Fuel_price', '$/L', css_class='form-group col-sm-6  ')),
                css_class='row'
            ),
            Div(
                Div('date_actual', css_class='form-group col-md-4  '),
                # Div('date_planned', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div(
                Div('cat1', css_class='form-group col-md-4  '),
                Div('cat2', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div(
                Div('account_source', css_class='form-group col-md-4  '),
                Div('account_destination', css_class='form-group col-md-4   '),
                css_class='row'
            ),
            Div(
                Div('verified', css_class='form-group col-md-4  '),
                Div('receipt', css_class='form-group col-md-4   '),
                Div('is_deleted', css_class='form-group col-md-4   '),
                css_class='row'
            ),
            Div(
                Div('audit', css_class='form-group col-md-4  '),
                Div('ismanual', css_class='form-group col-md-8   '),
                css_class='row'
            ),
            Field('comment'),
            Div(
                Div('budgetedevent', css_class='form-group col-md-4  '),
                Div('vendor', css_class='form-group col-md-4  '),
                Div('statement', css_class='form-group col-md-4   '),
                css_class='row'
            ),
        )


class TransactionAuditFormFull(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'description',
            'vendor',
            'amount_actual',
            'date_planned',
            'cat1',
            'cat2',
            'account_source',
            'account_destination',
            'statement',
            'currency',
            'amount_actual_foreign_currency',
            'verified',
            'receipt',
            'Fuel_L',
            'Fuel_price',
            'date_actual',
            'budgetedevent',
            'audit',
            'ismanual',
            'is_deleted',
            'comment',
        ]
        widgets = {
            'date_actual': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'placeholder': 'Select a date', 'type': 'date'}
            ),
            'date_planned': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'placeholder': 'Select a date', 'type': 'date'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.fields['account_source'].queryset = Account.admin_objects.filter(is_deleted=False)
        self.fields['statement'].queryset = Statement.admin_objects.filter(is_deleted=False)
        self.fields['vendor'].queryset = Vendor.admin_objects.filter(is_deleted=False)

        self.fields['amount_actual'].label = f"Audited Value"
        self.fields['date_actual'].label = f"Audited Date"
        self.fields['account_source'].label = f"Audited Account"
        self.helper.layout = Layout(
            Field('description'),
            Div(
                Div(PrependedText('amount_actual', '$', css_class='active form-group col-sm-6    ')),
                Div('date_actual', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div(
                Div('account_source', css_class='form-group col-md-6  '),
                css_class='row'
            ),
            Div(
                Div('is_deleted', css_class='form-group col-md-4   '),
                css_class='row'
            ),
            Div(
                Field('audit', type="hidden"),
                Field('currency', type='hidden'),
                Field('amount_actual_foreign_currency', type='hidden'),
                css_class='row'
            ),
            Field('comment'),
        )


class PreferenceForm(forms.ModelForm):
    class Meta:
        model = Preference
        fields = '__all__'
        widgets = {
            'start_interval': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'placeholder': 'Select a date', 'type': 'date'}
            ),
            'end_interval': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'placeholder': 'Select a date', 'type': 'date'}
            ),
            'max_interval_slider': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'placeholder': 'Select a date', 'type': 'date'}
            ),
            'min_interval_slider': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'placeholder': 'Select a date', 'type': 'date'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div('start_interval', css_class='form-group col-md-4  '),
                Div('end_interval', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div(
                Div('min_interval_slider', css_class='form-group col-md-4  '),
                Div('min_interval_slider', css_class='form-group col-md-4  '),
                css_class='row'
            ),
        )


class TransactionFormShort(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'id',
            'description',
            'cat1',
            'cat2',
            'account_source',
            'account_destination',
            # 'amount_planned',
            'amount_actual',
            'verified',
            'date_actual',
            'budgetedevent',
            'receipt'
        ]
        widgets = {
            'date_actual': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'placeholder': 'Select a date', 'type': 'date'}
            ),
            'date_planned': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'placeholder': 'Select a date', 'type': 'date'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'cat1' in self.initial:
            try:
                cat1 = int(self.initial.get('cat1'))
                self.fields['cat2'].queryset = Cat2.admin_objects.filter(cat1=cat1, is_deleted=False)
            except (ValueError, TypeError):
                self.fields['cat2'].queryset = Cat2.objects.none()
        else:
            self.fields['cat2'].queryset = Cat2.objects.none()
        self.fields['cat1'].queryset = Cat1.admin_objects.filter(is_deleted=False)
        self.fields['account_source'].queryset = Account.admin_objects.filter(is_deleted=False)
        self.fields['account_destination'].queryset = Account.admin_objects.filter(is_deleted=False)
        self.fields['budgetedevent'].queryset = BudgetedEvent.admin_objects.filter(is_deleted=False)

        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Field('id', css_class='form-group col-md-1', type='hidden'),
                Div('description', css_class='form-group col-md-2'),
                Div('cat1', css_class='form-group col-md-1'),
                Div('cat2', css_class='form-group col-md-2'),
                Div('account_source', css_class='form-group col-md-1'),
                Div('account_destination', css_class='form-group col-md-1'),
                Div('verified', css_class='form-group col-md-1'),
                Div('receipt', css_class='form-group col-md-1'),
                Div(PrependedText('amount_actual', '$'), css_class='form-group col-md-1'),
                Field('date_actual', css_class='form-group col-md-2  ', type='hidden'),
                # Div('amount_actual', css_class='form-group col-md-1'),
                Field('budgetedevent', css_class='form-group col-md-1', type='hidden'),
                # HTML('<a href="{% url 'budgetdb:update_be' event.budgetedevent_id %}"> <i class="fas fa-calendar"></i></a>'),
                css_class='row'
            ),
        )
        pass


TransactionFormSet = modelformset_factory(
    Transaction,
    form=TransactionFormShort,
    fields=[
            'id',
            'description',
            'cat1',
            'cat2',
            'account_source',
            'account_destination',
            'amount_planned',
            'amount_actual',
            'verified',
            'date_actual',
            'budgetedevent',
            'is_deleted',
            'receipt',
        ],
    extra=0,
    )


class TransactionModalForm(BSModalModelForm):
    class Meta:
        model = Transaction
        fields = [
            'description',
            'vendor',
            'amount_actual',
            'currency',
            # 'date_planned',
            'cat1',
            'cat2',
            'currency',
            'account_source',
            'account_destination',
            'statement',
            'verified',
            'receipt',
            'Fuel_L',
            'Fuel_price',
            'date_actual',
            'budgetedevent',
            'amount_actual_foreign_currency',
            'audit',
            'ismanual',
            'is_deleted',
            'comment',
        ]
        widgets = {
            'date_actual': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'placeholder': 'Select a date', 'type': 'date'}
            ),
            'date_planned': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'placeholder': 'Select a date', 'type': 'date'}
            ),
        }

    def __init__(self, *args, **kwargs):
        audit_view = kwargs.pop('audit', False)
        task = kwargs.pop('task', 'Update')
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['cat1'].queryset = Cat1.admin_objects.filter(is_deleted=False)
        currency_symbol = ''
        if audit_view is True:
            self.fields['amount_actual'].widget.attrs.update({'autofocus': True})
        else:
            self.fields['description'].widget.attrs.update({'autofocus': True})
        if 'cat1' in self.data:
            try:
                cat1 = int(self.data.get('cat1'))
                # currency_symbol = self.data.get('cat1')
                self.fields['cat2'].queryset = Cat2.admin_objects.filter(cat1=cat1, is_deleted=False)
            except (ValueError, TypeError):
                self.fields['cat2'].queryset = Cat2.objects.none()
        elif 'cat1' in self.initial:
            try:
                cat1 = int(self.initial.get('cat1'))
                self.fields['cat2'].queryset = Cat2.admin_objects.filter(cat1=cat1, is_deleted=False)
            except (ValueError, TypeError):
                self.fields['cat2'].queryset = Cat2.objects.none()
        else:
            self.fields['cat2'].queryset = Cat2.objects.none()

        # doublon? self.fields['cat1'].queryset = Cat1.admin_objects.filter(is_deleted=False)
        self.fields['account_source'].queryset = Account.admin_objects.filter(is_deleted=False)
        self.fields['account_destination'].queryset = Account.admin_objects.filter(is_deleted=False)
        self.fields['statement'].queryset = Statement.admin_objects.filter(is_deleted=False)
        self.fields['vendor'].queryset = Vendor.admin_objects.filter(is_deleted=False)
        self.fields['currency'].queryset = Preference.objects.get(pk=user.id).currencies
        self.fields['budgetedevent'].queryset = BudgetedEvent.admin_objects.filter(is_deleted=False)

        self.fields['cat1'].label = "Category"
        self.fields['cat2'].label = "Sub-Category"
        self.fields['amount_actual'].label = "Amount"
        allowRecurringPatternUpdate = True
        if kwargs['instance'] is not None:
            if kwargs['instance'].transactions is not None:
                if kwargs['instance'].transactions.first() is not None:
                    allowRecurringPatternUpdate = False
            if kwargs['instance'].budgetedevent is not None:
                if kwargs['instance'].budgetedevent.budgeted_events.first() is not None:
                    allowRecurringPatternUpdate = False
            if kwargs['instance'].audit is True:
                audit_view = True

        self.helper.layout = Layout(
            Field('description'),
            Div(
                Div('date_actual', css_class='form-group col-md-6  '),
                css_class='row'
            ),
        )
        if audit_view is False:
            self.helper.layout.extend([
                Div(
                    # Div(PrependedText('amount_actual', '$', css_class='form-group col-3')),
                    Div('amount_actual', css_class='form-group col-4'),
                    Div('currency', css_class='form-group col-4'),
                    Div('amount_actual_foreign_currency', css_class='form-group col-4  '),
                    css_class='row'
                ),
                Div(
                    # Div(AppendedText('Fuel_L', 'L', css_class='form-group col-2')),
                    # Div(AppendedText('Fuel_price', '$/L', css_class='form-group col-2')),
                    Div('Fuel_L', css_class='form-group col-4'),
                    Div('Fuel_price', css_class='form-group col-4'),
                    css_class='row fuel'
                ),
                Div(
                    Div('cat1', css_class='form-group col-md-4  '),
                    Div('cat2', css_class='form-group col-md-4  '),
                    css_class='row'
                ),
                Div(
                    Div('account_source', css_class='form-group col-6  '),
                    Div('account_destination', css_class='form-group col-6   '),
                    css_class='row'
                ),
                Div(
                    Div('verified', css_class='form-group col-md-4  '),
                    Div('receipt', css_class='form-group col-md-4   '),
                    Div('is_deleted', css_class='form-group col-md-4   '),
                    css_class='row'
                ),
                Div(
                    Div('ismanual', css_class='form-group col-md-8   '),
                    css_class='row'
                ),
                Div(
                    Div('budgetedevent', css_class='form-group col-md-4  '),
                    Div('vendor', css_class='form-group col-md-4  '),
                    Div('statement', css_class='form-group col-md-4   '),
                    Field('audit', type='hidden'),
                    css_class='row'
                ),
            ])
        else:
            self.helper.layout.extend([
                Div(
                    Div(PrependedText('amount_actual', '$', css_class='form-group col-sm-6    ')),
                    Field('account_source', type='hidden'),
                    Field('currency', type='hidden'),
                    Field('audit', type='hidden'),
                    Field('amount_actual_foreign_currency', type='hidden'),
                    Div('is_deleted', css_class='form-group col-md-4   '),
                    css_class='row'
                ),
            ])

        self.helper.layout.extend([
            Field('comment'),
            Div(
                HTML(f'<button type="submit" id="submit-id-submit" class="btn btn-primary" >{task}</button>'),
                HTML('<input type="cancel" name="cancel" value="cancel" class="btn btn-secondary .btn-close"  data-bs-dismiss="modal">'),
            ),
        ])

        a = 2
