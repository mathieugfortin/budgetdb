from django import forms
from dal import autocomplete
from .models import Cat1, Transaction, Cat2, BudgetedEvent, Vendor
from django.urls import reverse_lazy
from django_addanother.widgets import AddAnotherWidgetWrapper, AddAnotherEditSelectedWidgetWrapper
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class BudgetedEventForm(forms.ModelForm):
    class Meta:
        model = BudgetedEvent
        # fields = ('__all__')
        fields = (
            'description',
            'amount_planned',
            'cat1',
            'cat2',
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
            #               autocomplete.ModelSelect2(url='budgetdb:autocomplete_cat1'), reverse_lazy('budgetdb:create_cat')
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
