# budgetdb
https://github.com/mathieugfortin/budgetdb

I always find existing budget software lack at projecting to the future.  

With this, you can track all transactions in all your accounts.  
No data import, everything must be entered manually.

If I can file most of my repetitive expenses, use lump sums for areas where details are not available, there is no reason I can't have a pretty acurate view of my situation in a year or two.

From there, if I change a few parameters, tweak my savings a bit, cut an expense, increase mortgage payment by 10%, I can see real results for the short and medium terms.

Container needs a config file or environment variables with these variable names:
DEBUG(defaults to False), 
SECRET_KEY, 
DB_PASSWORD, 
DB_HOST, 
DB_PORT, 
DB_NAME, 
DB_USER, 
ALLOWED_HOSTS (comma separated list)

For email config, these are the env. variables:
EMAIL_BACKEND, default='django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST, default='smtp.gmail.com'
EMAIL_USE_SSL, default=False
EMAIL_USE_TLS, default=True
EMAIL_PORT, default=587
EMAIL_HOST_USER, no default
EMAIL_HOST_PASSWORD, no default

need more to handle CSRF_TRUSTED_ORIGINS...
