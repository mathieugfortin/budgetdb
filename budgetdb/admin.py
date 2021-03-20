from django.contrib import admin

from .models import Cat1, Cat2, CatBudget, AccountHost, Account
from .models import Vendor, Transaction, BudgetedEvent

admin.site.site_header = "My Family Budget admin"


# class Cat2Inline(admin.StackedInline):
class Cat2Inline(admin.TabularInline):

    model = Cat2
    extra = 3


class Cat1Admin(admin.ModelAdmin):
    fieldsets = [
        (None,               {'fields': ['name',
                                         'CatBudget'
                                         ]
                              }
         ),
    ]
    inlines = [Cat2Inline]


admin.site.register(Cat1, Cat1Admin)


class Cat2Admin(admin.ModelAdmin):
    fields = ['name',
              'cat1',
              'CatBudget'
              ]
    list_filter = ('name', )


# admin.site.register(Cat2, Cat2Admin)
admin.site.register(CatBudget)
# admin.site.register(Account)


class AccountInline(admin.TabularInline):
    model = Account
    extra = 3


class AccountHostAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,               {'fields': ['name']}),
    ]
    inlines = [AccountInline]


admin.site.register(AccountHost, AccountHostAdmin)
admin.site.register(Vendor)
admin.site.register(Transaction)


class BudgetedEventAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,              {'fields': ['description',
                                        'cat2',
                                        'amount_planned',
                                        'repeat_start',
                                        'account_source',
                                        'account_destination',
                                        'vendor',
                                        'budget_only'
                                        ]
                             }
         ),
        ('Recurring event', {'fields': ['isrecurring',
                                        'repeat_interval_days',
                                        'repeat_interval_weeks',
                                        'repeat_interval_months',
                                        'repeat_interval_years',
                                        'months_mask',
#                                        'repeat_weekday_mask',
#                                        'repeat_dayofmonth_mask',
#                                        'repeat_months_mask',
#                                        'repeat_weekofmonth_mask',
                                        ]}),
    ]
    
admin.site.register(BudgetedEvent, BudgetedEventAdmin)
