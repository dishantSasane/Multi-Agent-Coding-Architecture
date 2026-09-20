import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/shared/Button';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div role="alert" className="flex flex-col items-center justify-center p-8 text-center">
          <AlertTriangle className="mb-4 h-16 w-16 text-warning" aria-hidden="true" />
          <h2 className="mb-2 text-xl font-medium">Something went wrong</h2>
          <p className="text-muted-foreground mb-4 max-w-md">
            {this.state.error?.message || 'An unexpected error occurred.'}
          </p>
          <Button onClick={this.handleReset} variant="primary">
            Try Again
          </Button>
          <button
            onClick={() => {
              const reportBody = encodeURIComponent(
                `Error: ${this.state.error?.message}\n\nStack: ${this.state.error?.stack}`
              );
              window.open(`mailto:support@example.com?subject=CodeForge Error Report&body=${reportBody}`);
            }}
            className="mt-4 text-sm text-muted-foreground hover:text-foreground transition-colors duration-150 ease-out"
          >
            Report Issue
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
