import React, { useState, useEffect } from 'react';
import Plot from '../components/Plot';
import { ShieldAlert, Plus } from 'lucide-react';
import api from '../api';

const MarketCompare: React.FC = () => {
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  
  // Watchlist & Train ticker
  const [newTicker, setNewTicker] = useState('');
  const [training, setTraining] = useState(false);
  const [trainStatus, setTrainStatus] = useState('');

  // Ticker comparison state
  const [selectedTickers, setSelectedTickers] = useState<string[]>([]);
  const [loadingCompare, setLoadingCompare] = useState(false);
  const [compareData, setCompareData] = useState<any[]>([]);

  const fetchMarketSummary = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await api.get('/api/market-summary');
      setSummary(res.data);
      
      // Mặc định chọn 5 mã đầu tiên từ watchlist để so sánh
      if (res.data.watchlist && res.data.watchlist.length > 0 && selectedTickers.length === 0) {
        const defaultSelected = res.data.watchlist.slice(0, 5).map((item: any) => item.ticker);
        setSelectedTickers(defaultSelected);
      }
    } catch (err: any) {
      console.error(err);
      setErrorMsg('Không thể kết nối đến Backend API. Trang Thị Trường & So Sánh cần Backend đang chạy để hiển thị dữ liệu live.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMarketSummary();
  }, []);

  // Fetch Normalized Return comparison chart data
  useEffect(() => {
    const fetchNormalizedData = async () => {
      if (selectedTickers.length === 0) {
        setCompareData([]);
        return;
      }
      setLoadingCompare(true);
      try {
        const responses = await Promise.all(
          selectedTickers.map(async (t) => {
            try {
              const res = await api.get(`/api/data/${t}?days=120`);
              if (res.data && res.data.length > 0) {
                const sorted = [...res.data].sort((a: any, b: any) => new Date(a.date).getTime() - new Date(b.date).getTime());
                const firstVal = sorted[0].close;
                return {
                  ticker: t,
                  dates: sorted.map((d: any) => d.date),
                  normalized: sorted.map((d: any) => (d.close / firstVal) * 100),
                };
              }
            } catch (e) {
              console.error(`Error loading comparison for ${t}:`, e);
            }
            return null;
          })
        );
        setCompareData(responses.filter(Boolean));
      } catch (err) {
        console.error('Lỗi khi tải so sánh:', err);
      } finally {
        setLoadingCompare(false);
      }
    };

    fetchNormalizedData();
  }, [selectedTickers]);

  const handleTrainTicker = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTicker.trim()) return;

    setTraining(true);
    setTrainStatus(`Đang thêm và huấn luyện mô hình cho mã ${newTicker.toUpperCase()}... Vui lòng đợi ~1-2 phút.`);
    try {
      const res = await api.post(`/api/train/${newTicker.toUpperCase().trim()}`);
      if (res.status === 200) {
        setTrainStatus(`Đã thêm thành công mã ${newTicker.toUpperCase()} và hoàn thành huấn luyện model!`);
        setNewTicker('');
        fetchMarketSummary(); // Refresh summary lists
      }
    } catch (err: any) {
      console.error(err);
      setTrainStatus(`Lỗi: ${err.response?.data?.detail || 'Quá trình huấn luyện thất bại. Vui lòng thử lại!'}`);
    } finally {
      setTraining(false);
      setTimeout(() => setTrainStatus(''), 8000);
    }
  };

  const toggleTickerSelection = (ticker: string) => {
    if (selectedTickers.includes(ticker)) {
      setSelectedTickers(selectedTickers.filter(t => t !== ticker));
    } else {
      setSelectedTickers([...selectedTickers, ticker]);
    }
  };

  const getSignalColor = (sig: string) => {
    if (sig.includes('MUA MẠNH')) return '#10b981';
    if (sig.includes('MUA/GIỮ')) return '#34d399';
    if (sig.includes('GIỮ/BÁN')) return '#fb923c';
    if (sig.includes('BÁN MẠNH')) return '#ef4444';
    return '#94a3b8';
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Thị Trường & So Sánh</h2>

      {errorMsg && (
        <div style={styles.alertError}>
          <ShieldAlert size={24} />
          <div>
            <p style={{ fontWeight: 700 }}>Kết nối thất bại</p>
            <p style={{ fontSize: '13px', marginTop: '4px' }}>{errorMsg}</p>
            <p style={{ fontSize: '12px', marginTop: '6px', color: '#cbd5e1' }}>
              Hãy khởi chạy terminal backend: <code>uvicorn api.api_service:app --reload</code>
            </p>
          </div>
        </div>
      )}

      {loading ? (
        <div style={styles.loadingSpinner}>Đang tải dữ liệu live thị trường...</div>
      ) : summary ? (
        <div style={styles.contentGrid}>
          
          {/* 1. Top Tăng & Giảm */}
          <div style={styles.topCardsGrid}>
            <div className="glass-card" style={styles.card}>
              <h3 style={{ ...styles.cardTitle, color: '#10b981' }}>📈 Top Tăng Giá</h3>
              <table style={styles.miniTable}>
                <thead>
                  <tr>
                    <th style={styles.miniThLeft}>Ticker</th>
                    <th style={styles.miniTh}>Giá</th>
                    <th style={styles.miniTh}>Biến Động</th>
                    <th style={styles.miniTh}>AI Tín Hiệu</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.top_gainers?.map((item: any) => (
                    <tr key={item.ticker} style={styles.miniTr}>
                      <td style={styles.miniTdName}>{item.ticker}</td>
                      <td style={styles.miniTd}>${item.close.toFixed(2)}</td>
                      <td style={{ ...styles.miniTd, color: '#10b981', fontWeight: 700 }}>+{item.change_pct.toFixed(2)}%</td>
                      <td style={{ ...styles.miniTd, color: getSignalColor(item.signal), fontSize: '11px', fontWeight: 700 }}>{item.signal}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="glass-card" style={styles.card}>
              <h3 style={{ ...styles.cardTitle, color: '#ef4444' }}>📉 Top Giảm Giá</h3>
              <table style={styles.miniTable}>
                <thead>
                  <tr>
                    <th style={styles.miniThLeft}>Ticker</th>
                    <th style={styles.miniTh}>Giá</th>
                    <th style={styles.miniTh}>Biến Động</th>
                    <th style={styles.miniTh}>AI Tín Hiệu</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.top_losers?.map((item: any) => (
                    <tr key={item.ticker} style={styles.miniTr}>
                      <td style={styles.miniTdName}>{item.ticker}</td>
                      <td style={styles.miniTd}>${item.close.toFixed(2)}</td>
                      <td style={{ ...styles.miniTd, color: '#ef4444', fontWeight: 700 }}>{item.change_pct.toFixed(2)}%</td>
                      <td style={{ ...styles.miniTd, color: getSignalColor(item.signal), fontSize: '11px', fontWeight: 700 }}>{item.signal}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 2. Watchlist & Add Ticker Form */}
          <div className="glass-card" style={styles.card}>
            <div style={styles.watchlistHeader}>
              <h3 style={styles.cardTitle}>👤 Watchlist — Danh sách theo dõi & AI Signal</h3>
              
              {/* Form thêm & huấn luyện model */}
              <form onSubmit={handleTrainTicker} style={styles.addForm}>
                <input
                  type="text"
                  placeholder="Nhập Ticker mới (VD: NVDA, VHM.VN)"
                  value={newTicker}
                  onChange={(e) => setNewTicker(e.target.value)}
                  className="form-input"
                  style={styles.addInput}
                  disabled={training}
                />
                <button type="submit" className="btn btn-primary" style={styles.addBtn} disabled={training}>
                  <Plus size={16} />
                  <span>{training ? 'Đang Train...' : 'Thêm & Train Model'}</span>
                </button>
              </form>
            </div>

            {trainStatus && <div style={styles.trainStatusMsg}>{trainStatus}</div>}

            <div style={styles.tableContainer}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.thLeft}>Mã CP</th>
                    <th style={styles.thLeft}>Thị Trường</th>
                    <th style={styles.th}>Giá Đóng Cửa</th>
                    <th style={styles.th}>Thay Đổi Ngày</th>
                    <th style={styles.th}>Tín Hiệu AI</th>
                    <th style={{ ...styles.th, textAlign: 'center' }}>So Sánh</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.watchlist?.map((item: any) => {
                    const isSelected = selectedTickers.includes(item.ticker);
                    return (
                      <tr key={item.ticker} style={styles.tr}>
                        <td style={styles.tdName}>{item.ticker}</td>
                        <td style={styles.tdLeft}>{item.market}</td>
                        <td style={styles.td}>${item.close.toFixed(2)}</td>
                        <td style={{ ...styles.td, color: item.change_pct >= 0 ? '#10b981' : '#ef4444', fontWeight: 700 }}>
                          {item.change_pct >= 0 ? '+' : ''}{item.change_pct.toFixed(2)}%
                        </td>
                        <td style={{ ...styles.td, color: getSignalColor(item.signal), fontWeight: 700 }}>{item.signal}</td>
                        <td style={{ ...styles.td, textAlign: 'center' }}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleTickerSelection(item.ticker)}
                            style={styles.checkbox}
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* 3. Normalized Price Return Comparison (Base=100) */}
          <div className="glass-card" style={styles.card}>
            <h3 style={styles.cardTitle}>📈 So Sánh Normalized Return (Base = 100)</h3>
            <p style={styles.cardCaption}>
              Giá trị đóng cửa được chuẩn hóa về mức 100 tại phiên đầu tiên cách đây 120 phiên để so sánh chính xác tốc độ tăng trưởng.
            </p>

            {loadingCompare ? (
              <div style={styles.loadingSpinner}>Đang chuẩn hóa dữ liệu...</div>
            ) : compareData.length > 0 ? (
              <Plot
                data={compareData.map((d) => ({
                  x: d.dates,
                  y: d.normalized,
                  type: 'scatter',
                  mode: 'lines',
                  name: d.ticker,
                  line: { width: 2 },
                  hovertemplate: `<b>${d.ticker}</b>: %{y:.1f}%<extra></extra>`,
                }))}
                layout={{
                  height: 380,
                  margin: { l: 40, r: 10, t: 10, b: 30 },
                  paper_bgcolor: 'rgba(0,0,0,0)',
                  plot_bgcolor: 'rgba(0,0,0,0)',
                  xaxis: { gridcolor: 'rgba(255,255,255,0.05)', tickfont: { color: '#64748b' } },
                  yaxis: { gridcolor: 'rgba(255,255,255,0.05)', tickfont: { color: '#64748b' }, title: 'Normalized Return (%)' },
                  legend: { x: 0, y: 1, bgcolor: 'rgba(0,0,0,0)' },
                  hovermode: 'x unified',
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            ) : (
              <div style={styles.placeholderText}>Vui lòng chọn tối thiểu 1 mã ở bảng Watchlist trên để so sánh biểu đồ.</div>
            )}
          </div>

          {/* 4. Correlation Heatmap */}
          {summary.correlation && (
            <div style={styles.twoColumnHeatmap}>
              <div className="glass-card" style={{ ...styles.card, flex: '2 1 280px' }}>
                <h3 style={styles.cardTitle}>📊 Ma Trận Tương Quan Sinh Lời (120 phiên)</h3>
                <Plot
                  data={[
                    {
                      z: summary.correlation.z,
                      x: summary.correlation.x,
                      y: summary.correlation.y,
                      type: 'heatmap',
                      colorscale: 'RdBu',
                      zmin: -1,
                      zmax: 1,
                      colorbar: { tickfont: { color: '#64748b' } },
                    }
                  ]}
                  layout={{
                    height: 360,
                    margin: { l: 50, r: 10, t: 10, b: 50 },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    xaxis: { tickfont: { color: '#64748b' } },
                    yaxis: { tickfont: { color: '#64748b' } },
                  }}
                  config={{ displayModeBar: false, responsive: true }}
                  style={{ width: '100%' }}
                />
              </div>

              <div className="glass-card" style={{ ...styles.card, flex: '1 1 280px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                <h4 style={styles.heatmapExplainTitle}>Giải thích Chỉ Số Tương Quan (Correlation):</h4>
                <ul style={styles.heatmapList}>
                  <li>
                    <strong style={{ color: '#10b981' }}>+1.0 (Tương quan dương hoàn toàn):</strong> Hai mã luôn cùng tăng / giảm đồng pha với nhau. Không giúp phân tán rủi ro.
                  </li>
                  <li>
                    <strong style={{ color: '#94a3b8' }}>0.0 (Không tương quan):</strong> Hai mã biến động độc lập hoàn toàn, hỗ trợ đa dạng hóa danh mục tốt.
                  </li>
                  <li>
                    <strong style={{ color: '#ef4444' }}>-1.0 (Tương quan âm hoàn toàn):</strong> Hai mã biến động ngược pha nhau 100%. Rất thích hợp để hedging (phòng vệ giá).
                  </li>
                </ul>
              </div>
            </div>
          )}

        </div>
      ) : (
        <div style={styles.placeholderText}>Chưa tải được dữ liệu Live thị trường.</div>
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
    marginBottom: '24px',
  },
  alertError: {
    background: 'rgba(239, 68, 68, 0.15)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    color: '#fca5a5',
    borderRadius: '12px',
    padding: '20px',
    marginBottom: '24px',
    display: 'flex',
    gap: '16px',
    alignItems: 'flex-start',
  },
  loadingSpinner: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '240px',
    color: '#a5b4fc',
    fontWeight: 600,
  },
  contentGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  topCardsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '20px',
  },
  card: {
    padding: '24px',
  },
  cardTitle: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#f1f5f9',
    marginBottom: '14px',
  },
  cardCaption: {
    fontSize: '12px',
    color: '#64748b',
    marginTop: '-8px',
    marginBottom: '16px',
  },
  miniTable: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  miniThLeft: {
    fontSize: '11px',
    color: '#64748b',
    fontWeight: 600,
    paddingBottom: '8px',
    borderBottom: '1px solid rgba(148, 163, 184, 0.15)',
    textAlign: 'left',
  },
  miniTh: {
    fontSize: '11px',
    color: '#64748b',
    fontWeight: 600,
    paddingBottom: '8px',
    borderBottom: '1px solid rgba(148, 163, 184, 0.15)',
    textAlign: 'right',
  },
  miniTr: {
    borderBottom: '1px solid rgba(148, 163, 184, 0.05)',
  },
  miniTdName: {
    fontSize: '13px',
    fontWeight: 700,
    color: '#f1f5f9',
    padding: '10px 0',
    textAlign: 'left',
  },
  miniTd: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#cbd5e1',
    padding: '10px 0',
    textAlign: 'right',
  },
  watchlistHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '16px',
    marginBottom: '16px',
  },
  addForm: {
    display: 'flex',
    gap: '10px',
  },
  addInput: {
    width: '240px',
    height: '38px',
    padding: '8px 12px',
    fontSize: '13px',
  },
  addBtn: {
    height: '38px',
    padding: '0 16px',
    fontSize: '13px',
    fontWeight: 600,
  },
  trainStatusMsg: {
    background: 'rgba(56, 189, 248, 0.12)',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    color: '#bae6fd',
    borderRadius: '8px',
    padding: '10px 14px',
    fontSize: '13px',
    marginBottom: '16px',
  },
  tableContainer: {
    overflowY: 'auto',
    overflowX: 'auto',
    maxHeight: '340px',
    width: '100%',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  thLeft: {
    color: '#64748b',
    fontSize: '11px',
    fontWeight: 600,
    padding: '10px 16px',
    borderBottom: '1px solid rgba(148, 163, 184, 0.15)',
    textAlign: 'left',
  },
  th: {
    color: '#64748b',
    fontSize: '11px',
    fontWeight: 600,
    padding: '10px 16px',
    borderBottom: '1px solid rgba(148, 163, 184, 0.15)',
    textAlign: 'right',
  },
  tr: {
    borderBottom: '1px solid rgba(148, 163, 184, 0.05)',
  },
  tdName: {
    fontSize: '14px',
    fontWeight: 700,
    color: '#f1f5f9',
    padding: '12px 16px',
    textAlign: 'left',
  },
  tdLeft: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#94a3b8',
    padding: '12px 16px',
    textAlign: 'left',
  },
  td: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#cbd5e1',
    padding: '12px 16px',
    textAlign: 'right',
  },
  checkbox: {
    width: '16px',
    height: '16px',
    cursor: 'pointer',
  },
  placeholderText: {
    textAlign: 'center',
    padding: '40px',
    color: '#64748b',
    fontSize: '14px',
  },
  twoColumnHeatmap: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '20px',
  },
  heatmapExplainTitle: {
    fontSize: '15px',
    fontWeight: 700,
    color: '#f1f5f9',
    marginBottom: '12px',
  },
  heatmapList: {
    listStyleType: 'none',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  heatmapListLi: {
    fontSize: '13px',
    color: '#cbd5e1',
    lineHeight: '1.6',
  },
};

export default MarketCompare;
