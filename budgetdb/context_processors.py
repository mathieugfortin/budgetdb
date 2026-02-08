from crum import get_current_user
from budgetdb.models import Preference
from django.core.exceptions import ObjectDoesNotExist

def theme_processor(request):
    theme = 'light' 
    user=get_current_user()
    if user is not None:
        if user.id is not None:
            try:
                preference = Preference.objects.get(user=user)          
                theme = preference.theme
            except ObjectDoesNotExist:
                pass
    return {'preference_mode': theme}