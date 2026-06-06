import {
  NavigationContainer,
  createNavigationContainerRef,
  NavigationContainerRefWithCurrent,
} from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import * as Notifications from 'expo-notifications';
import { useEffect } from 'react';
import { ActivityIndicator, View } from 'react-native';

import { apiRequest } from '../api/client';
import { Medication } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import {
  fetchLatestDoseForReminder,
  getDoseLogIdFromNotification,
  speakReminderForDose,
} from '../notifications/reminderHandling';
import { LoginScreen } from '../screens/Auth/LoginScreen';
import { RegisterScreen } from '../screens/Auth/RegisterScreen';
import { AccessibilitySettingsScreen } from '../screens/Settings/AccessibilitySettingsScreen';
import { AddMedicationScreen } from '../screens/Patient/AddMedicationScreen';
import { CaregiverHomeScreen } from '../screens/Caregiver/CaregiverHomeScreen';
import { CaregiverDoseLogsScreen } from '../screens/Caregiver/CaregiverDoseLogsScreen';
import { CaregiverInviteAcceptScreen } from '../screens/Caregiver/CaregiverInviteAcceptScreen';
import { CaregiverVerificationReviewScreen } from '../screens/Caregiver/CaregiverVerificationReviewScreen';
import { DoseResultScreen } from '../screens/Patient/DoseResultScreen';
import { HomeScreen } from '../screens/Patient/HomeScreen';
import { MedicationDetailScreen } from '../screens/Patient/MedicationDetailScreen';
import { MedicationListScreen } from '../screens/Patient/MedicationListScreen';
import { ManualMedicationFormScreen } from '../screens/Patient/ManualMedicationFormScreen';
import { PatientDetailScreen } from '../screens/Caregiver/PatientDetailScreen';
import { RootStackParamList } from './types';
import { ScanLabelScreen } from '../screens/Patient/ScanLabelScreen';
import { ConfirmExtractedMedicationScreen } from '../screens/Patient/ConfirmExtractedMedicationScreen';
import { TodayScheduleScreen } from '../screens/Patient/TodayScheduleScreen';
import { VerifyMedicationScreen } from '../screens/Patient/VerifyMedicationScreen';

const Stack = createNativeStackNavigator<RootStackParamList>();
const navigationRef = createNavigationContainerRef<RootStackParamList>();

export function RootNavigator() {
  const { user, isLoading } = useAuth();

  useEffect(() => {
    const subscription = Notifications.addNotificationResponseReceivedListener(response => {
      const doseLogId = getDoseLogIdFromNotification(response);
      if (!doseLogId) return;
      void handleReminderTap(navigationRef, doseLogId);
    });
    return () => subscription.remove();
  }, []);

  if (isLoading) {
    return (
      <View accessibilityRole="progressbar" style={{ flex: 1, justifyContent: 'center' }}>
        <ActivityIndicator />
      </View>
    );
  }

  return (
    <NavigationContainer ref={navigationRef}>
      <Stack.Navigator>
        {!user ? (
          <>
            <Stack.Screen name="Login" component={LoginScreen} />
            <Stack.Screen name="Register" component={RegisterScreen} />
          </>
        ) : (
          <>
            <Stack.Screen name="PatientHome" component={HomeScreen} options={{ title: 'Home' }} />
            <Stack.Screen name="TodaySchedule" component={TodayScheduleScreen} />
            <Stack.Screen name="MedicationList" component={MedicationListScreen} />
            <Stack.Screen name="MedicationDetail" component={MedicationDetailScreen} />
            <Stack.Screen name="AddMedication" component={AddMedicationScreen} />
            <Stack.Screen name="ManualMedicationForm" component={ManualMedicationFormScreen} />
            <Stack.Screen name="ScanLabel" component={ScanLabelScreen} />
            <Stack.Screen name="ConfirmExtractedMedication" component={ConfirmExtractedMedicationScreen} />
            <Stack.Screen name="VerifyMedication" component={VerifyMedicationScreen} />
            <Stack.Screen name="DoseResult" component={DoseResultScreen} />
            <Stack.Screen name="CaregiverHome" component={CaregiverHomeScreen} />
            <Stack.Screen name="PatientDetail" component={PatientDetailScreen} />
            <Stack.Screen name="CaregiverDoseLogs" component={CaregiverDoseLogsScreen} />
            <Stack.Screen
              name="CaregiverVerificationReview"
              component={CaregiverVerificationReviewScreen}
            />
            <Stack.Screen name="CaregiverInviteAccept" component={CaregiverInviteAcceptScreen} />
            <Stack.Screen name="AccessibilitySettings" component={AccessibilitySettingsScreen} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export async function handleReminderTap(
  ref: NavigationContainerRefWithCurrent<RootStackParamList>,
  doseLogId: string,
): Promise<void> {
  const dose = await fetchLatestDoseForReminder(doseLogId);
  if (!dose) return;
  const medications = await apiRequest<Medication[]>('/api/v1/medications');
  await speakReminderForDose(dose, medications);
  if (ref.isReady()) {
    ref.navigate('VerifyMedication', { doseLogId: dose.id });
  }
}
