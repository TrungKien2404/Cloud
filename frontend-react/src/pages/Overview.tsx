import React, { useState, useEffect } from 'react';
import Plot from '../components/Plot';
import api from '../api';

const REGIONS: Record<string, any> = {
  "Việt Nam": {
    "chart_ticker": "FPT.VN",
    "chart_name": "FPT",
    "indices": [
      { "name": "FPT", "ticker": "FPT.VN" },
      { "name": "VIC", "ticker": "VIC.VN" },
      { "name": "HPG", "ticker": "HPG.VN" },
      { "name": "VHM", "ticker": "VHM.VN" },
      { "name": "VCB", "ticker": "VCB.VN" },
      { "name": "TCB", "ticker": "TCB.VN" },
      { "name": "VNM", "ticker": "VNM.VN" },
      { "name": "MWG", "ticker": "MWG.VN" },
      { "name": "CTG", "ticker": "CTG.VN" },
      { "name": "HDB", "ticker": "HDB.VN" },
    ],
  },
  "Mỹ": {
    "chart_ticker": "^GSPC",
    "chart_name": "S&P 500",
    "indices": [
      { "name": "S&P 500", "ticker": "^GSPC" },
      { "name": "Dow Jones", "ticker": "^DJI" },
      { "name": "NASDAQ", "ticker": "^IXIC" },
      { "name": "AAPL", "ticker": "AAPL" },
      { "name": "MSFT", "ticker": "MSFT" },
      { "name": "AMZN", "ticker": "AMZN" },
      { "name": "GOOGL", "ticker": "GOOGL" },
      { "name": "TSLA", "ticker": "TSLA" },
      { "name": "NVDA", "ticker": "NVDA" },
      { "name": "META", "ticker": "META" },
    ],
  },
  "Châu Âu": {
    "chart_ticker": "^STOXX50E",
    "chart_name": "Euro Stoxx 50",
    "indices": [
      { "name": "Euro Stoxx 50", "ticker": "^STOXX50E" },
      { "name": "FTSE 100", "ticker": "^FTSE" },
      { "name": "DAX", "ticker": "^GDAXI" },
      { "name": "CAC 40", "ticker": "^FCHI" },
      { "name": "LVMH", "ticker": "MC.PA" },
      { "name": "ASML", "ticker": "ASML" },
    ],
  },
  "Châu Á": {
    "chart_ticker": "^N225",
    "chart_name": "Nikkei 225",
    "indices": [
      { "name": "Nikkei 225", "ticker": "^N225" },
      { "name": "Hang Seng", "ticker": "^HSI" },
      { "name": "Shanghai", "ticker": "000001.SS" },
      { "name": "Toyota", "ticker": "7203.T" },
      { "name": "Samsung", "ticker": "005930.KS" },
      { "name": "Alibaba", "ticker": "9988.HK" },
    ],
  },
};

const CHART_PERIODS: Record<string, { period: string; interval: string }> = {
  "1D": { period: "1d", interval: "5m" },
  "5D": { period: "5d", interval: "15m" },
  "1M": { period: "1mo", interval: "1h" },
  "3M": { period: "3mo", interval: "1d" },
  "6M": { period: "6mo", interval: "1d" },
  "YTD": { period: "ytd", interval: "1d" },
  "1Y": { period: "1y", interval: "1d" },
  "ALL": { period: "max", interval: "1wk" },
};

