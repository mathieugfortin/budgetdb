from django import template

register = template.Library()

@register.filter(name='has_no_numbers')
def has_no_numbers(value):
    """
    Returns True if the string contains NO digits (0-9).
    """
    # Ensure we are working with a string
    string_value = str(value)
    
    # any() returns True if it finds a digit; we flip it with 'not'
    return not any(char.isdigit() for char in string_value)
