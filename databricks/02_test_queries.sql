-- Test queries sau khi pipeline chạy xong

SELECT *
FROM workspace.default.stock_dashboard_p
ORDER BY Ticker;


-- Dữ liệu để vẽ line chart trong Databricks
-- X axis: Date
-- Y axis: Close, MA20, MA50
-- Series/group: Ticker

SELECT
  Date,
  Ticker,
  Close,
  MA20,
  MA50,
  Signal,
  Trend
FROM workspace.default.stock_signal_p
WHERE Ticker IN ('AAPL', 'MSFT', 'TSLA')
ORDER BY Ticker, Date;


-- Đếm số dòng qua từng bảng

SELECT 'raw_seed' AS table_name, COUNT(*) AS rows
FROM stock_demo.cloud_stock_raw_seed

UNION ALL

SELECT 'stock_raw_p', COUNT(*)
FROM workspace.default.stock_raw_p

UNION ALL

SELECT 'stock_cleaned_p', COUNT(*)
FROM workspace.default.stock_cleaned_p

UNION ALL

SELECT 'stock_features_p', COUNT(*)
FROM workspace.default.stock_features_p

UNION ALL

SELECT 'stock_signal_p', COUNT(*)
FROM workspace.default.stock_signal_p

UNION ALL

SELECT 'stock_dashboard_p', COUNT(*)
FROM workspace.default.stock_dashboard_p;
