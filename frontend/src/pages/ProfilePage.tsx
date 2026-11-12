import { useState } from 'react';
import { Bell, BellRing, Copy, Key, Send, Smartphone } from 'lucide-react';

import { useMe, useMintApiToken, useTestNotification, useUpdateMe } from '../api/hooks/useProfile';
import { useDevicePush, usePushPublicKey, useSubscribePush, useUnsubscribePush } from '../api/hooks/usePush';
import type { UserRead } from '../api/types';
import { Field } from '../components/Field';
import { useToast } from '../components/Toast';
import { PushPermissionError, pushSupported } from '../lib/push';

function DevicePushToggle({ vapidKey }: { vapidKey: string }) {
  const { data: subscribed, isPending } = useDevicePush(vapidKey);
  const subscribePush = useSubscribePush(vapidKey);
  const unsubscribePush = useUnsubscribePush(vapidKey);
  const { notify } = useToast();

  if (isPending) return null;
  if (subscribed) {
    return (
      <button
        type="button"
        className="btn-secondary"
        disabled={unsubscribePush.isPending}
        onClick={() =>
          unsubscribePush.mutate(undefined, { onSuccess: () => notify('Push notifications disabled on this device') })
        }
      >
        Disable on this device
      </button>
    );
  }
  return (
    <button
      type="button"
      className="btn-primary"
      disabled={subscribePush.isPending}
      onClick={() =>
        subscribePush.mutate(undefined, {
          onSuccess: () => notify('Push notifications enabled on this device'),
          onError: (error) =>
            notify(
              error instanceof PushPermissionError
                ? 'Could not enable push: notification permission was denied'
                : `Could not enable push: ${error.message}`,
              'error',
            ),
        })
      }
    >
      <BellRing className="h-4 w-4" />
      Enable on this device
    </button>
  );
}

function DevicePushSection() {
  const { data: publicKey } = usePushPublicKey();
  // Server has no VAPID key or the browser can't do push: nothing to offer.
  if (!publicKey?.key || !pushSupported()) return null;

  return (
    <div className="mb-4 rounded-lg border border-stone-200 p-4">
      <h3 className="mb-1 flex items-center gap-2 text-sm font-medium">
        <Smartphone className="h-4 w-4 text-emerald-600" />
        Push notifications on this device
      </h3>
      <p className="mb-3 text-xs text-stone-500">
        Native notifications without ntfy, straight to this browser or installed app. On iPhone, add the
        app to your home screen first.
      </p>
      <DevicePushToggle vapidKey={publicKey.key} />
    </div>
  );
}

// Keyed on the saved value by the parent, so it re-initialises when the server
// value changes instead of copying it into state with an effect.
function TopicOverrideForm({ me }: { me: UserRead }) {
  const updateMe = useUpdateMe();
  const { notify } = useToast();
  const [topicOverride, setTopicOverride] = useState(me.ntfy_topic_override ?? '');

  return (
    <form
      className="mb-4"
      onSubmit={(event) => {
        event.preventDefault();
        updateMe.mutate(
          { ntfy_topic_override: topicOverride.trim() || null },
          { onSuccess: () => notify('Notification settings saved') },
        );
      }}
    >
      <Field label="ntfy topic override">
        {(id) => (
          <div className="flex gap-2">
            <input
              id={id}
              className="input-base max-w-xs"
              placeholder="Default topic when empty"
              value={topicOverride}
              onChange={(event) => setTopicOverride(event.target.value)}
            />
            <button type="submit" className="btn-secondary" disabled={updateMe.isPending}>
              Save
            </button>
          </div>
        )}
      </Field>
    </form>
  );
}

export function ProfilePage() {
  const { data: me } = useMe();
  const updateMe = useUpdateMe();
  const testNotification = useTestNotification();
  const mintApiToken = useMintApiToken();
  const { notify } = useToast();
  const [apiToken, setApiToken] = useState('');

  // App only renders routes once the session probe (the same query) succeeded.
  if (!me) return null;

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="mb-6 text-2xl font-bold">Profile</h1>

      <div className="card mb-6 p-6">
        <h2 className="mb-4 font-semibold">Account</h2>
        <dl className="grid grid-cols-[8rem_1fr] gap-y-2 text-sm">
          <dt className="text-stone-500">Display name</dt>
          <dd>{me.display_name}</dd>
          <dt className="text-stone-500">Email</dt>
          <dd>{me.email}</dd>
        </dl>
        <p className="mt-3 text-xs text-stone-400">Identity is managed by your SSO provider.</p>
      </div>

      <div className="card p-6">
        <h2 className="mb-4 flex items-center gap-2 font-semibold">
          <Bell className="h-5 w-5 text-emerald-600" />
          Notifications
        </h2>
        <DevicePushSection />
        <label className="mb-4 flex items-center gap-3 text-sm">
          <input
            type="checkbox"
            checked={me.ntfy_enabled}
            onChange={(event) =>
              updateMe.mutate(
                { ntfy_enabled: event.target.checked },
                { onSuccess: () => notify('Notification settings saved') },
              )
            }
          />
          Send me ntfy push notifications for overdue reminders
        </label>

        <TopicOverrideForm key={me.ntfy_topic_override ?? ''} me={me} />

        <button
          type="button"
          className="btn-primary"
          disabled={testNotification.isPending}
          onClick={() =>
            testNotification.mutate(undefined, { onSuccess: () => notify('Test notification sent') })
          }
        >
          <Send className="h-4 w-4" />
          Send test notification
        </button>
      </div>

      <div className="card mt-6 p-6">
        <h2 className="mb-1 flex items-center gap-2 font-semibold">
          <Key className="h-5 w-5 text-emerald-600" />
          API token
        </h2>
        <p className="mb-4 text-sm text-stone-500">
          A bearer token for scripts that call the API without a browser. Valid for 90 days and shown
          only once — copy it now. Send it as <code>Authorization: Bearer &lt;token&gt;</code>.
        </p>

        {apiToken ? (
          <div className="flex gap-2">
            <input className="input-base font-mono text-xs" aria-label="API token" readOnly value={apiToken} />
            <button
              type="button"
              className="btn-secondary"
              onClick={() =>
                // Clipboard access fails on plain http and in some embedded
                // browsers; only claim success once it actually happened.
                navigator.clipboard.writeText(apiToken).then(
                  () => notify('Token copied'),
                  () => notify('Copy failed: select the token and copy it manually', 'error'),
                )
              }
            >
              <Copy className="h-4 w-4" />
              Copy
            </button>
          </div>
        ) : (
          <button
            type="button"
            className="btn-primary"
            disabled={mintApiToken.isPending}
            onClick={() =>
              mintApiToken.mutate(undefined, { onSuccess: (res) => setApiToken(res.token) })
            }
          >
            <Key className="h-4 w-4" />
            Generate token
          </button>
        )}
      </div>
    </div>
  );
}
