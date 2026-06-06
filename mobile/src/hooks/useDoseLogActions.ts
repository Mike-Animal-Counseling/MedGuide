import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiRequest } from '../api/client';
import { DoseLog } from '../api/types';

const DOSE_QUERY_KEYS = [
  ['doseLogs'],
  ['doseLogs', 'today'],
] as const;

export function useDoseLogActions() {
  const queryClient = useQueryClient();

  async function invalidateDoseQueries() {
    await Promise.all(
      DOSE_QUERY_KEYS.map(queryKey => queryClient.invalidateQueries({ queryKey })),
    );
  }

  const confirm = useMutation({
    mutationFn: (doseLogId: string) =>
      apiRequest<DoseLog>(`/api/v1/dose-logs/${doseLogId}/confirm`, {
        method: 'PATCH',
        body: {
          confirmation_method: 'BUTTON',
          actual_taken_time: new Date().toISOString(),
        },
      }),
    onSuccess: invalidateDoseQueries,
  });

  const skip = useMutation({
    mutationFn: (doseLogId: string) =>
      apiRequest<DoseLog>(`/api/v1/dose-logs/${doseLogId}/skip`, {
        method: 'PATCH',
        body: {},
      }),
    onSuccess: invalidateDoseQueries,
  });

  const needsHelp = useMutation({
    mutationFn: (doseLogId: string) =>
      apiRequest<DoseLog>(`/api/v1/dose-logs/${doseLogId}/needs-help`, {
        method: 'PATCH',
        body: {},
      }),
    onSuccess: invalidateDoseQueries,
  });

  return { confirm, skip, needsHelp };
}
