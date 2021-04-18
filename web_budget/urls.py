import debug_toolbar
from django.contrib import admin
from django.urls import include,  path
from django.conf.urls.i18n import i18n_patterns
from django.views.generic.base import RedirectView

urlpatterns = i18n_patterns(
    path('budgetdb/', include('budgetdb.urls')),
    path('admin/', admin.site.urls, name='login'),
    path('__debug__/', include(debug_toolbar.urls)),
    path('favicon.ico', RedirectView.as_view(url='/static/budgetdb/favicon.ico')),
)
