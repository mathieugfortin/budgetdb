# budgetdb
https://github.com/mathieugfortin/budgetdb

I always find existing budget software lack at projecting to the future.  

With this, you can track all transactions in all your accounts.  
No data import, everything must be entered manually.

If I can file most of my repetitive expenses, use lump sums for areas where details are not available, there is no reason I can't have a pretty acurate view of my situation in a year or two.

From there, if I change a few parameters, tweak my savings a bit, cut an expense, increase mortgage payment by 10%, I can see real results for the short and medium terms.

Container needs a config file or environment variables with these variable names:
DEBUG(defaults to False), SECRET_KEY, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME, DB_USER, APP_HOST1, APP_HOST2

need more to handle CSRF_TRUSTED_ORIGINS...
