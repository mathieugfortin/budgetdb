from datetime import date
from crum import get_current_user
from django import forms
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.forms.models import modelformset_factory, inlineformset_factory, formset_factory
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Preference, Invitation
from .models import Account, AccountCategory, AccountHost, Cat1, Cat2, CatBudget, CatType, Vendor, Statement, Template
from .models import BudgetedEvent, Transaction, JoinedTransactions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Field, Fieldset, ButtonHolder, Div, LayoutObject, TEMPLATE_PACK, HTML, Hidden, Row, Column
from crispy_forms.bootstrap import AppendedText, PrependedText, StrictButton
from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm
from django_select2.forms import ModelSelect2Widget


class UserSignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('first_name', 'email')


class UserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('first_name', 'email')


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

    def render(self, form, context='', **kwargs):
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
            'unit_price',
            'users_admin',
            'users_view',
            'date_open',
            'date_closed',
            'is_deleted',
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
        self.fields['currency'].queryset = Preference.objects.get(user=user).currencies
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
                Div('unit_price', css_class='form-group col-md-4  '),
                Div('TFSA', css_class='form-group col-md-4  '),
                Div('RRSP', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div(
                Div('is_deleted', css_class='form-group col-md-4  '),
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
            'is_deleted',
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
                Div('is_deleted', css_class='form-group col-md-6  '),
                css_class='row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4  '),
                Div('users_view', css_class='form-group col-md-4  '),
                css_class='row'
            ),
        )


class InvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = (
            'email',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'InvitationForm'
        
        self.helper.layout = Layout(
            Div(
                Div('email', css_class='form-group col-md-6  '),
                css_class='row'
            ),
        )


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = (
            'name',
            'OFX_name',
            'users_admin',
            'users_view',
            'is_deleted',
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
                Div('OFX_name', css_class='form-group col-md-6  '),
                css_class='row'
            ),
            Div(
                Div('is_deleted', css_class='form-group col-md-6  '),
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
                'is_deleted',
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
                Div('is_deleted', css_class='form-group col-md-6  '),
                css_class='row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4  '),
                Div('users_view', css_class='form-group col-md-4  '),
                css_class='row'
            ),
        )


