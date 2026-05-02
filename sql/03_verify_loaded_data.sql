SELECT COUNT(*) FROM raw.dispatch_price;
SELECT MIN(settlementdate), MAX(settlementdate) FROM raw.dispatch_price;
SELECT * FROM raw.dispatch_price ORDER BY settlementdate DESC LIMIT 10;

SELECT COUNT(*) FROM raw.trading_regionsum;
SELECT MIN(settlementdate), MAX(settlementdate) FROM raw.trading_regionsum;
SELECT * FROM raw.trading_regionsum ORDER BY settlementdate DESC LIMIT 10;

SELECT COUNT(*) FROM raw.dispatch_regionsum;
SELECT MIN(settlementdate), MAX(settlementdate) FROM raw.dispatch_regionsum;
SELECT * FROM raw.dispatch_regionsum ORDER BY settlementdate DESC LIMIT 10;

SELECT COUNT(*) FROM raw.dispatch_unit_scada;
SELECT MIN(settlementdate), MAX(settlementdate) FROM raw.dispatch_unit_scada;
SELECT * FROM raw.dispatch_unit_scada ORDER BY settlementdate DESC LIMIT 10;

SELECT COUNT(*) FROM raw.dispatch_load;
SELECT MIN(settlementdate), MAX(settlementdate) FROM raw.dispatch_load;
SELECT * FROM raw.dispatch_load ORDER BY settlementdate DESC LIMIT 10;

SELECT COUNT(*) FROM raw.bids_per_offer;
SELECT MIN(settlementdate), MAX(settlementdate) FROM raw.bids_per_offer;
SELECT * FROM raw.bids_per_offer ORDER BY settlementdate DESC LIMIT 10;

SELECT COUNT(*) FROM raw.bid_day_offer;
SELECT MIN(settlementdate), MAX(settlementdate) FROM raw.bid_day_offer;
SELECT * FROM raw.bid_day_offer ORDER BY settlementdate DESC LIMIT 10;

SELECT COUNT(*) FROM raw.fcas_price;
SELECT MIN(settlementdate), MAX(settlementdate) FROM raw.fcas_price;
SELECT * FROM raw.fcas_price ORDER BY settlementdate DESC LIMIT 10;

SELECT COUNT(*) FROM raw.fcas_requirements;
SELECT MIN(settlementdate), MAX(settlementdate) FROM raw.fcas_requirements;
SELECT * FROM raw.fcas_requirements ORDER BY settlementdate DESC LIMIT 10;

SELECT COUNT(*) FROM raw.dispatch_constraints;
SELECT MIN(settlementdate), MAX(settlementdate) FROM raw.dispatch_constraints;
SELECT * FROM raw.dispatch_constraints ORDER BY settlementdate DESC LIMIT 10;

SELECT COUNT(*) FROM raw.constraint_rhs;
SELECT MIN(settlementdate), MAX(settlementdate) FROM raw.constraint_rhs;
SELECT * FROM raw.constraint_rhs ORDER BY settlementdate DESC LIMIT 10;

SELECT COUNT(*) FROM raw.constraint_details;
SELECT MIN(effectivedate), MAX(effectivedate) FROM raw.constraint_details;
SELECT * FROM raw.constraint_details ORDER BY effectivedate DESC LIMIT 10;

SELECT COUNT(*) FROM raw.constraint_equations;
SELECT MIN(effectivedate), MAX(effectivedate) FROM raw.constraint_equations;
SELECT * FROM raw.constraint_equations ORDER BY effectivedate DESC LIMIT 10;

SELECT COUNT(*) FROM raw.interconnector_results;
SELECT MIN(settlementdate), MAX(settlementdate) FROM raw.interconnector_results;
SELECT * FROM raw.interconnector_results ORDER BY settlementdate DESC LIMIT 10;

SELECT COUNT(*) FROM raw.rooftop_pv_actual;
SELECT MIN(interval_datetime), MAX(interval_datetime) FROM raw.rooftop_pv_actual;
SELECT * FROM raw.rooftop_pv_actual ORDER BY interval_datetime DESC LIMIT 10;
