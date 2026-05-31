declare module 'react-plotly.js' {
  import * as React from 'react';
  
  export interface PlotlyHTMLElement extends HTMLElement {
    on: (event: string, handler: (data: any) => void) => void;
  }

  export interface PlotProps {
    data: any[];
    layout?: any;
    config?: any;
    style?: React.CSSProperties;
    useResizeHandler?: boolean;
    className?: string;
    onInitialized?: (figure: any, graphDiv: PlotlyHTMLElement) => void;
    onUpdate?: (figure: any, graphDiv: PlotlyHTMLElement) => void;
    onPurge?: (figure: any, graphDiv: PlotlyHTMLElement) => void;
    onError?: (err: any) => void;
  }

  export default class Plot extends React.Component<PlotProps, any> {}
}

declare module 'react-plotly.js/factory' {
  export default function createPlotlyComponent(plotly: any): any;
}

declare module 'plotly.js-dist-min' {
  const plotly: any;
  export default plotly;
}
