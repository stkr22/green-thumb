// Browser-side Web Push helpers. The subscription lifecycle is:
// permission -> pushManager.subscribe(VAPID key) -> POST to the backend.

export function pushSupported(): boolean {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
}

function urlBase64ToUint8Array(base64: string): Uint8Array {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4);
  const raw = window.atob((base64 + padding).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from(raw, (char) => char.charCodeAt(0));
}

export async function getCurrentSubscription(): Promise<PushSubscription | null> {
  if (!pushSupported()) return null;
  const registration = await navigator.serviceWorker.ready;
  return registration.pushManager.getSubscription();
}

/** Ask for permission and subscribe this device; throws on denial. */
export async function subscribeDevice(vapidPublicKey: string): Promise<PushSubscriptionJSON> {
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') {
    throw new Error('Notification permission was not granted');
  }
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey) as BufferSource,
  });
  return subscription.toJSON();
}

/** Unsubscribe locally; returns the endpoint so the backend row can go too. */
export async function unsubscribeDevice(): Promise<string | null> {
  const subscription = await getCurrentSubscription();
  if (!subscription) return null;
  const endpoint = subscription.endpoint;
  await subscription.unsubscribe();
  return endpoint;
}
