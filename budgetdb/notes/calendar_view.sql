CREATE OR REPLACE VIEW calendar_view AS (
SELECT 
row_number() OVER () as id
,c.db_date
,be.budgetedevent_id AS budgetedevent_id
,t.id as transaction_id
,be.description AS BE_description
,t.description AS T_description

FROM budgetdb.budgetdb_mycalendar c
left join calendar_view_be be ON c.db_date = be.db_date
LEFT JOIN budgetdb.budgetdb_transaction t 
	ON COALESCE(t.date_actual,t.date_planned) = c.db_date
WHERE (be.budgetedevent_id is not null or t.id is not NULL)
 AND c.db_date BETWEEN '2021-01-01' AND '2021-05-01'
 
 ORDER BY c.db_date
 )