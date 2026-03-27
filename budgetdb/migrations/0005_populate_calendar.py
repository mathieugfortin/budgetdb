from django.db import migrations
from datetime import date, timedelta
import holidays

def populate_calendar_data(apps, schema_editor):
    MyCalendar = apps.get_model('budgetdb', 'MyCalendar')
    
    # 1. Wipe the table as requested
    MyCalendar.objects.all().delete()
    
    # 2. Initialize Quebec-specific holidays for the full range
    # This covers things like St-Jean-Baptiste and National Patriots' Day
    ca_qc_holidays = holidays.CountryHoliday('CA', subdiv='QC', years=range(2000, 2041))
    
    start_date = date(2000, 1, 1)
    end_date = date(2040, 12, 31)
    current = start_date
    calendar_entries = []

    while current <= end_date:
        # Check if the current date is a holiday
        # holidays library returns the name of the holiday if it exists, else None
        holiday_name = ca_qc_holidays.get(current)
        is_holiday = holiday_name is not None

        calendar_entries.append(MyCalendar(
            db_date=current,
            year=current.year,
            month=current.month,
            day=current.day,
            quarter=(current.month - 1) // 3 + 1,
            week=current.isocalendar()[1],
            day_name=current.strftime('%A'),
            month_name=current.strftime('%B'),
            weekend_flag=current.weekday() >= 5,
            holiday_flag=is_holiday,
            event=holiday_name if holiday_name else ""
        ))

        # Bulk create in chunks of 2000 for performance
        if len(calendar_entries) >= 2000:
            MyCalendar.objects.bulk_create(calendar_entries)
            calendar_entries = []
            
        current += timedelta(days=1)

    # Final batch save
    if calendar_entries:
        MyCalendar.objects.bulk_create(calendar_entries)

def reverse_calendar_data(apps, schema_editor):
    MyCalendar = apps.get_model('budgetdb', 'MyCalendar')
    MyCalendar.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('budgetdb', '0004_remove_paystubmapping_multiplier'),
    ]
    operations = [
        migrations.RunPython(populate_calendar_data, reverse_calendar_data),
    ]

