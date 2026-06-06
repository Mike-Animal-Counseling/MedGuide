import { useQuery } from '@tanstack/react-query';

import { apiRequest } from '../api/client';
import { Medication } from '../api/types';

export function useMedications() {
  return useQuery({
    queryKey: ['medications'],
    queryFn: () => apiRequest<Medication[]>('/api/v1/medications'),
  });
}
