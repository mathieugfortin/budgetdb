from crum import get_current_user
from budgetdb.models import Preference
from django.core.exceptions import ObjectDoesNotExist

def theme_processor(request):
    theme = 'light' 
    user=get_current_user()
    if user.id is not None:
        preference = Preference.objects.get(user=user)          
        theme = preference.theme
    return {'preference_mode': theme}