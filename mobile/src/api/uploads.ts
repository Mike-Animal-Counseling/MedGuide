import { apiRequest } from './client';
import { ScanLabelResult, VerifyMedicationResult } from '../navigation/types';

export type LocalImageAsset = {
  uri: string;
  contentType: string;
  sizeBytes?: number;
  fileName?: string;
};

export type SignedUploadResponse = {
  image_id: string;
  upload_url: string;
  upload_fields: Record<string, string>;
  expires_in_seconds: number;
};

export async function uploadMedicationLabelImage(asset: LocalImageAsset): Promise<ScanLabelResult> {
  const signed = await createSignedUpload('MEDICATION_LABEL', asset);

  await uploadToSignedPost(signed, asset);

  const scan = await apiRequest<Omit<ScanLabelResult, 'image_id'>>('/api/v1/ai/scan-label', {
    method: 'POST',
    body: { image_id: signed.image_id },
  });

  return { ...scan, image_id: signed.image_id };
}

export async function uploadVerificationImage(asset: LocalImageAsset): Promise<string> {
  const signed = await createSignedUpload('VERIFICATION_IMAGE', asset);
  await uploadToSignedPost(signed, asset);
  return signed.image_id;
}

export async function verifyMedicationImage(input: {
  doseLogId: string;
  asset: LocalImageAsset;
}): Promise<VerifyMedicationResult> {
  const imageId = await uploadVerificationImage(input.asset);
  const result = await apiRequest<Omit<VerifyMedicationResult, 'image_id'>>(
    '/api/v1/ai/verify-medication',
    {
      method: 'POST',
      body: {
        dose_log_id: input.doseLogId,
        image_id: imageId,
        verification_type: 'PILL_VERIFY',
      },
    },
  );
  return { ...result, image_id: imageId };
}

async function createSignedUpload(
  purpose: 'MEDICATION_LABEL' | 'VERIFICATION_IMAGE',
  asset: LocalImageAsset,
): Promise<SignedUploadResponse> {
  return apiRequest<SignedUploadResponse>('/api/v1/uploads/signed-url', {
    method: 'POST',
    body: {
      purpose,
      content_type: asset.contentType,
      size_bytes: asset.sizeBytes,
    },
  });
}

async function uploadToSignedPost(
  signed: SignedUploadResponse,
  asset: LocalImageAsset,
): Promise<void> {
  const formData = new FormData();
  Object.entries(signed.upload_fields).forEach(([key, value]) => {
    formData.append(key, value);
  });
  formData.append('file', {
    uri: asset.uri,
    name: asset.fileName ?? 'medication-label.jpg',
    type: asset.contentType,
  } as unknown as Blob);

  const response = await fetch(signed.upload_url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Image upload failed');
  }
}
