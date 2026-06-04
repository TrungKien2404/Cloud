CREATE OR REFRESH MATERIALIZED VIEW stock_raw_p
AS
SELECT
  CAST(Date AS DATE) AS Date,
  CAST(Ticker AS STRING) AS Ticker,
  CAST(Open AS DOUBLE) AS Open,
  CAST(High AS DOUBLE) AS High,
  CAST(Low AS DOUBLE) AS Low,
  CAST(Close AS DOUBLE) AS Close,
  CAST(Adj_Close AS DOUBLE) AS Adj_Close,
  CAST(Volume AS BIGINT) AS Volume,
  CAST(IngestedAt AS TIMESTAMP) AS IngestedAt
FROM stock_demo.cloud_stock_raw_seed;


CREATE OR REFRESH MATERIALIZED VIEW stock_cleaned_p
AS
SELECT
  Date,
  Ticker,
  Open,
  High,
  Low,
  Close,
  Adj_Close,
  Volume,
  IngestedAt
FROM stock_raw_p
WHERE Date IS NOT NULL
  AND Ticker IS NOT NULL
  AND Close IS NOT NULL
  AND Close > 0;


CREATE OR REFRESH MATERIALIZED VIEW stock_features_p
AS
SELECT
  Date,
  Ticker,
  Open,
  High,
  Low,
  Close,
  Adj_Close,
  Volume,
  IngestedAt,

  LAG(Close, 1) OVER (
    PARTITION BY Ticker
    ORDER BY Date
  ) AS Prev_Close,

  (Close / LAG(Close, 1) OVER (
    PARTITION BY Ticker
    ORDER BY Date
  ) - 1.0) AS Daily_Return,

  AVG(Close) OVER (
    PARTITION BY Ticker
    ORDER BY Date
    ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
  ) AS MA10,

  AVG(Close) OVER (
    PARTITION BY Ticker
    ORDER BY Date
    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
  ) AS MA20,

  AVG(Close) OVER (
    PARTITION BY Ticker
    ORDER BY Date
    ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
  ) AS MA50

FROM stock_cleaned_p;


CREATE OR REFRESH MATERIALIZED VIEW stock_signal_p
AS
SELECT
  Date,
  Ticker,
  Open,
  High,
  Low,
  Close,
  Adj_Close,
  Volume,
  IngestedAt,
  Prev_Close,
  Daily_Return,
  MA10,
  MA20,
  MA50,

  CASE
    WHEN Close > MA20 THEN 'BUY'
    WHEN Close < MA20 THEN 'SELL'
    ELSE 'HOLD'
  END AS Signal,

  CASE
    WHEN Close > MA20 AND MA20 > MA50 THEN 'Bullish'
    WHEN Close < MA20 AND MA20 < MA50 THEN 'Bearish'
    ELSE 'Neutral'
  END AS Trend

FROM stock_features_p;


CREATE OR REFRESH MATERIALIZED VIEW stock_dashboard_p
AS
WITH ranked AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY Ticker
      ORDER BY Date DESC
    ) AS rn
  FROM stock_signal_p
)
SELECT
  Date,
  Ticker,
  Close,
  Prev_Close,
  Daily_Return,
  MA10,
  MA20,
  MA50,
  Signal,
  Trend
FROM ranked
WHERE rn = 1;
