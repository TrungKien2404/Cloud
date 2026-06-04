import React from 'react';
import { TrendingUp, BarChart3, ArrowLeftRight, LogOut, User, RefreshCw, MessageSquare, PieChart, ChevronLeft, ChevronRight } from 'lucide-react';
import api from '../api';

interface SidebarProps {
  currentView: string;
  onViewChange: (view: string) => void;
  username: string;
  onLogout: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ currentView, onViewChange, username, onLogout, isCollapsed, onToggleCollapse }) => {
  const [updating, setUpdating] = React.useState(false);
  const [updateMsg, setUpdateMsg] = React.useState('');

  const menuItems = [
    { id: 'overview', name: 'Tổng quan thị trường', icon: BarChart3 },
    { id: 'analysis', name: 'Phân Tích & AI Dự Báo', icon: TrendingUp },
    { id: 'compare', name: 'Thị Trường & So Sánh', icon: ArrowLeftRight },
    { id: 'chat', name: 'Stock AI Assistant', icon: MessageSquare },
    { id: 'portfolio', name: 'Phân Bổ Danh Mục', icon: PieChart },
  ];

  const handleSystemUpdate = async () => {
    setUpdating(true);
    setUpdateMsg('Đang gửi lệnh cập nhật...');
    try {
      const res = await api.post('/api/update-data');
      if (res.status === 200 || res.status === 201 || res.status === 202) {
        setUpdateMsg('Đã kích hoạt cập nhật. Hoàn tất sau ~60 giây.');
      }
    } catch (err: any) {
      setUpdateMsg(`Lỗi: ${err.response?.data?.detail || err.message}`);
    } finally {
      setTimeout(() => {
        setUpdating(false);
        setUpdateMsg('');
      }, 5000);
    }
  };

  return (
    <aside style={{
      ...styles.sidebar,
      width: isCollapsed ? '80px' : '280px',
      padding: isCollapsed ? '24px 10px' : '24px',
      transition: 'all 0.3s ease',
    }}>
      <div style={{
        ...styles.header,
        justifyContent: isCollapsed ? 'center' : 'space-between',
        flexDirection: isCollapsed ? 'column' : 'row',
        gap: '12px',
        alignItems: 'center',
      }}>
        {!isCollapsed && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <TrendingUp size={28} color="#6366f1" />
            <h2 style={styles.title}>Stock AI</h2>
          </div>
        )}
        {isCollapsed && <TrendingUp size={28} color="#6366f1" style={{ marginBottom: '4px' }} />}
        
        <button 
          onClick={onToggleCollapse} 
          style={styles.collapseToggleBtn}
          title={isCollapsed ? "Mở rộng" : "Thu gọn"}
        >
          {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      <div style={{
        ...styles.userBadge,
        justifyContent: isCollapsed ? 'center' : 'flex-start',
        padding: isCollapsed ? '12px 10px' : '12px 16px',
        transition: 'all 0.3s ease',
      }}>
        <User size={16} color="#a5b4fc" style={{ flexShrink: 0 }} />
        {!isCollapsed && (
          <div style={styles.userInfo}>
            <span style={styles.userLabel}>đăng nhập với</span>
            <span style={styles.userName}>{username}</span>
          </div>
        )}
      </div>

      <nav style={styles.nav}>
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onViewChange(item.id)}
              style={{
                ...styles.navBtn,
                ...(isActive ? styles.navBtnActive : {}),
                justifyContent: isCollapsed ? 'center' : 'flex-start',
                padding: isCollapsed ? '12px' : '14px 20px',
                transition: 'all 0.2s ease',
              }}
              title={isCollapsed ? item.name : undefined}
            >
              <Icon size={20} color={isActive ? '#ffffff' : '#cbd5e1'} style={{ flexShrink: 0 }} />
              {!isCollapsed && <span>{item.name}</span>}
            </button>
          );
        })}
      </nav>

      <div style={styles.footer}>
        <button
          onClick={handleSystemUpdate}
          disabled={updating}
          style={{
            ...styles.updateBtn,
            justifyContent: isCollapsed ? 'center' : 'center',
            padding: isCollapsed ? '10px' : '10px 14px',
            transition: 'all 0.2s ease',
          }}
          title={isCollapsed ? "Cập nhật hệ thống" : undefined}
        >
          <RefreshCw size={16} className={updating ? 'spin' : ''} style={{ flexShrink: 0 }} />
          {!isCollapsed && <span>{updating ? 'Đang cập nhật...' : 'Cập nhật hệ thống'}</span>}
        </button>
        {updateMsg && !isCollapsed && <p style={styles.updateMsg}>{updateMsg}</p>}

        <hr style={styles.divider} />

        <button 
          onClick={onLogout} 
          style={{
            ...styles.logoutBtn,
            justifyContent: isCollapsed ? 'center' : 'center',
            padding: isCollapsed ? '10px' : '12px',
            transition: 'all 0.2s ease',
          }}
          title={isCollapsed ? "Đăng xuất" : undefined}
        >
          <LogOut size={16} style={{ flexShrink: 0 }} />
          {!isCollapsed && <span>Đăng xuất</span>}
        </button>
      </div>
    </aside>
  );
};

