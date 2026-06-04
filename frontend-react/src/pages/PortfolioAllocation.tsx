import React, { useState } from 'react';
import Plot from '../components/Plot';
import { Briefcase, ShieldAlert, Award, Plus, Trash2, Activity, Info, BarChart3 } from 'lucide-react';
import api from '../api';
import MetricCard from '../components/MetricCard';

interface Allocation {
  ticker: string;
  name: string;
  weight: number;
  amount: number;
  expected_return: number;
  volatility: number;
  risk_level: string;
  explanation: string;
}

interface PortfolioResult {
  summary: {
    total_capital: number;
    expected_return: number;
    portfolio_volatility: number;
    risk_score: number;
    diversification_index: number;
    explanation: string;
  };
  allocations: Allocation[];
  correlation: {
    assets: string[];
    matrix: number[][];
  };
}

const PRESET_TICKERS = [
  { ticker: 'FPT.VN', name: 'FPT Corp', type: 'VN' },
  { ticker: 'HPG.VN', name: 'Hòa Phát', type: 'VN' },
  { ticker: 'TCB.VN', name: 'Techcombank', type: 'VN' },
  { ticker: 'VNM.VN', name: 'Vinamilk', type: 'VN' },
  { ticker: 'HDB.VN', name: 'HDBank', type: 'VN' },
  { ticker: 'AAPL', name: 'Apple Inc.', type: 'US' },
  { ticker: 'TSLA', name: 'Tesla Inc.', type: 'US' },
  { ticker: 'MSFT', name: 'Microsoft', type: 'US' },
  { ticker: 'GC=F', name: 'Vàng (Gold)', type: 'Hàng hóa' },
  { ticker: 'BTC-USD', name: 'Bitcoin', type: 'Crypto' },
];

