import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  change?: string | number;
  changeType?: 'up' | 'down' | 'neutral';
  color?: 'green' | 'red' | 'yellow' | 'blue' | 'default';
}

const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  change,
  changeType = 'neutral',
  color = 'default',
}) => {
  const getThemeColors = () => {
    switch (color) {
      case 'green':
        return { text: '#10b981', bg: 'rgba(16, 185, 129, 0.1)' };
      case 'red':
        return { text: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)' };
      case 'yellow':
        return { text: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)' };
      case 'blue':
        return { text: '#38bdf8', bg: 'rgba(56, 189, 248, 0.1)' };
      default:
        return { text: '#f1f5f9', bg: 'rgba(255, 255, 255, 0.05)' };
    }
  };

  const colors = getThemeColors();

  return (
    <div className="glass-card" style={styles.card}>
      <p style={styles.label}>{label}</p>
      <div style={styles.valueRow}>
        <span
          className={`metric-value ${changeType}`}
          style={{
            ...styles.value,
            color: colors.text,
          }}
        >
          {value}
        </span>
        {change !== undefined && (
          <span
            style={{
              ...styles.change,
              color: changeType === 'up' ? '#10b981' : changeType === 'down' ? '#ef4444' : '#38bdf8',
              backgroundColor: changeType === 'up' ? 'rgba(16, 185, 129, 0.12)' : changeType === 'down' ? 'rgba(239, 68, 68, 0.12)' : 'rgba(56, 189, 248, 0.12)',
            }}
          >
            {change}
          </span>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  card: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    minHeight: '110px',
    padding: '20px 24px',
  },
  label: {
    color: '#94a3b8',
    fontSize: '13px',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  valueRow: {
    display: 'flex',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    marginTop: '8px',
  },
  value: {
    fontSize: '28px',
    fontWeight: 800,
  },
  change: {
    fontSize: '13px',
    fontWeight: 700,
    padding: '4px 8px',
    borderRadius: '6px',
  },
};

export default MetricCard;
