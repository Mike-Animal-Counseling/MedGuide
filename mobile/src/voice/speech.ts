import * as Speech from 'expo-speech';

export function speak(text: string): void {
  Speech.speak(text, { language: 'en-US', rate: 0.9 });
}
