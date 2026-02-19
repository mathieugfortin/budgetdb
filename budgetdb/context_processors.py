from crum import get_current_user
from budgetdb.models import Preference
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

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

def version_info(request):
    github_link = f"{settings.GITHUB_REPO_URL}/commit/{settings.GIT_SHA}"
    return {
        'APP_VERSION': settings.APP_VERSION,
        'BUILD_DATE': settings.BUILD_DATE,
        'GIT_SHA': settings.GIT_SHA,
    }