class TemplateForm(forms.ModelForm):
    class Meta:
        model = Template
        fields = [
            'description',
            'vendor',
            'amount_planned',
            'currency',
            'amount_planned_foreign_currency',
            'cat1',
            'cat2',
            'account_source',
            'account_destination',
            'ismanual',
            'comment',
            'users_admin',
            'users_view',
        ]

    def __init__(self, *args, **kwargs):
        task = kwargs.pop('task', 'Update')
        user = get_current_user()
        friends_ids = get_current_user().friends.values('id')
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'TemplateForm'

        if len(self.data) != 0:
            # form is bound, no need to build the layout
            # cat1 = int(self.data.get('cat1'))
            # self.fields['cat2'].queryset = Cat2.admin_objects.filter(cat1=cat1)
            return

        # form is unbound, build it
        preference = Preference.objects.get(user=user.id)
        currency_symbol = preference.currency_prefered.symbol
        if len(self.initial) == 0:
            # No initial values, set defaults
            self.fields['currency'].initial = preference.currency_prefered
            self.fields['currency'].data = preference.currency_prefered
            self.fields['cat2'].queryset = Cat2.objects.none()
            self.fields['vendor'].queryset = Vendor.admin_objects.filter(template__vendor__isnull=True)
        else:
            # initial values exist, set the correct dependant data
            try:
                cat1 = int(self.initial.get('cat1'))
                self.fields['cat2'].queryset = Cat2.admin_objects.filter(cat1=cat1)
            except (ValueError, TypeError):
                self.fields['cat2'].queryset = Cat2.objects.none()
            try:
                audit = self.initial.get('audit')
                if audit is True:
                    audit_view = True
            except (ValueError, TypeError):
                audit_view = False
            otherVendorsQS = Vendor.admin_objects.filter(template__vendor__isnull=True)
            thisVendorsQS = Vendor.admin_objects.filter(id=self.initial.get('vendor'))
            self.fields['vendor'].queryset = otherVendorsQS | thisVendorsQS

        self.fields['cat1'].queryset = Cat1.admin_objects.all()
        self.fields['account_source'].queryset = Account.admin_objects.all()
        self.fields['account_destination'].queryset = Account.admin_objects.all()
        self.fields['currency'].queryset = preference.currencies
        self.fields["users_admin"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_admin"].queryset = User.objects.filter(id__in=friends_ids,)
        self.fields["users_view"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_view"].queryset = User.objects.filter(id__in=friends_ids,)
        self.helper.layout = Layout(
            Div(
                Div('vendor', css_class='form-group col-md-6  '),
                css_class='row'
            ),
            Field('description'),
            Div(
                Div('amount_planned', css_class='form-group col-4'),
                Div('currency', css_class='form-group col-4'),
                Div('amount_planned_foreign_currency', css_class='form-group col-4  '),
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
                Div('ismanual', css_class='form-group col-md-8   '),
                css_class='row'
            ),
            Field('comment'),
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
            'is_deleted',
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
                Div('is_deleted', css_class='form-group col-md-6  '),
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
            'is_deleted',
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
            Div(
                Div('is_deleted', css_class='form-group col-md-10  '),
            ),
        )


class RecurringBitmaps(forms.Form):
    weekdays = [(1, 'Monday'), (2, 'Tuesday'), (4, 'Wednesday'), (8, 'Thursday'), (16, 'Friday'), (32, 'Saturday'), (64, 'Sunday')]
    weeks = [(1, '1'), (2, '2'), (4, '3'), (8, '4'), (16, '5')]
    months = [(1, 'January'), (2, 'February'), (4, 'March'), (8, 'April'), (16, 'May'), (32, 'June'), (64, 'July'),
              (128, 'August'), (256, 'September'), (512, 'October'), (1024, 'November'), (2048, 'December')]
    days = [(1, '1'), (2, '2'), (4, '3'), (8, '4'), (16, '5'), (32, '6'), (64, '7'), (128, '8'),
            (256, '9'), (512, '10'), (1024, '11'), (2048, '12'), (4096, '13'), (8192, '14'), (2**14, '15'),
            (2**15, '16'), (2**16, '17'), (2**17, '18'), (2**18, '19'), (2**19, '20'), (2**20, '21'), (2**21, '22'),
            (2**22, '23'), (2**23, '24'), (2**24, '25'), (2**25, '26'), (2**26, '27'), (2**27, '28'), (2**28, '29'),
            (2**29, '30'), (2**30, '31')
            ]
    daysOfWeek = forms.MultipleChoiceField(required=False, initial=[1, 2, 4, 8, 16, 32, 64],
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
            'currency',
            'amount_planned_foreign_currency',
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
            'is_deleted',
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
        task = kwargs.pop('task', 'Update')
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        friends_ids = get_current_user().friends.values('id')
        self.helper = FormHelper()

        if len(self.data) != 0:
            # form is bound, no need to build the layout
            return
        # form is unbound, build it
        preference = Preference.objects.get(user=user.id)
        currency_symbol = preference.currency_prefered.symbol
        if len(self.initial) == 0:
            # No initial values, set defaults
            self.fields['currency'].initial = preference.currency_prefered
            self.fields['currency'].data = preference.currency_prefered
            self.fields['cat2'].queryset = Cat2.objects.none()
        else:
            # initial values exist, set the correct dependant data
            try:
                cat1 = int(self.initial.get('cat1'))
                self.fields['cat2'].queryset = Cat2.admin_objects.filter(cat1=cat1)
            except (ValueError, TypeError):
                self.fields['cat2'].queryset = Cat2.objects.none()

        self.helper.form_id = 'BudgetedEventForm'
        self.fields['cat1'].queryset = Cat1.admin_objects.all()
        self.fields['account_source'].queryset = Account.admin_objects.all()
        self.fields['account_destination'].queryset = Account.admin_objects.all()
        self.fields['vendor'].queryset = Vendor.admin_objects.all()
        self.fields["users_admin"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_admin"].queryset = User.objects.filter(id__in=friends_ids,)
        self.fields["users_view"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_view"].queryset = User.objects.filter(id__in=friends_ids,)
        self.fields['currency'].queryset = Preference.objects.get(pk=user.id).currencies

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
                    Div('amount_planned', css_class='form-group col-md-4  '),
                    # Div(PrependedText('amount_planned', '$', css_class='form-group col-md-4  ')),
                    Div('currency', css_class='form-group col-md-4  '),
                    Div('amount_planned_foreign_currency', css_class='form-group col-md-4  '),
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
                    Div('is_deleted', css_class='form-group col-md-4  '),
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
                    Field('repeat_weekday_mask', type="hidden"),
                    Field('repeat_months_mask', type="hidden"),
                    Field('repeat_dayofmonth_mask', type="hidden"),
                    Field('repeat_weekofmonth_mask', type="hidden"),
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
                    Div('currency', css_class='form-group col-md-4  '),
                    Div('amount_planned_foreign_currency', css_class='form-group col-md-4  '),
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
                    Field('is_deleted', css_class='form-group col-md-4  ', type="hidden"),
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
                    HTML('<h3><span class="material-symbols-outlined">warning</span>This event is part of a Joint Transaction.</h3> <h3>If you want to modify the recurrence timing, do it through the joint transaction</h3>'),
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


class Cat1Form(forms.ModelForm):
    class Meta:
        model = Cat1
        fields = (
            'name',
            'catbudget',
            'cattype',
            'is_deleted',
            'users_admin',
            'users_view',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        friends_ids = get_current_user().friends.values('id')
        self.fields['cattype'].queryset = CatType.admin_objects.all()
        self.fields['catbudget'].queryset = CatBudget.admin_objects.all()
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
                Div('is_deleted', css_class='form-group col-md-4  '),
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
            'unit_price',
            'is_deleted',
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
        self.fields['cattype'].queryset = CatType.admin_objects.all()
        self.fields['catbudget'].queryset = CatBudget.admin_objects.all()
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
                Div('unit_price', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div(
                Div('cattype', css_class='form-group col-md-4  '),
                Div('catbudget', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div(
                Div('is_deleted', css_class='form-group col-md-4  '),
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


class PreferenceForm(forms.ModelForm):
    class Meta:
        model = Preference
        fields = '__all__'
        widgets = {
            'slider_start': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'placeholder': 'Select a date', 'type': 'date'}
            ),
            'slider_stop': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'placeholder': 'Select a date', 'type': 'date'}
            ),
            'timeline_stop': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'placeholder': 'Select a date', 'type': 'date'}
            ),
            'timeline_start': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={'class': 'form-control', 'placeholder': 'Select a date', 'type': 'date'}
            ),
            'currencies': forms.CheckboxSelectMultiple(
            ),
            'favorite_accounts': forms.CheckboxSelectMultiple(
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['favorite_accounts'].queryset = Account.view_objects.all()
        self.fields['currency_prefered'].label = 'Prefered Currency'
        self.fields['timeline_start'].label = 'Timeline Beginning'
        self.fields['timeline_stop'].label = 'Timeline End'
        self.fields['slider_start'].label = 'Start of time selection'
        self.fields['slider_stop'].label = 'End of time selection'
        
        self.helper.layout = Layout(
            Div(
                Div('theme', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div(
                Div('slider_start', css_class='form-group col-md-4  '),
                Div('slider_stop', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div(
                Div('timeline_start', css_class='form-group col-md-4  '),
                Div('timeline_stop', css_class='form-group col-md-4  '),
                css_class='row'
            ),
            Div(
                Div('currencies', css_class='form-group col-md-4  '),
                Div('currency_prefered', css_class='form-group col-md-4  '),
                Field('user', type="hidden"),
                css_class='row'
            ),
            Div(
                Div('favorite_accounts', css_class='form-group col-md-4  '),
                css_class='row'
            ),
        )

    def save(self, commit=True):
        if 'timeline_stop' in self.changed_data:
            new_timeline_stop = self.cleaned_data['timeline_stop']
            accounts = Account.view_objects.all()
            for account in accounts:
                account.check_balances(new_timeline_stop)
        super(PreferenceForm, self).save(commit)


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
                self.fields['cat2'].queryset = Cat2.admin_objects.filter(cat1=cat1)
            except (ValueError, TypeError):
                self.fields['cat2'].queryset = Cat2.objects.none()
        else:
            self.fields['cat2'].queryset = Cat2.objects.none()
        self.fields['cat1'].queryset = Cat1.admin_objects.all()
        self.fields['account_source'].queryset = Account.admin_objects.all()
        self.fields['account_destination'].queryset = Account.admin_objects.all()
        self.fields['budgetedevent'].queryset = BudgetedEvent.admin_objects.all()

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


class TransactionOFXImportForm(forms.Form):
    #account = forms.ModelChoiceField(
    #    queryset=Account.admin_objects.all(),
    #    help_text="Which account do these transactions belong to?"
    #)
    ofx_file = forms.FileField(
        label="Select OFX File",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.ofx'  # This filters the file dialog
        })
    )


class TransactionModalForm(BSModalModelForm):
    statement = forms.ModelChoiceField(
        queryset=Statement.admin_objects.none(),  # populate in __init__
        required=False, 
        empty_label="---------"
    )
    vendor = forms.ModelChoiceField(
        queryset=Vendor.view_objects.all(),
        widget=forms.Select(attrs={'class': 'django-select2'}),
        required=False, 
        empty_label="---------"
    )    
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
            'Unit_QTY',
            'Unit_price',
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
            'statement': ModelSelect2Widget(
                model=Statement,
                search_fields=['statement_date__icontains'],
                attrs={
                    'class': 'django-select2',
                    'data-placeholder': 'Optional: Select a statement',
                    'data-allow-clear': 'true',  # Select2 heavy widgets look for data-attributes
                },
            ),
            'vendor': ModelSelect2Widget(
                model=Vendor,
                search_fields=['name__icontains'],
                attrs={
                    'class': 'django-select2',
                    'data-placeholder': 'Optional: Select a vendor',
                    'data-allow-clear': 'true',  # Select2 heavy widgets look for data-attributes
                },                
            )
        }

    def __init__(self, *args, **kwargs):
        audit_view = kwargs.pop('audit', False)
        task = kwargs.pop('task', 'Update')
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        if len(self.data) != 0:
            # statement queryser somehow gets whiped out by the ajax requests anmd the form won't save.
            self.fields['statement'].queryset = Statement.admin_objects.order_by('-statement_date')
            # self.fields['cat2'].queryset = Cat2.admin_objects.filter(cat1=cat1)
            return

        # form is unbound, build it
        preference = Preference.objects.get(user=user.id)
        currency_symbol = preference.currency_prefered.symbol
        if len(self.initial) == 0:
            # No initial values, set defaults
            self.fields['currency'].initial = preference.currency_prefered
            self.fields['currency'].data = preference.currency_prefered
            self.fields['cat2'].queryset = Cat2.objects.none()
            self.fields['amount_actual'].initial = None
        else:
            # initial values exist, set the correct dependant data
            try:
                cat1 = int(self.initial.get('cat1'))
                self.fields['cat2'].queryset = Cat2.admin_objects.filter(cat1=cat1)
            except (ValueError, TypeError):
                self.fields['cat2'].queryset = Cat2.objects.none()
            try:
                audit = self.initial.get('audit')
                if audit is True:
                    audit_view = True
            except (ValueError, TypeError):
                audit_view = False

        self.fields['cat1'].queryset = Cat1.admin_objects.all()
        self.fields['account_source'].queryset = Account.admin_objects.all()
        self.fields['account_source'].label = 'Source'
        self.fields['account_destination'].queryset = Account.admin_objects.all()
        self.fields['account_destination'].label = 'Destination'
        self.fields['statement'].queryset = Statement.admin_objects.order_by('-statement_date')
        self.fields['statement'].widget.attrs.update({
                                                'class': 'django-select2',
                                                'data-width': '100%' # Optional: helps Select2 fit inside modal widths
                                                })
        #self.fields['statement'].widget=StatementWidget()
        # self.fields['statement'].label_from_instance = (lambda obj: f'{obj.date:%Y-%m-%d} – {obj.name[:25]}…' if len(obj.name) > 25   else f'{obj.date:%Y-%m-%d} – {obj.name}')
        self.fields['vendor'].queryset = Vendor.view_objects.all()
        self.fields['currency'].queryset = preference.currencies
        self.fields['budgetedevent'].queryset = BudgetedEvent.admin_objects.all()

        # will I need to add all labels here for translations?
        # self.fields['amount_actual'].label = "Amount"

        allowRecurringPatternUpdate = True
        if kwargs['instance'] is not None:
            if kwargs['instance'].transactions is not None:
                if kwargs['instance'].transactions.first() is not None:
                    allowRecurringPatternUpdate = False
            if kwargs['instance'].budgetedevent is not None:
                if kwargs['instance'].budgetedevent.budgeted_events.first() is not None:
                    allowRecurringPatternUpdate = False

        if audit_view is False:
            self.helper.layout = Layout(
                Row(
                    Column('vendor', css_class='col-6'),
                    ),
                Row(
                    Column('description', css_class='col-12'),
                    ),
            )
        else:
            self.helper.layout = Layout(
                Row(
                    Column('description', css_class='col-12'),
                ),
            )

        self.helper.layout.extend([
            Row(
                Column('date_actual', css_class=' col-6'),
            ),
            Row(
                Column(PrependedText('amount_actual', '$', attributes={"step": "0.01", "type": "number"}), css_class='col-6'),
                Column('currency', css_class='col-6' ),
            ),
            Row(
                Column(PrependedText('amount_actual_foreign_currency', '$', attributes={"step": "0.01", "type": "number"}),css_class='col-4'),
            ),
        ])

        if audit_view is False:
            self.helper.layout.extend([
                Row(
                    Column('cat1', css_class='col-md-6'),
                    Column('cat2', css_class='col-md-6'),
                ),
                Row(
                    Column('Unit_QTY', css_class='col-6'),
                    Column('Unit_price', css_class='col-6'),
                ),
                Row(
                    Column('account_source', css_class='col-5 mb-3'),
                    Column(
                        HTML('<label class="form-label">&nbsp;</label>'),
                        StrictButton(
                            '<span class="material-symbols-outlined">swap_horiz</span>',
                            name='flip',
                            type="button",
                            css_class="btn btn-danger mb-5",
                            onclick="changeaccounts()"
                        ),
                        css_class='col-2 mb-3 d-grid' # 'd-grid' makes the button fill the column width
                    ),
                    Column('account_destination', css_class='col-5 mb-3'),
                ),
                Row(
                    Column('statement', css_class='col-10'),
                ),
                Row(
                    Column(css_class='col-2 mb-1'),
                    Column(
                        Row('verified', css_class='mb-1'),
                        Row('receipt', css_class='mb-1'),
                        Row('is_deleted', css_class='mb-1'),
                        Row('ismanual', css_class='mb-1'),    
                        css_class='col-8 mb-1 '
                    ),
                ),
                Row(
                    Column('budgetedevent', css_class='col-12'),
                ),
                Field('audit', type='hidden'),
            ])
        else:
            self.helper.layout.extend([
                Row(
                    Field('account_source', type='hidden'),
                    Field('audit', type='hidden'),
                    Div('is_deleted', css_class='col-md-4'),
                ),
                Row(
                    Column('Unit_QTY', css_class='col-4'),
                    Column('Unit_price', css_class='col-4'),
                ),
            ])

        self.helper.layout.extend([
            Row(
                    Column('comment', css_class='col-12'),
                ),
            Row(
                Column(
                    HTML(f'<button type="submit" id="submit-id-submit" class="btn btn-primary">{task}</button>'),
                ),
                Column(
                    HTML('<button type="button" name="cancel" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>'),
                ),                
            ),
        ])


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
            'Unit_QTY',
            'Unit_price',
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
        audit_view = kwargs.pop('audit', False)
        task = kwargs.pop('task', 'Update')
        user = kwargs.pop('user', None)
        if user is None:
            raise PermissionDenied
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'TransactionFormFull'
        if len(self.data) != 0:
            # form is bound, no need to build the layout
            # cat1 = int(self.data.get('cat1'))
            # self.fields['cat2'].queryset = Cat2.admin_objects.filter(cat1=cat1)
            return

        # form is unbound, build it
        preference = Preference.objects.get(user=user.id)
        currency_symbol = preference.currency_prefered.symbol
        if len(self.initial) == 0:
            # No initial values, set defaults
            self.fields['currency'].initial = preference.currency_prefered
            self.fields['currency'].data = preference.currency_prefered
            self.fields['cat2'].queryset = Cat2.objects.none()
        else:
            # initial values exist, set the correct dependant data
            try:
                cat1 = int(self.initial.get('cat1'))
                self.fields['cat2'].queryset = Cat2.admin_objects.filter(cat1=cat1)
            except (ValueError, TypeError):
                self.fields['cat2'].queryset = Cat2.objects.none()
            try:
                audit = self.initial.get('audit')
                if audit is True:
                    audit_view = True
            except (ValueError, TypeError):
                audit_view = False

        self.fields['cat1'].queryset = Cat1.admin_objects.all()
        self.fields['account_source'].queryset = Account.admin_objects.all()
        self.fields['account_destination'].queryset = Account.admin_objects.all()
        self.fields['statement'].queryset = Statement.admin_objects.all()
        self.fields['vendor'].queryset = Vendor.admin_objects.all()
        self.fields['currency'].queryset = preference.currencies
        self.fields['budgetedevent'].queryset = BudgetedEvent.admin_objects.all()

        # will I need to add all labels here for translations?
        # self.fields['amount_actual'].label = "Amount"

        allowRecurringPatternUpdate = True
        if kwargs['instance'] is not None:
            if kwargs['instance'].transactions is not None:
                if kwargs['instance'].transactions.first() is not None:
                    allowRecurringPatternUpdate = False
            if kwargs['instance'].budgetedevent is not None:
                if kwargs['instance'].budgetedevent.budgeted_events.first() is not None:
                    allowRecurringPatternUpdate = False

        self.helper.layout = Layout(
            Field('description'),
            Div(
                Div('date_actual', css_class='form-group col-md-6  '),
                css_class='row'
            ),
            Div(
                # Div(PrependedText('amount_actual', '$', css_class='form-group col-3 input-group-sm')),
                Div('amount_actual', css_class='form-group col-4'),
                Div('currency', css_class='form-group col-4'),
                Div('amount_actual_foreign_currency', css_class='form-group col-4  '),
                css_class='row'
            ),
        )
        if audit_view is False:
            self.helper.layout.extend([
                Div(
                    # Div(AppendedText('Unit_QTY', 'L', css_class='form-group col-2')),
                    # Div(AppendedText('Unit_price', '$/L', css_class='form-group col-2')),
                    Div(AppendedText('Unit_QTY', 'L', css_class='form-group col-sm-6   mr-0  ')),
                    Div(AppendedText('Unit_price', '$/L', css_class='form-group col-sm-6  ')),
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
                    # Div('audit', css_class='form-group col-md-4  '),
                    Field('audit', type='hidden'),
                    Div('ismanual', css_class='form-group col-md-8   '),
                    css_class='row'
                ),
                Div(
                    Div('budgetedevent', css_class='form-group col-md-4  '),
                    Div('vendor', css_class='form-group col-md-4  '),
                    Div('statement', css_class='form-group col-md-4   '),
                    css_class='row'
                ),
            ])
        else:
            self.helper.layout.extend([
                Div(
                    # Div(PrependedText('amount_actual', '$', css_class='form-group col-sm-6', input_size="input-group-sm")),
                    Field('account_source', type='hidden'),
                    # Field('currency', type='hidden'),
                    Field('audit', type='hidden'),
                    # Field('amount_actual_foreign_currency', type='hidden'),
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