const styles: Record<string, React.CSSProperties> = {
  sidebar: {
    width: '280px',
    height: '100vh',
    position: 'fixed',
    top: 0,
    left: 0,
    background: 'rgba(15, 23, 42, 0.95)',
    borderRight: '1px solid rgba(148, 163, 184, 0.12)',
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    zIndex: 100,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '24px',
  },
  collapseToggleBtn: {
    background: 'rgba(255, 255, 255, 0.04)',
    border: '1px solid rgba(148, 163, 184, 0.15)',
    borderRadius: '50%',
    color: '#cbd5e1',
    width: '32px',
    height: '32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  title: {
    fontSize: '20px',
    fontWeight: 800,
    color: '#f1f5f9',
    letterSpacing: '-0.5px',
  },
  userBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    background: 'rgba(99, 102, 241, 0.12)',
    border: '1px solid rgba(99, 102, 241, 0.25)',
    borderRadius: '12px',
    padding: '12px 16px',
    marginBottom: '30px',
  },
  userInfo: {
    display: 'flex',
    flexDirection: 'column',
  },
  userLabel: {
    fontSize: '11px',
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  userName: {
    fontSize: '15px',
    fontWeight: 700,
    color: '#a5b4fc',
  },
  nav: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    flexGrow: 1,
  },
  navBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    width: '100%',
    padding: '14px 20px',
    borderRadius: '12px',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    background: 'rgba(30, 41, 59, 0.6)',
    color: '#cbd5e1',
    fontSize: '16px',
    fontWeight: 600,
    cursor: 'pointer',
    textAlign: 'left',
    transition: 'all 0.2s ease',
  },
  navBtnActive: {
    background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.4), rgba(168, 85, 247, 0.3))',
    borderColor: 'rgba(99, 102, 241, 0.7)',
    color: '#ffffff',
    boxShadow: '0 4px 16px rgba(99, 102, 241, 0.2)',
  },
  footer: {
    marginTop: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  updateBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    width: '100%',
    padding: '10px 14px',
    borderRadius: '8px',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    background: 'rgba(30, 41, 59, 0.4)',
    color: '#94a3b8',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  updateMsg: {
    fontSize: '11px',
    color: '#38bdf8',
    textAlign: 'center',
    marginTop: '4px',
  },
  divider: {
    border: 0,
    borderTop: '1px solid rgba(148, 163, 184, 0.12)',
    margin: '8px 0',
  },
  logoutBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    width: '100%',
    padding: '12px',
    borderRadius: '10px',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    background: 'rgba(239, 68, 68, 0.12)',
    color: '#fca5a5',
    fontSize: '15px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
};

export default Sidebar;
