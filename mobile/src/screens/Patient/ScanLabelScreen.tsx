import { CameraView } from 'expo-camera';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useMutation } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { uploadMedicationLabelImage } from '../../api/uploads';
import { requestCameraPermission } from '../../camera/camera';
import { AccessibleButton } from '../../components/AccessibleButton';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { VoicePrompt } from '../../components/VoicePrompt';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'ScanLabel'>;

export function ScanLabelScreen({ navigation }: Props) {
  const cameraRef = useRef<CameraView | null>(null);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: async () => {
      const picture = await cameraRef.current?.takePictureAsync({ quality: 0.85 });
      if (!picture?.uri) {
        throw new Error('Camera did not return an image');
      }
      return uploadMedicationLabelImage({
        uri: picture.uri,
        contentType: 'image/jpeg',
        fileName: 'medication-label.jpg',
      });
    },
    onSuccess: response => {
      if (response.result === 'UNREADABLE_IMAGE') {
        setMessage(response.safety_message);
        return;
      }
      navigation.navigate('ConfirmExtractedMedication', { scan: response });
    },
    onError: () =>
      setMessage(
        'Label scanning is unavailable. You can continue by entering confirmed medication details manually.',
      ),
  });

  async function askCameraPermission() {
    const granted = await requestCameraPermission();
    setHasPermission(granted);
    setMessage(
      granted
        ? 'Camera permission granted. Place the medication label clearly in view.'
        : 'Camera permission was not granted. You can add this medication manually.',
    );
  }

  return (
    <Screen title="Scan label">
      <VoicePrompt text="Please confirm all extracted medication information before saving." />
      <AccessibleButton
        title="Allow camera"
        onPress={() => void askCameraPermission()}
        accessibilityLabel="Allow camera"
        accessibilityHint="Requests camera permission for label scanning"
      />
      {hasPermission ? (
        <View style={styles.cameraContainer}>
          <CameraView
            ref={cameraRef}
            style={styles.camera}
            facing="back"
            onCameraReady={() => setCameraReady(true)}
          />
          <Text accessibilityRole="text">
            Keep the label flat, well lit, and inside the camera view.
          </Text>
          <AccessibleButton
            title={mutation.isPending ? 'Uploading and scanning...' : 'Capture and scan label'}
            disabled={mutation.isPending || !cameraReady}
            onPress={() => mutation.mutate()}
            accessibilityLabel="Capture and scan label"
            accessibilityHint="Takes a photo, uploads it with a signed URL, and scans the label"
          />
        </View>
      ) : null}
      {hasPermission === false ? (
        <AccessibleButton
          title="Enter manually instead"
          onPress={() => navigation.navigate('ManualMedicationForm')}
          accessibilityLabel="Enter medication manually"
          accessibilityHint="Opens the manual medication entry form"
        />
      ) : null}
      {message ? <StatusCard title="Scan result" message={message} /> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  cameraContainer: { gap: 12 },
  camera: {
    borderRadius: 16,
    height: 360,
    overflow: 'hidden',
  },
});
