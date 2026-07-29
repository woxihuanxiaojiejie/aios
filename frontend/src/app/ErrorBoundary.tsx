import { Alert } from "antd";
import type { ErrorInfo, ReactNode } from "react";
import { Component } from "react";

type State = {
  error: Error | null;
};

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("AIOS frontend error", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <Alert
          type="error"
          showIcon
          message="The page could not render."
          description={this.state.error.message}
        />
      );
    }
    return this.props.children;
  }
}
