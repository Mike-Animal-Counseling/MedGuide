import { AccessibleButton } from './AccessibleButton';

type Props = {
  title: string;
  onPress: () => void;
  accessibilityLabel: string;
  accessibilityHint: string;
};

export function LargeActionButton(props: Props) {
  return <AccessibleButton {...props} />;
}
