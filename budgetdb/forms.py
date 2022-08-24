from django import forms
from django.shortcuts import get_object_or_404
from .models import User, Preference
from .models import Account, AccountCategory, AccountHost, Cat1, Cat2, CatBudget, CatType, Vendor, Statement
from .models import BudgetedEvent, Transaction, JoinedTransactions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Field, Fieldset, ButtonHolder, Div, LayoutObject, TEMPLATE_PACK, HTML, Hidden
from django.template.loader import render_to_string
from crispy_forms.bootstrap import AppendedText, PrependedText
from django.forms.models import modelformset_factory, inlineformset_factory, formset_factory
from datetime import datetime, date
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from crum import get_current_user


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
            'users_admin',
            'users_view',
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
        self.helper.layout = Layout(
            Div(
                Div('name', css_class='form-group col-md-4 mb-0'),
                Div('account_number', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Div('comment', css_class='form-group col-md-6 mb-0'),
            Div(
                Div('account_host', css_class='form-group col-md-4 mb-0'),
                Div('account_parent', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('TFSA', css_class='form-group col-md-4 mb-0'),
                Div('RRSP', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4 mb-0'),
                Div('users_view', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
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
                Div('name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4 mb-0'),
                Div('users_view', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
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
                Div('name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4 mb-0'),
                Div('users_view', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
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
        self.fields["users_admin"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_admin"].queryset = User.objects.filter(id__in=friends_ids,)
        self.fields["users_view"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_view"].queryset = User.objects.filter(id__in=friends_ids,)
        self.helper.layout = Layout(
            Div(
                Div('account', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('statement_date', css_class='form-group col-md-4 mb-0'),
                Div('balance', css_class='form-group col-md-4 mb-0'),
                Div('minimum_payment', css_class='form-group col-md-4 mb-0'),
                Div('statement_due_date', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('comment', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('payment_transaction', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4 mb-0'),
                Div('users_view', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
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
                Div('name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4 mb-0'),
                Div('users_view', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
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
                Div('name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('accounts', css_class='form-group col-md-4 mb-0'),
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4 mb-0'),
                Div('users_view', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
        )


class BudgetedEventForm(forms.ModelForm):
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
        self.fields['vendor'].queryset = Vendor.admin_objects.filter(is_deleted=False)
        self.fields["users_admin"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_admin"].queryset = User.objects.filter(id__in=friends_ids,)
        self.fields["users_view"].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields["users_view"].queryset = User.objects.filter(id__in=friends_ids,)
        self.helper.layout = Layout(
            Div(
                Div('description', css_class='form-group col-md-6 mb-0'),
                Div('vendor', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('cat1', css_class='form-group col-md-4 mb-0'),
                Div('cat2', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Div(
                # Div('amount_planned', css_class='form-group col-md-4 mb-0'),
                Div(PrependedText('amount_planned', '$', css_class='form-group col-sm-6 mb-0 ml-0')),
                Div('account_source', css_class='form-group col-md-4 mb-0'),
                Div('account_destination', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('budget_only', css_class='form-group col-md-4 mb-0'),
                Div('ismanual', css_class='form-group col-md-4 mb-0'),
                Div('isrecurring', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('repeat_start', css_class='form-group col-md-4 mb-0'),
                Div('repeat_stop', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('repeat_interval_days', css_class='form-group col-md-2 mb-0'),
                Div('repeat_interval_weeks', css_class='form-group col-md-2 mb-0'),
                Div('repeat_interval_months', css_class='form-group col-md-2 mb-0'),
                Div('repeat_interval_years', css_class='form-group col-md-2 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4 mb-0'),
                Div('users_view', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
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
                Div('name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('cattype', css_class='form-group col-md-4 mb-0'),
                Div('catbudget', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4 mb-0'),
                Div('users_view', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
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
                Div('name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('cattype', css_class='form-group col-md-4 mb-0'),
                Div('catbudget', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('users_admin', css_class='form-group col-md-4 mb-0'),
                Div('users_view', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
        )


class JoinedTransactionsForm(forms.ModelForm):
    class Meta:
        model = JoinedTransactions
        fields = [
            'name',
        ]

    def save(self):
        return super().save(self)

    def __init__(self, *args, **kwargs):
        pk = kwargs.pop('pk', None)
        date = kwargs.pop('date', None)
        super(JoinedTransactionsForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = True
        self.helper.layout = Layout(
            Hidden('name', self.initial['name']),
            # Field('name'),
            Div(
                HTML("<div class='col-md-2' >Description</div>"),
                HTML("<div class='col-md-1' >Category</div>"),
                HTML("<div class='col-md-2' >Subcategory</div>"),
                HTML("<div class='col-md-1' >Source</div>"),
                HTML("<div class='col-md-1' >Destination</div>"),
                HTML("<div class='col-md-1 text-center' >Verified</div>"),
                HTML("<div class='col-md-1 text-center' >Receipt</div>"),
                HTML("<div class='col-md-1 text-center' >Deleted</div>"),
                HTML("<div class='col-md-1' >Ammount</div>"),
                css_class='form-row'
            ),
            Div(
                Fieldset('', Formset('formset', helper_context_name='helper')),
            )
        )


class TransactionFormFull(forms.ModelForm):
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
        self.fields['cat1'].queryset = Cat1.admin_objects.filter(is_deleted=False)
        if 'cat1' in self.initial:
            try:
                cat1 = int(self.initial.get('cat1'))
                self.fields['cat2'].queryset = Cat2.admin_objects.filter(cat1=cat1, is_deleted=False)
            except (ValueError, TypeError):
                self.fields['cat2'].queryset = Cat2.objects.none()
        elif 'cat1' not in self.data:
            self.fields['cat2'].queryset = Cat2.objects.none()

        self.fields['cat1'].queryset = Cat1.admin_objects.filter(is_deleted=False)
        self.fields['account_source'].queryset = Account.admin_objects.filter(is_deleted=False)
        self.fields['account_destination'].queryset = Account.admin_objects.filter(is_deleted=False)
        self.fields['statement'].queryset = Statement.admin_objects.filter(is_deleted=False)
        self.fields['vendor'].queryset = Vendor.admin_objects.filter(is_deleted=False)
        self.fields['budgetedevent'].queryset = BudgetedEvent.admin_objects.filter(is_deleted=False)

        self.fields['cat1'].label = "Category"
        self.fields['cat2'].label = "Sub-Category"
        self.fields['amount_actual'].label = "Ammount"
        self.helper.layout = Layout(
            Field('description'),
            Div(
                Div(PrependedText('amount_actual', '$', css_class='form-group col-sm-6 mb-0 ml-0')),
                Div(AppendedText('Fuel_L', 'L', css_class='form-group col-sm-6 mb-0 mr-0 ml-0')),
                Div(AppendedText('Fuel_price', '$/L', css_class='form-group col-sm-6 mb-0')),
                css_class='form-row'
            ),
            Div(
                Div('date_actual', css_class='form-group col-md-4 mb-0'),
                Div('date_planned', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('cat1', css_class='form-group col-md-4 mb-0'),
                Div('cat2', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('account_source', css_class='form-group col-md-4 mb-0'),
                Div('account_destination', css_class='form-group col-md-4 mb-0 '),
                css_class='form-row'
            ),
            Div(
                Div('verified', css_class='form-group col-md-4 mb-0'),
                Div('receipt', css_class='form-group col-md-4 mb-0 '),
                Div('is_deleted', css_class='form-group col-md-4 mb-0 '),
                css_class='form-row'
            ),
            Div(
                Div('audit', css_class='form-group col-md-4 mb-0'),
                Div('ismanual', css_class='form-group col-md-8 mb-0 '),
                css_class='form-row'
            ),
            Field('comment'),
            Div(
                Div('budgetedevent', css_class='form-group col-md-4 mb-0'),
                Div('vendor', css_class='form-group col-md-4 mb-0'),
                Div('statement', css_class='form-group col-md-4 mb-0 '),
                css_class='form-row'
            ),
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
                Div('start_interval', css_class='form-group col-md-4 mb-0'),
                Div('end_interval', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Div(
                Div('min_interval_slider', css_class='form-group col-md-4 mb-0'),
                Div('min_interval_slider', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
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
                Field('date_actual', css_class='form-group col-md-2 mb-0', type='hidden'),
                # Div('amount_actual', css_class='form-group col-md-1'),
                Field('budgetedevent', css_class='form-group col-md-1', type='hidden'),
                # HTML('<a href="{% url 'budgetdb:update_be' event.budgetedevent_id %}"> <i class="fas fa-calendar"></i></a>'),
                css_class='form-row'
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
