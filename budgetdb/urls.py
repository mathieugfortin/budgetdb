from django.urls import path
from . import views

# from budgetdb.views import CategoryDetailView, TransactionDetailView,
# # saveTransaction, BudgetedEventList

app_name = 'budgetdb'

urlpatterns = [
    path('', views.IndexView.as_view(),
         name='home'),

    # chart JS
    path('chart/', views.FirstGraph.as_view(), name='line_chart'),
    path('chartJSON', views.FirstGraphJSON.as_view(), name='line_chart_json'),

    # Cat1
    path('cat1/', views.CategoryListView.as_view(),
         name='list_cat'),
    path('cat1/<int:pk>/', views.CategoryDetailView.as_view(),
         name='details_cat'),
    path('cat1/add/', views.CreateCat1.as_view(),
         name='create_cat'),
    path('cat1/ac/', views.AutocompleteCat1.as_view(),
         name='autocomplete_cat1'),

    # Cat2
    path('cat2/<int:pk>/', views.SubCategoryDetailView.as_view(),
         name='details_subcat'),
    path('cat2/add/', views.CreateCat2.as_view(),
         name='create_cat2'),
    path('cat2/ac/', views.AutocompleteCat2.as_view(),
         name='autocomplete_cat2'),
    path('ajax/load-cat2/', views.load_cat2,
         name='ajax_load_cat2'),

    # Transaction
    path('<int:pk>/saveTransaction/', views.saveTransaction,
         name='saveTransaction'),
    path('transaction/<int:pk>/', views.TransactionDetailView.as_view(),
         name='details_transaction'),
    path('transaction/<int:pk>/', views.TransactionDetailView.as_view(),
         name='details_transaction_Audit'),
    path('calendar/', views.TransactionCalendarView.as_view(),
         name='calendar_transaction'),
    path('list/', views.TransactionListView.as_view(),
         name='list_transaction'),


    # AccountAudit
    path('accountaudit/<int:pk>/', views.TransactionDetailView.as_view(),
         name='details_accountaudit'),

    # BudgetedEvent
    path('budgetedEvent/', views.budgetedEventsListView.as_view(),
         name='list_be'),
    path('budgetedEvent/<int:pk>/', views.BudgetedEventDetailView.as_view(),
         name='details_be'),
    path('budgetedEvent/add/', views.BudgetedEventCreateView.as_view(),
         name='add_be'),
    path('budgetedEvent/add/submit/', views.BudgetedEventSubmit,
         name='submit_be'),
    path('budgetedEvent/mod/<int:pk>/', views.BudgetedEventView.as_view(),
         name='change_be'),

    # Vendor
    path('vendor/ac/', views.AutocompleteVendor.as_view(),
         name='autocomplete_vendor'),
    path('vendor/add/', views.CreateVendor.as_view(),
         name='create_vendor'),

    # Account
    path('account/', views.AccountListView.as_view(),
         name='list_account'),
    path('account/add/', views.CreateAccount.as_view(),
         name='create_account'),
    path('account/ac/', views.AutocompleteAccount.as_view(),
         name='autocomplete_account'),
    path('account/list/<int:pk>/', views.AccountperiodicView3.as_view(),
         name='list_account_activity'),

    # Graph
    path('graph/', views.FirstGraph.as_view(),
         name='graph'),

]
