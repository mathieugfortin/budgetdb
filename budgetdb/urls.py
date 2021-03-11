from django.urls import path
from . import views

# from budgetdb.views import CategoryDetailView, TransactionDetailView,
# # saveTransaction, BudgetedEventList

app_name = 'budgetdb'

urlpatterns = [
    path('', views.IndexView.as_view(),
         name='index'),
    path('category/<int:pk>/', views.CategoryDetailView.as_view(),
         name='category'),
    path('<int:pk>/saveTransaction/', views.saveTransaction,
         name='saveTransaction'),
    path('budgetedEvent/', views.budgetedEventsListView.as_view(),
         name='list_be'),
    path('budgetedEvent/<int:pk>/', views.BudgetedEventDetailView.as_view(),
         name='details_be'),
    path('transaction/<int:pk>/', views.TransactionDetailView.as_view(),
         name='details_transaction'),
    path('budgetedEvent/add/', views.BudgetedEventCreateView.as_view(),
         name='add_be'),
    path('budgetedEvent/mod/<int:pk>/', views.BudgetedEventView.as_view(),
         name='change_be'),
    path('vendor/ac/', views.AutocompleteVendor.as_view(),
         name='autocomplete_vendor'),
    path('vendor/add/', views.CreateVendor.as_view(),
         name='create_vendor'),
    path('account/add/', views.CreateVendor.as_view(),
         name='create_account'),
    path('cat1/add/', views.CreateCat1.as_view(),
         name='create_cat1'),
    path('cat2/add/', views.CreateCat2.as_view(),
         name='create_cat2'),
    path('account/ac/', views.AutocompleteAccount.as_view(),
         name='autocomplete_account'),
    path('cat1/ac/', views.AutocompleteCat1.as_view(),
         name='autocomplete_cat1'),
    path('cat2/ac/', views.AutocompleteCat2.as_view(),
         name='autocomplete_cat2'),
    path('calendar/', views.CalendarTableView.as_view(),
         name='calendar'),
    path('list/', views.CalendarListView.as_view(),
         name='list_full'),

]