const PortfolioAllocation: React.FC = () => {
  const [capital, setCapital] = useState<number>(100000000);
  const [riskProfile, setRiskProfile] = useState<'An toàn' | 'Cân bằng' | 'Tăng trưởng'>('Cân bằng');
  const [selectedTickers, setSelectedTickers] = useState<string[]>(['FPT.VN', 'HPG.VN', 'AAPL', 'GC=F']);
  const [customTicker, setCustomTicker] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [result, setResult] = useState<PortfolioResult | null>(null);

  const handleTickerToggle = (ticker: string) => {
    if (selectedTickers.includes(ticker)) {
      if (selectedTickers.length <= 2) {
        alert('Danh mục cần có tối thiểu 2 tài sản để đa dạng hóa.');
        return;
      }
      setSelectedTickers(selectedTickers.filter(t => t !== ticker));
    } else {
      setSelectedTickers([...selectedTickers, ticker]);
    }
  };

  const handleAddCustomTicker = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanTicker = customTicker.trim().toUpperCase();
    if (!cleanTicker) return;

    if (selectedTickers.includes(cleanTicker)) {
      alert('Mã này đã nằm trong danh mục lựa chọn.');
      return;
    }

    setSelectedTickers([...selectedTickers, cleanTicker]);
    setCustomTicker('');
  };

  const handleRemoveTicker = (ticker: string) => {
    if (selectedTickers.length <= 2) {
      alert('Danh mục cần có tối thiểu 2 tài sản để đa dạng hóa.');
      return;
    }
    setSelectedTickers(selectedTickers.filter(t => t !== ticker));
  };

  const handleOptimize = async () => {
    if (selectedTickers.length < 2) {
      setErrorMsg('Vui lòng chọn tối thiểu 2 mã tài sản.');
      return;
    }
    if (capital <= 0) {
      setErrorMsg('Vui lòng nhập nguồn vốn hợp lệ lớn hơn 0.');
      return;
    }

    setLoading(true);
    setErrorMsg('');
    try {
      const res = await api.post('/api/portfolio/allocate', {
        capital,
        risk_profile: riskProfile,
        tickers: selectedTickers,
      });
      setResult(res.data);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.response?.data?.detail || 'Lỗi khi tối ưu hóa danh mục. Vui lòng kiểm tra lại các mã tài sản.');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const getRiskScoreColor = (score: number) => {
    if (score <= 3.5) return '#10b981'; // Green
    if (score <= 6.5) return '#f59e0b'; // Amber
    return '#ef4444'; // Red
  };

  const formatCurrency = (val: number) => {
    return val.toLocaleString('vi-VN', { style: 'currency', currency: 'VND' });
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Tối Ưu Hóa & Phân Bổ Danh Mục</h2>
      <p style={styles.subtitle}>
        Sử dụng học máy & phân tích định lượng để phân bổ nguồn vốn của bạn vào các tài sản tối ưu theo khẩu vị rủi ro.
      </p>

      {errorMsg && (
        <div style={styles.alertError}>
          <ShieldAlert size={20} />
          <span>{errorMsg}</span>
        </div>
      )}

      <div style={styles.contentGrid}>
        {/* Left Column: Inputs */}
        <div className="glass-card" style={styles.inputColumn}>
          <h3 style={styles.sectionTitle}>1. Cấu hình Nguồn vốn & Khẩu vị</h3>
          
          {/* Capital Input */}
          <div style={styles.formGroup}>
            <label style={styles.label}>Tổng Nguồn Vốn Đầu Tư (VND)</label>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(Number(e.target.value))}
              placeholder="Ví dụ: 100000000"
              className="form-input"
              style={styles.numberInput}
              min={1000000}
            />
            <p style={styles.inputDesc}>Số tiền dự định phân bổ (ví dụ: {formatCurrency(capital)}).</p>
          </div>

          <hr style={styles.divider} />

          {/* Risk Profile Selector */}
          <div style={styles.formGroup}>
            <label style={styles.label}>Khẩu Vị Rủi Ro</label>
            <div style={styles.riskProfileGrid}>
              {[
                { id: 'An toàn', name: 'An toàn', desc: 'Ưu tiên bảo toàn vốn, biến động thấp' },
                { id: 'Cân bằng', name: 'Cân bằng', desc: 'Tối ưu hóa Sharpe (Lợi nhuận/Rủi ro)' },
                { id: 'Tăng trưởng', name: 'Tăng trưởng', desc: 'Tối đa hóa tăng trưởng, chấp nhận sụt giảm' }
              ].map((profile) => {
                const isActive = riskProfile === profile.id;
                return (
                  <div
                    key={profile.id}
                    onClick={() => setRiskProfile(profile.id as any)}
                    style={{
                      ...styles.riskProfileCard,
                      ...(isActive ? styles.activeRiskProfile : {})
                    }}
                  >
                    <span style={{
                      ...styles.profileName,
                      color: isActive ? '#ffffff' : '#cbd5e1'
                    }}>{profile.name}</span>
                    <span style={styles.profileDesc}>{profile.desc}</span>
                  </div>
                );
              })}
            </div>
          </div>

          <hr style={styles.divider} />

          {/* Tickers Selection */}
          <div style={styles.formGroup}>
            <label style={styles.label}>2. Chọn các tài sản muốn phân bổ</label>
            <div style={styles.presetGrid}>
              {PRESET_TICKERS.map((item) => {
                const isSelected = selectedTickers.includes(item.ticker);
                return (
                  <button
                    key={item.ticker}
                    onClick={() => handleTickerToggle(item.ticker)}
                    style={{
                      ...styles.presetBadge,
                      ...(isSelected ? styles.activePresetBadge : {})
                    }}
                  >
                    <span style={{ fontSize: '11px', color: isSelected ? '#a5b4fc' : '#64748b', marginRight: '4px' }}>
                      [{item.type}]
                    </span>
                    <span>{item.name} ({item.ticker})</span>
                  </button>
                );
              })}
            </div>

            {/* Custom Ticker Input */}
            <form onSubmit={handleAddCustomTicker} style={styles.customTickerForm}>
              <input
                type="text"
                placeholder="Thêm mã khác (VD: NVDA, ETH-USD...)"
                value={customTicker}
                onChange={(e) => setCustomTicker(e.target.value)}
                className="form-input"
                style={styles.customInput}
              />
              <button type="submit" style={styles.addBtn}>
                <Plus size={16} />
                <span>Thêm</span>
              </button>
            </form>

            {/* Selected List */}
            <div style={{ marginTop: '14px' }}>
              <span style={{ ...styles.label, fontSize: '12px' }}>
                Danh sách đã chọn ({selectedTickers.length}):
              </span>
              <div style={styles.selectedContainer}>
                {selectedTickers.map((t) => (
                  <div key={t} style={styles.selectedTag}>
                    <span>{t}</span>
                    <button
                      onClick={() => handleRemoveTicker(t)}
                      style={styles.removeTagBtn}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Action button */}
          <button
            onClick={handleOptimize}
            disabled={loading}
            style={{
              ...styles.optimizeBtn,
              ...(loading ? styles.optimizeBtnDisabled : {})
            }}
          >
            <Activity size={18} className={loading ? 'spin' : ''} />
            <span>{loading ? 'Đang chạy thuật toán tối ưu...' : '🤖 AI Tối Ưu Hóa Danh Mục'}</span>
          </button>
        </div>

        {/* Right Column: Output */}
        <div style={styles.resultColumn}>
          {loading ? (
            <div className="glass-card" style={styles.loadingCard}>
              <div style={styles.spinner}></div>
              <span style={{ marginTop: '16px', fontWeight: 600, color: '#a5b4fc' }}>
                Đang nạp dữ liệu Yahoo Finance & Chạy tối ưu hóa MPT...
              </span>
            </div>
          ) : result ? (
            /* Results Presentation */
            <div style={styles.resultsGrid}>
              
              {/* Summary Stats Cards */}
              <div style={styles.metricsGrid}>
                <MetricCard
                  label="Lợi nhuận kỳ vọng năm"
                  value={`${result.summary.expected_return.toFixed(2)}%`}
                  color="green"
                />
                <MetricCard
                  label="Biến động danh mục"
                  value={`${result.summary.portfolio_volatility.toFixed(2)}%`}
                  color="yellow"
                />
                <MetricCard
                  label="Chỉ số đa dạng hóa"
                  value={`${result.summary.diversification_index.toFixed(1)}%`}
                  color="blue"
                />
                <MetricCard
                  label="Điểm rủi ro danh mục"
                  value={`${result.summary.risk_score.toFixed(1)} / 10`}
                  color="default"
                />
              </div>

              {/* Pie/Donut Chart & AI Advice Card */}
              <div style={styles.chartAndAdviceGrid}>
                {/* Donut Chart */}
                <div className="glass-card" style={styles.chartCard}>
                  <h4 style={styles.cardTitle}>Biểu đồ tỷ lệ phân bổ</h4>
                  <div style={styles.chartWrapper}>
                    <Plot
                      data={[
                        {
                          values: result.allocations.map(a => a.weight),
                          labels: result.allocations.map(a => a.ticker),
                          type: 'pie',
                          hole: 0.45,
                          marker: {
                            colors: ['#6366f1', '#8b5cf6', '#10b981', '#38bdf8', '#f59e0b', '#ef4444', '#ec4899', '#14b8a6', '#64748b']
                          },
                          textinfo: 'label+percent',
                          textposition: 'inside',
                          automargin: true
                        }
                      ]}
                      layout={{
                        height: 280,
                        margin: { l: 10, r: 10, t: 10, b: 10 },
                        paper_bgcolor: 'rgba(0,0,0,0)',
                        plot_bgcolor: 'rgba(0,0,0,0)',
                        font: { color: '#cbd5e1', size: 11 },
                        showlegend: false
                      }}
                      config={{ displayModeBar: false, responsive: true }}
                      style={{ width: '100%' }}
                    />
                  </div>
                </div>

                {/* AI Advice */}
                <div className="glass-card" style={styles.adviceCard}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <Award size={20} color="#6366f1" />
                    <h4 style={{ ...styles.cardTitle, margin: 0 }}>Lời khuyên phân bổ từ AI</h4>
                  </div>
                  <p style={styles.adviceText}>{result.summary.explanation}</p>
                  
                  <div style={styles.riskBadgeContainer}>
                    <span style={styles.riskLabel}>Mức độ rủi ro:</span>
                    <span style={{
                      ...styles.riskBadge,
                      backgroundColor: getRiskScoreColor(result.summary.risk_score),
                    }}>
                      {result.summary.risk_score <= 3.5 ? 'AN TOÀN THẤP' : result.summary.risk_score <= 6.5 ? 'TRUNG BÌNH' : 'MẠO HIỂM CAO'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Table of Allocations */}
              <div className="glass-card" style={styles.tableCard}>
                <h4 style={styles.cardTitle}>Chi tiết phân chia vốn</h4>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.thLeft}>Mã tài sản</th>
                      <th style={styles.th}>Tỷ trọng (%)</th>
                      <th style={styles.th}>Số tiền phân bổ</th>
                      <th style={styles.th}>LN kỳ vọng</th>
                      <th style={styles.th}>Rủi ro</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.allocations.map((alloc) => (
                      <React.Fragment key={alloc.ticker}>
                        <tr style={styles.tr}>
                          <td style={styles.tdLeft}>
                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                              <span style={styles.assetTicker}>{alloc.ticker}</span>
                              <span style={styles.assetName}>{alloc.name}</span>
                            </div>
                          </td>
                          <td style={styles.td}>{alloc.weight.toFixed(1)}%</td>
                          <td style={{ ...styles.td, color: '#a5b4fc', fontWeight: 700 }}>
                            {formatCurrency(alloc.amount)}
                          </td>
                          <td style={styles.td}>{alloc.expected_return.toFixed(1)}% / năm</td>
                          <td style={styles.td}>
                            <span style={{
                              color: alloc.risk_level.includes('High') ? '#ef4444' : alloc.risk_level.includes('Medium') ? '#f59e0b' : '#10b981',
                              fontSize: '12px',
                              fontWeight: 700
                            }}>
                              {alloc.risk_level.split(' ')[0]}
                            </span>
                          </td>
                        </tr>
                        <tr>
                          <td colSpan={5} style={styles.explanationTd}>
                            <Info size={12} color="#64748b" style={{ flexShrink: 0, marginTop: '2px' }} />
                            <span>{alloc.explanation}</span>
                          </td>
                        </tr>
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Correlation Matrix */}
              <div className="glass-card" style={styles.tableCard}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                  <BarChart3 size={18} color="#8b5cf6" />
                  <h4 style={{ ...styles.cardTitle, margin: 0 }}>Ma trận hệ số tương quan chéo</h4>
                </div>
                <p style={styles.caption}>
                  Tương quan gần 1.0 nghĩa là tài sản biến động cùng chiều (tăng đa dạng hóa kém); gần 0 hoặc âm nghĩa là giảm thiểu rủi ro rất tốt.
                </p>
                <div style={{ overflowX: 'auto', marginTop: '12px' }}>
                  <table style={styles.corrTable}>
                    <thead>
                      <tr>
                        <th style={styles.corrThEmpty}></th>
                        {result.correlation.assets.map(asset => (
                          <th key={asset} style={styles.corrTh}>{asset}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.correlation.assets.map((asset1, idx1) => (
                        <tr key={asset1} style={styles.corrTr}>
                          <td style={styles.corrTdLabel}>{asset1}</td>
                          {result.correlation.matrix[idx1].map((val, idx2) => {
                            let bg = 'rgba(15, 23, 42, 0.4)';
                            let color = '#cbd5e1';
                            if (val > 0.6) { bg = 'rgba(239, 68, 68, 0.15)'; color = '#fca5a5'; }
                            else if (val < 0.1) { bg = 'rgba(16, 185, 129, 0.15)'; color = '#a7f3d0'; }
                            return (
                              <td key={idx2} style={{ ...styles.corrTd, backgroundColor: bg, color: color }}>
                                {val.toFixed(2)}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          ) : (
            /* Placeholder state */
            <div className="glass-card" style={styles.placeholderCard}>
              <Briefcase size={56} color="#475569" style={{ marginBottom: '16px' }} />
              <h3 style={styles.placeholderTitle}>Chưa cấu hình danh mục tối ưu</h3>
              <p style={styles.placeholderDesc}>
                Nhập số vốn đầu tư, lựa chọn khẩu vị rủi ro và các tài sản mong muốn ở bảng cấu hình bên trái. Bấm nút <b>AI Tối ưu hóa danh mục</b> để bắt đầu chạy thuật toán.
              </p>
            </div>
          )}
        </div>
      </div>
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
    margin: 0,
  },
  subtitle: {
    fontSize: '14px',
    color: '#94a3b8',
    margin: '6px 0 24px 0',
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
  contentGrid: {
    display: 'flex',
    gap: '24px',
    alignItems: 'flex-start',
  },
  inputColumn: {
    width: '360px',
    padding: '24px',
    flexShrink: 0,
  },
  resultColumn: {
    flexGrow: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  sectionTitle: {
    fontSize: '16px',
    fontWeight: 800,
    color: '#f1f5f9',
    marginBottom: '20px',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    marginBottom: '16px',
  },
  label: {
    fontSize: '13px',
    fontWeight: 700,
    color: '#94a3b8',
    marginBottom: '8px',
  },
  numberInput: {
    width: '100%',
  },
  inputDesc: {
    fontSize: '11px',
    color: '#64748b',
    marginTop: '6px',
    margin: '6px 0 0 0',
  },
  divider: {
    border: 0,
    borderTop: '1px solid rgba(148, 163, 184, 0.12)',
    margin: '18px 0',
  },
  riskProfileGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  riskProfileCard: {
    padding: '12px 16px',
    background: 'rgba(30, 41, 59, 0.4)',
    border: '1px solid rgba(148, 163, 184, 0.12)',
    borderRadius: '10px',
    cursor: 'pointer',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    transition: 'all 0.2s',
  },
  activeRiskProfile: {
    background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(168, 85, 247, 0.1))',
    borderColor: 'rgba(99, 102, 241, 0.5)',
    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.15)',
  },
  profileName: {
    fontSize: '14px',
    fontWeight: 700,
  },
  profileDesc: {
    fontSize: '11px',
    color: '#64748b',
  },
  presetGrid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
    marginBottom: '12px',
  },
  presetBadge: {
    padding: '6px 10px',
    background: 'rgba(30, 41, 59, 0.3)',
    border: '1px solid rgba(148, 163, 184, 0.1)',
    borderRadius: '6px',
    color: '#cbd5e1',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
    display: 'flex',
    alignItems: 'center',
  },
  activePresetBadge: {
    background: 'rgba(99, 102, 241, 0.18)',
    borderColor: 'rgba(99, 102, 241, 0.5)',
    color: '#ffffff',
  },
  customTickerForm: {
    display: 'flex',
    gap: '8px',
  },
  customInput: {
    flexGrow: 1,
    padding: '8px 12px',
    fontSize: '12px',
  },
  addBtn: {
    padding: '8px 14px',
    background: 'rgba(148, 163, 184, 0.1)',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    borderRadius: '8px',
    color: '#f1f5f9',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    transition: 'all 0.2s',
  },
  selectedContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
    marginTop: '8px',
  },
  selectedTag: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 8px 4px 10px',
    background: 'rgba(99, 102, 241, 0.1)',
    border: '1px solid rgba(99, 102, 241, 0.25)',
    borderRadius: '6px',
    color: '#a5b4fc',
    fontSize: '12px',
    fontWeight: 700,
  },
  removeTagBtn: {
    background: 'transparent',
    border: 'none',
    color: '#64748b',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    padding: 0,
    transition: 'color 0.2s',
  },
  optimizeBtn: {
    width: '100%',
    padding: '14px',
    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    border: 'none',
    borderRadius: '12px',
    color: '#ffffff',
    fontSize: '14px',
    fontWeight: 700,
    cursor: 'pointer',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '8px',
    boxShadow: '0 4px 16px rgba(99, 102, 241, 0.25)',
    transition: 'all 0.2s',
    marginTop: '20px',
  },
  optimizeBtnDisabled: {
    background: 'rgba(148, 163, 184, 0.1)',
    color: '#475569',
    cursor: 'not-allowed',
    boxShadow: 'none',
  },
  loadingCard: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '80px 24px',
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: '4px solid rgba(99, 102, 241, 0.15)',
    borderTop: '4px solid #6366f1',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  placeholderCard: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '120px 40px',
    textAlign: 'center',
  },
  placeholderTitle: {
    fontSize: '18px',
    fontWeight: 800,
    color: '#e2e8f0',
    margin: '0 0 10px 0',
  },
  placeholderDesc: {
    fontSize: '13px',
    color: '#64748b',
    maxWidth: '480px',
    margin: 0,
    lineHeight: '1.6',
  },
  resultsGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '16px',
  },
  chartAndAdviceGrid: {
    display: 'grid',
    gridTemplateColumns: '320px 1fr',
    gap: '20px',
  },
  chartCard: {
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
  },
  cardTitle: {
    fontSize: '15px',
    fontWeight: 800,
    color: '#f1f5f9',
    margin: '0 0 12px 0',
  },
  chartWrapper: {
    width: '100%',
    display: 'flex',
    justifyContent: 'center',
  },
  adviceCard: {
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    background: 'rgba(30, 41, 59, 0.3)',
  },
  adviceText: {
    fontSize: '13px',
    color: '#cbd5e1',
    lineHeight: '1.7',
    margin: 0,
  },
  riskBadgeContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginTop: '16px',
  },
  riskLabel: {
    fontSize: '12px',
    color: '#64748b',
  },
  riskBadge: {
    padding: '4px 10px',
    borderRadius: '6px',
    color: '#ffffff',
    fontSize: '11px',
    fontWeight: 800,
    letterSpacing: '0.5px',
  },
  tableCard: {
    padding: '24px',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    marginTop: '8px',
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
    borderBottom: '1px solid rgba(148, 163, 184, 0.08)',
  },
  tdLeft: {
    padding: '14px 16px',
    textAlign: 'left',
  },
  assetTicker: {
    fontSize: '14px',
    fontWeight: 700,
    color: '#f1f5f9',
  },
  assetName: {
    fontSize: '11px',
    color: '#64748b',
    marginTop: '2px',
  },
  td: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#cbd5e1',
    padding: '14px 16px',
    textAlign: 'right',
  },
  explanationTd: {
    padding: '10px 16px 14px 16px',
    fontSize: '12px',
    color: '#94a3b8',
    background: 'rgba(148, 163, 184, 0.02)',
    borderBottom: '1px solid rgba(148, 163, 184, 0.05)',
    display: 'flex',
    gap: '8px',
    alignItems: 'flex-start',
  },
  caption: {
    fontSize: '12px',
    color: '#64748b',
    margin: '4px 0 0 0',
  },
  corrTable: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  corrThEmpty: {
    width: '80px',
    borderBottom: '1px solid rgba(148, 163, 184, 0.15)',
  },
  corrTh: {
    color: '#64748b',
    fontSize: '10px',
    fontWeight: 700,
    padding: '10px',
    borderBottom: '1px solid rgba(148, 163, 184, 0.15)',
    textAlign: 'center',
  },
  corrTr: {
    borderBottom: '1px solid rgba(148, 163, 184, 0.05)',
  },
  corrTdLabel: {
    fontSize: '11px',
    fontWeight: 700,
    color: '#cbd5e1',
    padding: '10px',
    textAlign: 'left',
  },
  corrTd: {
    fontSize: '11px',
    fontWeight: 600,
    padding: '10px',
    textAlign: 'center',
    borderRadius: '4px',
  }
};

export default PortfolioAllocation;
