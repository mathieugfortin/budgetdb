# from datetime import datetime
from calendar import HTMLCalendar
from datetime import datetime, timedelta
from django.urls import reverse, reverse_lazy
from ofxparse import OfxParser
from .models import Transaction, Statement, Vendor, PaystubMapping, Cat2, JoinedTransactions
from django.db.models import Q
from dateutil import parser
import pdfplumber
import re
from decimal import Decimal

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
    vendor_mappings = list(Vendor.view_objects.exclude(OFX_name__isnull=True).exclude(OFX_name=""))
    transfer_cat = Cat2.objects.get(system_object=True, name='transfer')
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
            Q(fit_id=item['fit_id']) | Q(fit_id_transfer=item['fit_id'])
        ).exists():
            status = "duplicate"
        else:
            item_date = datetime.strptime(item['date'], "%Y-%m-%d").date()
            date_range = (
                item_date - timedelta(days=fuzzy_date_match), 
                item_date + timedelta(days=fuzzy_date_match)
            )
            match_conditions = (
                Q(account_source=account, amount_actual=item['amount'], fit_id__isnull=True) |
                Q(account_destination=account, amount_actual=-item['amount'], fit_id__isnull=True) |
                Q(account_source=account, amount_actual=item['amount'], cat2=transfer_cat) |
                Q(account_destination=account, amount_actual=item['amount'], cat2=transfer_cat)
            )
            match = Transaction.admin_objects.filter(
                match_conditions,
                date_actual__range=date_range
            ).exclude(pk__in=matched_ids).first()

            if match:
                status = "match"
                existing_id = match.id
                existing_desc = match.description
                matched_ids.append(match.id) # list of already matched transactions
                if match.cat2 == transfer_cat and match.fit_id:
                    fit_handling = 'transfer'
            else:
                # 3. Vendor Match
                desc_lower = item['description'].lower()
                for vendor in vendor_mappings:
                    if vendor.OFX_name.lower() in desc_lower:
                        matched_vendor_id = vendor.id
                        vendor_name = vendor.name
                        break

        # Merge the analysis back into the item
        item.update({
            'status': status,
            'existing_id': existing_id,
            'vendor_id': matched_vendor_id,
            'existing_desc': existing_desc,
            'fit_handling': fit_handling,
            'vendor_name': vendor_name
        })
        final_data.append(item)
        
    return final_data


