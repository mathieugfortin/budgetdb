CREATE OR REPLACE VIEW budgetdb.budgetdb_account_presentation
AS
SELECT 
a.* , CONCAT('.',GROUP_CONCAT(ca.id  ORDER BY ca.id SEPARATOR ', .')) AS childrens
FROM budgetdb.budgetdb_account a
LEFT JOIN budgetdb.budgetdb_account pa ON a.account_parent_id=pa.id
LEFT JOIN budgetdb.budgetdb_account ca ON ca.account_parent_id=a.id
GROUP BY a.id
ORDER BY coalesce(pa.name,a.name),a.account_parent_id
