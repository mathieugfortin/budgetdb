from django.urls import path, register_converter, include

from . import views


class FourDigitYearConverter:
    regex = '[0-9]{4}'

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return '%04d' % value


class TwoDigitMonthConverter:
    regex = '[0-9]{2}'

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return '%04d' % value


class TwoDigitDayConverter:
    regex = '[0-9]{2}'

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return '%04d' % value


register_converter(FourDigitYearConverter, 'yyyy')
register_converter(TwoDigitMonthConverter, 'mm')
register_converter(TwoDigitDayConverter, 'dd')

app_name = 'budgetdb'

urlpatterns = [
    path('', views.IndexView.as_view(), name='home'),

    path('preference/getJSON', views.PreferenceGetJSON,
         name='preferences_json'),
    path('preference/setIntervalJSON', views.PreferenceSetIntervalJSON,
         name='setinterval_json'),

    # User
    path('user/signup/', views.UserSignupView.as_view(),
         name='signup'),
    path('user/login/', views.UserLoginView.as_view(),
         name='login'),

    ##########################################################################################################
    # redirects
    path('account/max_redirect/<int:pk>/', views.ObjectMaxRedirect.as_view(model='Account'),
         name='account_max_redirect'),
    path('accountHost/max_redirect/<int:pk>/', views.ObjectMaxRedirect.as_view(model='AccountHost'),
         name='accounthost_max_redirect'),
    path('accountcat/max_redirect/<int:pk>/', views.ObjectMaxRedirect.as_view(model='AccountCategory'),
         name='accountcategory_max_redirect'),
    path('cat1/max_redirect/<int:pk>/', views.ObjectMaxRedirect.as_view(model='Cat1'),
         name='cat1_max_redirect'),
    path('cat2/max_redirect/<int:pk>/', views.ObjectMaxRedirect.as_view(model='Cat2'),
         name='cat2_max_redirect'),
    path('cattype/max_redirect/<int:pk>/', views.ObjectMaxRedirect.as_view(model='CatType'),
         name='cattype_max_redirect'),
    path('catbudget/max_redirect/<int:pk>/', views.ObjectMaxRedirect.as_view(model='CatBudget'),
         name='catbudget_max_redirect'),
    path('vendor/max_redirect/<int:pk>/', views.ObjectMaxRedirect.as_view(model='Vendor'),
         name='vendor_max_redirect'),
    path('transaction/max_redirect/<int:pk>/', views.ObjectMaxRedirect.as_view(model='Transaction'),
         name='transaction_max_redirect'),

    # Account
    path('account/ListJSON', views.GetAccountViewListJSON,
         name='account_list_view_json'),
    path('account/ListDetailedJSON', views.GetAccountDetailedViewListJSON,
         name='account_list_detailed_view_json'),
    path('account/', views.AccountListViewSimple.as_view(),
         name='list_account_simple'),
    path('account/details', views.AccountSummaryView.as_view(),
         name='list_account_summary'),
    path('account/<int:pk>/', views.AccountDetailView.as_view(),
         name='details_account'),
    path('account/add/', views.AccountCreateView.as_view(),
         name='create_account'),
    path('account/update/<int:pk>/', views.AccountUpdateView.as_view(),
         name='update_account'),
    path('account/ac/', views.AutocompleteAccount.as_view(),
         name='autocomplete_account'),
    path('account/listactivity/<int:pk>/', views.AccountListActivityView.as_view(),
         name='list_account_activity'),

    # AccountCategory
    path('accountcat/ListJSON', views.GetAccountCatViewListJSON, name='accountcat_view_list_json'),
    path('accountcat/<int:pk>/', views.AccountCatDetailView.as_view(),
         name='details_accountcategory'),
    path('accountcat/update/<int:pk>/', views.AccountCatUpdateView.as_view(),
         name='update_accountcategory'),
    path('accountcat/', views.AccountCatListView.as_view(),
         name='list_accountcategory'),
    path('accountcat/add/', views.AccountCatCreateView.as_view(),
         name='create_accountcategory'),

    # Account_Host
    path('accountHost/ListJSON', views.GetAccountHostViewListJSON, name='account_host_list_json'),
    path('accountHost/<int:pk>/', views.AccountHostDetailView.as_view(),
         name='details_accounthost'),
    path('accountHost/add/', views.AccountHostCreateView.as_view(),
         name='create_accounthost'),
    path('accountHost/update/<int:pk>/', views.AccountHostUpdateView.as_view(),
         name='update_accounthost'),
    path('accountHost/', views.AccountHostListView.as_view(),
         name='list_accounthost'),

    # chart JS
    path('timeline2/', views.timeline2.as_view(), name='timeline_chart'),
    path('timeline2JSON', views.timeline2JSON, name='timeline2_chart_json'),

    # Cat1
    path('cat1/PieChartJSON', views.GetCat1TotalPieChartData, name='cat1_piechart_json'),
    path('cat1/BarChartJSON', views.GetCat1TotalBarChartData, name='cat1_barchart_json'),
    path('cat1/ListJSON', views.GetCat1ListJSON, name='cat1_list_json'),
    path('cat1/', views.Cat1ListView.as_view(),
         name='list_cat1'),
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
    path('cat2/BarChartJSON', views.GetCat2TotalBarChartData, name='cat2_barchart_json'),
    path('cat2/', views.Cat2ListView.as_view(),
         name='list_cat2'),
    path('cat2/<int:pk>/', views.Cat2DetailView.as_view(),
         name='details_cat2'),
    path('cat2/add/<int:cat1_id>', views.Cat2CreateView.as_view(),
         name='create_cat2'),
    path('cat2/update/<int:pk>/', views.Cat2UpdateView.as_view(),
         name='update_cat2'),
    path('cat2/ac/', views.AutocompleteCat2.as_view(),
         name='autocomplete_cat2'),
    path('ajax/load-cat2/', views.load_cat2,
         name='ajax_load_cat2'),

    # CatType
    path('cattype/ListJSON', views.GetCatTypeListJSON, name='cattype_list_json'),
    path('cattype/pie-chart/<int:cat_type_pk>', views.CatTotalPieChart.as_view(), name='cattype_pie'),
    path('cattype/bar-chart/<int:cat_type_pk>', views.CatTotalBarChart.as_view(), name='cattype_bar'),

    path('cattype/', views.CatTypeListView.as_view(),
         name='list_cattype'),
    path('cattype/<int:pk>/', views.CatTypeDetailView.as_view(),
         name='details_cattype'),
    path('cattype/add/', views.CatTypeCreateView.as_view(),
         name='create_cattype'),
    path('cattype/update/<int:pk>/', views.CatTypeUpdateView.as_view(),
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

    # Preferences
    path('preferences/update/', views.PreferencesUpdateView.as_view(),
         name='update_preferences'),

    # Statement
    path('statement/', views.StatementListView.as_view(),
         name='list_statement'),
    path('statement/<int:pk>/', views.StatementDetailView.as_view(),
         name='details_statement'),
    path('statement/create/', views.StatementCreateView.as_view(),
         name='create_statement'),
    path('statement/update/<int:pk>/', views.StatementUpdateView.as_view(),
         name='update_statement'),

    # Transaction
    path('transaction/toggleverifyJSON', views.TransactionVerifyToggleJSON,
         name='toggleverifytransaction_json'),
    path('transaction/togglereceiptJSON', views.TransactionReceiptToggleJSON,
         name='togglereceipttransaction_json'),
    path('<int:pk>/saveTransaction/', views.saveTransaction,
         name='saveTransaction'),
    path('transaction/<int:pk>/', views.TransactionDetailView.as_view(),
         name='details_transaction'),
    path('transaction/add/', views.TransactionCreateView.as_view(),
         name='create_transaction'),
    path('transaction/delete/<int:pk>/', views.TransactionDelete,
         name='delete_transaction'),
    path('transaction/add/<slug:date>/<int:account_pk>', views.TransactionCreateViewFromDateAccount.as_view(),
         name='create_transaction_from_date_account'),
    path('transaction/add/<int:account_pk>', views.TransactionCreateViewFromDateAccount.as_view(),
         name='create_transaction_from_date_account'),
    path('transaction/addaudit/<slug:date>/<int:account_pk>/<slug:amount>', views.TransactionAuditCreateViewFromDateAccount.as_view(),
         name='create_transaction_audit_from_account'),
    path('transaction/addaudit/<int:account_pk>', views.TransactionAuditCreateViewFromDateAccount.as_view(),
         name='create_transaction_audit_from_account'),
    path('transaction/update/<int:pk>/', views.TransactionUpdateView.as_view(),
         name='update_transaction'),
    path('transaction/update_popup/<int:pk>/', views.TransactionUpdatePopupView.as_view(),
         name='update_transaction_popup'),
    path('transaction/update_modal/<int:pk>/', views.TransactionModalUpdate.as_view(),
         name='update_transaction_modal'),
    # path('audit/<int:pk>/', views..as_view(),
    #      name='details_Audit'),
    path('calendar/', views.TransactionCalendarView.as_view(),
         name='calendar_transaction'),
    path('transaction/list/', views.TransactionListView.as_view(),
         name='list_transaction'),
    path('transaction/unverified_list/', views.TransactionUnverifiedListView.as_view(),
         name='list_unverified_transaction'),
    path('transaction/manual_list/', views.TransactionManualListView.as_view(),
         name='list_manual_transaction'),
    path('ajax/load-payment-transaction/', views.load_payment_transaction,
         name='ajax_load_payment_transaction'),

    # Joined Transactions
    path('joinedtransactions/list/', views.JoinedTransactionListView.as_view(),
         name='list_joinedtransactions'),   
    path('joinedtransactions/add/', views.JoinedTransactionsUpdateView.as_view(),
         name='create_joinedtransactions'),
    # path('joinedtransactions/update/<int:pk>/<yyyy:year>/<mm:month>/<dd:day>', views.JoinedTransactionsUpdateView.as_view(),
    path('joinedtransactions/update/<int:pk>/<slug:date>/', views.JoinedTransactionsUpdateView.as_view(),
         name='update_joinedtransactions'),
    path('joinedtransactions/<int:pk>/<slug:date>/', views.JoinedTransactionsDetailView.as_view(),
         name='details_joinedtransactions'),

    # Vendor
    path('vendorListJSON', views.GetVendorListJSON, name='vendor_list_json'),
    path('vendor/', views.VendorListView.as_view(),
         name='list_vendor'),
    path('vendor/<int:pk>/', views.VendorDetailView.as_view(),
         name='details_vendor'),
    path('vendor/add/', views.VendorCreateView.as_view(),
         name='create_vendor'),
    path('vendor/update/<int:pk>/', views.VendorUpdateView.as_view(),
         name='update_vendor'),
    path('vendor/ac/', views.AutocompleteVendor.as_view(),
         name='autocomplete_vendor'),
]
