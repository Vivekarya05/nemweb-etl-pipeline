# AEMO NEMWeb Pipeline Handoff Document

This document is a project handoff summary for further work in ChatGPT or any other AI assistant.

It captures:
- the current project objective
- the business use cases
- the NEM tables currently mapped in the pipeline
- the target PostgreSQL tables
- the important columns to consider
- the current enabled vs advanced datasets

## Project Context

This project is a local AEMO NEMWeb ETL pipeline and dashboard built to:
- download public AEMO NEMWeb market data directly from NEMWeb URLs
- parse AEMO C / I / D formatted files correctly
- clean and validate the extracted data
- load the final output into PostgreSQL
- provide a local web dashboard for date selection, business model selection, dataset selection, duplicate checks, status tracking, and logs

Core technologies used:
- Python
- Flask
- pandas
- requests
- BeautifulSoup
- SQLAlchemy
- psycopg2
- PostgreSQL

Important implementation note:
- NEMOSIS is not used
- direct NEMWeb URL extraction is used

## Current Core Datasets Enabled In The Pipeline

These are the currently enabled core datasets in the pipeline:

1. `raw.dispatch_price`
2. `raw.dispatch_regionsum`
3. `raw.trading_price`
4. `raw.trading_regionsum`
5. `raw.dispatch_unit_scada`
6. `raw.dispatch_constraints`
7. `raw.rooftop_pv_actual`

## Current Advanced / Optional Datasets Configured But Not Fully Finalised

These are configured in the pipeline but are currently disabled or require more verification:

1. `raw.dispatch_load`
2. `raw.next_day_dispatch`
3. `raw.bids_per_offer`
4. `raw.bid_day_offer`
5. `raw.fcas_price`
6. `raw.fcas_requirements`
7. `raw.fcas_recovery`
8. `raw.fcas_constraints`
9. `raw.constraint_rhs`
10. `raw.constraint_details`
11. `raw.constraint_equations`
12. `raw.interconnector_results`
13. `raw.intermittent_generation`
14. `raw.semi_scheduled_generation`

## Business Use Cases And Table Mapping

### 1. Price Drivers Analysis

Purpose:
- explain regional price movements
- compare dispatch and trading interval price behaviour
- combine prices with regional demand and generation context

Tables and columns:

| Business Case | NEM Table Pattern | Target Table | Important Columns |
|---|---|---|---|
| Price Drivers Analysis | `DISPATCHPRICE` | `raw.dispatch_price` | `settlementdate`, `regionid`, `intervention`, `rrp`, `eep`, `rop`, `raise6secrrp`, `raise60secrrp`, `raise5minrrp`, `raiseregrrp`, `lower6secrrp`, `lower60secrrp`, `lower5minrrp`, `lowerregrrp`, `raise1secrrp`, `lower1secrrp`, `lastchanged` |
| Price Drivers Analysis | `TRADINGREGIONSUM` | `raw.trading_regionsum` | `settlementdate`, `regionid`, `intervention`, `totaldemand`, `availablegeneration`, `availableload`, `demandforecast`, `dispatchablegeneration`, `dispatchableload`, `netinterchange`, `excessgeneration`, `lastchanged` |
| Price Drivers Analysis | `DISPATCHREGIONSUM` | `raw.dispatch_regionsum` | `settlementdate`, `regionid`, `intervention`, `totaldemand`, `availablegeneration`, `availableload`, `demandforecast`, `dispatchablegeneration`, `dispatchableload`, `netinterchange`, `excessgeneration`, `totalintermittentgeneration`, `demand_and_nonschedgen`, `uigf`, `lastchanged` |

### 2. Demand & Net Demand Analysis

Purpose:
- study operational demand
- compare underlying demand with rooftop PV impact
- assess net demand at regional level

Tables and columns:

