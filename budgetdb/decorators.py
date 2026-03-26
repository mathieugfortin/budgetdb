from django.http import JsonResponse
from functools import wraps

def login_required_ajax(view_func):
    @wraps(view_func) # This preserves the original function's name and docstring
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper