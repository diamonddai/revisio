import { Component, type ReactNode } from "react";
import { ConfigProvider } from "antd";
import AppLayout from "./app/AppLayout";

class ErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  state = { hasError: false, error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError && this.state.error) {
      return (
        <div style={{ padding: 24, fontFamily: "sans-serif" }}>
          <h2>Page load error</h2>
          <pre style={{ background: "#f5f5f5", padding: 12, overflow: "auto" }}>
            {this.state.error.message}
          </pre>
          <p>Open browser console (F12) for details.</p>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  return (
    <ErrorBoundary>
      <ConfigProvider
        theme={{
          token: {
            borderRadius: 8,
          },
        }}
      >
        <AppLayout />
      </ConfigProvider>
    </ErrorBoundary>
  );
}
