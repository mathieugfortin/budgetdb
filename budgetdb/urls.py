from django.urls import path
from . import views

# from budgetdb.views import CategoryDetailView, TransactionDetailView,
# # saveTransaction, BudgetedEventList

app_name = 'budgetdb'

urlpatterns = [
    path('', views.IndexView.as_view(),
         name='home'),

    # Cat1
    path('category', views.CategoryListView.as_view(),
         name='list_cat'),
    path('category/<int:pk>/', views.CategoryDetailView.as_view(),
         name='details_cat'),
    path('cat1/add/', views.CreateCat1.as_view(),
         name='create_cat'),
    path('cat1/ac/', views.AutocompleteCat1.as_view(),
         name='autocomplete_cat1'),

    # Cat2
    path('subcategory/<int:pk>/', views.SubCategoryDetailView.as_view(),
         name='details_subcat'),
    path('cat2/add/', views.CreateCat2.as_view(),
         name='create_cat2'),
    path('cat2/ac/', views.AutocompleteCat2.as_view(),
         name='autocomplete_cat2'),

    # Transaction
    path('<int:pk>/saveTransaction/', views.saveTransaction,
         name='saveTransaction'),
    path('transaction/<int:pk>/', views.TransactionDetailView.as_view(),
         name='details_transaction'),

    # BudgetedEvent
    path('budgetedEvent/', views.budgetedEventsListView.as_view(),
         name='list_be'),
    path('budgetedEvent/<int:pk>/', views.BudgetedEventDetailView.as_view(),
         name='details_be'),
    path('budgetedEvent/add/', views.BudgetedEventCreateView.as_view(),
         name='add_be'),
    path('budgetedEvent/mod/<int:pk>/', views.BudgetedEventView.as_view(),
         name='change_be'),

    # Vendor
    path('vendor/ac/', views.AutocompleteVendor.as_view(),
         name='autocomplete_vendor'),
    path('vendor/add/', views.CreateVendor.as_view(),
         name='create_vendor'),

    # Account
    path('account/add/', views.CreateVendor.as_view(),
         name='create_account'),
    path('account/ac/', views.AutocompleteAccount.as_view(),
         name='autocomplete_account'),
    path('account/<int:pk>/', views.AccountperiodicView.as_view(),
         name='list_account_activity'),

    # Calendar_view
    path('calendar/', views.CalendarTableView.as_view(),
         name='table_calendar'),
    path('list/', views.CalendarListView.as_view(),
         name='list_calendar'),

]
