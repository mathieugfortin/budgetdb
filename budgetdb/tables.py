import django_tables2 as tables
from .models import BudgetedEvent
from django.utils.html import format_html
from django.urls import reverse


class BudgetedEventListTable(tables.Table):
    lastTransactionDate = tables.Column(verbose_name='Last planned transaction', orderable=False)

    class Meta:
        model = BudgetedEvent
        fields = ("description", "lastTransactionDate")
        attrs = {"class": "table table-hover"}
        # per_page = 30

    def render_description(self, value, record):
        return format_html('<a href="{}">{}</a>',
                           reverse('budgetdb:details_be', kwargs={'pk': record.id}),
                           value, record.description)

    def render_lastTransactionDate(self, value, record):
        if value == "No Transaction":
            # return format_html('<div class="alert alert-danger" role="alert">{}</div>', value)
            return format_html('<button type="button" class="btn btn-danger">{}</button>', value)
        else:
            return format_html('{}', value)
