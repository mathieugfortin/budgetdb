# paystubengine.py
from datetime import timedelta
from .models import Transaction, PaystubMapping, Cat2, JoinedTransactions
from dateutil import parser
from django.utils.dateparse import parse_date
import pdfplumber
import re
from decimal import Decimal, ROUND_HALF_UP
import unicodedata
from collections import defaultdict


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

    def strip_accents(self, text):
        # Decompose the characters
        text = unicodedata.normalize('NFD', text)
        # Filter out the combining accent marks
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        return text

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
        extracted_text = self.strip_accents(extracted_text)
        return extracted_text

    def _tokenize_all(self):
        tokenized = []
        self.sequence_map = {}
        regex = r'\s{2,}|\s(?=\$|\d|-(?!\s))'
        title_clean_pattern = r'\s+(Retro|Current|YTD|Rate|Hours|Earnings|Amount|Year to Date|Rétro|Taux en cours|Heures en cours|Gains en cours|En cours|Cumulatif).*'
        
        for line_idx, line in enumerate(self.raw_text.split('\n'), start=1):
            clean_line = line.strip()
            if not clean_line: 
                continue
            
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
                        section_name=section_name,
                        line_sequence=sequence,
                        token_count=token_count
                    )

    def get_mapping_key(self, keyword, tokens):
        """Standardized key generation used everywhere."""
        count = len(tokens)
        return f"{keyword} [{count}]"

    def get_active_mappings(self):
        """Returns a list of tuples: (mapping_key, tokens) preserving duplicates and order."""
        active_list = []
        
        # self.tokenized_lines is already a list of lines in reading order
        for parts in self.tokenized_lines:
            keyword = parts[0]
            key = self.get_mapping_key(keyword, parts)
            active_list.append((key, parts))
            
        return active_list

    def get_unmapped_keys(self):
            """
            Returns a list of keys found in the PDF that are not 
            fully configured in the database.
            """
            # FIX: Extract unique keys from the list of tuples
            active_pdf_keys = set(key for key, tokens in self.get_active_mappings())
            
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
        
        # allow for a date range
        if isinstance(pay_date, str):
            pay_date = parse_date(pay_date)        
        start_date = pay_date - timedelta(days=2)
        end_date = pay_date + timedelta(days=2)

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
        cat1_name =''

        if mapping.is_net_pay:
            existing_tx = Transaction.admin_objects.filter(
                date_actual__range=(start_date, end_date),
                account_source=self.profile.pay_account,
                cat2=Cat2.objects.get(name='transfer',system_object=True)
            ).exclude(id__in=matched_tx_ids).first()
            
            cat2 = Cat2.objects.get(name='transfer',system_object=True)
            cat1_name = cat2.cat1.name
            category = cat2.name
            if existing_tx:
                target_destination_account = existing_tx.account_destination or self.profile.checking_account
            else:
                target_destination_account = self.profile.checking_account
            target_source_account = self.profile.pay_account
        else:    
            cat2=mapping.category
            cat1_name = cat2.cat1.name
            existing_tx = Transaction.objects.filter(
                account_source=target_source_account,
                date_actual__range=(start_date, end_date),
                cat2=cat2,
                is_deleted=False,
            ).exclude(id__in=matched_tx_ids).first()

        action = {
            'mapping_id': mapping.id,
            'category': category,
            'cat1_name': cat1_name,
            'tx_date': pay_date,
            'destination_account': target_destination_account,
            'source_account': target_source_account,
            'val': final_amount,
            'color_class': 'text-danger' if final_amount < 0 else 'text-success',
            'paystub_id':paystub_id,
        }

        if existing_tx:
            action.update({'tx_date': existing_tx.date_actual})
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
        
        running_total = Decimal('0.00') 
        reported_net_pay = Decimal('0.00')
        
        # Get all saved rules 
        mappings = PaystubMapping.admin_objects.filter(profile=self.profile).order_by('line_sequence')
               
        # Get the ordered list of PDF lines
        pdf_active_lines = self.get_active_mappings() 

        mapping_dict = defaultdict(list)
        for m in mappings:
            mapping_dict[m.line_keyword].append(m)
        matched_tx_ids = set()

        # 3. Loop over every single physical line found in the PDF
        for key, tokens in pdf_active_lines:
            rules = mapping_dict.get(key, [])
            for mapping in rules:
            
                if not mapping:
                    # Line on PDF doesn't have a matching database rule yet
                    continue
                    
                if mapping.is_header:
                    if current_section["actions"]:
                        sections.append(current_section)
                    current_section = {"header": mapping.line_keyword, "actions": []}
                    continue
                    
                if mapping.is_ignored or mapping.is_date_line:
                    continue

                # 4. Process this unique line instance
                action = self.process_mapping_line(mapping, pay_date, tokens, matched_tx_ids=matched_tx_ids)
                
                for jt in action.get('potential_jts', []):
                    all_discovered_jts[jt['id']] = jt['name']

                current_section["actions"].append(action)

                # --- THE MATH PART ---
                if self.profile.pay_account == action['source_account']: 
                    running_total -= Decimal(str(action['val'])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                elif self.profile.pay_account == action['destination_account']:
                    running_total += Decimal(action['val']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                if getattr(mapping, 'is_net_pay', False): 
                    reported_net_pay = Decimal(action['val']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        sections.append(current_section)
        
        is_balanced = round(running_total, 2)

        return sections, is_balanced, running_total, reported_net_pay, all_discovered_jts       


            