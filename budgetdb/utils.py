from datetime import datetime, timedelta
from calendar import HTMLCalendar
from django.urls import reverse, reverse_lazy
from .models import Transaction


class Calendar(HTMLCalendar):
    def __init__(self, year=None, month=None):
        self.year = year
        self.month = month
        super(Calendar, self).__init__()

    def formatday(self, day, events):
        events_per_day = events.filter(date_actual__day=day, audit=0)
        d = ''
        for event in events_per_day:
            url = reverse(f'{event._meta.app_label}:details_transaction', args=[event.id])
            d += f'<li> <a href="{url}"> {event.description} </a></li>'
            d = d

        if day != 0:
            return f"<td><span class='date'>{day}</span><ul> {d} </ul></td>"
        return '<td></td>'

    # formats a week as a tr
    def formatweek(self, theweek, events):
        week = ''
        for d, weekday in theweek:
            week += self.formatday(d, events)
        return f'<tr> {week} </tr>'

    # formats a month as a table
    # filter events by year and month
    def formatmonth(self, withyear=True):
        events = Transaction.objects.filter(date_actual__year=self.year, date_actual__month=self.month)

        cal = f'<table border="0" cellpadding="0" cellspacing="0" class="calendar">\n'
        cal += f'{self.formatmonthname(self.year, self.month, withyear=withyear)}\n'
        cal += f'{self.formatweekheader()}\n'
        for week in self.monthdays2calendar(self.year, self.month):
            cal += f'{self.formatweek(week, events)}\n'
        return cal

    def formatdaylist(self, day, events):
        events_per_day = events.filter(date_actual__day=day)
        d = ''
        for event in events_per_day:
            url1 = reverse(f'{event._meta.app_label}:details_transaction', args=[event.id])      
            d += f'<td>{event.date_actual}</td>'
            d += f'<td> <a href="{url1}"> {event.description} </a></td>'
            d += f'<td>{event.amount_actual}$</td>'
            d += f'<td>{event.account_source}</td><td>{event.account_destination}</td>'
            if event.BudgetedEvent_id is None:
                d += f'<td>None</td>'
            else:
                url2 = reverse(f'{event._meta.app_label}:details_be', args=[event.BudgetedEvent_id])
                d += f'<td> <a href="{url2}"> {event.BudgetedEvent} </a></td>'
            d += f'</tr>\n'

        if day != 0:
            return d
        return '<td></td>'

    # formats a month as a list
    # filter events by year and month
    def formatmonthlist(self, withyear=True):
        events_per_month = Transaction.objects.filter(date_actual__year=self.year, date_actual__month=self.month)
        cal = f'<table border="0" cellpadding="0" cellspacing="0" class="calendar" id="calendarlist">\n'
        cal += f'{self.formatmonthname(self.year, self.month, withyear=withyear)}\n'
        cal += f'<tr><th class="date">Date</th><th class="description">Description</th><th class="Ammount">Ammount</th><th class="source">Source</th><th class="destination">Destination</th><th class="destination">Recurence</th></tr>\n'
        cal += f'<tr><td><input type="text" id="myDate" onkeyup="myFunctionDate()" placeholder="filter"></td>'
        cal += f'<td><input type="text" id="myDesc" onkeyup="myFunctionDesc()" placeholder="filter"></td>'
        cal += f'<td><input type="text" id="myAmm" onkeyup="myFunctionAmm()" placeholder="filter"></td>'
        cal += f'<td><input type="text" id="mySource" onkeyup="myFunctionSource()" placeholder="filter"></td>'
        cal += f'<td><input type="text" id="myDest" onkeyup="myFunctionDest()" placeholder="filter"></td>'
        cal += f'<td><input type="text" id="myBE" onkeyup="myFunctionBE()" placeholder="filter"></td></tr>\n'
        day = 0

        for event in events_per_month:
            if event.date_actual.day != day:
                day = event.date_actual.day
                cal += self.formatdaylist(day, events_per_month)

        return cal


class Bitmap():
    bits = []
    n = 0

    def __init__(self, n):
        self.n = n
        self.bits = [False for i in range(n)]

    def __str__(self):
        intvalue = 0
        for i in range(n):
            intvalue += 2**n*bits[n]
        return intvalue
