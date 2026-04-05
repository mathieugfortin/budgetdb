from django import template
from datetime import date

register = template.Library()

@register.filter
def display_amount(record, view_account):
    """
    Returns the amount with the correct sign based on 
    whether the current view is the source or destination.
    """
    if record.audit:
        return ""
        
    value = record.amount_actual
    
    # If it's only a budget placeholder 
    if record.budget_only is True and record.date_actual <= date.today():
        return ""

    # If the current account is the source, it's an outflow (negative)    
    if view_account and value != 0 and record.account_source == view_account:
        return value * -1
        
    return value