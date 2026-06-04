import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import LoginRegister from './pages/LoginRegister';
import Overview from './pages/Overview';
import AiAnalysis from './pages/AiAnalysis';
import MarketCompare from './pages/MarketCompare';
import ChatAssistant from './pages/ChatAssistant';
import PortfolioAllocation from './pages/PortfolioAllocation';

const App: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('');
  const [currentView, setCurrentView] = useState('overview');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

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
        marginLeft: isSidebarCollapsed ? '80px' : '280px',
        transition: 'margin-left 0.3s ease',
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
    marginLeft: '280px', // Đẩy lùi bằng đúng chiều rộng Sidebar
    flexGrow: 1,
    padding: '30px 40px',
    minHeight: '100vh',
    overflowY: 'auto',
  },
};

export default App;
