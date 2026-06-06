import { CameraView } from 'expo-camera';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useMutation } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { verifyMedicationImage } from '../../api/uploads';
import { requestCameraPermission } from '../../camera/camera';
import { AccessibleButton } from '../../components/AccessibleButton';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { VoicePrompt } from '../../components/VoicePrompt';
import { useDoseLogActions } from '../../hooks/useDoseLogActions';
import { useMedications } from '../../hooks/useMedications';
import { useTodayDoseLogs } from '../../hooks/useTodayDoseLogs';
import { MedicationVerificationResult, RootStackParamList } from '../../navigation/types';
import {
  buildMedicationCheckIntro,
  VERIFICATION_CAMERA_GUIDANCE,
} from '../../voice/verificationVoicePrompt';

type Props = NativeStackScreenProps<RootStackParamList, 'VerifyMedication'>;

export function VerifyMedicationScreen({ navigation, route }: Props) {
  const cameraRef = useRef<CameraView | null>(null);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    result: MedicationVerificationResult;
    safety_message: string;
    confidence_score: number | null;
  } | null>(null);
  const { data: doses } = useTodayDoseLogs();
  const { data: medications } = useMedications();
  const { confirm, needsHelp } = useDoseLogActions();
  const dose =
    doses?.find(item => item.id === route.params?.doseLogId) ??
    doses?.find(item => item.status === 'PENDING');
  const medication = medications?.find(item => item.id === dose?.medication_id);
  const checkIntro = buildMedicationCheckIntro(medication);
  const mutation = useMutation({
    mutationFn: async () => {
      if (!dose) {
        throw new Error('No pending dose selected');
      }
      const picture = await cameraRef.current?.takePictureAsync({ quality: 0.85 });
      if (!picture?.uri) {
        throw new Error('Camera did not return an image');
      }
      return verifyMedicationImage({
        doseLogId: dose.id,
        asset: {
          uri: picture.uri,
          contentType: 'image/jpeg',
          fileName: 'medication-verification.jpg',
        },
      });
    },
    onSuccess: response =>
      setResult({
        result: response.result,
        safety_message: response.safety_message,
        confidence_score: response.confidence_score,
      }),
    onError: () =>
      setError('Verification is unavailable. Please check the label or contact your caregiver.'),
  });

  async function askCameraPermission() {
    const granted = await requestCameraPermission();
    setHasPermission(granted);
    setError(granted ? null : 'Camera permission was not granted. You can contact your caregiver.');
  }

  function retake() {
    setResult(null);
    setError(null);
  }

  function markTaken() {
    if (!dose) return;
    confirm.mutate(dose.id, {
      onSuccess: () => navigation.navigate('DoseResult', { result: result?.safety_message }),
    });
  }

  function contactCaregiver() {
    if (!dose) return;
    needsHelp.mutate(dose.id);
  }

  const canMarkTakenPrimary = result?.result === 'MATCH_LIKELY';
  const canMarkTakenWithExtraConfirmation = result?.result === 'MATCH_UNCERTAIN';
  const shouldRetake = result
    ? ['MATCH_UNCERTAIN', 'CAREGIVER_REVIEW_REQUIRED', 'NO_MATCH', 'UNREADABLE_IMAGE'].includes(
        result.result,
      )
    : false;

  return (
    <Screen title="Verify medication">
      <StatusCard
        title="Safety reminder"
        message="MedGuide compares this image only with your currently due medication and cannot identify every medication."
      />
      <VoicePrompt text={checkIntro} buttonTitle="Read dose instruction" />
      <VoicePrompt text={VERIFICATION_CAMERA_GUIDANCE} buttonTitle="Read camera guidance" />
      {!dose ? (
        <StatusCard
          title="No pending dose selected"
          message="Go back to today's schedule and choose a pending dose."
          tone="warning"
        />
      ) : null}
      <AccessibleButton
        title="Allow camera"
        onPress={() => void askCameraPermission()}
        accessibilityLabel="Allow camera for verification"
        accessibilityHint="Requests camera permission for medication verification"
      />
      {hasPermission && !result ? (
        <View style={styles.cameraContainer}>
          <CameraView
            ref={cameraRef}
            style={styles.camera}
            facing="back"
            onCameraReady={() => setCameraReady(true)}
          />
          <Text accessibilityRole="text">{VERIFICATION_CAMERA_GUIDANCE}</Text>
          <AccessibleButton
            title={mutation.isPending ? 'Checking...' : 'Capture and check medication'}
            disabled={mutation.isPending || !cameraReady || !dose}
            onPress={() => mutation.mutate()}
            accessibilityLabel="Capture and check medication"
            accessibilityHint="Uploads an image and asks MedGuide to compare it with the currently due medication"
          />
        </View>
      ) : null}
      {error ? <StatusCard title="Verification problem" message={error} tone="warning" /> : null}
      {result ? (
        <VerificationResultActions
          result={result.result}
          safetyMessage={result.safety_message}
          confidenceScore={result.confidence_score}
          canMarkTakenPrimary={canMarkTakenPrimary}
          canMarkTakenWithExtraConfirmation={canMarkTakenWithExtraConfirmation}
          shouldRetake={shouldRetake}
          markTakenPending={confirm.isPending}
          needsHelpPending={needsHelp.isPending}
          onMarkTaken={markTaken}
          onRetake={retake}
          onContactCaregiver={contactCaregiver}
        />
      ) : null}
    </Screen>
  );
}

