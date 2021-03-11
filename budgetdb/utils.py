from datetime import datetime, timedelta
from calendar import HTMLCalendar
from django.urls import reverse, reverse_lazy
from .models import CalendarView


class Calendar(HTMLCalendar):
    def __init__(self, year=None, month=None):
        self.year = year
        self.month = month
        super(Calendar, self).__init__()

    def formatday(self, day, events):
        events_per_day = events.filter(db_date__day=day)
        d = ''
        for event in events_per_day:
            if event.budgetedevent_id is not None:
                d += F"<li> <a href=\"{reverse('budgetdb:details_be',args=[event.budgetedevent_id])}\"> {event.BE_description} </a></li>"
            if event.transaction_id is not None:
                d += F"<li> <a href=\"{reverse('budgetdb:details_transaction',args=[event.transaction_id])}\"> {event.T_description} </a></li>"

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
        events = CalendarView.objects.filter(db_date__year=self.year, db_date__month=self.month)

        cal = f'<table border="0" cellpadding="0" cellspacing="0" class="calendar">\n'
        cal += f'{self.formatmonthname(self.year, self.month, withyear=withyear)}\n'
        cal += f'{self.formatweekheader()}\n'
        for week in self.monthdays2calendar(self.year, self.month):
            cal += f'{self.formatweek(week, events)}\n'
        return cal

    def formatdaylist(self, day, events):
        events_per_day = events.filter(db_date__day=day)
        d = ''
        for event in events_per_day:
            if event.budgetedevent_id is not None:
                d += f'<td>{event.db_date}</td>'
                d += f'<td>{event.BE_description}</td><td>{event.BE_ammount}$</td>'
                d += f'<td>{event.BE_source}</td><td>{event.BE_destination}</td></tr>\n'
            if event.transaction_id is not None:
                d += f'<td>{event.db_date}</td>'
                d += f'<td>{event.T_description}</td><td>{event.T_ammount}$</td>'
                d += f'<td>{event.T_source}</td><td>{event.T_destination}</td></tr>\n'

        if day != 0:
            return d
        return '<td></td>'

    # formats a month as a list
    # filter events by year and month
    def formatmonthlist(self, withyear=True):
        events_per_month = CalendarView.objects.filter(db_date__year=self.year, db_date__month=self.month)
        cal = f'<table border="0" cellpadding="0" cellspacing="0" class="calendar" id="calendarlist">\n'
        cal += f'{self.formatmonthname(self.year, self.month, withyear=withyear)}\n'
        cal += f'<tr><th class="date">Date</th><th class="description">Description</th><th class="Ammount">Ammount</th><th class="source">Source</th><th class="destination">Destination</th></tr>\n'
        cal += f'<tr><td><input type="text" id="myDate" onkeyup="myFunctionDate()" placeholder="filter"></td>'
        cal += f'<td><input type="text" id="myDesc" onkeyup="myFunctionDesc()" placeholder="filter"></td>'
        cal += f'<td><input type="text" id="myAmm" onkeyup="myFunctionAmm()" placeholder="filter"></td>'
        cal += f'<td><input type="text" id="mySource" onkeyup="myFunctionSource()" placeholder="filter"></td>'
        cal += f'<td><input type="text" id="myDest" onkeyup="myFunctionDest()" placeholder="filter"></td></tr>\n'
        day = 0

        for event in events_per_month:
            if event.db_date.day != day:
                day = event.db_date.day
                cal += self.formatdaylist(day, events_per_month)

        return cal