| Business Case | NEM Table Pattern | Target Table | Important Columns |
|---|---|---|---|
| Demand & Net Demand Analysis | `DISPATCHREGIONSUM` | `raw.dispatch_regionsum` | `settlementdate`, `regionid`, `totaldemand`, `availablegeneration`, `availableload`, `netinterchange`, `totalintermittentgeneration`, `demand_and_nonschedgen`, `uigf`, `lastchanged` |
| Demand & Net Demand Analysis | `TRADINGREGIONSUM` | `raw.trading_regionsum` | `settlementdate`, `regionid`, `totaldemand`, `availablegeneration`, `availableload`, `netinterchange`, `demandforecast`, `lastchanged` |
| Demand & Net Demand Analysis | `ROOFTOPPVACTUAL` | `raw.rooftop_pv_actual` | `interval_datetime`, `regionid`, `measurement_type`, `mw`, `lastchanged` |

### 3. BESS Trading Analysis

Purpose:
- study battery trading behaviour
- combine prices, system demand, SCADA, and constraints
- extend later with bids/offers when finalised

Tables and columns:

| Business Case | NEM Table Pattern | Target Table | Important Columns |
|---|---|---|---|
| BESS Trading Analysis | `DISPATCHPRICE` | `raw.dispatch_price` | `settlementdate`, `regionid`, `rrp`, `eep`, `rop`, FCAS-related price columns, `lastchanged` |
| BESS Trading Analysis | `DISPATCHREGIONSUM` | `raw.dispatch_regionsum` | `settlementdate`, `regionid`, `totaldemand`, `availablegeneration`, `netinterchange`, `uigf`, `lastchanged` |
| BESS Trading Analysis | `TRADINGREGIONSUM` | `raw.trading_regionsum` | `settlementdate`, `regionid`, `totaldemand`, `availablegeneration`, `netinterchange`, `lastchanged` |
| BESS Trading Analysis | `DISPATCH_UNIT_SCADA` | `raw.dispatch_unit_scada` | `settlementdate`, `duid`, `scadavalue`, `lastchanged` |
| BESS Trading Analysis | `BIDPEROFFER_D` | `raw.bids_per_offer` | to be confirmed |
| BESS Trading Analysis | `BIDDAYOFFER_D` | `raw.bid_day_offer` | to be confirmed |
| BESS Trading Analysis | `DISPATCHCONSTRAINT` | `raw.dispatch_constraints` | `settlementdate`, `constraintid`, `marginalvalue`, `rhs`, `violationdegree`, `lastchanged` |

### 4. FCAS Market Analysis

Purpose:
- analyse FCAS price, requirement, recovery, and constraint interactions
- compare FCAS market conditions with regional dispatch outcomes

Tables and columns:

| Business Case | NEM Table Pattern | Target Table | Important Columns |
|---|---|---|---|
| FCAS Market Analysis | `DISPATCHPRICE` | `raw.dispatch_price` | `settlementdate`, `regionid`, FCAS price columns such as `raise6secrrp`, `raise60secrrp`, `raise5minrrp`, `raiseregrrp`, `lower6secrrp`, `lower60secrrp`, `lower5minrrp`, `lowerregrrp`, `raise1secrrp`, `lower1secrrp` |
| FCAS Market Analysis | `FCASPRICE` | `raw.fcas_price` | to be confirmed |
| FCAS Market Analysis | `FCASREQUIREMENT` | `raw.fcas_requirements` | to be confirmed |
| FCAS Market Analysis | `FCASRECOVERY` | `raw.fcas_recovery` | to be confirmed |
| FCAS Market Analysis | `FCASCONSTRAINT` | `raw.fcas_constraints` | to be confirmed |
| FCAS Market Analysis | `DISPATCH_UNIT_SCADA` | `raw.dispatch_unit_scada` | `settlementdate`, `duid`, `scadavalue`, `lastchanged` |

### 5. Network Constraints Analysis

Purpose:
- analyse constraint-driven price outcomes
- study network limitations and interconnector effects

Tables and columns:

