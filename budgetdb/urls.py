from django.urls import path

from . import views

# from budgetdb.views import Cat1DetailView, TransactionDetailView,
# # saveTransaction, BudgetedEventList

app_name = 'budgetdb'

urlpatterns = [
    path('', views.IndexView.as_view(), name='home'),

   

    path('preference/getJSON', views.PreferenceGetJSON, name='preferences_json'),
    path('preference/setIntervalJSON', views.PreferenceSetIntervalJSON, name='setinterval_json'),
    
    # Account
    path('account/ListJSON', views.GetAccountListJSON, name='account_list_json'),
    path('account/', views.AccountListView.as_view(),
         name='list_account'),
    path('account/<int:pk>/', views.AccountDetailView.as_view(),
         name='details_account'),
    path('account/add/', views.AccountCreateView.as_view(),
         name='create_account'),
    path('account/update/<int:pk>/', views.AccountUpdateView.as_view(),
         name='update_account'),
    path('account/ac/', views.AutocompleteAccount.as_view(),
         name='autocomplete_account'),

    path('account/list/<int:pk>/', views.AccountperiodicView.as_view(),
         name='list_account_activity'),

    # AccountCategory
    path('accountcat/ListJSON', views.GetAccountCatListJSON, name='accountcat_list_json'),

    # Account_Host
    path('accountHost/ListJSON', views.GetAccountHostListJSON, name='account_host_list_json'),
    path('accountHost/<int:pk>/', views.AccountHostDetailView.as_view(),
         name='details_account_host'),
    path('accountHost/add/', views.AccountHostCreateView.as_view(),
         name='create_account_host'),
    path('accountHost/update/<int:pk>/', views.AccountHostUpdateView.as_view(),
         name='update_account_host'),
    path('accountHost/', views.AccountHostListView.as_view(),
         name='list_account_host'),


    # chart JS
    path('timeline2/', views.timeline2.as_view(), name='timeline_chart'),
    path('timeline2JSON', views.timeline2JSON, name='timeline2_chart_json'),

    # Cat1
    path('cat1/PieChartJSON', views.GetCat1TotalPieChartData, name='cat1_piechart_json'),
    path('cat1/ListJSON', views.GetCat1ListJSON, name='cat1_list_json'),
    path('cat1/', views.Cat1ListView.as_view(),
         name='list_cat'),
    path('cat1/<int:pk>/', views.Cat1DetailView.as_view(),
         name='details_cat1'),
    path('cat1/add/', views.Cat1CreateView.as_view(),
         name='create_cat1'),
    path('cat1/update/<int:pk>/', views.Cat1UpdateView.as_view(),
         name='update_cat1'),
    path('cat1/ac/', views.AutocompleteCat1.as_view(),
         name='autocomplete_cat1'),

    # Cat2
    path('cat2/PieChartJSON', views.GetCat2TotalPieChartData, name='cat2_piechart_json'),
    path('cat2/<int:pk>/', views.Cat2DetailView.as_view(),
         name='details_cat2'),
    path('cat2/add/<int:cat1_id>', views.Cat2Create.as_view(),
         name='create_cat2'),
    path('cat2/update/<int:pk>/', views.Cat2UpdateView.as_view(),
         name='update_cat2'),
    path('cat2/ac/', views.AutocompleteCat2.as_view(),
         name='autocomplete_cat2'),
    path('ajax/load-cat2/', views.load_cat2,
         name='ajax_load_cat2'),

    # CatType   *****details, create and update NOT IMPLEMENTED*****
    path('cattype/ListJSON', views.GetCatTypeListJSON, name='cattype_list_json'),
    path('cattype/pie-chart/<int:cat_type_pk>', views.CatTotalChart.as_view(), name='cat1_pie'),
    path('cattype/<int:pk>/', views.Cat2DetailView.as_view(),
         name='details_cattype'),
    path('cattype/add/', views.Cat2Create.as_view(),
         name='create_cattype'),
    path('cattype/update/<int:pk>/', views.Cat2UpdateView.as_view(),
         name='update_cattype'),

    # BudgetedEvent
    path('budgetedEvent/', views.budgetedEventsListView.as_view(),
         name='list_be'),
    path('budgetedEvent/<int:pk>/', views.BudgetedEventDetailView.as_view(),
         name='details_be'),
    path('budgetedEvent/create/', views.BudgetedEventCreate.as_view(),
         name='create_be'),
    path('budgetedEvent/createfromt/<int:transaction_id>/', views.BudgetedEventCreateFromTransaction.as_view(),
         name='create_be_from_t'),
    path('budgetedEvent/create/submit/', views.BudgetedEventSubmit,
         name='submit_be'),
    path('budgetedEvent/update/<int:pk>/', views.BudgetedEventUpdate.as_view(),
         name='update_be'),

    # Transaction
    path('transaction/toggleverifyJSON', views.TransactionVerifyToggleJSON,
         name='toggleverifytransaction_json'),
    path('<int:pk>/saveTransaction/', views.saveTransaction,
         name='saveTransaction'),
    path('transaction/<int:pk>/', views.TransactionDetailView.as_view(),
         name='details_transaction'),
    path('transaction/add/', views.TransactionCreateView.as_view(),
         name='create_transaction'),
    path('transaction/add/<slug:date>/<int:account_pk>', views.TransactionCreateViewFromDateAccount.as_view(),
         name='create_transaction_from_date_account'),
    path('transaction/update/<int:pk>/', views.TransactionUpdateView.as_view(),
         name='update_transaction'),
    path('transaction/<int:pk>/', views.TransactionDetailView.as_view(),
         name='details_transaction_Audit'),
    path('calendar/', views.TransactionCalendarView.as_view(),
         name='calendar_transaction'),
    path('transaction/list/', views.TransactionListView.as_view(),
         name='list_transaction'),

    # Vendor
    path('vendorListJSON', views.GetVendorListJSON, name='vendor_list_json'),
    path('vendor/', views.VendorListView.as_view(),
         name='list_vendor'),
    path('vendor/<int:pk>', views.VendorDetailView.as_view(),
         name='details_vendor'),
    path('vendor/add/', views.VendorCreate.as_view(),
         name='create_vendor'),
    path('vendor/update/<int:pk>/', views.VendorUpdateView.as_view(),
         name='update_vendor'),
    path('vendor/ac/', views.AutocompleteVendor.as_view(),
         name='autocomplete_vendor'),
]