const Overview: React.FC = () => {
  const [category, setCategory] = useState('Chứng khoán');
  const [region, setRegion] = useState('Việt Nam');
  const [period, setPeriod] = useState('1D');
  
  const [chartTicker, setChartTicker] = useState(REGIONS["Việt Nam"]["chart_ticker"]);
  const [chartName, setChartName] = useState(REGIONS["Việt Nam"]["chart_name"]);
  
  // Data State
  const [chartData, setChartData] = useState<any>(null);
  const [indicesSummaries, setIndicesSummaries] = useState<Record<string, any>>({});
  
  const [loadingChart, setLoadingChart] = useState(false);
  const [loadingTable, setLoadingTable] = useState(false);

  // Cập nhật ticker khi đổi Region
  const handleRegionChange = (newRegion: string) => {
    setRegion(newRegion);
    setChartTicker(REGIONS[newRegion]["chart_ticker"]);
    setChartName(REGIONS[newRegion]["chart_name"]);
  };

  // Fetch Chart Data
  useEffect(() => {
    const fetchChart = async () => {
      setLoadingChart(true);
      try {
        const params = CHART_PERIODS[period];
        const res = await api.get(`/api/yfinance/chart/${chartTicker}`, {
          params: { period: params.period, interval: params.interval }
        });
        setChartData(res.data);
      } catch (err) {
        console.error('Lỗi tải dữ liệu biểu đồ:', err);
        setChartData(null);
      } finally {
        setLoadingChart(false);
      }
    };
    fetchChart();
  }, [chartTicker, period]);

  // Fetch Table Data for Region
  useEffect(() => {
    const fetchTable = async () => {
      setLoadingTable(true);
      const tickers = REGIONS[region]["indices"].map((idx: any) => idx.ticker);
      const summaries: Record<string, any> = {};

      // Gọi tuần tự hoặc song song lấy summary
      await Promise.all(
        tickers.map(async (t: string) => {
          try {
            const res = await api.get(`/api/yfinance/summary/${t}`);
            summaries[t] = res.data;
          } catch (err) {
            console.error(`Lỗi summary ticker ${t}:`, err);
          }
        })
      );
      setIndicesSummaries(summaries);
      setLoadingTable(false);
    };
    fetchTable();
  }, [region]);

  const fmtPct = (val: number | null) => {
    if (val === undefined || val === null) return '—';
    return `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;
  };

  const getPctColor = (val: number | null) => {
    if (val === undefined || val === null) return '#94a3b8';
    return val >= 0 ? '#10b981' : '#ef4444';
  };

  // Tính toán các chỉ số của chart đang xem
  const isUp = chartData ? (chartData.latest - chartData.first) >= 0 : true;
  const lineColor = isUp ? '#10b981' : '#ef4444';
  const fillColor = isUp ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)';

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Thị trường</h2>

      {/* Category Tabs */}
      <div style={styles.tabBar}>
        {['Chứng khoán', 'Hàng hóa', 'Tiền tệ', 'Tiền ảo'].map((cat) => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className="btn"
            style={{
              ...styles.catBtn,
              ...(category === cat ? styles.catBtnActive : styles.catBtnInactive),
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      {category !== 'Chứng khoán' ? (
        <div className="glass-card" style={styles.developmentMsg}>
          <h3>Tính năng {category} đang được phát triển — Sắp ra mắt!</h3>
        </div>
      ) : (
        <div style={styles.mainLayout}>
          {/* CỘT TRÁI - BIỂU ĐỒ */}
          <div style={styles.leftColumn}>
            {/* Period selector */}
            <div style={styles.periodBar}>
              {Object.keys(CHART_PERIODS).map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  style={{
                    ...styles.periodBtn,
                    ...(period === p ? styles.periodBtnActive : {}),
                  }}
                >
                  {p}
                </button>
              ))}
            </div>

            <div className="glass-card" style={styles.chartCard}>
              {loadingChart ? (
                <div style={styles.loadingSpinner}>Đang tải biểu đồ...</div>
              ) : chartData ? (
                <div>
                  <div style={styles.chartHeader}>
                    <div>
                      <span style={styles.tickerName}>{chartName}</span>
                      <span style={styles.tickerCode}> ({chartTicker})</span>
                    </div>
                    <div style={styles.chartValueRow}>
                      <span style={styles.chartPrice}>{chartData.latest.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                      <span style={{ ...styles.chartChange, color: lineColor }}>
                        {isUp ? '▲' : '▼'} {Math.abs(chartData.latest - chartData.first).toFixed(2)} ({((chartData.latest - chartData.first) / chartData.first * 100).toFixed(2)}%)
                      </span>
                    </div>
                  </div>

                  <div style={styles.plotlyWrapper}>
                    <Plot
                      data={[
                        {
                          x: chartData.dates,
                          y: chartData.closes,
                          type: 'scatter',
                          mode: 'lines',
                          line: { color: lineColor, width: 2 },
                          fill: 'tozeroy',
                          fillcolor: fillColor,
                          hoverinfo: 'y',
                        },
                      ]}
                      layout={{
                        height: 320,
                        margin: { l: 0, r: 10, t: 10, b: 20 },
                        paper_bgcolor: 'rgba(0,0,0,0)',
                        plot_bgcolor: 'rgba(0,0,0,0)',
                        xaxis: {
                          showgrid: true,
                          gridcolor: 'rgba(255,255,255,0.05)',
                          zeroline: false,
                          tickfont: { color: '#64748b' }
                        },
                        yaxis: {
                          showgrid: true,
                          gridcolor: 'rgba(255,255,255,0.05)',
                          zeroline: false,
                          side: 'right',
                          tickfont: { color: '#64748b' }
                        },
                        showlegend: false,
                        hovermode: 'x unified',
                      }}
                      config={{ displayModeBar: false, responsive: true }}
                      style={{ width: '100%', height: '100%' }}
                    />
                  </div>
                </div>
              ) : (
                <div style={styles.errorText}>Không thể tải dữ liệu chỉ số này.</div>
              )}
            </div>
          </div>

          {/* CỘT PHẢI - BẢNG CHỈ SỐ CLICKABLE */}
          <div style={styles.rightColumn}>
            {/* Region selector */}
            <div style={styles.regionBar}>
              {Object.keys(REGIONS).map((r) => (
                <button
                  key={r}
                  onClick={() => handleRegionChange(r)}
                  style={{
                    ...styles.regionBtn,
                    ...(region === r ? styles.regionBtnActive : {}),
                  }}
                >
                  {r}
                </button>
              ))}
            </div>

            <div className="glass-card" style={styles.tableCard}>
              {loadingTable ? (
                <div style={styles.loadingSpinner}>Đang tải bảng chỉ số...</div>
              ) : (
                <div style={styles.tableContainer}>
                  <table style={styles.table}>
                    <thead>
                      <tr>
                        <th style={{ ...styles.th, textAlign: 'left' }}>Tên</th>
                        <th style={styles.th}>Giá</th>
                        <th style={styles.th}>D</th>
                        <th style={styles.th}>W</th>
                        <th style={styles.th}>M</th>
                        <th style={styles.th}>Q</th>
                        <th style={styles.th}>YTD</th>
                      </tr>
                    </thead>
                    <tbody>
                      {REGIONS[region]["indices"].map((idx: any) => {
                        const sum = indicesSummaries[idx.ticker] || {};
                        const isSelected = chartTicker === idx.ticker;
                        return (
                          <tr
                            key={idx.ticker}
                            onClick={() => {
                              setChartTicker(idx.ticker);
                              setChartName(idx.name);
                            }}
                            style={{
                              ...styles.tr,
                              ...(isSelected ? styles.trSelected : {}),
                            }}
                          >
                            <td style={styles.tdName}>{idx.name}</td>
                            <td style={styles.tdPrice}>
                              {sum.price !== undefined ? sum.price.toLocaleString(undefined, { minimumFractionDigits: 2 }) : '—'}
                            </td>
                            <td style={{ ...styles.tdPct, color: getPctColor(sum.D) }}>{fmtPct(sum.D)}</td>
                            <td style={{ ...styles.tdPct, color: getPctColor(sum.W) }}>{fmtPct(sum.W)}</td>
                            <td style={{ ...styles.tdPct, color: getPctColor(sum.M) }}>{fmtPct(sum.M)}</td>
                            <td style={{ ...styles.tdPct, color: getPctColor(sum.Q) }}>{fmtPct(sum.Q)}</td>
                            <td style={{ ...styles.tdPct, color: getPctColor(sum.YTD) }}>{fmtPct(sum.YTD)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '10px 0',
  },
  title: {
    fontSize: '28px',
    fontWeight: 900,
    color: '#f1f5f9',
    marginBottom: '16px',
  },
  tabBar: {
    display: 'flex',
    gap: '12px',
    marginBottom: '20px',
  },
  catBtn: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 600,
  },
  catBtnActive: {
    background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
    color: '#ffffff',
    border: 'none',
  },
  catBtnInactive: {
    background: 'rgba(30, 41, 59, 0.4)',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    color: '#cbd5e1',
  },
  developmentMsg: {
    textAlign: 'center',
    padding: '60px',
    color: '#94a3b8',
  },
  mainLayout: {
    display: 'flex',
    gap: '24px',
    marginTop: '10px',
  },
  leftColumn: {
    flex: 3,
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  rightColumn: {
    flex: 2,
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  periodBar: {
    display: 'flex',
    background: 'rgba(15, 23, 42, 0.4)',
    padding: '4px',
    borderRadius: '10px',
    gap: '4px',
    maxWidth: 'max-content',
  },
  periodBtn: {
    padding: '6px 12px',
    background: 'transparent',
    border: 'none',
    color: '#94a3b8',
    fontWeight: 600,
    fontSize: '12px',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  periodBtnActive: {
    background: '#6366f1',
    color: '#ffffff',
  },
  regionBar: {
    display: 'flex',
    background: 'rgba(15, 23, 42, 0.4)',
    padding: '4px',
    borderRadius: '10px',
    gap: '4px',
    width: '100%',
  },
  regionBtn: {
    flex: 1,
    padding: '6px 0',
    background: 'transparent',
    border: 'none',
    color: '#94a3b8',
    fontWeight: 600,
    fontSize: '12px',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    textAlign: 'center',
  },
  regionBtnActive: {
    background: '#6366f1',
    color: '#ffffff',
  },
  chartCard: {
    padding: '24px',
    minHeight: '440px',
  },
  chartHeader: {
    display: 'flex',
    flexDirection: 'column',
    marginBottom: '16px',
  },
  tickerName: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#f1f5f9',
  },
  tickerCode: {
    fontSize: '12px',
    color: '#64748b',
  },
  chartValueRow: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '12px',
    marginTop: '6px',
  },
  chartPrice: {
    fontSize: '32px',
    fontWeight: 800,
    color: '#f1f5f9',
    letterSpacing: '-1px',
  },
  chartChange: {
    fontSize: '14px',
    fontWeight: 700,
  },
  plotlyWrapper: {
    width: '100%',
    height: '320px',
  },
  tableCard: {
    padding: '16px',
    minHeight: '458px',
    display: 'flex',
    flexDirection: 'column',
  },
  tableContainer: {
    overflowY: 'auto',
    maxHeight: '420px',
    width: '100%',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  th: {
    color: '#64748b',
    fontSize: '11px',
    fontWeight: 600,
    padding: '8px 4px',
    borderBottom: '1px solid rgba(148, 163, 184, 0.15)',
    textAlign: 'right',
    textTransform: 'uppercase',
  },
  tr: {
    borderBottom: '1px solid rgba(148, 163, 184, 0.05)',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  trSelected: {
    background: 'rgba(99, 102, 241, 0.15)',
  },
  tdName: {
    fontSize: '13px',
    fontWeight: 700,
    color: '#f1f5f9',
    padding: '10px 4px',
    textAlign: 'left',
  },
  tdPrice: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#cbd5e1',
    padding: '10px 4px',
    textAlign: 'right',
  },
  tdPct: {
    fontSize: '12px',
    fontWeight: 600,
    padding: '10px 4px',
    textAlign: 'right',
  },
  loadingSpinner: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '300px',
    color: '#94a3b8',
    fontSize: '14px',
    fontWeight: 600,
  },
  errorText: {
    textAlign: 'center',
    color: '#ef4444',
    paddingTop: '100px',
  },
};

export default Overview;
