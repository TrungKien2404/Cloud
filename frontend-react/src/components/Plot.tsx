import React, { useEffect, useRef } from 'react';

interface PlotProps {
  data: any[];
  layout?: any;
  config?: any;
  style?: React.CSSProperties;
}

const Plot: React.FC<PlotProps> = ({ data, layout, config, style }) => {
  const divRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const Plotly = (window as any).Plotly;
    if (divRef.current && Plotly) {
      Plotly.newPlot(divRef.current, data, layout, {
        responsive: true,
        ...config
      });
    }
  }, [data, layout, config]);

  // Tự động thay đổi kích thước biểu đồ khi cửa sổ trình duyệt thay đổi
  useEffect(() => {
    const handleResize = () => {
      const Plotly = (window as any).Plotly;
      if (divRef.current && Plotly) {
        Plotly.Plots.resize(divRef.current);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return <div ref={divRef} style={style} />;
};

export default Plot;
