import datetime
from datetime import date

from django.test import TestCase
from django.utils import timezone

from .models import BudgetedEvent, CatBudget


class BudgetedEventTests(TestCase):
    # fixtures = ["budgetdb/fixtures/calendarfixture.json"]

    def test_BudgetedEvent_recurring_match(self):
        dateCheck = datetime.date.today()
        budgetedEvent = BudgetedEvent(repeat_start=dateCheck)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_not_recurring_match(self):
        dateCheck = datetime.date.today()
        budgetedEvent = BudgetedEvent(repeat_start=dateCheck, isrecurring=False)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_repeat_start_after_date_checked(self):
        dateCheck = datetime.date.today()
        budgetedEvent = BudgetedEvent(repeat_start=dateCheck)
        dateCheck = dateCheck + datetime.timedelta(days=-1)
        self.assertIs(budgetedEvent.checkDate(dateCheck), False)

    def test_BudgetedEvent_not_recurring_no_match(self):
        dateCheck = datetime.date.today()
        budgetedEvent = BudgetedEvent(repeat_start=dateCheck, isrecurring=False)
        dateCheck = dateCheck + datetime.timedelta(days=1)
        self.assertIs(budgetedEvent.checkDate(dateCheck), False)

    def test_BudgetedEvent_repeat_start_matches_date_checked_repeat_interval_days_n0(self):
        dateCheck = datetime.date.today()
        interval = 2
        budgetedEvent = BudgetedEvent(repeat_start=dateCheck, repeat_interval_days=interval)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_repeat_interval_days_bad(self):
        dateCheck = datetime.date.today()
        interval = 2
        budgetedEvent = BudgetedEvent(repeat_start=dateCheck, repeat_interval_days=interval)
        dateCheck = dateCheck + datetime.timedelta(days=1)
        self.assertIs(budgetedEvent.checkDate(dateCheck), False)

    def test_BudgetedEvent_repeat_start_matches_date_checked_repeat_interval_days_n1(self):
        dateCheck = datetime.date.today()
        interval = 2
        budgetedEvent = BudgetedEvent(repeat_start=dateCheck, repeat_interval_days=interval)
        dateCheck = dateCheck + datetime.timedelta(days=interval)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_repeat_start_matches_date_checked_repeat_interval_days_n2(self):
        dateCheck = datetime.date.today()
        interval = 2
        budgetedEvent = BudgetedEvent(repeat_start=dateCheck, repeat_interval_days=interval)
        dateCheck = dateCheck + datetime.timedelta(days=2 * interval)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_repeat_start_matches_date_checked_repeat_interval_days_nm1(self):
        dateCheck = datetime.date.today()
        interval = 2
        budgetedEvent = BudgetedEvent(repeat_start=dateCheck, repeat_interval_days=interval)
        dateCheck = dateCheck + datetime.timedelta(days=-interval)
        self.assertIs(budgetedEvent.checkDate(dateCheck), False)

    def test_BudgetedEvent_repeat_start_matches_date_checked_repeat_interval_years_n1(self):
        dateCheck = datetime.date.today()
        interval = 2
        budgetedEvent = BudgetedEvent(repeat_start=dateCheck, repeat_interval_years=interval)
        dateCheck = date(dateCheck.year + interval, dateCheck.month, dateCheck.day)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_repeat_start_matches_date_checked_repeat_interval_years_n2(self):
        dateCheck = datetime.date.today()
        interval = 2
        budgetedEvent = BudgetedEvent(repeat_start=dateCheck, repeat_interval_years=interval)
        dateCheck = date(dateCheck.year + 2*interval, dateCheck.month, dateCheck.day)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_repeat_start_matches_date_checked_repeat_interval_years_nm1(self):
        dateCheck = datetime.date.today()
        interval = 2
        budgetedEvent = BudgetedEvent(repeat_start=dateCheck, repeat_interval_years=interval)
        dateCheck = date(dateCheck.year + 1, dateCheck.month, dateCheck.day)
        self.assertIs(budgetedEvent.checkDate(dateCheck), False)

    def test_BudgetedEvent_repeat_start_matches_date_checked_repeat_interval_years_nm2(self):
        dateCheck = datetime.date.today()
        interval = 2
        budgetedEvent = BudgetedEvent(repeat_start=dateCheck, repeat_interval_years=interval)
        dateCheck = date(dateCheck.year + interval, dateCheck.month + 1, dateCheck.day)
        self.assertIs(budgetedEvent.checkDate(dateCheck), False)

    def test_BudgetedEvent_matches_weekdaymask1(self):
        dateCheck = datetime.date(2019, 12, 23)  # Monday, mask = 1, dec 23 is a monday
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 1), repeat_weekday_mask=1)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_matches_weekdaymask1b(self):
        dateCheck = datetime.date(2019, 12, 24)  # Monday, mask = 1, dec 24 is a Tuesday
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 1), repeat_weekday_mask=1)
        self.assertIs(budgetedEvent.checkDate(dateCheck), False)

    def test_BudgetedEvent_matches_weekdaymask2(self):
        dateCheck = datetime.date(2019, 12, 24)  # Tuesday, mask = 2, dec 24 is a Tuesday
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 1), repeat_weekday_mask=2)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_matches_weekdaymask2b(self):
        dateCheck = datetime.date(2019, 12, 25)  # Tuesday, mask = 2, dec 25 is a Wednesday
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 1), repeat_weekday_mask=2)
        self.assertIs(budgetedEvent.checkDate(dateCheck), False)

    def test_BudgetedEvent_matches_weekdaymask3(self):
        dateCheck = datetime.date(2019, 12, 25)  # Wednesday, mask = 4, dec 25 is a Wednesday
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 1), repeat_weekday_mask=4)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_matches_weekdaymask4(self):
        dateCheck = datetime.date(2019, 12, 26)  # Thursday, mask = 8, dec 26 is a Thursday
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 1), repeat_weekday_mask=8)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_matches_weekdaymask5(self):
        dateCheck = datetime.date(2019, 12, 27)  # Friday, mask = 16, dec 27 is a Friday
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 1), repeat_weekday_mask=16)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_matches_weekdaymask6(self):
        dateCheck = datetime.date(2019, 12, 28)  # Saturday, mask = 32, dec 28 is a Saturday
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 1), repeat_weekday_mask=32)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_matches_weekdaymask7(self):
        dateCheck = datetime.date(2019, 12, 29)  # Sunday, mask = 64, dec 29 is a Sunday
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 1), repeat_weekday_mask=64)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_matches_weekdaymask_multiple(self):
        dateCheck = datetime.date(2019, 12, 24)  # Tuesday, mask = 15 0001111, dec 24 is a Tuesday
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 1), repeat_weekday_mask=15)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_matches_weekdaymask_multiplebad(self):
        dateCheck = datetime.date(2019, 12, 24)  # Tuesday, mask = 48  0110000, dec 24 is a Tuesday
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 1), repeat_weekday_mask=48)
        self.assertIs(budgetedEvent.checkDate(dateCheck), False)

    def test_BudgetedEvent_matches_monthmask1(self):
        dateCheck = datetime.date(2020, 1, 23)
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 23), repeat_months_mask=1)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_matches_monthmask1b(self):
        dateCheck = datetime.date(2019, 12, 23)
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 1), repeat_months_mask=1)
        self.assertIs(budgetedEvent.checkDate(dateCheck), False)

    def test_BudgetedEvent_matches_monthmask2(self):
        dateCheck = datetime.date(2019, 12, 23)   # 2048 = 100 000 000 000
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 12, 23), repeat_months_mask=2048)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_matches_monthmask2b(self):
        dateCheck = datetime.date(2019, 12, 23)   # 2048 = 100 000 000 000
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 23), repeat_months_mask=2048)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_matches_monthmask2c(self):
        dateCheck = datetime.date(2020, 11, 23)   # 2048 = 100 000 000 000
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 23), repeat_months_mask=2048)
        self.assertIs(budgetedEvent.checkDate(dateCheck), False)

    def test_BudgetedEvent_matches_monthmask3(self):
        dateCheck = datetime.date(2019, 4, 23)   # 255 = 11 111 111
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 23), repeat_months_mask=255)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_matches_monthmask3b(self):
        dateCheck = datetime.date(2019, 4, 22)   # 255 = 11 111 111
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 23), repeat_months_mask=255)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_matches_monthmask3c(self):
        dateCheck = datetime.date(2019, 4, 5)   # 255 = 11 111 111
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 4), repeat_months_mask=255, repeat_dayofmonth_mask=8)
        self.assertIs(budgetedEvent.checkDate(dateCheck), False)

    def test_BudgetedEvent_matches_monthmask4(self):
        dateCheck = datetime.date(2019, 4, 23)
        # mask is for month 12 and 11: 1036=110 000 000 000,
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 23), repeat_months_mask=3072)
        self.assertIs(budgetedEvent.checkDate(dateCheck), False)

    def test_BudgetedEvent_matches_dayofmonthmask1(self):
        dateCheck = datetime.date(2019, 4, 10)
        # mask is for day 11 and 10: 1036=11 000 000 000, 10th bit is SET
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 1), repeat_dayofmonth_mask=1536)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_matches_dayofmonthmask2(self):
        dateCheck = datetime.date(2019, 4, 9)
        # mask is for day 11 and 10: 1036=11 000 000 000, 9th bit is NOT set
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2019, 1, 1), repeat_dayofmonth_mask=1536)
        self.assertIs(budgetedEvent.checkDate(dateCheck), False)

    def test_BudgetedEvent_matches_weekofmonthmask1(self):
        dateCheck = datetime.date(2021, 3, 3)
        # mask is for day wednesday of week 1 and 4: 9=01001, 4th week bit is SET, 3rd bit of weekday is set
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2021, 3, 2), repeat_weekofmonth_mask=9, repeat_weekday_mask=4)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_matches_weekofmonthmask1b(self):
        dateCheck = datetime.date(2021, 3, 4)
        # mask is for day wednesday of week 1 and 4: 9=01001, 4th week bit is SET, 3rd bit of weekday is set
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2021, 3, 2), repeat_weekofmonth_mask=9, repeat_weekday_mask=4)
        self.assertIs(budgetedEvent.checkDate(dateCheck), False)

    def test_BudgetedEvent_matches_weekofmonthmask2(self):
        dateCheck = datetime.date(2021, 3, 24)
        # mask is for day wednesday of week 1 and 4: 9=01001, 4th week bit is SET, 3rd bit of weekday is set
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2021, 3, 2), repeat_weekofmonth_mask=9, repeat_weekday_mask=4)
        self.assertIs(budgetedEvent.checkDate(dateCheck), True)

    def test_BudgetedEvent_matches_weekofmonthmask2b(self):
        dateCheck = datetime.date(2021, 3, 17)
        # mask is for day wednesday of week 1 and 4: 9=01001, 4th week bit is SET, 3rd bit of weekday is set
        budgetedEvent = BudgetedEvent(repeat_start=datetime.date(2021, 3, 2), repeat_weekofmonth_mask=9, repeat_weekday_mask=4)
        self.assertIs(budgetedEvent.checkDate(dateCheck), False)

