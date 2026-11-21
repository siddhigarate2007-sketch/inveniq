# InvenIQ Lakehouse Data Dictionary

This document serves as the canonical reference for the 11 tables residing in the DuckDB/Parquet lakehouse (`data/lakehouse/inveniq_lake.duckdb`). All tables follow strict point-in-time correctness with zero target leakage.

---

## 1. Dimensional Tables

### `dim_destination`
Defines the destination catalog (Indian domestic and international tourist nodes).
- **Primary Key:** `destination_id` (VARCHAR)
- **Granularity:** One record per tourist destination.

| Column Name | Data Type | Nullable | Description | Sample / Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `destination_id` | VARCHAR | NO | Unique destination code | `DEST_GOA`, `DEST_DUBAI` |
| `name` | VARCHAR | NO | Full destination display name | `Goa`, `Dubai`, `Kashmir` |
| `country` | VARCHAR | NO | Host nation | `India`, `UAE`, `Thailand` |
| `region` | VARCHAR | NO | Geographic region | `West India`, `Middle East` |
| `tier` | INTEGER | NO | Commercial tier ranking (1=Metropolitan/Major, 2=Regional leisure) | `1`, `2` |
| `domestic` | BOOLEAN | NO | True if Indian domestic, False if international | `TRUE`, `FALSE` |
| `lead_time_profile` | VARCHAR | NO | Typical booking lead-time regime | `SHORT_HAUL`, `LONG_HAUL` |

---

### `dim_property` (Hotels)
Defines accommodation properties under supplier allotment contracts.
- **Primary Key:** `property_id` (VARCHAR)
- **Foreign Keys:** `destination_id` -> `dim_destination(destination_id)`

| Column Name | Data Type | Nullable | Description | Sample / Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `property_id` | VARCHAR | NO | Unique property identifier | `PROP_GOA_001` |
| `destination_id` | VARCHAR | NO | Destination identifier | `DEST_GOA` |
| `name` | VARCHAR | NO | Property commercial name | `Taj Exotica Resort & Spa` |
| `star_rating` | INTEGER | NO | Quality tier (3, 4, 5 stars) | `3`, `4`, `5` |
| `chain_code` | VARCHAR | YES | Hospitality chain identifier | `IHCL`, `MARRIOTT`, `ACCOR` |
| `total_rooms` | INTEGER | NO | Total physical capacity of property | `50` to `400` |
| `avg_base_rate_inr`| DOUBLE | NO | Baseline rack rate before seasonality | `₹4,500` to `₹42,000` |

---

### `dim_route` (Airlines)
Defines flight route corridors connecting departure hubs to destination gateways.
- **Primary Key:** `route_id` (VARCHAR)
- **Foreign Keys:** `destination_id` -> `dim_destination(destination_id)`

| Column Name | Data Type | Nullable | Description | Sample / Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `route_id` | VARCHAR | NO | Route identifier | `ROUTE_BOM_GOA_01` |
| `destination_id` | VARCHAR | NO | Destination arrival gateway | `DEST_GOA` |
| `origin_airport` | VARCHAR | NO | 3-letter IATA origin hub | `DEL`, `BOM`, `BLR` |
| `dest_airport` | VARCHAR | NO | 3-letter IATA destination | `GOI`, `DXB`, `SXR` |
| `carrier_code` | VARCHAR | NO | 2-letter IATA carrier code | `6E` (IndiGo), `AI` (Air India), `EK` (Emirates) |
| `daily_frequency` | INTEGER | NO | Scheduled daily block flights | `1` to `8` |

---

### `dim_supplier`
Defines contracting wholesalers, hotel chains, and airline consolidators.
- **Primary Key:** `supplier_id` (VARCHAR)

| Column Name | Data Type | Nullable | Description | Sample / Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `supplier_id` | VARCHAR | NO | Unique supplier identifier | `SUP_IHCL_TAJ`, `SUP_INDIGO` |
| `name` | VARCHAR | NO | Registered corporate supplier name | `IHCL Hotels Limited` |
| `supplier_type` | VARCHAR | NO | Categorization | `HOTEL_CHAIN`, `AIRLINE`, `DMC` |
| `reliability_score`| DOUBLE | NO | Historical fulfillment fidelity (0.0 to 1.0) | `0.92` to `0.99` |
| `payment_terms_days`| INTEGER | NO | Credit / settlement window in days | `15`, `30`, `45` |

---

### `dim_calendar`
Universal date dimension enriched with Indian holiday spikes and seasonality tags.
- **Primary Key:** `date` (DATE)

| Column Name | Data Type | Nullable | Description | Sample / Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `date` | DATE | NO | Calendar date | `2024-10-31` |
| `year` | INTEGER | NO | Calendar year | `2024` |
| `month` | INTEGER | NO | Month index (1 - 12) | `10` |
| `day_of_week` | INTEGER | NO | ISO day (1=Monday, 7=Sunday) | `4` |
| `is_weekend` | BOOLEAN | NO | True if Saturday or Sunday | `TRUE`, `FALSE` |
| `is_holiday` | BOOLEAN | NO | National or state gazetted holiday | `TRUE`, `FALSE` |
| `is_festival` | BOOLEAN | NO | Spike festival (Diwali, NYE, Eid) | `TRUE`, `FALSE` |
| `festival_name` | VARCHAR | YES | Festival label | `Diwali`, `Christmas/NYE` |
| `season_tag` | VARCHAR | NO | Seasonal demand level | `PEAK`, `SHOULDER`, `MONSOON` |

