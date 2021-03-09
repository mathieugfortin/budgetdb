CREATE OR REPLACE VIEW calendar_view AS (
SELECT 
row_number() OVER () as id
,b.db_date
,b.id AS budgetedevent_id
,t.id as transaction_id
,t.description

FROM calendar_view_p b
LEFT JOIN budgetdb.budgetdb_transaction t 
	ON COALESCE(t.date_actual,t.date_planned) = b.db_date
--		AND t.BudgetedEvent_id IS null
WHERE b.db_date BETWEEN '2021-01-01' AND '2021-05-01'

ORDER BY db_date