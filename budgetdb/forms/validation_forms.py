from django import forms
from budgetdb.models import *

class CatType_Cat1_begin_end_ValForm(forms.Form):
    cattype = forms.IntegerField(required=True)
    cat1 = forms.IntegerField(required=True)
    begin = forms.DateField(input_formats=['%Y-%m-%d'], required=True)
    end = forms.DateField(input_formats=['%Y-%m-%d'], required=True)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        cattype_pk = cleaned_data.get("cattype")
        cat1_pk = cleaned_data.get("cat1")
        begin = cleaned_data.get("begin")
        end = cleaned_data.get("end")
        
        # Permission
        if cattype_pk:
            try:
                cleaned_data['cattype_obj'] = CatType.view_objects.get(pk=cattype_pk)
            except CatType.DoesNotExist:
                raise forms.ValidationError({"cattype": "Category Type not found or access denied."})
        if cat1_pk:
            try:
                cleaned_data['cat1_obj'] = Cat1.view_objects.get(pk=cat1_pk)
            except Cat1.DoesNotExist:
                raise forms.ValidationError({"cat1": "Category not found or access denied."})

        if begin and end and begin > end:
            raise forms.ValidationError("End date must be after begin date.")
        return cleaned_data        


class CatType_begin_end_ValForm(forms.Form):
    cattype = forms.IntegerField(required=True)
    begin = forms.DateField(input_formats=['%Y-%m-%d'], required=True)
    end = forms.DateField(input_formats=['%Y-%m-%d'], required=True)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        cattype_pk = cleaned_data.get("cattype")
        cat1_pk = cleaned_data.get("cat1")
        begin = cleaned_data.get("begin")
        end = cleaned_data.get("end")

        # Permission
        if cattype_pk:
            try:
                cleaned_data['cattype_obj'] = CatType.view_objects.get(pk=cattype_pk)
            except CatType.DoesNotExist:
                raise forms.ValidationError({"cattype": "Category Type not found or access denied."})

        # data validation
        if begin and end and begin > end:
            raise forms.ValidationError("End date must be after begin date.")
        return cleaned_data                


class CatTy2pe_begin_end_ValForm(forms.Form):
    cattype = forms.IntegerField(required=True)
    begin = forms.DateField(input_formats=['%Y-%m-%d'], required=True)
    end = forms.DateField(input_formats=['%Y-%m-%d'], required=True)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        cattype_pk = cleaned_data.get("cattype")
        cat1_pk = cleaned_data.get("cat1")
        begin = cleaned_data.get("begin")
        end = cleaned_data.get("end")

        # Permission
        if cattype_pk:
            try:
                cleaned_data['cattype_obj'] = CatType.view_objects.get(pk=cattype_pk)
            except CatType.DoesNotExist:
                raise forms.ValidationError({"cattype": "Category Type not found or access denied."})

        # data validation
        if begin and end and begin > end:
            raise forms.ValidationError("End date must be after begin date.")
        return cleaned_data                        