#    def test_BudgetedEvent_listNextTransactions(self):
#        repeat_start = datetime.date(2021, 3, 2)
#        be1 = BudgetedEvent(repeat_start=repeat_start, repeat_interval_days=2, repeat_weekday_mask=31)
#        print(be1.listNextTransactions(n=60, begin_interval=repeat_start, interval_length_months=1))
#        self.assertTrue(False)

    def test_CatBudget_1(self):
        cb1 = CatBudget(amount=10, amount_frequency='D')
        self.assertTrue(cb1.budget_daily() == 10)

    def test_CatBudget_2(self):
        cb1 = CatBudget(amount=10, amount_frequency='D')
        self.assertTrue(cb1.budget_weekly() == 70)

    def test_CatBudget_3(self):
        cb1 = CatBudget(amount=10, amount_frequency='D')
        self.assertTrue(cb1.budget_monthly() == 300)

    def test_CatBudget_4(self):
        cb1 = CatBudget(amount=10, amount_frequency='D')
        self.assertTrue(cb1.budget_yearly() == 3650)

    def test_CatBudget_1B(self):
        cb1 = CatBudget(amount=70, amount_frequency='W')
        self.assertTrue(cb1.budget_daily() == 10)

    def test_CatBudget_2B(self):
        cb1 = CatBudget(amount=10, amount_frequency='W')
        self.assertTrue(cb1.budget_weekly() == 10)

    def test_CatBudget_3B(self):
        cb1 = CatBudget(amount=10, amount_frequency='W')
        self.assertTrue(cb1.budget_monthly() == 43.3)

    def test_CatBudget_4B(self):
        cb1 = CatBudget(amount=10, amount_frequency='W')
        self.assertTrue(cb1.budget_yearly() == 520)

    def test_CatBudget_1c(self):
        cb1 = CatBudget(amount=300, amount_frequency='M')
        self.assertTrue(cb1.budget_daily() == 10)

    def test_CatBudget_2c(self):
        cb1 = CatBudget(amount=433, amount_frequency='M')
        self.assertTrue(cb1.budget_weekly() == 100)

    def test_CatBudget_3c(self):
        cb1 = CatBudget(amount=10, amount_frequency='M')
        self.assertTrue(cb1.budget_monthly() == 10)

    def test_CatBudget_4c(self):
        cb1 = CatBudget(amount=10, amount_frequency='M')
        self.assertTrue(cb1.budget_yearly() == 120)

    def test_CatBudget_1D(self):
        cb1 = CatBudget(amount=365, amount_frequency='Y')
        self.assertTrue(cb1.budget_daily() == 1)

    def test_CatBudget_2D(self):
        cb1 = CatBudget(amount=520, amount_frequency='Y')
        self.assertTrue(cb1.budget_weekly() == 10)

    def test_CatBudget_3D(self):
        cb1 = CatBudget(amount=120, amount_frequency='Y')
        self.assertTrue(cb1.budget_monthly() == 10)

    def test_CatBudget_4D(self):
        cb1 = CatBudget(amount=10, amount_frequency='Y')
        self.assertTrue(cb1.budget_yearly() == 10)