class PaystubEngine:
    def __init__(self, data, profile):
        self.sections = {}
        self.profile = profile
        
        # If 'data' is a string, we already have the text.
        # If it's bytes/file, we open the source file it.
        if isinstance(data, str):
            self.raw_text = data
        else:
            self.raw_text = self._extract_text(data)
            
        self.tokenized_lines = self._tokenize_all()
        #self.token_dict = self._tokenize(self.raw_text)

    def _extract_text(self, pdf_file):
        """Internal helper to convert binary PDF to string text."""
        extracted_text = ""
        try:
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n"
        except Exception as e:
            print(f"PDF Extraction Error: {e}")
            return ""
        return extracted_text

    def _tokenize_all(self):
        tokenized = []
        self.sequence_map = {}
        regex = r'\s{2,}|\s(?=\$|\d|-(?!\s))'
        title_clean_pattern = r'\s+(Retro|Current|YTD|Rate|Hours|Earnings|Amount|Year to Date|Rétro|Taux en cours|Heures en cours|Gains en cours|En cours|Cumulatif).*'
        
        for line_idx, line in enumerate(self.raw_text.split('\n'), start=1):
            clean_line = line.strip()
            if not clean_line: continue
            
            parts = [p.strip() for p in re.split(regex, clean_line) if p.strip()]
            
            if not parts:
                continue

            parts[0] = re.sub(title_clean_pattern, '', parts[0], flags=re.IGNORECASE).strip()

            # Intercept the specific bank deposit line
            # Checking if it looks like the account line (has a date and a $)
            if len(parts) >= 3 and '/' in parts[-2] and '$' in parts[-1]:
                date_key = f"{parts[0]} (Date)"
                total_key = f"{parts[0]} (Total)"
                # Split it into two virtual lines for the mapping engine
                tokenized.append([f"{parts[0]} (Date)", parts[-2]])
                tokenized.append([f"{parts[0]} (Total)", parts[-1]])
                # Save sequence for the split lines
                if date_key not in self.sequence_map: 
                    self.sequence_map[date_key] = line_idx
                if total_key not in self.sequence_map: 
                    self.sequence_map[total_key] = line_idx
            else:
                keyword = parts[0]
                tokenized.append(parts)
                
                # Save sequence for standard lines
                if keyword not in self.sequence_map: 
                    self.sequence_map[keyword] = line_idx

        return tokenized

    def calculate_mapped_value(self, mapping, tokens):
        """
        Takes the saved mapping (with index string like "1,3") 
        and the raw tokens, returns the final float.
        """
        if not mapping.column_indices or mapping.column_indices == "-1":
            return 0.0

        total = 0.0
        # "1,3" -> [1, 3]
        indices = [int(i) for i in mapping.column_indices.split(',')]
        
        for idx in indices:
            try:
                # Clean "$1,234.56" -> "1234.56"
                raw_val = tokens[idx].replace('$', '').replace(',', '').strip()
                total += float(raw_val)
            except (IndexError, ValueError):
                continue
                
        return abs(total)

    def sync_mappings_with_db(self):
        token_dict = self.get_token_dict()

        for keyword, occurrences in token_dict.items():
            for tokens in occurrences:
                token_count = len(tokens)
                section_name = self.find_section_for_keyword(keyword)
                sequence = self.sequence_map.get(keyword, 999)

                mapping_key = f"{keyword} [{token_count}]"

                existing_rules = PaystubMapping.objects.filter(
                    profile=self.profile,
                    line_keyword=mapping_key,
                    token_count=token_count
                )
                if existing_rules.exists():
                    # match the PDF structure.
                    existing_rules.update(
                        line_sequence=sequence,
                    )
                else:
                    # Create the initial 'Empty' mapping
                    PaystubMapping.objects.create(
                        profile=self.profile,
                        line_keyword=mapping_key,
                        section_name=self.find_section_for_keyword(keyword),
                        line_sequence=sequence,
                        token_count=token_count
                    )

    def get_mapping_key(self, keyword, tokens):
        """Standardized key generation used everywhere."""
        count = len(tokens)
        return f"{keyword} [{count}]"

    def get_active_mappings(self):
        """Returns a dict of mapping_key -> tokens."""
        active = {}
        tokens_map = self.get_token_dict()
        for keyword, occurrences in tokens_map.items():
            for tokens in occurrences:
                key = self.get_mapping_key(keyword, tokens)
                active[key] = tokens
        return active

    def get_unmapped_keys(self):
        """
        Returns a list of keys found in the PDF that are not 
        fully configured in the database.
        """
        active_pdf_keys = self.get_active_mappings().keys()
        existing_mappings = PaystubMapping.objects.filter(
            profile=self.profile, 
            line_keyword__in=active_pdf_keys
        )

        ready_keywords = set()
        for m in existing_mappings:
            is_metadata = m.is_ignored or m.is_header or m.is_date_line or m.is_net_pay
            has_cat = m.category_id is not None
            needs_destination = m.is_pass_through 
            has_dest = m.destination_account_id is not None
            
            if is_metadata or (has_cat and (not needs_destination or has_dest)):
                ready_keywords.add(m.line_keyword)

        # Return the difference: keys in PDF but not in 'ready' set
        return [key for key in active_pdf_keys if key not in ready_keywords]

    def get_mapped_amounts(self):
        """
        Returns a dictionary: { cat2_id: total_decimal_amount }
        """
        results = {}
        mappings = PaystubMapping.objects.select_related('category').all()

        for map_obj in mappings:
            section_lines = self.sections.get(map_obj.section_name, [])
            
            # Find the specific line in this section
            for line in section_lines:
                if map_obj.line_keyword.lower() in line.lower():
                    # Tokenize by multiple spaces or tabs
                    tokens = re.split(r'\s{2,}', line)
                    
                    line_sum = Decimal('0.00')
                    for idx in map_obj.get_indices():
                        try:
                            # Clean the token ($ and ,)
                            raw_val = tokens[idx].replace('$', '').replace(',', '').strip()
                            # Handle negative signs like $-89.97 or -89.97
                            if raw_val.startswith('$-'):
                                raw_val = raw_val.replace('$-', '-')
                            
                            line_sum += Decimal(raw_val)
                        except (IndexError, ValueError):
                            continue
                    
                    # Aggregate by category ID
                    cat_id = map_obj.category.id
                    results[cat_id] = results.get(cat_id, Decimal('0.00')) + line_sum
                    
        return results

    def get_token_dict(self):
        token_map = {}
        for parts in self.tokenized_lines:
            keyword = parts[0]
            if keyword not in token_map:
                token_map[keyword] = []
            token_map[keyword].append(parts)
        return token_map

    def find_section_for_keyword(self, keyword):
        """
        Looks through the engine's internal section dictionary 
        to see which header 'owns' this line keyword.
        """
        for section_name, lines in self.sections.items():
            for line in lines:
                # Check if this keyword is at the start of any line in this section
                if line.strip().startswith(keyword):
                    return section_name
        return "General" # Fallback if not found

    def find_pay_date(self):
        """Looks for the date string using the user's saved mapping."""
        # 1. Get the line keyword and index saved as the date line
        date_mapping = PaystubMapping.objects.filter(
            profile=self.profile, 
            is_date_line=True
        ).first()

        if date_mapping:
            # tokens is a list of lists: e.g., [['000605371', '2024/01/05', '$2,292.27']]
            occurrences = self.get_token_dict().get(date_mapping.keyword_label)
            
            # Check that we have at least one occurrence of this line
            if occurrences and len(occurrences) > 0:
                tokens = occurrences[0]
                try:
                    # Use the saved index (e.g. index 2 from your debug screenshot)
                    indices = [int(i) for i in date_mapping.column_indices.split(',')]
                    
                    for idx in indices:
                        raw_date = tokens[idx]
                        try:
                            stub_date = parser.parse(raw_date).date()
                        except (IndexError, ValueError):
                            continue
                        return stub_date

                except (ValueError, IndexError, TypeError):
                    return None
        return None

    def process_mapping_line(self, mapping, pay_date, tokens, *, matched_tx_ids=None, commit=False, paystub_id=None, manual_jt_id=None):
        """ Compares extracted PDF data against the DB to propose an action or save, depending on commit.  """
        
        # Initialize the set if not provided
        if matched_tx_ids is None:
            matched_tx_ids = set()

        if mapping.is_date_line or mapping.is_header or mapping.is_ignored:
            if commit:
                return None # Commit view can just ignore this
            return {
                'type': 'INFO', 
                'category': 'Metadata', 
                'val': 0, 
                'ignore_in_math': True,
                'label': mapping.line_keyword 
            }

        final_amount = self.calculate_mapped_value(mapping, tokens)
        target_source_account = None
        discovered_jt = None
        target_destination_account = mapping.destination_account or self.profile.pay_account

        if mapping.entry_type == mapping.EntryType.DEDUCTION:
            target_destination_account = None or mapping.destination_account
            target_source_account = self.profile.pay_account
            
        category = mapping.category.name if mapping.category else "No Category"

        if mapping.is_net_pay:
            existing_tx = Transaction.admin_objects.filter(
                date_actual=pay_date,
                account_source=self.profile.pay_account,
                cat2=Cat2.objects.get(name='transfer',system_object=True)
            ).exclude(id__in=matched_tx_ids).first()
            
            cat2 = Cat2.objects.get(name='transfer',system_object=True)
            category = cat2.name
            if existing_tx:
                target_destination_account = existing_tx.account_destination or self.profile.checking_account
            else:
                target_destination_account = self.profile.checking_account
            target_source_account = self.profile.pay_account
        else:    
            cat2=mapping.category
            existing_tx = Transaction.objects.filter(
                account_source=target_source_account,
                date_actual=pay_date,
                cat2=cat2
            ).exclude(id__in=matched_tx_ids).first()

        action = {
            'mapping_id': mapping.id,
            'category': category,
            'destination_account': target_destination_account,
            'source_account': target_source_account,
            'val': final_amount,
            'color_class': 'text-danger' if final_amount < 0 else 'text-success',
            'paystub_id':paystub_id,
        }

        if existing_tx:
            # Mark this transaction as "claimed" so duplicate lines don't grab it again
            matched_tx_ids.add(existing_tx.id)
            
            direct_jts = list(existing_tx.joined_transactions.values('id', 'name'))
            event_jts = []
            if hasattr(existing_tx, 'budgetedevent') and existing_tx.budgetedevent:
                event_jts = list(existing_tx.budgetedevent.joined_transactions.values('id', 'name'))

            all_potential_jts = {jt['id']: jt for jt in direct_jts + event_jts}.values()
            
            action.update({'potential_jts': list(all_potential_jts)})

            if round(float(existing_tx.amount_actual), 2) != round(float(final_amount), 2):
                action.update({
                    'type': 'UPDATE',
                    'old_val': existing_tx.amount_actual,
                    'tx_id': existing_tx.id
                })
            else:
                action.update({
                    'type': 'MATCH',
                    'tx_id': existing_tx.id
                })
        else:
            action.update({'type': 'CREATE'})

        if commit:
            final_jt = JoinedTransactions.admin_objects.get(id=manual_jt_id) if manual_jt_id else discovered_jt

            if existing_tx:
                existing_tx.amount_actual = Decimal(format(final_amount, ".2f"))
                existing_tx.comment = f"Updated via: {mapping.line_keyword}"
                existing_tx.receipt=True
                existing_tx.paystub_id=paystub_id
                existing_tx.account_source = target_source_account
                existing_tx.account_destination = target_destination_account
                existing_tx.save()
                tx = existing_tx
            else:
                currency = target_source_account.currency if target_source_account else target_destination_account.currency
                cat1 = cat2.cat1 if cat2 else None

                tx = Transaction.objects.create(
                    date_actual=pay_date,
                    amount_actual=Decimal(format(final_amount, ".2f")),
                    account_source=target_source_account,
                    account_destination=target_destination_account,
                    cat1=cat1,
                    cat2=cat2,
                    receipt=True,
                    currency=currency,
                    comment=f"Created via: {mapping.line_keyword}",
                    description=mapping.line_keyword,
                    paystub_id=paystub_id
                )
                # Add new tx to the exclusion set so subsequent duplicates don't falsely match it!
                matched_tx_ids.add(tx.id) 
            
            if final_jt:
                if not final_jt.transactions.filter(pk=tx.pk).exists():
                    if not (tx.budgetedevent and final_jt.budgetedevents.filter(pk=tx.budgetedevent.pk).exists()):
                        final_jt.transactions.add(tx)
            return tx

        return action

    def get_grouped_actions(self, pay_date):
        sections = []
        current_section = {"header": "General", "actions": []}
        all_discovered_jts = {}
        
        # Mathematical counters
        running_total = 0 # Sum of all earnings/deductions
        reported_net_pay = 0 # The value of the specific 'Net Pay' line
        
        # 1. Get all your saved rules
        mappings = PaystubMapping.admin_objects.filter(profile=self.profile).order_by('line_sequence')
        matched_tx_ids = set()
        # 2. Get the actual PDF data
        pdf_active_map = self.get_active_mappings() 

        for mapping in mappings:
            if mapping.is_header:
                if current_section["actions"]:
                    sections.append(current_section)
                current_section = {"header": mapping.line_keyword, "actions": []}
                continue
            # 3. Pull the tokens for this line
            tokens =  pdf_active_map.get(mapping.line_keyword)
            if tokens and not mapping.is_ignored:
                if mapping.is_date_line:
                        continue
                action = self.process_mapping_line(mapping, pay_date, tokens, matched_tx_ids=matched_tx_ids)
                # Add any JTs found in this line to the master list
                for jt in action.get('potential_jts', []):
                    all_discovered_jts[jt['id']] = jt['name']

                current_section["actions"].append(action)
                if mapping.is_net_pay:
                    reported_net_pay = action['val']
                else:
                    running_total += action['val']

                # --- THE MATH PART ---
                # If this is the 'Net Pay' line, we store it separately to compare
                if getattr(mapping, 'is_net_pay', False): 
                    reported_net_pay = action['val']
                else:
                    # Add/Subtract this line from our calculated total
                    running_total += action['val']

        # Push the final section
        sections.append(current_section)
        
        # 4. Final Verification
        # Is what we calculated == what the PDF says was deposited?
        is_balanced = round(running_total, 2) == round(reported_net_pay, 2)

        return sections, is_balanced, running_total, reported_net_pay, all_discovered_jts        


        