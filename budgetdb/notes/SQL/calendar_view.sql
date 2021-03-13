CREATE OR REPLACE VIEW calendar_view AS (
	SELECT * FROM calendar_view_be
	UNION ALL
	SELECT * FROM calendar_view_T
	UNION ALL
	SELECT * FROM calendar_view_A

ORDER BY 3
)