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


def import_ofx_transactions(ofx_file, account, statement=None):
    ofx = OfxParser.parse(ofx_file)
    ofx_account = ofx.account
    vendors = Vendor.view_objects.exclude(OFX_name__isnull=True).exclude(OFX_name="")
    created_count = 0
    matched_count = 0

    for tx in ofx_account.statement.transactions:
        # 1. Exact match by FIT_ID (Already imported)
        if Transaction.admin_objects.filter(fit_id=tx.id).exists():
            continue
        

        # 2. Match manual entries (Same date, amount, and account, but no fit_id)
        # We use a tolerance or exact match depending on your bank's accuracy
        # Find a manual entry within +/- 2 days of the bank date

        date_start = tx.date - datetime.timedelta(days=2)
        date_end = tx.date + datetime.timedelta(days=2)
        existing_manual = Transaction.admin_objects.filter(
            account_source=account,
            # date_actual=tx.date,
            date_actual__range=(date_start, date_end),
            amount_actual=-tx.amount,
            fit_id__isnull=True,  # Only match if it hasn't been linked to an ID yet
        ).first()
        if not existing_manual:
            existing_manual = Transaction.admin_objects.filter(
                account_destination=account,
                # date_actual=tx.date,
                date_actual__range=(date_start, date_end),
                amount_actual=tx.amount,
                fit_id__isnull=True,  # Only match if it hasn't been linked to an ID yet
            ).first()

        if existing_manual:
            # Link the manual transaction to the Bank's ID
            
            existing_manual.fit_id = tx.id
            existing_manual.comment=tx.memo or tx.payee
            # Optionally update the description if the bank version is better
            # existing_manual.description = tx.memo or tx.payee 
            existing_manual.save()
            matched_count += 1
        else:
            # 3. Create a brand new transaction
            matched_vendor_id = None
            bank_desc = (tx.memo or tx.payee or "").strip().lower()
            for vendor in vendors:
                    if vendor.OFX_name.lower() in bank_desc:
                        matched_vendor = vendor
                        break # Stop at the first match

            Transaction.objects.create(
                account_source=account,
                currency=account.currency,
                statement=statement,
                date_actual=tx.date,
                amount_actual=-tx.amount,
                description=tx.memo or tx.payee,
                fit_id=tx.id,
                vendor=matched_vendor,
            )
            created_count += 1
            
    return created_count, matched_count


def analyze_ofx_transactions(ofx_file, account):
    ofx = OfxParser.parse(ofx_file)
    ofx_account = ofx.account
    transactions = []

    # Get vendors with OFX aliases to avoid repeated DB calls in the loop
    vendor_mappings = Vendor.objects.exclude(OFX_name__isnull=True).exclude(OFX_name="")

    for tx in ofx_account.statement.transactions:
        print(f"--- DEBUGGING 11 {tx.payee} {tx.date} ---")
        status = "new"
        existing_id = None
        matched_vendor_id = None
        matched_vendor = ""
        bank_desc = (tx.memo or tx.payee or "").strip()
        
        # 1. Check for exact duplicate (FIT_ID)
        if Transaction.objects.filter(fit_id=tx.id).exists():
            status = "duplicate"
        else:
            # 2. Check for manual match (Same date, amount, and no fit_id)
            # Find a manual entry within +/- 2 days of the bank date
            date_start = tx.date - datetime.timedelta(days=2)
            date_end = tx.date + datetime.timedelta(days=2)
            match = Transaction.objects.filter(
                account_source=account,
                date_actual__range=(date_start, date_end),
                amount_actual=-tx.amount,
                fit_id__isnull=True
            ).first()
            if not match:
                match = Transaction.objects.filter(
                    account_destination=account,
                    date_actual__range=(date_start, date_end),
                    amount_actual=tx.amount,
                    fit_id__isnull=True
                ).first()

            if match:
                status = "match"
                existing_id = match.id
            else:
                # 3. Smart Vendor Lookup
                for vendor in vendor_mappings:
                    if vendor.OFX_name.lower() in bank_desc.lower():
                        matched_vendor_id = vendor.id
                        matched_vendor = vendor.name
                        break 

        transactions.append({
            'fit_id': tx.id,
            'date_actual': tx.date.strftime('%Y-%m-%d'), # Strings are session-friendly
            'amount_actual': float(tx.amount),
            'description': bank_desc,
            'status': status,
            'existing_id': existing_id,
            'vendor_id': matched_vendor_id,
            'vendor': matched_vendor,
        })
    return transactions