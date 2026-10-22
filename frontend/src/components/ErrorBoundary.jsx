import { Component } from "react";

/**
 * Catches render errors so a single broken component cannot blank the app.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("Unhandled UI error", error, info?.componentStack);
  }

  handleReload = () => {
    this.setState({ error: null });
  };

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 p-6">
        <div className="max-w-md rounded-xl border border-red-200 bg-white p-6 text-center">
          <h1 className="text-lg font-semibold text-gray-900">Something went wrong</h1>
          <p className="mt-2 text-sm text-gray-600">
            The interface hit an unexpected error. Your uploaded documents are unaffected.
          </p>
          <pre className="mt-3 overflow-x-auto rounded bg-gray-100 p-2 text-left text-xs text-gray-700">
            {String(error.message || error)}
          </pre>
          <button
            type="button"
            onClick={this.handleReload}
            className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }
}
