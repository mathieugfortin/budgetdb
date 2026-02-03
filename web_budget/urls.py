# import debug_toolbar
from django.contrib import admin
from django.urls import include,  path
from django.conf.urls.i18n import i18n_patterns
from django.views.generic.base import RedirectView

app_name = 'web_budget'

urlpatterns = i18n_patterns(
    path('', include('budgetdb.urls')),
    path("select2/", include("django_select2.urls")),
)
