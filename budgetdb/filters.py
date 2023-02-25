import django_filters
from .models import BudgetedEvent


class BudgetedEventFilter(django_filters.FilterSet):
    description = django_filters.CharFilter(lookup_expr='iexact')

    class Meta:
        model = BudgetedEvent
        fields = ['description']