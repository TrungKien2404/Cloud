import React, { useState } from 'react';
import { TrendingUp, Lock, User, Mail, ShieldAlert } from 'lucide-react';
import api from '../api';

interface LoginRegisterProps {
  onLoginSuccess: (username: string, token: string) => void;
}

const LoginRegister: React.FC<LoginRegisterProps> = ({ onLoginSuccess }) => {
  const [isLoginTab, setIsLoginTab] = useState(true);
  
  // Login State
  const [loginUser, setLoginUser] = useState('');
  const [loginPass, setLoginPass] = useState('');
  
  // Register State
  const [regUser, setRegUser] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPass, setRegPass] = useState('');
  const [regConfirmPass, setRegConfirmPass] = useState('');

  // Status State
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginUser.trim() || !loginPass) {
      setErrorMsg('Vui lòng nhập tên đăng nhập và mật khẩu.');
      return;
    }

    setLoading(true);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      const res = await api.post('/api/auth/login', {
        username: loginUser,
        password: loginPass,
      });
      const { access_token, username } = res.data;
      onLoginSuccess(username, access_token);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Sai tên đăng nhập hoặc mật khẩu!');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regUser.trim() || !regEmail.trim() || !regPass || !regConfirmPass) {
      setErrorMsg('Vui lòng điền đầy đủ tất cả thông tin.');
      return;
    }
    if (regPass !== regConfirmPass) {
      setErrorMsg('Mật khẩu xác nhận không trùng khớp!');
      return;
    }

    setLoading(true);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      await api.post('/api/auth/register', {
        username: regUser,
        email: regEmail,
        password: regPass,
      });
      setSuccessMsg('Đăng ký tài khoản thành công! Hãy chuyển sang Đăng Nhập.');
      // Clear register form
      setRegUser('');
      setRegEmail('');
      setRegPass('');
      setRegConfirmPass('');
      // Switch tab after short delay
      setTimeout(() => {
        setIsLoginTab(true);
        setErrorMsg('');
        setSuccessMsg('');
      }, 3000);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Đăng ký thất bại. Tên đăng nhập có thể đã tồn tại.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.logoContainer}>
          <TrendingUp size={48} color="#6366f1" />
          <h1 style={styles.logoText}>Stock AI System</h1>
          <p style={styles.logoSub}>Nền tảng phân tích & dự báo cổ phiếu thông minh</p>
        </div>

        {/* Tab Header */}
        <div style={styles.tabHeader}>
          <button
            onClick={() => { setIsLoginTab(true); setErrorMsg(''); setSuccessMsg(''); }}
            style={{
              ...styles.tabBtn,
              ...(isLoginTab ? styles.tabBtnActive : {}),
            }}
          >
            🔑 Đăng Nhập
          </button>
          <button
            onClick={() => { setIsLoginTab(false); setErrorMsg(''); setSuccessMsg(''); }}
            style={{
              ...styles.tabBtn,
              ...(!isLoginTab ? styles.tabBtnActive : {}),
            }}
          >
            ✨ Đăng Ký
          </button>
        </div>

        {errorMsg && (
          <div style={styles.alertError}>
            <ShieldAlert size={18} />
            <span>{errorMsg}</span>
          </div>
        )}

        {successMsg && (
          <div style={styles.alertSuccess}>
            <span>{successMsg}</span>
          </div>
        )}

        {isLoginTab ? (
          /* LOGIN FORM */
          <form onSubmit={handleLogin} style={styles.form}>
            <div className="form-group">
              <label>Tên đăng nhập</label>
              <div style={styles.inputWrapper}>
                <User size={18} color="#64748b" style={styles.inputIcon} />
                <input
                  type="text"
                  placeholder="Nhập username..."
                  value={loginUser}
                  onChange={(e) => setLoginUser(e.target.value)}
                  className="form-input"
                  style={styles.paddedInput}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-group">
              <label>Mật khẩu</label>
              <div style={styles.inputWrapper}>
                <Lock size={18} color="#64748b" style={styles.inputIcon} />
                <input
                  type="password"
                  placeholder="Nhập mật khẩu..."
                  value={loginPass}
                  onChange={(e) => setLoginPass(e.target.value)}
                  className="form-input"
                  style={styles.paddedInput}
                  disabled={loading}
                />
              </div>
            </div>

            <button type="submit" className="btn btn-primary" style={styles.submitBtn} disabled={loading}>
              {loading ? 'Đang xác thực...' : 'Đăng Nhập'}
            </button>
          </form>
        ) : (
          /* REGISTER FORM */
          <form onSubmit={handleRegister} style={styles.form}>
            <div className="form-group">
              <label>Tên đăng nhập (tối thiểu 3 ký tự)</label>
              <div style={styles.inputWrapper}>
                <User size={18} color="#64748b" style={styles.inputIcon} />
                <input
                  type="text"
                  placeholder="Tên đăng nhập..."
                  value={regUser}
                  onChange={(e) => setRegUser(e.target.value)}
                  className="form-input"
                  style={styles.paddedInput}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-group">
              <label>Email</label>
              <div style={styles.inputWrapper}>
                <Mail size={18} color="#64748b" style={styles.inputIcon} />
                <input
                  type="email"
                  placeholder="example@email.com"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  className="form-input"
                  style={styles.paddedInput}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-group">
              <label>Mật khẩu (tối thiểu 6 ký tự)</label>
              <div style={styles.inputWrapper}>
                <Lock size={18} color="#64748b" style={styles.inputIcon} />
                <input
                  type="password"
                  placeholder="Mật khẩu..."
                  value={regPass}
                  onChange={(e) => setRegPass(e.target.value)}
                  className="form-input"
                  style={styles.paddedInput}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-group">
              <label>Xác nhận mật khẩu</label>
              <div style={styles.inputWrapper}>
                <Lock size={18} color="#64748b" style={styles.inputIcon} />
                <input
                  type="password"
                  placeholder="Xác nhận mật khẩu..."
                  value={regConfirmPass}
                  onChange={(e) => setRegConfirmPass(e.target.value)}
                  className="form-input"
                  style={styles.paddedInput}
                  disabled={loading}
                />
              </div>
            </div>

            <button type="submit" className="btn btn-primary" style={styles.submitBtn} disabled={loading}>
              {loading ? 'Đang tạo tài khoản...' : 'Tạo Tài Khoản'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    width: '100vw',
    background: 'linear-gradient(135deg, #090d16 0%, #11132c 50%, #090d16 100%)',
    padding: '20px',
  },
  card: {
    background: 'rgba(30, 41, 59, 0.88)',
    border: '1px solid rgba(148, 163, 184, 0.18)',
    borderRadius: '24px',
    padding: '40px',
    backdropFilter: 'blur(16px)',
    WebkitBackdropFilter: 'blur(16px)',
    boxShadow: '0 24px 64px rgba(0, 0, 0, 0.45)',
    maxWidth: '440px',
    width: '100%',
    textAlign: 'center',
  },
  logoContainer: {
    marginBottom: '28px',
  },
  logoText: {
    fontSize: '28px',
    fontWeight: 800,
    color: '#f1f5f9',
    marginTop: '12px',
    marginBottom: '4px',
    letterSpacing: '-0.5px',
  },
  logoSub: {
    fontSize: '13px',
    color: '#64748b',
  },
  tabHeader: {
    display: 'flex',
    background: 'rgba(15, 23, 42, 0.5)',
    borderRadius: '12px',
    padding: '4px',
    gap: '4px',
    marginBottom: '24px',
  },
  tabBtn: {
    flex: 1,
    padding: '10px 0',
    border: 0,
    background: 'transparent',
    borderRadius: '9px',
    fontSize: '15px',
    fontWeight: 600,
    color: '#94a3b8',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  tabBtnActive: {
    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    color: '#ffffff',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
  },
  inputWrapper: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
  },
  inputIcon: {
    position: 'absolute',
    left: '14px',
    pointerEvents: 'none',
  },
  paddedInput: {
    paddingLeft: '44px',
  },
  submitBtn: {
    marginTop: '12px',
    width: '100%',
  },
  alertError: {
    background: 'rgba(239, 68, 68, 0.15)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    color: '#fca5a5',
    borderRadius: '10px',
    padding: '12px 16px',
    marginBottom: '20px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    fontSize: '14px',
    textAlign: 'left',
  },
  alertSuccess: {
    background: 'rgba(16, 185, 129, 0.15)',
    border: '1px solid rgba(16, 185, 129, 0.3)',
    color: '#a7f3d0',
    borderRadius: '10px',
    padding: '12px 16px',
    marginBottom: '20px',
    fontSize: '14px',
    textAlign: 'left',
  },
};

export default LoginRegister;