| Business Case | NEM Table Pattern | Target Table | Important Columns |
|---|---|---|---|
| Network Constraints Analysis | `DISPATCHPRICE` | `raw.dispatch_price` | `settlementdate`, `regionid`, `rrp`, `rop`, `lastchanged` |
| Network Constraints Analysis | `DISPATCHCONSTRAINT` | `raw.dispatch_constraints` | `settlementdate`, `constraintid`, `marginalvalue`, `rhs`, `violationdegree`, `lastchanged` |
| Network Constraints Analysis | `CONSTRAINTRHS` | `raw.constraint_rhs` | to be confirmed |
| Network Constraints Analysis | `CONSTRAINTDETAIL` | `raw.constraint_details` | to be confirmed |
| Network Constraints Analysis | `CONSTRAINTEQUATION` | `raw.constraint_equations` | to be confirmed |
| Network Constraints Analysis | `INTERCONNECTORRES` | `raw.interconnector_results` | to be confirmed |

### 6. Renewable Integration Analysis

Purpose:
- analyse renewables, rooftop PV, intermittent generation, and regional demand interaction
- study the effect of variable renewable generation on operational demand and system conditions

Tables and columns:

| Business Case | NEM Table Pattern | Target Table | Important Columns |
|---|---|---|---|
| Renewable Integration Analysis | `DISPATCHREGIONSUM` | `raw.dispatch_regionsum` | `settlementdate`, `regionid`, `totaldemand`, `availablegeneration`, `totalintermittentgeneration`, `demand_and_nonschedgen`, `uigf`, `lastchanged` |
| Renewable Integration Analysis | `TRADINGREGIONSUM` | `raw.trading_regionsum` | `settlementdate`, `regionid`, `totaldemand`, `availablegeneration`, `demandforecast`, `lastchanged` |
| Renewable Integration Analysis | `ROOFTOPPVACTUAL` | `raw.rooftop_pv_actual` | `interval_datetime`, `regionid`, `measurement_type`, `mw`, `lastchanged` |
| Renewable Integration Analysis | `INTERMITTENTGENERATION` | `raw.intermittent_generation` | to be confirmed |
| Renewable Integration Analysis | `SEMISCHEDULEDGENERATION` | `raw.semi_scheduled_generation` | to be confirmed |
| Renewable Integration Analysis | `DISPATCH_UNIT_SCADA` | `raw.dispatch_unit_scada` | `settlementdate`, `duid`, `scadavalue`, `lastchanged` |

### 7. Full NEM Market Dataset

Purpose:
- load every currently enabled dataset from the pipeline configuration

Enabled tables included:
- `raw.dispatch_price`
- `raw.dispatch_regionsum`
- `raw.trading_price`
- `raw.trading_regionsum`
- `raw.dispatch_unit_scada`
- `raw.dispatch_constraints`
- `raw.rooftop_pv_actual`

### 8. Custom Dataset Selection

Purpose:
- let the user manually choose only the required datasets

## Most Important Cross-Project Columns

These are the most important reusable columns across the pipeline:

- `settlementdate`
- `interval_datetime`
- `regionid`
- `duid`
- `rrp`
- `eep`
- `rop`
- `totaldemand`
- `availablegeneration`
- `availableload`
- `netinterchange`
- `demandforecast`
- `totalintermittentgeneration`
- `demand_and_nonschedgen`
- `uigf`
- `scadavalue`
- `constraintid`
- `marginalvalue`
- `rhs`
- `violationdegree`
- `measurement_type`
- `mw`
- `lastchanged`

## Current Priority Tables For Further Development

If continuing the project, the best priority tables to focus on are:

1. `raw.dispatch_price`
2. `raw.dispatch_regionsum`
3. `raw.trading_price`
4. `raw.trading_regionsum`
5. `raw.dispatch_unit_scada`
6. `raw.dispatch_constraints`
7. `raw.rooftop_pv_actual`

These currently provide the strongest foundation for:
- price analysis
- demand analysis
- renewable integration analysis
- operational market dashboards





