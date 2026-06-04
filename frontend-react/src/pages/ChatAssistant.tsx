import React, { useState, useEffect, useRef } from 'react';
import { Send, AlertTriangle, Sparkles, Zap, Settings, RefreshCw, Plus, Trash2, MessageSquare, Menu, ArrowLeft } from 'lucide-react';
import api from '../api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const ChatAssistant: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Đang tải lịch sử trò chuyện...'
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [analysisMode, setAnalysisMode] = useState<'Nhanh' | 'Thông minh'>(() => {
    const saved = localStorage.getItem('stock_ai_chat_analysis_mode');
    return (saved as 'Nhanh' | 'Thông minh') || 'Nhanh';
  });
  
  // Threads State
  const [threads, setThreads] = useState<{ id: string; title: string; created_at?: string }[]>([]);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);

  // Mobile and Sidebar states
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const [showSidebar, setShowSidebar] = useState(window.innerWidth > 768);

  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth <= 768;
      setIsMobile(mobile);
      setShowSidebar(!mobile);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Advanced config states
  const [showConfig, setShowConfig] = useState(false);
  const [isOllamaReady, setIsOllamaReady] = useState(false);
  const [availableModels, setAvailableModels] = useState<string[]>(['qwen2.5:1.5b']);
  const [selectedModel, setSelectedModel] = useState<string>(() => {
    return localStorage.getItem('stock_ai_chat_selected_model') || 'qwen2.5:1.5b';
  });
  const [checkingStatus, setCheckingStatus] = useState(false);
  const [sending, setSending] = useState(false);
  
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of chat
  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchThreads = async (selectActiveId: string | null = null) => {
    try {
      const res = await api.get('/api/chat/threads');
      const fetchedThreads = res.data.threads;
      setThreads(fetchedThreads);
      
      if (selectActiveId) {
        setCurrentThreadId(selectActiveId);
        fetchThreadDetails(selectActiveId);
      } else if (fetchedThreads.length > 0) {
        setCurrentThreadId(fetchedThreads[0].id);
        fetchThreadDetails(fetchedThreads[0].id);
      } else {
        handleCreateThread();
      }
    } catch (err) {
      console.error('Lỗi khi tải danh sách cuộc trò chuyện:', err);
    }
  };

  const fetchThreadDetails = async (threadId: string) => {
    try {
      const res = await api.get(`/api/chat/threads/${threadId}`);
      setMessages(res.data.messages);
    } catch (err) {
      console.error('Lỗi khi tải chi tiết cuộc trò chuyện:', err);
    }
  };

  const handleCreateThread = async () => {
    try {
      setSending(true);
      const res = await api.post('/api/chat/threads');
      const newThread = res.data;
      setThreads(prev => [newThread, ...prev]);
      setCurrentThreadId(newThread.id);
      setMessages(newThread.messages);
      if (isMobile) {
        setShowSidebar(false);
      }
    } catch (err) {
      console.error('Lỗi khi tạo cuộc trò chuyện mới:', err);
    } finally {
      setSending(false);
    }
  };

  const handleDeleteThread = async (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation();
    if (window.confirm('Bạn có chắc chắn muốn xóa cuộc trò chuyện này không?')) {
      try {
        await api.delete(`/api/chat/threads/${threadId}`);
        const updatedThreads = threads.filter(t => t.id !== threadId);
        setThreads(updatedThreads);
        
        if (currentThreadId === threadId) {
          if (updatedThreads.length > 0) {
            setCurrentThreadId(updatedThreads[0].id);
            fetchThreadDetails(updatedThreads[0].id);
          } else {
            handleCreateThread();
          }
        }
      } catch (err) {
        console.error('Lỗi khi xóa cuộc trò chuyện:', err);
        alert('Không thể xóa cuộc trò chuyện. Vui lòng thử lại.');
      }
    }
  };

  const handleSelectThread = (threadId: string) => {
    if (threadId === currentThreadId || sending) return;
    setCurrentThreadId(threadId);
    fetchThreadDetails(threadId);
    if (isMobile) {
      setShowSidebar(false);
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, sending]);

  useEffect(() => {
    localStorage.setItem('stock_ai_chat_analysis_mode', analysisMode);
  }, [analysisMode]);

  useEffect(() => {
    localStorage.setItem('stock_ai_chat_selected_model', selectedModel);
  }, [selectedModel]);

  // Check Ollama status on load and periodically
  const checkStatus = async () => {
    setCheckingStatus(true);
    try {
      const res = await api.get('/api/chat/status');
      setIsOllamaReady(res.data.alive);
      if (res.data.alive) {
        const modelsRes = await api.get('/api/chat/models');
        const models = modelsRes.data.models;
        setAvailableModels(models);
        if (models.length > 0 && !models.includes(selectedModel)) {
          setSelectedModel(models.includes('qwen2.5:1.5b') ? 'qwen2.5:1.5b' : models[0]);
        }
      }
    } catch (err) {
      setIsOllamaReady(false);
    } finally {
      setCheckingStatus(false);
    }
  };

  useEffect(() => {
    fetchThreads();
    checkStatus();
    const interval = setInterval(checkStatus, 15000); // Check status every 15s
    return () => clearInterval(interval);
  }, []);

  const handleSendMessage = async (text: string) => {
    if (!text.trim() || sending) return;
    
    const newMsg: Message = { role: 'user', content: text };
    setMessages(prev => [...prev, newMsg]);
    setInputText('');
    setSending(true);

    if (analysisMode === 'Thông minh' && !isOllamaReady) {
      setTimeout(() => {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `<div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 14px 18px; color: #fca5a5; font-size: 14px;">
            <b>Chế độ phân tích thông minh chưa sẵn sàng.</b><br />
            Vui lòng bật trợ lý AI cục bộ (Ollama) hoặc mở rộng bảng <b>Cài đặt nâng cao</b> ở góc trên bên phải để xem hướng dẫn khởi động.
          </div>`
        }]);
        setSending(false);
      }, 500);
      return;
    }

    try {
      const res = await api.post('/api/chat', {
        message: text,
        mode: analysisMode,
        model: selectedModel,
        thread_id: currentThreadId
      });

      const { response, thread_id, thread_title } = res.data;

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response
      }]);

      if (thread_id) {
        setCurrentThreadId(thread_id);
        
        setThreads(prev => {
          const index = prev.findIndex(t => t.id === thread_id);
          if (index !== -1) {
            const updated = [...prev];
            if (updated[index].title !== thread_title) {
              updated[index] = { ...updated[index], title: thread_title };
            }
            return updated;
          } else {
            return [{ id: thread_id, title: thread_title, created_at: new Date().toISOString() }, ...prev];
          }
        });
      }
    } catch (err: any) {
      console.error(err);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `❌ Lỗi: Không thể kết nối tới server backend tại port 8000. Vui lòng đảm bảo backend FastAPI đang chạy.`
      }]);
    } finally {
      setSending(false);
    }
  };

  const handleClearChat = async () => {
    if (!currentThreadId) return;
    if (window.confirm('Bạn có chắc chắn muốn dọn dẹp toàn bộ tin nhắn trong cuộc trò chuyện này không?')) {
      try {
        setSending(true);
        const res = await api.put(`/api/chat/threads/${currentThreadId}/clear`);
        setMessages(res.data.thread.messages);
        setThreads(prev => prev.map(t => t.id === currentThreadId ? { ...t, title: res.data.thread.title } : t));
      } catch (err) {
        console.error('Lỗi khi dọn dẹp cuộc trò chuyện:', err);
        alert('Không thể dọn dẹp cuộc trò chuyện. Vui lòng thử lại.');
      } finally {
        setSending(false);
      }
    }
  };

  const handleDownloadPDF = (htmlContent: string) => {
    const tickerMatch = htmlContent.match(/Phân tích nhanh\s+([A-Za-z0-9.-]+)/i);
    const tickerName = tickerMatch ? tickerMatch[1].trim() : 'Stock';
    const dateStr = new Date().toISOString().slice(0, 10);

    const runExport = () => {
      const element = document.createElement('div');
      element.innerHTML = htmlContent;
      
      element.style.padding = '40px';
      element.style.background = '#0f172a';
      element.style.color = '#cbd5e1';
      element.style.width = '700px';
      element.style.boxSizing = 'border-box';
      
      const headings = element.querySelectorAll('h3, h4');
      headings.forEach(h => {
        (h as HTMLElement).style.color = '#ffffff';
      });
      
      const tables = element.querySelectorAll('table');
      tables.forEach(t => {
        (t as HTMLElement).style.width = '100%';
        (t as HTMLElement).style.borderCollapse = 'collapse';
      });
      
      const opt = {
        margin:       [10, 10, 10, 10],
        filename:     `Bao_cao_phan_tich_${tickerName}_${dateStr}.pdf`,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true, backgroundColor: '#0f172a' },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
      };
      
      // @ts-ignore
      html2pdf().from(element).set(opt).save();
    };

    // @ts-ignore
    if (typeof html2pdf !== 'undefined') {
      runExport();
    } else {
      const script = document.createElement('script');
      script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js';
      script.onload = () => {
        runExport();
      };
      document.body.appendChild(script);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(inputText);
    }
  };

  return (
    <div style={{
      ...styles.container,
      height: isMobile ? 'calc(100vh - 178px)' : 'calc(100vh - 80px)'
    }}>
      {/* Desktop Header */}
      {!isMobile && (
        <header style={styles.header}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <button 
              onClick={() => setShowSidebar(!showSidebar)}
              style={styles.toggleSidebarBtn}
              title={showSidebar ? "Ẩn lịch sử trò chuyện" : "Hiện lịch sử trò chuyện"}
            >
              <Menu size={20} />
            </button>
            <div>
              <h2 style={styles.title}>Stock AI Assistant</h2>
              <p style={styles.subtitle}>Bộ não phân tích chứng khoán offline cục bộ & miễn phí</p>
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '10px' }}>
            {/* Clear History Button */}
            <button 
              onClick={handleClearChat}
              disabled={sending}
              style={styles.clearHistoryBtn}
            >
              <span>🧹 Xóa lịch sử</span>
            </button>

            {/* Advanced Config Button */}
            <button 
              onClick={() => { setShowConfig(!showConfig); checkStatus(); }}
              style={{
                ...styles.configToggleBtn,
                ...(showConfig ? styles.configToggleBtnActive : {})
              }}
            >
              <Settings size={18} />
              <span>Cấu hình nâng cao</span>
            </button>
          </div>
        </header>
      )}

      {/* Mobile Header (Sidebar list view) */}
      {isMobile && showSidebar && (
        <header style={styles.header}>
          <div>
            <h2 style={{ ...styles.title, fontSize: '20px' }}>Lịch sử trò chuyện</h2>
            <p style={styles.subtitle}>Chọn một cuộc hội thoại hoặc tạo mới</p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button 
              onClick={() => { setShowConfig(!showConfig); checkStatus(); }}
              style={{
                ...styles.configToggleBtn,
                padding: '8px 10px',
                ...(showConfig ? styles.configToggleBtnActive : {})
              }}
              title="Cấu hình AI"
            >
              <Settings size={18} />
            </button>
          </div>
        </header>
      )}

      {/* Mobile Header (Chat view) */}
      {isMobile && !showSidebar && (
        <header style={{ ...styles.header, gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden', flex: 1 }}>
            <button 
              onClick={() => setShowSidebar(true)}
              style={styles.mobileBackBtn}
              title="Quay lại danh sách"
            >
              <ArrowLeft size={18} />
            </button>
            <div style={{ overflow: 'hidden' }}>
              <h2 style={{ ...styles.title, fontSize: '16px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {threads.find(t => t.id === currentThreadId)?.title || "Cuộc trò chuyện mới"}
              </h2>
              <span style={{ fontSize: '11px', color: '#64748b' }}>Stock AI Assistant</span>
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
            <button 
              onClick={handleClearChat}
              disabled={sending}
              style={{
                ...styles.clearHistoryBtn,
                padding: '8px 10px',
              }}
              title="Dọn dẹp cuộc trò chuyện"
            >
              <span>🧹</span>
            </button>
            <button 
              onClick={() => { setShowConfig(!showConfig); checkStatus(); }}
              style={{
                ...styles.configToggleBtn,
                padding: '8px 10px',
                ...(showConfig ? styles.configToggleBtnActive : {})
              }}
              title="Cấu hình AI"
            >
              <Settings size={18} />
            </button>
          </div>
        </header>
      )}
  
      {/* Main Content Area */}
      <div style={{
        ...styles.workspace,
        gap: (isMobile || !showSidebar) ? '0' : '24px'
      }}>
        {/* Left Sidebar - Chat Threads */}
        {showSidebar && (
          <div style={{
            ...styles.chatSidebar,
            ...(isMobile ? { width: '100%' } : {})
          }}>
            <button 
              onClick={handleCreateThread}
              disabled={sending}
              style={styles.newChatBtn}
              onMouseOver={(e) => {
                e.currentTarget.style.background = 'linear-gradient(135deg, rgba(99, 102, 241, 0.3), rgba(168, 85, 247, 0.25))';
                e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.6)';
                e.currentTarget.style.color = '#ffffff';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.background = 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(168, 85, 247, 0.1))';
                e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.4)';
                e.currentTarget.style.color = '#cbd5e1';
              }}
            >
              <Plus size={16} />
              <span>Cuộc trò chuyện mới</span>
            </button>
            
            <div style={styles.threadList}>
              {threads.map((thread) => {
                const isActive = thread.id === currentThreadId;
                return (
                  <div
                    key={thread.id}
                    onClick={() => handleSelectThread(thread.id)}
                    style={{
                      ...styles.threadItem,
                      ...(isActive ? styles.activeThreadItem : {}),
                    }}
                    onMouseOver={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)';
                      }
                    }}
                    onMouseOut={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.borderColor = 'transparent';
                      }
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', overflow: 'hidden', flexGrow: 1 }}>
                      <MessageSquare 
                        size={14} 
                        style={{ 
                          color: isActive ? '#818cf8' : '#64748b', 
                          marginRight: '8px', 
                          flexShrink: 0 
                        }} 
                      />
                      <span style={styles.threadTitle} title={thread.title}>
                        {thread.title}
                      </span>
                    </div>
                    
                    <button
                      onClick={(e) => handleDeleteThread(e, thread.id)}
                      style={styles.deleteThreadBtn}
                      onMouseOver={(e) => {
                        e.currentTarget.style.color = '#ef4444';
                        e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)';
                      }}
                      onMouseOut={(e) => {
                        e.currentTarget.style.color = '#64748b';
                        e.currentTarget.style.background = 'transparent';
                      }}
                      title="Xóa cuộc hội thoại"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Right Area - Chat Room */}
        {(!isMobile || !showSidebar) && (
          <div style={styles.chatSection}>
            {/* Chat Messages Log */}
            <div className="glass-card" style={styles.chatWindow}>
              {messages.map((msg, idx) => (
                <div 
                  key={idx} 
                  style={{
                    ...styles.messageRow,
                    justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                    flexDirection: 'column',
                    alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                    gap: '8px'
                  }}
                >
                  <div 
                    style={{
                      ...styles.messageBubble,
                      ...(msg.role === 'user' ? styles.userBubble : styles.assistantBubble)
                    }}
                    dangerouslySetInnerHTML={{ __html: msg.content }}
                  />
                  {msg.role === 'assistant' && msg.content.includes('Phân tích nhanh') && (
                    <button
                      onClick={() => handleDownloadPDF(msg.content)}
                      style={{
                        background: 'rgba(99, 102, 241, 0.2)',
                        border: '1px solid rgba(99, 102, 241, 0.4)',
                        borderRadius: '6px',
                        color: '#a5b4fc',
                        fontSize: '12px',
                        fontWeight: 600,
                        padding: '6px 12px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        marginLeft: '4px',
                        transition: 'all 0.2s',
                      }}
                      onMouseOver={(e) => {
                        e.currentTarget.style.background = 'rgba(99, 102, 241, 0.35)';
                      }}
                      onMouseOut={(e) => {
                        e.currentTarget.style.background = 'rgba(99, 102, 241, 0.2)';
                      }}
                    >
                      <span>Tải báo cáo PDF</span>
                    </button>
                  )}
                </div>
              ))}
              {sending && (
                <div style={{ ...styles.messageRow, justifyContent: 'flex-start' }}>
                  <div style={{ ...styles.messageBubble, ...styles.assistantBubble, display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div className="dot-pulse" style={styles.typingDot}></div>
                    <span style={{ fontSize: '13px', color: '#94a3b8' }}>AI đang lập luận và viết câu trả lời...</span>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Chat Input Bar */}
            <div style={styles.inputArea}>
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Nhập câu hỏi của bạn và nhấn Enter để gửi..."
                disabled={sending}
                style={styles.textarea}
                rows={1}
              />
              <button
                onClick={() => handleSendMessage(inputText)}
                disabled={sending || !inputText.trim()}
                style={{
                  ...styles.sendBtn,
                  ...((sending || !inputText.trim()) ? styles.sendBtnDisabled : {})
                }}
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        )}

        {/* Right Area - Sidebar Settings (Conditional or Floating panel) */}
        <div style={{
          ...styles.configPanel,
          ...(showConfig ? styles.configPanelShow : styles.configPanelHide)
        }}>
          <h3 style={styles.configTitle}>Cấu hình AI</h3>
          <hr style={styles.configDivider} />

          {/* Mode selector */}
          <div style={styles.configGroup}>
            <label style={styles.configLabel}>Chế độ phân tích:</label>
            <div style={styles.radioGroup}>
              <button 
                onClick={() => setAnalysisMode('Nhanh')}
                style={{
                  ...styles.radioBtn,
                  ...(analysisMode === 'Nhanh' ? styles.radioBtnActive : {})
                }}
              >
                <Zap size={14} />
                <span>Phân tích nhanh</span>
              </button>
              <button 
                onClick={() => setAnalysisMode('Thông minh')}
                style={{
                  ...styles.radioBtn,
                  ...(analysisMode === 'Thông minh' ? styles.radioBtnActive : {})
                }}
              >
                <Sparkles size={14} />
                <span>Phân tích thông minh</span>
              </button>
            </div>
            <p style={styles.configDesc}>
              {analysisMode === 'Nhanh' 
                ? 'Phân tích nhanh: Trả báo cáo chỉ số kỹ thuật & dự đoán ML tức thì sau 0.1 giây, chạy offline hoàn toàn.' 
                : 'Phân tích thông minh: Trò chuyện tự nhiên, sử dụng AI cục bộ để diễn giải chỉ báo thật, tránh bịa số liệu.'}
            </p>
          </div>

          <hr style={styles.configDivider} />

          {/* Local LLM status */}
          <div style={styles.configGroup}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={styles.configLabel}>Trạng thái trợ lý cục bộ:</span>
              <button onClick={checkStatus} disabled={checkingStatus} style={styles.refreshBtn}>
                <RefreshCw size={12} className={checkingStatus ? 'spin' : ''} />
              </button>
            </div>

            {isOllamaReady ? (
              <div style={styles.statusSuccess}>
                <span style={styles.statusDotGreen}></span>
                <span>Sẵn sàng (Ollama online)</span>
              </div>
            ) : (
              <div style={styles.statusDanger}>
                <span style={styles.statusDotRed}></span>
                <span>Chưa sẵn sàng (Ollama offline)</span>
              </div>
            )}

            {isOllamaReady ? (
              <div style={{ marginTop: '12px' }}>
                <label style={{ ...styles.configLabel, fontSize: '11px', display: 'block', marginBottom: '4px' }}>Chọn mô hình cục bộ:</label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  style={styles.select}
                >
                  {availableModels.map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
            ) : (
              <div style={styles.helpBox}>
                <AlertTriangle size={16} color="#fca5a5" style={{ flexShrink: 0, marginTop: '2px' }} />
                <div style={{ fontSize: '11px', color: '#94a3b8', lineHeight: '1.5' }}>
                  Yêu cầu phần mềm trợ lý AI cục bộ (Ollama) chạy ở cổng 11434. <br /><br />
                  <b>Cách cài đặt:</b><br />
                  1. Cài đặt <b>Ollama</b> từ ollama.com.<br />
                  2. Mở CMD / Terminal và tải mô hình ngôn ngữ siêu nhẹ:<br />
                  <code style={styles.code}>ollama run qwen2.5:1.5b</code>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '10px 0',
    display: 'flex',
    flexDirection: 'column',
    height: 'calc(100vh - 80px)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
    flexShrink: 0,
  },
  toggleSidebarBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '40px',
    height: '40px',
    background: 'rgba(30, 41, 59, 0.4)',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    borderRadius: '10px',
    color: '#cbd5e1',
    cursor: 'pointer',
    transition: 'all 0.2s',
    flexShrink: 0,
  },
  mobileBackBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '36px',
    height: '36px',
    background: 'rgba(30, 41, 59, 0.6)',
    border: '1px solid rgba(148, 163, 184, 0.25)',
    borderRadius: '8px',
    color: '#cbd5e1',
    cursor: 'pointer',
    transition: 'all 0.2s',
    flexShrink: 0,
  },
  clearHistoryBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 16px',
    background: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    borderRadius: '10px',
    color: '#fca5a5',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  title: {
    fontSize: '28px',
    fontWeight: 900,
    color: '#f1f5f9',
    margin: 0,
  },
  subtitle: {
    fontSize: '13px',
    color: '#64748b',
    margin: '4px 0 0 0',
  },
  configToggleBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 16px',
    background: 'rgba(30, 41, 59, 0.4)',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    borderRadius: '10px',
    color: '#cbd5e1',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  configToggleBtnActive: {
    background: 'rgba(99, 102, 241, 0.2)',
    borderColor: 'rgba(99, 102, 241, 0.5)',
    color: '#ffffff',
  },
  chatSidebar: {
    width: '260px',
    background: 'rgba(15, 23, 42, 0.4)',
    border: '1px solid rgba(148, 163, 184, 0.12)',
    borderRadius: '12px',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
    height: '100%',
    overflow: 'hidden',
    flexShrink: 0,
    backdropFilter: 'blur(10px)',
  },
  newChatBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: '10px 14px',
    background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(168, 85, 247, 0.1))',
    border: '1px solid rgba(99, 102, 241, 0.4)',
    borderRadius: '8px',
    color: '#cbd5e1',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
    width: '100%',
  },
  threadList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    overflowY: 'auto',
    flexGrow: 1,
    paddingRight: '2px',
  },
  threadItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 12px',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    border: '1px solid transparent',
    background: 'transparent',
  },
  activeThreadItem: {
    background: 'rgba(99, 102, 241, 0.15)',
    borderColor: 'rgba(99, 102, 241, 0.3)',
  },
  threadTitle: {
    fontSize: '13px',
    color: '#cbd5e1',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    flexGrow: 1,
  },
  deleteThreadBtn: {
    background: 'transparent',
    border: 'none',
    color: '#64748b',
    cursor: 'pointer',
    padding: '4px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '4px',
    transition: 'all 0.2s',
  },
  workspace: {
    display: 'flex',
    gap: '24px',
    flexGrow: 1,
    height: '100%',
    overflow: 'hidden',
    position: 'relative',
  },
  chatSection: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'hidden',
  },
  instructionsCard: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
    background: 'rgba(30, 41, 59, 0.4)',
    border: '1px solid rgba(148, 163, 184, 0.12)',
    borderRadius: '12px',
    padding: '12px 16px',
    marginBottom: '14px',
    flexShrink: 0,
  },
  bulbIcon: {
    fontSize: '16px',
  },
  instructionsText: {
    margin: 0,
    fontSize: '13px',
    color: '#94a3b8',
    lineHeight: '1.6',
  },
  presetsContainer: {
    display: 'flex',
    gap: '8px',
    marginBottom: '14px',
    overflowX: 'auto',
    flexShrink: 0,
    paddingBottom: '4px',
  },
  presetBtn: {
    padding: '8px 14px',
    background: 'rgba(30, 41, 59, 0.6)',
    border: '1px solid rgba(148, 163, 184, 0.15)',
    borderRadius: '8px',
    color: '#cbd5e1',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    transition: 'all 0.2s',
  },
  chatWindow: {
    flexGrow: 1,
    padding: '24px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    marginBottom: '14px',
  },
  messageRow: {
    display: 'flex',
    width: '100%',
  },
  messageBubble: {
    maxWidth: '75%',
    padding: '14px 18px',
    borderRadius: '16px',
    fontSize: '14px',
    lineHeight: '1.6',
  },
  userBubble: {
    background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
    color: '#ffffff',
    borderTopRightRadius: '2px',
    boxShadow: '0 4px 12px rgba(79, 70, 229, 0.25)',
  },
  assistantBubble: {
    background: 'rgba(30, 41, 59, 0.75)',
    color: '#e2e8f0',
    border: '1px solid rgba(148, 163, 184, 0.15)',
    borderTopLeftRadius: '2px',
  },
  typingDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: '#818cf8',
    animation: 'pulse 1s infinite alternate',
  },
  inputArea: {
    display: 'flex',
    gap: '10px',
    background: 'rgba(15, 23, 42, 0.8)',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    borderRadius: '12px',
    padding: '8px 12px',
    alignItems: 'center',
    flexShrink: 0,
  },
  textarea: {
    flexGrow: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: '#f1f5f9',
    fontSize: '14px',
    resize: 'none',
    maxHeight: '80px',
    fontFamily: 'inherit',
    lineHeight: '1.5',
    padding: '6px 0',
  },
  sendBtn: {
    width: '40px',
    height: '40px',
    borderRadius: '8px',
    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    border: 'none',
    color: '#ffffff',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  sendBtnDisabled: {
    background: 'rgba(148, 163, 184, 0.1)',
    color: '#475569',
    cursor: 'not-allowed',
  },
  footerNote: {
    margin: '4px 0 0 0',
    textAlign: 'center',
    fontSize: '11px',
    color: '#64748b',
    flexShrink: 0,
  },
  configPanel: {
    width: '320px',
    background: 'rgba(15, 23, 42, 0.9)',
    borderLeft: '1px solid rgba(148, 163, 184, 0.12)',
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    gap: '18px',
    transition: 'all 0.3s ease',
    overflowY: 'auto',
  },
  configPanelShow: {
    display: 'flex',
  },
  configPanelHide: {
    display: 'none',
  },
  configTitle: {
    fontSize: '18px',
    fontWeight: 800,
    color: '#f1f5f9',
    margin: 0,
  },
  configDivider: {
    border: 0,
    borderTop: '1px solid rgba(148, 163, 184, 0.12)',
    margin: 0,
  },
  configGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  configLabel: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#94a3b8',
  },
  configDesc: {
    fontSize: '11px',
    color: '#64748b',
    margin: '4px 0 0 0',
    lineHeight: '1.4',
  },
  radioGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  radioBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 14px',
    borderRadius: '8px',
    border: '1px solid rgba(148, 163, 184, 0.15)',
    background: 'rgba(30, 41, 59, 0.4)',
    color: '#cbd5e1',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    textAlign: 'left',
    transition: 'all 0.2s',
  },
  radioBtnActive: {
    background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(168, 85, 247, 0.1))',
    borderColor: 'rgba(99, 102, 241, 0.5)',
    color: '#ffffff',
  },
  refreshBtn: {
    background: 'transparent',
    border: 'none',
    color: '#64748b',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  statusSuccess: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    background: 'rgba(16, 185, 129, 0.08)',
    border: '1px solid rgba(16, 185, 129, 0.25)',
    borderRadius: '8px',
    padding: '10px 14px',
    fontSize: '12px',
    fontWeight: 700,
    color: '#10b981',
  },
  statusDanger: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    background: 'rgba(239, 68, 68, 0.08)',
    border: '1px solid rgba(239, 68, 68, 0.25)',
    borderRadius: '8px',
    padding: '10px 14px',
    fontSize: '12px',
    fontWeight: 700,
    color: '#fca5a5',
  },
  select: {
    width: '100%',
    padding: '10px',
    borderRadius: '8px',
    background: '#0f172a',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    color: '#f1f5f9',
    fontSize: '12px',
    outline: 'none',
  },
  helpBox: {
    display: 'flex',
    gap: '8px',
    background: 'rgba(30, 41, 59, 0.3)',
    border: '1px solid rgba(148, 163, 184, 0.1)',
    borderRadius: '8px',
    padding: '12px',
    marginTop: '6px',
  },
  code: {
    display: 'block',
    background: '#0f172a',
    padding: '6px 8px',
    borderRadius: '4px',
    color: '#fca5a5',
    marginTop: '6px',
    border: '1px solid rgba(148, 163, 184, 0.1)',
  },
};

export default ChatAssistant;
