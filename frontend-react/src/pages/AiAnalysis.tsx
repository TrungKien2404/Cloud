import React, { useState } from 'react';
import Plot from '../components/Plot';
import { Search, ShieldAlert, Award } from 'lucide-react';
import api from '../api';
import MetricCard from '../components/MetricCard';

const AiAnalysis: React.FC = () => {
  const [ticker, setTicker] = useState('AAPL');
  const [period, setPeriod] = useState('1y');
  const [interval, setIntervalVal] = useState('1d');

  // Loading and error states
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [data, setData] = useState<any>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker.trim()) {
      setErrorMsg('Vui lòng nhập ticker.');
      return;
    }

    setLoading(true);
    setErrorMsg('');
    try {
      const res = await api.get(`/api/ai-analysis/${ticker.toUpperCase().trim()}`, {
        params: { period, interval }
      });
      setData(res.data);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.response?.data?.detail || 'Không tải được dữ liệu phân tích. Vui lòng kiểm tra lại mã cổ phiếu!');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const getRsiColor = (val: number) => {
    if (val >= 70) return 'red';
    if (val <= 30) return 'green';
    return 'blue';
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Phân Tích & AI Dự Báo</h2>
      <p style={styles.subtitle}>
        Hỗ trợ mọi mã trên Yahoo Finance: cổ phiếu Mỹ, Crypto (BTC-USD), cổ phiếu Việt Nam (*.VN), hàng hóa, v.v.
      </p>

      {/* SEARCH FORM */}
      <form onSubmit={handleSearch} style={styles.searchForm}>
        <div style={styles.formRow}>
          <div style={{ ...styles.formGroup, flex: 2 }}>
            <label style={styles.label}>Nhập mã cổ phiếu</label>
            <div style={styles.inputWrapper}>
              <Search size={18} color="#64748b" style={styles.inputIcon} />
              <input
                type="text"
                placeholder="VD: AAPL, TSLA, BTC-USD, FPT.VN..."
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                className="form-input"
                style={styles.paddedInput}
                disabled={loading}
              />
            </div>
          </div>

          <div style={{ ...styles.formGroup, flex: 1 }}>
            <label style={styles.label}>Khoảng thời gian (Period)</label>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="form-input"
              style={styles.select}
              disabled={loading}
            >
              <option value="6mo">6 tháng</option>
              <option value="1y">1 năm</option>
              <option value="2y">2 năm</option>
              <option value="5y">5 năm</option>
            </select>
          </div>

          <div style={{ ...styles.formGroup, flex: 1 }}>
            <label style={styles.label}>Độ chia nến (Interval)</label>
            <select
              value={interval}
              onChange={(e) => setIntervalVal(e.target.value)}
              className="form-input"
              style={styles.select}
              disabled={loading}
            >
              <option value="1d">1 ngày (Daily)</option>
              <option value="1wk">1 tuần (Weekly)</option>
              <option value="1mo">1 tháng (Monthly)</option>
            </select>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={styles.searchBtn}
            disabled={loading}
          >
            {loading ? 'Đang phân tích...' : 'Phân Tích & Dự Báo'}
          </button>
        </div>
      </form>

      {errorMsg && (
        <div style={styles.alertError}>
          <ShieldAlert size={20} />
          <span>{errorMsg}</span>
        </div>
      )}

      {loading ? (
        <div style={styles.loadingSpinner}>
          <div style={styles.spinner}></div>
          <span style={{ marginTop: '16px', fontWeight: 600 }}>Đang chạy mô hình và phân tích kỹ thuật...</span>
        </div>
      ) : data ? (
        /* KHU VỰC KẾT QUẢ */
        <div style={styles.resultContainer}>
          
          {/* 1. Metric Cards */}
          <div style={styles.metricsGrid}>
            <MetricCard label="Giá Hiện Tại" value={`$${data.current_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}`} color="default" />
            <MetricCard label="RSI (14)" value={data.rsi.toFixed(1)} color={getRsiColor(data.rsi)} />
            <MetricCard label="Biến Động (20-day)" value={`${data.volatility.toFixed(2)}%`} color="yellow" />
            <MetricCard label="MACD" value={data.macd.toFixed(3)} color={data.macd > data.macd_signal ? 'green' : 'red'} />
          </div>

          {/* 2. Candlestick + Volume Chart */}
          <div className="glass-card" style={styles.chartCard}>
            <h3 style={styles.sectionTitle}>Biểu đồ kỹ thuật: {data.ticker}</h3>
            <div style={styles.plotlyWrapper}>
              <Plot
                data={[
                  {
                    x: data.dates,
                    open: data.opens,
                    high: data.highs,
                    low: data.lows,
                    close: data.closes,
                    type: 'candlestick',
                    name: 'OHLC',
                    increasing: { line: { color: '#10b981' } },
                    decreasing: { line: { color: '#ef4444' } },
                  },
                  {
                    x: data.dates,
                    y: data.ma20_line,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'MA20',
                    line: { color: '#f59e0b', width: 1.5 },
                  },
                  {
                    x: data.dates,
                    y: data.ma50_line,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'MA50',
                    line: { color: '#38bdf8', width: 1.5 },
                  },
                ]}
                layout={{
                  height: 400,
                  margin: { l: 30, r: 10, t: 10, b: 30 },
                  paper_bgcolor: 'rgba(0,0,0,0)',
                  plot_bgcolor: 'rgba(0,0,0,0)',
                  xaxis: {
                    showgrid: true,
                    gridcolor: 'rgba(255,255,255,0.05)',
                    rangeslider: { visible: false },
                    tickfont: { color: '#64748b' }
                  },
                  yaxis: {
                    showgrid: true,
                    gridcolor: 'rgba(255,255,255,0.05)',
                    tickfont: { color: '#64748b' }
                  },
                  showlegend: true,
                  legend: { x: 0, y: 1, bgcolor: 'rgba(0,0,0,0)' },
                  hovermode: 'x unified',
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>
          </div>

          {/* 3. RSI & MACD Charts */}
          <div style={styles.twoColumnGrid}>
            <div className="glass-card" style={styles.smallChartCard}>
              <Plot
                data={[
                  {
                    x: data.dates,
                    y: data.rsi_line,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'RSI(14)',
                    line: { color: '#8b5cf6', width: 2 },
                  }
                ]}
                layout={{
                  title: { text: 'RSI — Relative Strength Index (14)', font: { color: '#f1f5f9', size: 14 } },
                  height: 240,
                  margin: { l: 30, r: 10, t: 40, b: 30 },
                  paper_bgcolor: 'rgba(0,0,0,0)',
                  plot_bgcolor: 'rgba(0,0,0,0)',
                  yaxis: { range: [0, 100], gridcolor: 'rgba(255,255,255,0.05)', tickfont: { color: '#64748b' } },
                  xaxis: { gridcolor: 'rgba(255,255,255,0.05)', tickfont: { color: '#64748b' } },
                  shapes: [
                    { type: 'line', y0: 70, y1: 70, x0: data.dates[0], x1: data.dates[data.dates.length - 1], line: { color: '#ef4444', dash: 'dash', width: 1 } },
                    { type: 'line', y0: 30, y1: 30, x0: data.dates[0], x1: data.dates[data.dates.length - 1], line: { color: '#10b981', dash: 'dash', width: 1 } }
                  ]
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>

            <div className="glass-card" style={styles.smallChartCard}>
              <Plot
                data={[
                  {
                    x: data.dates,
                    y: data.macd_line,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'MACD',
                    line: { color: '#38bdf8', width: 2 },
                  },
                  {
                    x: data.dates,
                    y: data.macd_sig_line,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Signal',
                    line: { color: '#f59e0b', width: 1.5, dash: 'dash' },
                  },
                  {
                    x: data.dates,
                    y: data.hist_line,
                    type: 'bar',
                    name: 'Hist',
                    marker: { color: data.hist_line.map((v: number) => v >= 0 ? '#10b981' : '#ef4444') },
                    opacity: 0.5,
                  }
                ]}
                layout={{
                  title: { text: 'MACD — Convergence/Divergence', font: { color: '#f1f5f9', size: 14 } },
                  height: 240,
                  margin: { l: 30, r: 10, t: 40, b: 30 },
                  paper_bgcolor: 'rgba(0,0,0,0)',
                  plot_bgcolor: 'rgba(0,0,0,0)',
                  yaxis: { gridcolor: 'rgba(255,255,255,0.05)', tickfont: { color: '#64748b' } },
                  xaxis: { gridcolor: 'rgba(255,255,255,0.05)', tickfont: { color: '#64748b' } },
                  showlegend: false
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>
          </div>

          {/* 4. ML Model Performance Table */}
          <div className="glass-card" style={styles.tableCard}>
            <h3 style={styles.sectionTitle}>So Sánh Hiệu Năng Các Model ML</h3>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.thLeft}>Mô hình</th>
                  <th style={styles.th}>MAE</th>
                  <th style={styles.th}>RMSE</th>
                  <th style={styles.th}>R²</th>
                  <th style={styles.th}>MAPE (%)</th>
                </tr>
              </thead>
              <tbody>
                {data.model_results.map((res: any) => {
                  const isBest = res.Model === data.best_model_name;
                  return (
                    <tr key={res.Model} style={{
                      ...styles.tr,
                      ...(isBest ? styles.trBest : {}),
                    }}>
                      <td style={styles.tdName}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {isBest && <Award size={16} color="#10b981" />}
                          <span>{res.Model}</span>
                        </div>
                      </td>
                      <td style={styles.td}>{res.MAE.toFixed(4)}</td>
                      <td style={styles.td}>{res.RMSE.toFixed(4)}</td>
                      <td style={styles.td}>{res['R²'] !== null && res['R²'] !== undefined ? Number(res['R²']).toFixed(4) : '—'}</td>
                      <td style={styles.td}>{typeof res['MAPE (%)'] === 'number' ? `${res['MAPE (%)'].toFixed(2)}%` : res['MAPE (%)']}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p style={styles.caption}>
              Best model: <strong>{data.best_model_name}</strong> (Mô hình có RMSE thấp nhất được ưu tiên sử dụng).
            </p>
          </div>

          {/* 5. Actual vs Predicted Chart */}
          {data.actual_vs_predicted && (
            <div className="glass-card" style={styles.chartCard}>
              <Plot
                data={[
                  {
                    x: data.actual_vs_predicted.dates,
                    y: data.actual_vs_predicted.actuals,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Giá Thực Tế (Actual)',
                    line: { color: '#10b981', width: 2 },
                  },
                  {
                    x: data.actual_vs_predicted.dates,
                    y: data.actual_vs_predicted.predictions,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Giá Dự Báo (Predicted)',
                    line: { color: '#f59e0b', width: 2, dash: 'dot' },
                  }
                ]}
                layout={{
                  title: { text: `Kiểm thử kiểm chứng Actual vs Predicted — ${data.ticker} (Tập Test 20%)`, font: { color: '#f1f5f9', size: 15 } },
                  height: 300,
                  margin: { l: 40, r: 10, t: 40, b: 30 },
                  paper_bgcolor: 'rgba(0,0,0,0)',
                  plot_bgcolor: 'rgba(0,0,0,0)',
                  xaxis: { gridcolor: 'rgba(255,255,255,0.05)', tickfont: { color: '#64748b' } },
                  yaxis: { gridcolor: 'rgba(255,255,255,0.05)', tickfont: { color: '#64748b' } },
                  legend: { x: 0, y: 1, bgcolor: 'rgba(0,0,0,0)' }
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>
          )}

          {/* 6. AI Recommendation & Trend */}
          <div className="glass-card" style={styles.recoCard}>
            <div style={styles.recoLeft}>
              <div
                style={{
                  ...styles.signalBadge,
                  color: data.recommendation.color,
                  borderColor: data.recommendation.color,
                  backgroundColor: data.recommendation.bg,
                }}
              >
                {data.recommendation.reco}
              </div>
              <div style={styles.recoValues}>
                <p style={styles.recoLabel}>Xu Hướng Dự Báo:</p>
                <p style={{ ...styles.recoValue, color: data.expected_change_pct >= 0 ? '#10b981' : '#ef4444' }}>
                  {data.recommendation.trend}
                </p>
                <p style={styles.recoLabel}>Tỷ Suất Dự Kiến:</p>
                <p style={{ ...styles.recoValue, color: data.recommendation.color }}>
                  {data.expected_change_pct >= 0 ? '+' : ''}{data.expected_change_pct.toFixed(2)}%
                </p>
              </div>
            </div>

            <div style={styles.recoRight}>
              <h4 style={styles.recoHeadline}>Phân tích các tín hiệu chỉ báo kỹ thuật:</h4>
              <ul style={styles.recoList}>
                {data.recommendation.reasons.map((r: string, idx: number) => (
                  <li key={idx} style={styles.recoItem}>
                    • {r.replace(/\*\*/g, '')}
                  </li>
                ))}
              </ul>
              <div style={styles.recoExplanation}>
                <strong>Đánh giá chung:</strong> <em>{data.recommendation.explanation}</em>
              </div>
            </div>
          </div>

          <div style={styles.financialWarning}>
            ⚠️ <strong>Lưu ý quan trọng:</strong> Kết quả phân tích và dự đoán trên được tạo tự động bằng mô hình AI và học máy, chỉ phục vụ mục đích nghiên cứu khoa học. Đây hoàn toàn không phải là lời khuyên đầu tư tài chính. Thị trường chứng khoán luôn có rủi ro cao, vui lòng cân nhắc kỹ trước khi giao dịch.
          </div>

        </div>
      ) : (
        /* TRẠNG THÁI CHỜ */
        <div className="glass-card" style={styles.placeholderCard}>
          <h3>Chưa có dữ liệu phân tích</h3>
          <p>Vui lòng nhập ticker ở thanh tìm kiếm phía trên để hệ thống bắt đầu kéo dữ liệu lịch sử và huấn luyện mô hình học máy.</p>
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
  },
  subtitle: {
    fontSize: '14px',
    color: '#94a3b8',
    marginBottom: '24px',
  },
  searchForm: {
    background: 'rgba(30, 41, 59, 0.4)',
    border: '1px solid rgba(148, 163, 184, 0.12)',
    borderRadius: '16px',
    padding: '20px 24px',
    marginBottom: '24px',
  },
  formRow: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'flex-end',
    gap: '16px',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    flex: '1 1 200px',
  },
  label: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#94a3b8',
    marginBottom: '8px',
  },
  inputWrapper: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
  },
  inputIcon: {
    position: 'absolute',
    left: '14px',
  },
  paddedInput: {
    paddingLeft: '44px',
    width: '100%',
  },
  select: {
    cursor: 'pointer',
    width: '100%',
  },
  searchBtn: {
    padding: '12px 24px',
    height: '46px',
    minWidth: '180px',
    flex: '1 1 180px',
  },
  alertError: {
    background: 'rgba(239, 68, 68, 0.15)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    color: '#fca5a5',
    borderRadius: '12px',
    padding: '16px 20px',
    marginBottom: '24px',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  loadingSpinner: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '360px',
    color: '#a5b4fc',
  },
  spinner: {
    width: '50px',
    height: '50px',
    border: '5px solid rgba(99, 102, 241, 0.15)',
    borderTop: '5px solid #6366f1',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  placeholderCard: {
    textAlign: 'center',
    padding: '80px 24px',
    color: '#64748b',
  },
  resultContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '20px',
  },
  chartCard: {
    padding: '24px',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#f1f5f9',
    marginBottom: '16px',
  },
  plotlyWrapper: {
    width: '100%',
  },
  twoColumnGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '20px',
  },
  smallChartCard: {
    padding: '16px',
  },
  tableCard: {
    padding: '24px',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    marginTop: '10px',
  },
  thLeft: {
    color: '#64748b',
    fontSize: '11px',
    fontWeight: 600,
    padding: '10px 16px',
    borderBottom: '1px solid rgba(148, 163, 184, 0.15)',
    textAlign: 'left',
    textTransform: 'uppercase',
  },
  th: {
    color: '#64748b',
    fontSize: '11px',
    fontWeight: 600,
    padding: '10px 16px',
    borderBottom: '1px solid rgba(148, 163, 184, 0.15)',
    textAlign: 'right',
    textTransform: 'uppercase',
  },
  tr: {
    borderBottom: '1px solid rgba(148, 163, 184, 0.05)',
  },
  trBest: {
    background: 'rgba(16, 185, 129, 0.12)',
  },
  tdName: {
    fontSize: '14px',
    fontWeight: 700,
    color: '#f1f5f9',
    padding: '14px 16px',
    textAlign: 'left',
  },
  td: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#cbd5e1',
    padding: '14px 16px',
    textAlign: 'right',
  },
  caption: {
    fontSize: '12px',
    color: '#64748b',
    marginTop: '12px',
  },
  recoCard: {
    display: 'flex',
    gap: '30px',
    padding: '30px',
    background: 'rgba(30, 41, 59, 0.6)',
  },
  recoLeft: {
    flex: 2,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '20px',
    borderRight: '1px solid rgba(148, 163, 184, 0.12)',
    paddingRight: '30px',
  },
  signalBadge: {
    fontSize: '32px',
    fontWeight: 900,
    border: '2px solid',
    borderRadius: '16px',
    padding: '20px 40px',
    textAlign: 'center',
    letterSpacing: '2px',
    boxShadow: '0 4px 14px rgba(0,0,0,0.2)',
  },
  recoValues: {
    width: '100%',
    textAlign: 'center',
  },
  recoLabel: {
    fontSize: '12px',
    color: '#64748b',
    textTransform: 'uppercase',
    marginTop: '10px',
  },
  recoValue: {
    fontSize: '18px',
    fontWeight: 700,
  },
  recoRight: {
    flex: 3,
  },
  recoHeadline: {
    fontSize: '16px',
    fontWeight: 700,
    color: '#f1f5f9',
    marginBottom: '12px',
  },
  recoList: {
    listStyleType: 'none',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  recoItem: {
    fontSize: '14px',
    color: '#cbd5e1',
    lineHeight: '1.6',
  },
  recoExplanation: {
    background: 'rgba(148, 163, 184, 0.06)',
    borderRadius: '10px',
    padding: '16px',
    marginTop: '18px',
    borderLeft: '4px solid #38bdf8',
    fontSize: '13px',
    color: '#94a3b8',
    lineHeight: '1.8',
  },
  financialWarning: {
    background: 'rgba(245, 158, 11, 0.08)',
    border: '1px solid rgba(245, 158, 11, 0.25)',
    color: '#fde047',
    borderRadius: '10px',
    padding: '16px 20px',
    fontSize: '13px',
    lineHeight: '1.6',
  },
};

export default AiAnalysis;
