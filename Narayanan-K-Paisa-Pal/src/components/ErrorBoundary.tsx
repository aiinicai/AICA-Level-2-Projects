import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in Paisa Pal:', error, errorInfo);
  }

  public handleReload = () => {
    window.location.reload();
  };

  public handleReset = () => {
    try {
      localStorage.clear();
      window.location.reload();
    } catch {
      window.location.reload();
    }
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-[#EEF1F5] dark:bg-[#0B1220] text-[#0F1B2D] dark:text-[#E8EDF5]">
          <div className="max-w-md w-full bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-6 shadow-xl text-center space-y-4">
            <div className="w-12 h-12 mx-auto rounded-full bg-rose-100 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold">Something went wrong</h2>
              <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mt-1">
                {this.state.error?.message || 'An unexpected error occurred while running Paisa Pal.'}
              </p>
            </div>
            <div className="pt-2 flex flex-col gap-2">
              <button
                onClick={this.handleReload}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-[#0E7C86] hover:bg-[#128e9a] text-white font-semibold text-xs transition"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Reload App</span>
              </button>
              <button
                onClick={this.handleReset}
                className="w-full py-2 px-4 rounded-xl border border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 text-xs text-[#6F7E92] dark:text-[#8594AA] transition"
              >
                Clear Local Cache & Restart
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
