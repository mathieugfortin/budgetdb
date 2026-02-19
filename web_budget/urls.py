# import debug_toolbar
from django.contrib import admin
from django.urls import include,  path
from django.conf.urls.i18n import i18n_patterns
from django.views.generic.base import RedirectView
from django.contrib.auth import views as auth_views

app_name = 'web_budget'

urlpatterns = i18n_patterns(
    path('', include(('budgetdb.urls', 'budgetdb'), namespace='budgetdb')),
    path("select2/", include("django_select2.urls")),
    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(
        html_email_template_name='registration/password_reset_email.html'
        ), name='password_reset'),
    path('accounts/', include('django.contrib.auth.urls')),
)
