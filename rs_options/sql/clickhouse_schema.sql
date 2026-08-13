-- Data Pipeline Architecture — ClickHouse reference DDL (spec §46)
-- Tiered OPRA-scale storage: hot NVMe → warm → cold object storage.
-- Configure storage_policy 'tiered' with volumes: hot, warm, cold.

CREATE TABLE IF NOT EXISTS options_nbbo (
    trade_date   Date,
    ts           DateTime64(3, 'UTC') CODEC(DoubleDelta, LZ4),
    underlying   LowCardinality(String),
    expiry       Date,
    strike       Decimal(10, 2),
    right        Enum8('C' = 1, 'P' = 2),
    bid          Float64 CODEC(Gorilla, ZSTD(3)),
    ask          Float64 CODEC(Gorilla, ZSTD(3)),
    bid_size     UInt32,
    ask_size     UInt32,
    exchange_ts  DateTime64(3, 'UTC') CODEC(DoubleDelta, LZ4),
    receipt_ts   DateTime64(3, 'UTC') CODEC(DoubleDelta, LZ4)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_date)
ORDER BY (underlying, expiry, strike, right, ts)
TTL trade_date + INTERVAL 90 DAY TO VOLUME 'warm',
    trade_date + INTERVAL 2 YEAR TO VOLUME 'cold'
SETTINGS storage_policy = 'tiered';

CREATE TABLE IF NOT EXISTS options_trades (
    trade_date   Date,
    ts           DateTime64(3, 'UTC') CODEC(DoubleDelta, LZ4),
    underlying   LowCardinality(String),
    expiry       Date,
    strike       Decimal(10, 2),
    right        Enum8('C' = 1, 'P' = 2),
    price        Float64 CODEC(Gorilla, ZSTD(3)),
    size         UInt32,
    exchange     LowCardinality(String),
    conditions   String CODEC(ZSTD(3)),
    exchange_ts  DateTime64(3, 'UTC') CODEC(DoubleDelta, LZ4),
    receipt_ts   DateTime64(3, 'UTC') CODEC(DoubleDelta, LZ4)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_date)
ORDER BY (underlying, expiry, strike, right, ts)
SETTINGS storage_policy = 'tiered';

CREATE TABLE IF NOT EXISTS options_bars_1m (
    trade_date   Date,
    ts           DateTime('UTC') CODEC(DoubleDelta, LZ4),
    underlying   LowCardinality(String),
    expiry       Date,
    strike       Decimal(10, 2),
    right        Enum8('C' = 1, 'P' = 2),
    open         Float64 CODEC(Gorilla, ZSTD(3)),
    high         Float64 CODEC(Gorilla, ZSTD(3)),
    low          Float64 CODEC(Gorilla, ZSTD(3)),
    close        Float64 CODEC(Gorilla, ZSTD(3)),
    volume       UInt32,
    vwap         Float64 CODEC(Gorilla, ZSTD(3)),
    n_trades     UInt32
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_date)
ORDER BY (underlying, expiry, strike, right, ts)
SETTINGS storage_policy = 'tiered';

CREATE TABLE IF NOT EXISTS chains_eod (
    trade_date    Date,
    underlying    LowCardinality(String),
    expiry        Date,
    strike        Decimal(10, 2),
    right         Enum8('C' = 1, 'P' = 2),
    bid           Float64 CODEC(Gorilla, ZSTD(3)),
    ask           Float64 CODEC(Gorilla, ZSTD(3)),
    last          Float64 CODEC(Gorilla, ZSTD(3)),
    volume        UInt32,
    open_interest UInt32,
    iv            Float32 CODEC(Gorilla, ZSTD(3)),
    delta         Float32 CODEC(Gorilla, ZSTD(3)),
    gamma         Float32 CODEC(Gorilla, ZSTD(3)),
    theta         Float32 CODEC(Gorilla, ZSTD(3)),
    vega          Float32 CODEC(Gorilla, ZSTD(3)),
    greeks_source LowCardinality(String),    -- vendor | model:<version>
    data_source   LowCardinality(String)     -- versioned vendor id (spec §46.6)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_date)
ORDER BY (underlying, trade_date, expiry, strike, right)
SETTINGS storage_policy = 'tiered';

CREATE TABLE IF NOT EXISTS underlying_bars_1m (
    trade_date  Date,
    ts          DateTime('UTC') CODEC(DoubleDelta, LZ4),
    ticker      LowCardinality(String),
    open        Float64 CODEC(Gorilla, ZSTD(3)),
    high        Float64 CODEC(Gorilla, ZSTD(3)),
    low         Float64 CODEC(Gorilla, ZSTD(3)),
    close       Float64 CODEC(Gorilla, ZSTD(3)),
    volume      UInt64,
    vwap        Float64 CODEC(Gorilla, ZSTD(3))
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_date)
ORDER BY (ticker, ts)
SETTINGS storage_policy = 'tiered';

-- Vol surface snapshots power skew percentiles (spec §25).
CREATE TABLE IF NOT EXISTS iv_surface_snapshots (
    trade_date      Date,
    ts              DateTime('UTC') CODEC(DoubleDelta, LZ4),
    underlying      LowCardinality(String),
    tenor_days      UInt16,
    atm_iv          Float32,
    rr25            Float32,
    bf25            Float32,
    put_skew_slope  Float32,
    call_skew_slope Float32,
    term_slope      Float32,
    fit_method      LowCardinality(String),   -- raw | poly | svi:<version>
    skew_state      LowCardinality(String)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_date)
ORDER BY (underlying, tenor_days, ts)
SETTINGS storage_policy = 'tiered';

CREATE TABLE IF NOT EXISTS macro_events (
    event_ts    DateTime('UTC'),
    event       LowCardinality(String),
    tier        UInt8,
    expected    Nullable(Float64),
    actual      Nullable(Float64),
    prior       Nullable(Float64),
    revised     Nullable(Float64),
    status      Enum8('scheduled' = 1, 'released' = 2, 'revised' = 3),
    released_ts Nullable(DateTime('UTC'))     -- receipt-side stamp (spec §49)
)
ENGINE = ReplacingMergeTree(released_ts)
ORDER BY (event, event_ts);

-- Point-in-time universe membership (survivorship protection, spec §50).
CREATE TABLE IF NOT EXISTS universe_membership (
    ticker      LowCardinality(String),
    tier        Enum8('A' = 1, 'B' = 2, 'C' = 3),
    valid_from  Date,
    valid_to    Nullable(Date),               -- NULL = current
    reason      String
)
ENGINE = MergeTree
ORDER BY (ticker, valid_from);

-- Example as-of alignment (spec §46.4, pattern 2):
--   SELECT o.*, u.close AS underlying_px
--   FROM options_nbbo o
--   ASOF JOIN underlying_bars_1m u
--     ON o.underlying = u.ticker AND o.ts >= u.ts
