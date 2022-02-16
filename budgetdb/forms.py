from django import forms
from dal import autocomplete
from .models import Cat1, Transaction, Cat2, BudgetedEvent, Vendor
from django.urls import reverse_lazy
from django_addanother.widgets import AddAnotherWidgetWrapper, AddAnotherEditSelectedWidgetWrapper
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Field, ButtonHolder, Div
from crispy_forms.bootstrap import AppendedText, PrependedText


class DateInput(forms.DateInput):
    input_type = 'date'


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
        )

        widgets = {
            #            'account_source': AddAnotherWidgetWrapper(
            #               autocomplete.ModelSelect2(url='budgetdb:autocomplete_account'), reverse_lazy('budgetdb:create_account')
            #              ),
            #         'account_destination': AddAnotherWidgetWrapper(
            #            autocomplete.ModelSelect2(url='budgetdb:autocomplete_account'), reverse_lazy('budgetdb:create_account')
            #           ),
            #            'cat1': AddAnotherWidgetWrapper(
            #               autocomplete.ModelSelect2(url='budgetdb:autocomplete_cat1'), reverse_lazy('budgetdb:create_cat1')
            #              ),
            #            'cat2': AddAnotherWidgetWrapper(
            #               autocomplete.ModelSelect2(url='budgetdb:autocomplete_cat2', forward=['cat1']), reverse_lazy('budgetdb:create_cat2')
            #              ),
            #            'vendor': AddAnotherWidgetWrapper(
            #               autocomplete.ModelSelect2(url='budgetdb:autocomplete_vendor'), reverse_lazy('budgetdb:create_vendor')
            #              ),
            'repeat_start': forms.widgets.DateInput(attrs={'type': 'date'}),
            'repeat_stop': forms.widgets.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'BudgetedEventForm'
        # self.helper.form_class = 'blueForms'
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_action = 'submit/'

        self.helper.add_input(Submit('submit', 'Submit'))
        # self.fields['cat2'].queryset = Cat2.objects.none()


class JoinedTransactionsForm(forms.ModelForm):
    pass


class TransactionForm(forms.ModelForm):

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
            'deleted',
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
        self.helper.form_method = 'POST'
        self.helper.add_input(Submit('submit', 'Update', css_class='btn-primary'))

        # self.helper.form_class = 'form-horizontal'
        self.fields['cat1'].label = "Category"
        self.fields['cat2'].label = "Sub-Category"
        if 'cat1' in self.initial:
            try:
                cat1 = int(self.initial.get('cat1'))
                self.fields['cat2'].queryset = Cat2.objects.filter(cat1=cat1, deleted=False)
            except (ValueError, TypeError):
                self.fields['cat2'].queryset = Cat2.objects.none()
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
                Div('deleted', css_class='form-group col-md-4 mb-0 '),
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
