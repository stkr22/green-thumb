import { useMutation, useQuery } from '@tanstack/react-query';

import { api, jsonBody } from '../client';
import type { PushPublicKey, PushSubscriptionRead } from '../types';
import { subscribeDevice, unsubscribeDevice } from '../../lib/push';

export function usePushPublicKey() {
  return useQuery({
    queryKey: ['push', 'public-key'],
    queryFn: () => api<PushPublicKey>('/api/v1/notifications/push/public-key'),
    staleTime: Infinity, // the VAPID key never changes while deployed
  });
}

/** Permission prompt + browser subscribe + backend registration in one go. */
export function useSubscribePush() {
  return useMutation({
    mutationFn: async (vapidPublicKey: string) => {
      const subscription = await subscribeDevice(vapidPublicKey);
      return api<PushSubscriptionRead>('/api/v1/notifications/push/subscriptions', {
        method: 'POST',
        ...jsonBody(subscription),
      });
    },
  });
}

export function useUnsubscribePush() {
  return useMutation({
    mutationFn: async () => {
      const endpoint = await unsubscribeDevice();
      if (endpoint) {
        await api<void>('/api/v1/notifications/push/unsubscribe', { method: 'POST', ...jsonBody({ endpoint }) });
      }
    },
  });
}
