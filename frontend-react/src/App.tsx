import React, { useState, useEffect } from 'react';
import { TrendingUp, RefreshCw, LogOut } from 'lucide-react';
import Sidebar from './components/Sidebar';
import LoginRegister from './pages/LoginRegister';
import Overview from './pages/Overview';
import AiAnalysis from './pages/AiAnalysis';
import MarketCompare from './pages/MarketCompare';
import ChatAssistant from './pages/ChatAssistant';
import PortfolioAllocation from './pages/PortfolioAllocation';
import api from './api';

const App: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('');
  const [currentView, setCurrentView] = useState('overview');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const [updating, setUpdating] = useState(false);

  // Listen to screen size changes
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Kiểm tra token lưu trữ khi khởi động
  useEffect(() => {
    const token = localStorage.getItem('stock_ai_token');
    const savedUser = localStorage.getItem('stock_ai_username');
    if (token && savedUser) {
      setIsAuthenticated(true);
      setUsername(savedUser);
    }
  }, []);

  const handleLoginSuccess = (user: string, token: string) => {
    localStorage.setItem('stock_ai_token', token);
    localStorage.setItem('stock_ai_username', user);
    localStorage.removeItem('stock_ai_chat_messages');
    setUsername(user);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('stock_ai_token');
    localStorage.removeItem('stock_ai_username');
    localStorage.removeItem('stock_ai_chat_messages');
    setUsername('');
    setIsAuthenticated(false);
    setCurrentView('overview');
  };

  const handleSystemUpdate = async () => {
    setUpdating(true);
    try {
      await api.post('/api/update-data');
      alert('Đã gửi lệnh cập nhật hệ thống thành công! Quá trình xử lý chạy ngầm mất khoảng 60 giây.');
    } catch (err: any) {
      alert(`Lỗi cập nhật hệ thống: ${err.response?.data?.detail || err.message}`);
    } finally {
      setUpdating(false);
    }
  };

  const renderActiveView = () => {
    switch (currentView) {
      case 'overview':
        return <Overview />;
      case 'analysis':
        return <AiAnalysis />;
      case 'compare':
        return <MarketCompare />;
      case 'chat':
        return <ChatAssistant />;
      case 'portfolio':
        return <PortfolioAllocation />;
      default:
        return <Overview />;
    }
  };

  if (!isAuthenticated) {
    return <LoginRegister onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div style={styles.appLayout}>
      {/* Top Header for Mobile only */}
      {isMobile && (
        <header style={styles.mobileHeader}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingUp size={20} color="#6366f1" />
            <span style={{ fontWeight: 800, fontSize: '16px', color: '#f1f5f9' }}>Stock AI</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '12px', color: '#a5b4fc', fontWeight: 600 }}>{username}</span>
            <button
              onClick={handleSystemUpdate}
              disabled={updating}
              style={styles.mobileHeaderBtn}
              title="Cập nhật hệ thống"
            >
              <RefreshCw size={14} className={updating ? 'spin' : ''} color="#cbd5e1" />
            </button>
            <button
              onClick={handleLogout}
              style={{ ...styles.mobileHeaderBtn, borderColor: 'rgba(239, 68, 68, 0.25)', background: 'rgba(239, 68, 68, 0.1)' }}
              title="Đăng xuất"
            >
              <LogOut size={14} color="#fca5a5" />
            </button>
          </div>
        </header>
      )}

      <Sidebar
        currentView={currentView}
        onViewChange={setCurrentView}
        username={username}
        onLogout={handleLogout}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      />

      <main style={{
        ...styles.mainContent,
        marginLeft: isMobile ? '0' : (isSidebarCollapsed ? '80px' : '280px'),
        paddingTop: isMobile ? '84px' : '30px', // Đẩy xuống tránh bị Mobile Header che khuất
        paddingBottom: isMobile ? '94px' : '30px', // Tránh bị che bởi Bottom Nav
        paddingLeft: isMobile ? '16px' : '40px',
        paddingRight: isMobile ? '16px' : '40px',
        transition: 'all 0.3s ease',
      }}>
        {renderActiveView()}
      </main>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  appLayout: {
    display: 'flex',
    minHeight: '100vh',
    width: '100vw',
    backgroundColor: '#0b0f19',
    position: 'relative',
  },
  mainContent: {
    flexGrow: 1,
    minHeight: '100vh',
    overflowY: 'auto',
  },
  mobileHeader: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    height: '56px',
    background: 'rgba(15, 23, 42, 0.95)',
    borderBottom: '1px solid rgba(148, 163, 184, 0.12)',
    backdropFilter: 'blur(16px)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0 16px',
    zIndex: 1000,
  },
  mobileHeaderBtn: {
    background: 'rgba(255, 255, 255, 0.04)',
    border: '1px solid rgba(148, 163, 184, 0.15)',
    borderRadius: '8px',
    padding: '6px 10px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
  },
};

export default App;
