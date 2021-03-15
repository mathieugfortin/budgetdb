CREATE OR REPLACE VIEW calendar_view_T AS (
	SELECT 
		row_number() OVER () as id
		,'transaction' AS e_type
		,c.db_date
		,t.id AS e_id
		,t.description
		,t.amount_actual AS amount
		,t.account_destination_id
		,t.account_source_id
		,t.cat1_id
		,t.cat2_id
		,0 AS future_only
	
	FROM budgetdb.budgetdb_mycalendar c
	JOIN budgetdb.budgetdb_transaction t ON t.date_actual = c.db_date
)