type VerificationResultActionsProps = {
  result: MedicationVerificationResult;
  safetyMessage: string;
  confidenceScore: number | null;
  canMarkTakenPrimary: boolean;
  canMarkTakenWithExtraConfirmation: boolean;
  shouldRetake: boolean;
  markTakenPending: boolean;
  needsHelpPending: boolean;
  onMarkTaken: () => void;
  onRetake: () => void;
  onContactCaregiver: () => void;
};

function VerificationResultActions({
  result,
  safetyMessage,
  confidenceScore,
  canMarkTakenPrimary,
  canMarkTakenWithExtraConfirmation,
  shouldRetake,
  markTakenPending,
  needsHelpPending,
  onMarkTaken,
  onRetake,
  onContactCaregiver,
}: VerificationResultActionsProps) {
  return (
    <>
      <StatusCard
        title={formatResult(result)}
        message={`${safetyMessage}${confidenceScore === null ? '' : ` Confidence ${Math.round(
          confidenceScore * 100,
        )} percent.`}`}
        tone={result === 'MATCH_LIKELY' ? 'success' : 'warning'}
      />
      <VoicePrompt text={safetyMessage} buttonTitle="Read verification result" />
      {canMarkTakenPrimary ? (
        <AccessibleButton
          title="Mark as Taken"
          disabled={markTakenPending}
          onPress={onMarkTaken}
          accessibilityLabel="Mark dose as taken"
          accessibilityHint="Confirms this dose after a result that appears to match"
        />
      ) : null}
      {canMarkTakenWithExtraConfirmation ? (
        <>
          <StatusCard
            title="Extra confirmation required"
            message="Only mark this dose as taken if you personally checked the label or confirmed with a caregiver."
            tone="warning"
          />
          <AccessibleButton
            title="Mark as taken after checking label"
            disabled={markTakenPending}
            onPress={onMarkTaken}
            accessibilityLabel="Mark as taken after checking label"
            accessibilityHint="Confirms this uncertain dose only after extra user confirmation"
          />
        </>
      ) : null}
      {shouldRetake ? (
        <AccessibleButton
          title="Retake photo"
          onPress={onRetake}
          accessibilityLabel="Retake verification photo"
          accessibilityHint="Clears the result and returns to the camera"
        />
      ) : null}
      {result !== 'MATCH_LIKELY' ? (
        <AccessibleButton
          title="Contact caregiver"
          disabled={needsHelpPending}
          onPress={onContactCaregiver}
          accessibilityLabel="Contact caregiver"
          accessibilityHint="Marks this dose as needing help so a caregiver can follow up"
        />
      ) : null}
    </>
  );
}

function formatResult(result: MedicationVerificationResult): string {
  switch (result) {
    case 'MATCH_LIKELY':
      return 'Appears to match';
    case 'MATCH_UNCERTAIN':
      return 'Match uncertain';
    case 'UNREADABLE_IMAGE':
      return 'Image unreadable';
    case 'NO_MATCH':
      return 'Cannot confirm match';
    case 'CAREGIVER_REVIEW_REQUIRED':
      return 'Caregiver review needed';
  }
}

const styles = StyleSheet.create({
  cameraContainer: { gap: 12 },
  camera: {
    borderRadius: 16,
    height: 360,
    overflow: 'hidden',
  },
});
