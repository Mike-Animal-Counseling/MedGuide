import { useQuery } from '@tanstack/react-query';

import { apiRequest } from '../api/client';
import { DoseLog } from '../api/types';

export function useTodayDoseLogs() {
  return useQuery({
    queryKey: ['doseLogs', 'today'],
    queryFn: () => apiRequest<DoseLog[]>('/api/v1/dose-logs/today'),
  });
}
