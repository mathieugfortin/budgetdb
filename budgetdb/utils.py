# from datetime import datetime
from calendar import HTMLCalendar
from django.urls import reverse, reverse_lazy
from ofxparse import OfxParser
from .models import Transaction, Statement, Vendor
from django.db.models import Q
import datetime

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
        events = Transaction.view_objects.filter(date_actual__year=self.year, date_actual__month=self.month).order_by("description")

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
            if event.can_view() is False:
                continue
            if event.audit == 1:
                d += f'<tr class="AUDIT">'
            elif event.budgetedevent_id is not None and event.verified == 0:
                d += f'<tr class="BUDGET">'
            elif event.verified == 0:
                d += f'<tr class="UNVERIFIED">'
            else:
                d += f'<tr>'

            url1 = reverse(f'{event._meta.app_label}:details_transaction', args=[event.id])
            d += f'<td>{event.date_actual}</td>'
            d += f'<td> <a href="{url1}"> {event.description} </a></td>'
            d += f'<td>{event.amount_actual}$</td>'
            d += f'<td>{event.account_source}</td><td>{event.account_destination}</td>'
            d += f'<td>{event.cat1}</td><td>{event.cat2}</td>'
            if event.budgetedevent_id is None:
                d += f'<td>None</td>'
            else:
                url2 = reverse(f'{event._meta.app_label}:details_be', args=[event.budgetedevent_id])
                d += f'<td> <a href="{url2}"> {event.budgetedevent} </a></td>'
            d += f'</tr>\n'

        if day != 0:
            return d
        return '<td></td>'

    # formats a month as a list
    # filter events by year and month
    def formatmonthlist(self, withyear=True):
        events_per_month = Transaction.view_objects.filter(date_actual__year=self.year, date_actual__month=self.month).order_by("date_actual")
        cal = f'<table border="0" cellpadding="0" cellspacing="0" class="calendar" id="calendarlist">\n'
        cal += f'{self.formatmonthname(self.year, self.month, withyear=withyear)}\n'
        cal += f'<tr>\n'
        cal += f'<th>Date</th><th>Description</th><th>amount</th>'
        cal += f'<th>Source</th><th>Destination</th>'
        cal += f'<th>Category</th><th>Subcategory</th>'
        cal += f'<th>Recurence</th>\n'
        cal += f'</tr>\n'
        cal += f'<tr>\n'
        cal += f'<td><input type="text" id="myDate" onkeyup="myFunctionDate()" placeholder="filter"></td>\n'
        cal += f'<td><input type="text" id="myDesc" onkeyup="myFunctionDesc()" placeholder="filter"></td>\n'
        cal += f'<td><input type="text" id="myAmm" onkeyup="myFunctionAmm()" placeholder="filter"></td>\n'
        cal += f'<td><input type="text" id="mySource" onkeyup="myFunctionSource()" placeholder="filter"></td>\n'
        cal += f'<td><input type="text" id="myDest" onkeyup="myFunctionDest()" placeholder="filter"></td>\n'
        cal += f'<td><input type="text" id="myCat1" onkeyup="myFunctionCat1()" placeholder="filter"></td>\n'
        cal += f'<td><input type="text" id="myCat2" onkeyup="myFunctionCat2()" placeholder="filter"></td>\n'
        cal += f'<td><input type="text" id="myBE" onkeyup="myFunctionBE()" placeholder="filter"></td>\n'
        cal += f'</tr>\n'
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
        for i in range(self.n):
            intvalue += 2**i*self.bits[i]
        return intvalue


def serialize_ofx(ofx, account=None):
    """
    Converts OfxParser object into a JSON-serializable list of dicts.
    """
    serialized_data = []
    org = ""
    fid = ""
    if hasattr(ofx, 'institution'):
        org = ofx.institution.organization
        fid = ofx.institution.fid

    for tx in ofx.account.statement.transactions:
        amount = float(tx.amount)
        # Flip sign if the account settings require it
        if account and account.ofx_flip_sign:
            tx.amount *= -1        
        serialized_data.append({
            'fit_id': tx.id,
            'date': tx.date.strftime('%Y-%m-%d'),
            'amount': float(tx.amount),
            'description': (tx.memo or tx.payee or "").strip(),
        })
    return serialized_data, org, fid


def analyze_ofx_serialized_data(serialized_list, account):
    """
    Takes the flattened session data and adds Vendor/Duplicate/Match context.
    """
    final_data = []
    matched_ids = []
    vendor_mappings = Vendor.view_objects.exclude(OFX_name__isnull=True).exclude(OFX_name="")

    for item in serialized_list:
        status = "new"
        existing_id = None
        matched_vendor_id = None
        
        # 1. Duplicate Check
        if Transaction.view_objects.filter(fit_id=item['fit_id']).exists():
            status = "duplicate"
        else:
            # 2. Manual Match Check
            match = Transaction.admin_objects.filter(
                account_source=account,
                date_actual=item['date'], 
                amount_actual=item['amount'], 
                fit_id__isnull=True
            ).exclude(pk__in=matched_ids).first()  #exclude already matched transactions
            
            if match:
                status = "match"
                existing_id = match.id
                matched_ids.append(match.id) # list of already matched transactions
            else:
                # 3. Vendor Match
                for vendor in vendor_mappings:
                    if vendor.OFX_name.lower() in item['description'].lower():
                        matched_vendor_id = vendor.id
                        break

        # Merge the analysis back into the item
        item.update({
            'status': status,
            'existing_id': existing_id,
            'vendor_id': matched_vendor_id,
            'vendor_name': Vendor.objects.get(id=matched_vendor_id).name if matched_vendor_id else ""
        })
        final_data.append(item)
        
    return final_data
