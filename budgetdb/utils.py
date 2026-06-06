# from datetime import datetime
from calendar import HTMLCalendar
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Q
from django.urls import reverse

from .models import Cat2, Transaction, Vendor


class Calendar(HTMLCalendar):
    def __init__(self, year=None, month=None):
        self.year = year
        self.month = month
        super(Calendar, self).__init__()

    def formatday(self, day, events):
        events_per_day = events.filter(date_actual__day=day, audit=0)
        d = ""
        for event in events_per_day:
            url = reverse(
                f"{event._meta.app_label}:details_transaction", args=[event.id]
            )
            d += f'<li> <a href="{url}"> {event.description} </a></li>'
            d = d

        if day != 0:
            return f"<td><span class='date'>{day}</span><ul> {d} </ul></td>"
        return "<td></td>"

    # formats a week as a tr
    def formatweek(self, theweek, events):
        week = ""
        for d, weekday in theweek:
            week += self.formatday(d, events)
        return f"<tr> {week} </tr>"

    # formats a month as a table
    # filter events by year and month
    def formatmonth(self, withyear=True):
        events = Transaction.view_objects.filter(
            date_actual__year=self.year, date_actual__month=self.month
        ).order_by("description")

        cal = '<table border="0" cellpadding="0" cellspacing="0" class="calendar">\n'
        cal += f"{self.formatmonthname(self.year, self.month, withyear=withyear)}\n"
        cal += f"{self.formatweekheader()}\n"
        for week in self.monthdays2calendar(self.year, self.month):
            cal += f"{self.formatweek(week, events)}\n"
        return cal


class Bitmap:
    bits = []
    n = 0

    def __init__(self, n):
        self.n = n
        self.bits = [False for i in range(n)]

    def __str__(self):
        intvalue = 0
        for i in range(self.n):
            intvalue += 2**i * self.bits[i]
        return intvalue


def serialize_ofx(ofx, account=None):
    """
    Converts OfxParser object into a JSON-serializable list of dicts.
    """
    serialized_data = []
    org = ""
    fid = ""
    if hasattr(ofx, "institution"):
        org = ofx.institution.organization
        fid = ofx.institution.fid

    for tx in ofx.account.statement.transactions:
        # Flip sign if the account settings require it
        if account and account.ofx_flip_sign:
            tx.amount *= -1
        serialized_data.append(
            {
                "fit_id": tx.id,
                "date": tx.date.strftime("%Y-%m-%d"),
                "amount": float(tx.amount),
                "description": (tx.memo or tx.payee or "").strip(),
            }
        )
    return serialized_data, org, fid


def analyze_ofx_serialized_data(serialized_list, account):
    """
    Takes the flattened session data and adds Vendor/Duplicate/Match context.
    """
    final_data = []
    matched_ids = []
    vendor_mappings = list(
        Vendor.view_objects.exclude(OFX_name__isnull=True).exclude(OFX_name="")
    )
    transfer_cat = Cat2.objects.get(system_object=True, name="transfer")
    fuzzy_date_match = 4

    for item in serialized_list:
        status = "new"
        existing_id = None
        matched_vendor_id = None
        existing_desc = None
        fit_handling = None
        vendor_name = ""

        # 1. Duplicate Check
        if Transaction.view_objects.filter(
            Q(fit_id=item["fit_id"]) | Q(fit_id_transfer=item["fit_id"])
        ).exists():
            status = "duplicate"
        else:
            item_date = datetime.strptime(item["date"], "%Y-%m-%d").date()
            date_range = (
                item_date - timedelta(days=fuzzy_date_match),
                item_date + timedelta(days=fuzzy_date_match),
            )
            match_conditions = (
                Q(
                    account_source=account,
                    amount_actual=item["amount"],
                    fit_id__isnull=True,
                )
                | Q(
                    account_destination=account,
                    amount_actual=-item["amount"],
                    fit_id__isnull=True,
                )
                | Q(
                    account_source=account,
                    amount_actual=item["amount"],
                    cat2=transfer_cat,
                )
                | Q(
                    account_destination=account,
                    amount_actual=item["amount"],
                    cat2=transfer_cat,
                )
            )
            match = (
                Transaction.admin_objects.filter(
                    match_conditions, date_actual__range=date_range
                )
                .exclude(pk__in=matched_ids)
                .first()
            )

            if match:
                status = "match"
                existing_id = match.id
                existing_desc = match.description
                matched_ids.append(match.id)  # list of already matched transactions
                if match.cat2 == transfer_cat and match.fit_id:
                    fit_handling = "transfer"
            else:
                # 3. Vendor Match
                desc_lower = item["description"].lower()
                for vendor in vendor_mappings:
                    if vendor.OFX_name.lower() in desc_lower:
                        matched_vendor_id = vendor.id
                        vendor_name = vendor.name
                        break

        # Merge the analysis back into the item
        item.update(
            {
                "status": status,
                "existing_id": existing_id,
                "vendor_id": matched_vendor_id,
                "existing_desc": existing_desc,
                "fit_handling": fit_handling,
                "vendor_name": vendor_name,
            }
        )
        final_data.append(item)

    return final_data


def format_money(value):
    """Ensures a value is a Decimal with 2-place precision."""
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
