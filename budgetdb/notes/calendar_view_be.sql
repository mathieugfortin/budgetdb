CREATE OR REPLACE VIEW calendar_view_be AS (
	SELECT distinct
	row_number() OVER () as id
	,c.db_date
	,be.id as budgetedevent_id
	,be.description

	FROM budgetdb.budgetdb_mycalendar c
	LEFT JOIN budgetdb.budgetdb_transaction tb ON tb.date_planned = c.db_date
	LEFT JOIN budgetdb.budgetdb_transaction tc ON tb.date_actual = c.db_date
	LEFT JOIN budgetdb.budgetdb_budgetedevent be ON (
		c.db_date >= be.repeat_start	
		AND (be.repeat_stop is null or c.db_date <= be.repeat_stop )
		AND 1<<(c.day-1) & be.repeat_dayofmonth_mask
		AND 1<<(c.month-1) & be.repeat_months_mask
		AND 1<<weekday(c.db_date) & be.repeat_weekday_mask
		AND 1<<(floor((datediff(c.db_date,STR_TO_DATE(CONCAT(c.year,'-',c.month,'-01'), '%Y-%m-%d'))+1)/7)) & be.repeat_weekofmonth_mask
		AND (tb.id is null or not ( tb.BudgetedEvent_id=be.id )) -- AND tb.date_actual != c.db_date))
	)
	AND (
		be.repeat_start=c.db_date
		OR (
			be.isrecurring=1 AND (
				(c.day = day(be.repeat_start) AND timestampdiff(month,be.repeat_start,c.db_date) % be.repeat_interval_months = 0)
				OR (datediff(be.repeat_start,c.db_date) % be.repeat_interval_days = 0)
				OR (c.day = day(be.repeat_start) AND c.month=MONTH(be.repeat_start) AND (YEAR(be.repeat_start)-c.year) % be.repeat_interval_years = 0)
				OR (datediff(be.repeat_start,c.db_date)%7=0 AND (datediff(c.db_date,be.repeat_start)/7) % be.repeat_interval_weeks = 0)
			)
		)
	)
	WHERE be.id IS NOT null
		AND c.db_date BETWEEN '2021-01-01' AND '2021-05-01'
)
