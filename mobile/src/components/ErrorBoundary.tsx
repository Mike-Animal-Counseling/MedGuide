import { Component, PropsWithChildren, ReactNode } from 'react';
import { Text, View } from 'react-native';

import { reportClientError } from '../observability/errorReporter';

type State = { error: Error | null };

export class ErrorBoundary extends Component<PropsWithChildren, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error): void {
    reportClientError(error, { boundary: 'AppErrorBoundary' });
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <View accessible accessibilityRole="alert" style={{ flex: 1, justifyContent: 'center', padding: 24 }}>
          <Text>Something went wrong. Please restart the app or try again later.</Text>
        </View>
      );
    }
    return this.props.children;
  }
}
