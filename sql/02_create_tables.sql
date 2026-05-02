CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS raw.dispatch_price (
    settlementdate TIMESTAMP,
    regionid TEXT,
    rrp NUMERIC,
    intervention TEXT,
    lastchanged TEXT
);

CREATE TABLE IF NOT EXISTS raw.trading_regionsum (
    settlementdate TIMESTAMP,
    regionid TEXT,
    totaldemand NUMERIC,
    availablegeneration NUMERIC,
    intervention TEXT,
    lastchanged TEXT
);

CREATE TABLE IF NOT EXISTS raw.dispatch_regionsum (
    settlementdate TIMESTAMP,
    regionid TEXT,
    totaldemand NUMERIC,
    availablegeneration NUMERIC,
    netinterchange NUMERIC,
    intervention TEXT,
    lastchanged TEXT
);

CREATE TABLE IF NOT EXISTS raw.dispatch_unit_scada (
    settlementdate TIMESTAMP,
    duid TEXT,
    scadavalue NUMERIC,
    intervention TEXT,
    lastchanged TEXT
);

CREATE TABLE IF NOT EXISTS raw.dispatch_load (
    settlementdate TIMESTAMP,
    duid TEXT,
    clearedmw NUMERIC,
    intervention TEXT,
    lastchanged TEXT
);

CREATE TABLE IF NOT EXISTS raw.bids_per_offer (
    settlementdate TIMESTAMP,
    duid TEXT,
    bidtype TEXT,
    bandavail1 NUMERIC,
    maxavail NUMERIC,
    lastchanged TEXT
);

CREATE TABLE IF NOT EXISTS raw.bid_day_offer (
    settlementdate TIMESTAMP,
    duid TEXT,
    bidtype TEXT,
    dailyenergyconstraint NUMERIC,
    lastchanged TEXT
);

CREATE TABLE IF NOT EXISTS raw.fcas_price (
    settlementdate TIMESTAMP,
    regionid TEXT,
    service TEXT,
    price NUMERIC,
    lastchanged TEXT
);

CREATE TABLE IF NOT EXISTS raw.fcas_requirements (
    settlementdate TIMESTAMP,
    regionid TEXT,
    service TEXT,
    requirement NUMERIC,
    lastchanged TEXT
);

CREATE TABLE IF NOT EXISTS raw.dispatch_constraints (
    settlementdate TIMESTAMP,
    constraintid TEXT,
    rhs NUMERIC,
    marginalvalue NUMERIC,
    lastchanged TEXT
);

CREATE TABLE IF NOT EXISTS raw.constraint_rhs (
    settlementdate TIMESTAMP,
    constraintid TEXT,
    rhs NUMERIC,
    lastchanged TEXT
);

CREATE TABLE IF NOT EXISTS raw.constraint_details (
    effectivedate TIMESTAMP,
    constraintid TEXT,
    description TEXT,
    lastchanged TEXT
);

CREATE TABLE IF NOT EXISTS raw.constraint_equations (
    effectivedate TIMESTAMP,
    constraintid TEXT,
    equation TEXT,
    lastchanged TEXT
);

CREATE TABLE IF NOT EXISTS raw.interconnector_results (
    settlementdate TIMESTAMP,
    interconnectorid TEXT,
    mwflow NUMERIC,
    lastchanged TEXT
);

CREATE TABLE IF NOT EXISTS raw.rooftop_pv_actual (
    interval_datetime TIMESTAMP,
    regionid TEXT,
    measurement_type TEXT,
    mw NUMERIC,
    lastchanged TEXT
);
