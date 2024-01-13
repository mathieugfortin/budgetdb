DROP PROCEDURE IF EXISTS fill_date_dimension;
DELIMITER //

CREATE PROCEDURE fill_date_dimension(IN startdate DATE,IN stopdate DATE)
BEGIN
    DECLARE currentdate DATE;
    SET currentdate = startdate;
    WHILE currentdate < stopdate DO
        INSERT INTO budgetdb_mycalendar VALUES (
                        YEAR(currentdate)*10000+MONTH(currentdate)*100 + DAY(currentdate),
                        currentdate,
                        YEAR(currentdate),
                        MONTH(currentdate),
                        DAY(currentdate),
                        QUARTER(currentdate),
                        WEEKOFYEAR(currentdate),
                        DATE_FORMAT(currentdate,'%W'),
                        DATE_FORMAT(currentdate,'%M'),
                        0,
                        CASE DAYOFWEEK(currentdate) WHEN 1 THEN 1 WHEN 7 then 1 ELSE 0 END,
                        '');
        SET currentdate = ADDDATE(currentdate,INTERVAL 1 DAY);
    END WHILE;
END
//
DELIMITER ;




TRUNCATE TABLE budgetdb_mycalendar;

CALL fill_date_dimension('2004-01-01','2025-12-31');
OPTIMIZE TABLE budgetdb_mycalendar;
