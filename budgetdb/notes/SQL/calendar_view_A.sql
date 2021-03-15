CREATE OR REPLACE VIEW calendar_view_A AS (
	SELECT 
		row_number() OVER () as id
		,'accountaudit' AS e_type
		,c.db_date
		,a.id AS e_id
		,a.`comment` AS description
		,a.audit_amount AS amount
		,a.account_id AS account_destination_id
		,a.account_id AS account_source_id
		,NULL AS cat1_id
		,NULL AS cat2_id
		,0 as future_only
	
	FROM budgetdb.budgetdb_mycalendar c
	JOIN budgetdb.budgetdb_accountaudit a ON c.db_date = a.audit_date
)