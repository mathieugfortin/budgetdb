# budgetdb
I always find existing budget software lack at projecting to the future.  

If I can file most of my repetitive expenses, use lump sums for areas wher details are not available, there is no reason I can't have a pretty acurate view of my situation in  a year or two.

From there, if I change a few parameters, tweak my savings a bit, cut an expense, increase mortgage payment by 10%, I can see real results for the short and medium terms.

I used to have an excel sheet that did that pretty well but at over 12MB, debugging became a chore and it fell by the wayside.  This is an attempt at getting that back.




ToDo list:
Dynamic budgetedEvents are killing performance.  They should create unverified Transactions.  Handling of budgetedEvents change will be tricky

NEXT*****When BE changes, delete linked unverified transaction and create new ones. May fuck up the date_planned.  
    Do I even need date_planned?  Yes, to avoid creating a transaction on a transaction that was moved.  
    I will probably need a form to correct the orphan ones.  yerk


many cat1, cat2, views to finish
check if audit is the last event of the day...  order them so
TransactionListView uses calendars and it's slow, refactor like AccountperiodicView but for all accounts


Dynamic Total on chart?  
a chart with a running total per account category would be nice.  cashflow, savings, mortgage...




