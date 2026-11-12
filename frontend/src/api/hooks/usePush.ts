import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, jsonBody } from '../client';
import { pushPublicKeyQuery } from '../queries';
import type { PushSubscriptionRead } from '../types';
import { getCurrentSubscription, pushSupported, subscribeDevice, unsubscribeDevice, usesKey } from '../../lib/push';

const deviceKey = (vapidKey: string) => ['push', 'device', vapidKey] as const;

function registerWithServer(subscription: PushSubscription): Promise<PushSubscriptionRead> {
  return api<PushSubscriptionRead>('/api/v1/notifications/push/subscriptions', {
    method: 'POST',
    ...jsonBody(subscription.toJSON()),
  });
}

export function usePushPublicKey() {
  return useQuery(pushPublicKeyQuery);
}

/**
 * Whether this device receives pushes, reconciled with the server on load.
 * A subscription made with an old VAPID key can never receive our pushes, so
 * it's dropped; a valid one is re-registered (an idempotent upsert), which
 * restores a server row lost to a database reset.
 */
export function useDevicePush(vapidKey: string | null | undefined) {
  return useQuery({
    queryKey: deviceKey(vapidKey ?? ''),
    queryFn: async () => {
      const subscription = await getCurrentSubscription();
      if (!subscription) return false;
      if (!usesKey(subscription, vapidKey!)) {
        await subscription.unsubscribe();
        return false;
      }
      await registerWithServer(subscription);
      return true;
    },
    enabled: Boolean(vapidKey) && pushSupported(),
    staleTime: Infinity,
    retry: false,
  });
}

/** Permission prompt + browser subscribe + backend registration in one go. */
export function useSubscribePush(vapidKey: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const subscription = await subscribeDevice(vapidKey);
      try {
        await registerWithServer(subscription);
      } catch (error) {
        // Without the server row nothing would ever be sent; don't leave the
        // browser believing it's subscribed.
        await subscription.unsubscribe();
        throw error;
      }
    },
    // The page explains the failure itself (denied permission vs. server error).
    meta: { errorToast: false },
    onSuccess: () => queryClient.setQueryData(deviceKey(vapidKey), true),
  });
}

export function useUnsubscribePush(vapidKey: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const endpoint = await unsubscribeDevice();
      if (endpoint) {
        await api<void>('/api/v1/notifications/push/unsubscribe', { method: 'POST', ...jsonBody({ endpoint }) });
      }
    },
    onSettled: () => queryClient.setQueryData(deviceKey(vapidKey), false),
  });
}
