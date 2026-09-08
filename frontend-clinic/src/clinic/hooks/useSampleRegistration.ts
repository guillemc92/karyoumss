import { useMutation, useQueryClient } from '@tanstack/react-query';
import { registrationClient } from '../api/registrationClient';
import type { SampleRegistrationData } from '../types/registration';

export function useSampleRegistration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SampleRegistrationData) => registrationClient.register(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['clinic', 'samples'] });
    },
  });
}