---

## 2. Fact Tables

### `fact_bookings`
Historical confirmed and cancelled travel bookings across all TBO B2B sub-agents.
- **Primary Key:** `booking_id` (VARCHAR)
- **Granularity:** One record per individual booked travel unit.

| Column Name | Data Type | Nullable | Description | Sample / Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `booking_id` | VARCHAR | NO | Unique transaction identifier | `BKG_2024_00012` |
| `booking_ts` | TIMESTAMP | NO | Timestamp when booking was executed | `2024-04-12 14:22:00` |
| `travel_date` | DATE | NO | Check-in date or departure date | `2024-05-10` |
| `lead_time_days` | INTEGER | NO | `travel_date - booking_date` | `0` to `120` |
| `product_type` | VARCHAR | NO | Product category | `HOTEL`, `FLIGHT` |
| `entity_id` | VARCHAR | NO | Foreign key to `dim_property` or `dim_route` | `PROP_GOA_001` |
| `supplier_id` | VARCHAR | NO | Wholesaler providing inventory | `SUP_IHCL_TAJ` |
| `quantity` | INTEGER | NO | Units booked (rooms or seats) | `1` to `5` |
| `cost_price_inr` | DOUBLE | NO | Net procurement cost per unit | `₹16,500` |
| `sell_price_inr` | DOUBLE | NO | Gross realization sell price per unit | `₹22,800` |
| `cancelled` | BOOLEAN | NO | True if booking was subsequently cancelled | `TRUE`, `FALSE` |
| `cancel_ts` | TIMESTAMP | YES | Timestamp of cancellation event | `2024-04-28 09:15:00` |

---

### `fact_searches` (Look-to-Book Pipeline)
B2B search queries from travel agents, capturing latent demand intent before conversion.
- **Granularity:** Daily aggregated search volume per destination and travel date.

| Column Name | Data Type | Nullable | Description | Sample / Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `search_date` | DATE | NO | Date search query was made | `2024-04-12` |
| `destination_id` | VARCHAR | NO | Destination queried | `DEST_GOA` |
| `product_type` | VARCHAR | NO | Searched product category | `HOTEL`, `FLIGHT` |
| `travel_date` | DATE | NO | Targeted travel date | `2024-05-10` |
| `search_volume` | INTEGER | NO | Cumulative search queries | `120` to `4,500` |
| `clicks` | INTEGER | NO | Product detail impressions / clicks | `15` to `650` |
| `look_to_book_ratio`| DOUBLE | NO | Searches divided by confirmed bookings | `12.5` to `85.0` |

---

### `fact_soldouts` (Demand Censoring Engine)
Records of capacity exhaustion periods where zero units were available for sale.
- **Granularity:** Daily record per entity when allotment reached 0.

| Column Name | Data Type | Nullable | Description | Sample / Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `entity_id` | VARCHAR | NO | Property or flight route identifier | `PROP_KASHMIR_002` |
| `date` | DATE | NO | Date inventory hit zero allotment | `2024-01-15` |
| `duration_hours` | DOUBLE | NO | Hours unavailable during active search hours | `8.0` to `24.0` |
| `estimated_lost_demand` | DOUBLE | NO | Uncensored latent demand via Tobit estimator | `15.4` to `48.2` units |

---

### `fact_supplier_terms`
Active supplier contract terms, MOQ bounds, and cutoff release schedules.

| Column Name | Data Type | Nullable | Description | Sample / Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `supplier_id` | VARCHAR | NO | Supplier identifier | `SUP_KERZNER_INTL` |
| `entity_id` | VARCHAR | NO | Property or flight route identifier | `PROP_DXB_001` |
| `allotment_size` | INTEGER | NO | Maximum block units available for pre-buy | `50` to `250` |
| `min_order_qty` | INTEGER | NO | Minimum order quantity (MOQ) | `10` to `50` |
| `release_cutoff_days`| INTEGER | NO | Cutoff deadline before travel date for penalty-free release | `7`, `14`, `21`, `30` |
| `cancel_penalty_pct` | DOUBLE | NO | Forfeiture rate for unsold units post-cutoff | `0.50` to `1.00` |
| `volume_discount_pct`| DOUBLE | NO | Early pre-buy cost discount | `0.05` to `0.15` |

---

### `fact_external_signals`
Macro signals driving travel demand fluctuations.

| Column Name | Data Type | Nullable | Description | Sample / Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `date` | DATE | NO | Observation date | `2024-10-15` |
| `destination_id` | VARCHAR | NO | Destination identifier | `DEST_GOA` |
| `weather_score` | DOUBLE | NO | 0 (monsoon/storm) to 1.0 (ideal sunny) | `0.85` |
| `fuel_price_index` | DOUBLE | NO | Jet fuel index (base 100.0) | `104.2` |
| `competitor_price_idx`| DOUBLE | NO | Relative OTA pricing index | `0.98` to `1.12` |
| `fx_rate_usd_inr` | DOUBLE | NO | Daily USD/INR currency exchange rate | `83.45` |
