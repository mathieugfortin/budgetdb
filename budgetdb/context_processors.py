from crum import get_current_user
from budgetdb.models import Preference

def theme_processor(request):
    preference = Preference.objects.get(user=get_current_user())          
    return {'preference_mode': preference.theme}