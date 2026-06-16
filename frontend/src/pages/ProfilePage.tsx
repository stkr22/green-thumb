import { useEffect, useState } from 'react';
import { Bell, Send } from 'lucide-react';

import { useMe, useTestNotification, useUpdateMe } from '../api/hooks/useProfile';
import { useToast } from '../components/Toast';

export function ProfilePage() {
  const { data: me } = useMe();
  const updateMe = useUpdateMe();
  const testNotification = useTestNotification();
  const { notify } = useToast();
  const [topicOverride, setTopicOverride] = useState('');

  useEffect(() => {
    setTopicOverride(me?.ntfy_topic_override ?? '');
  }, [me?.ntfy_topic_override]);

  if (!me) {
    return <p className="text-stone-500">Loading profile…</p>;
  }

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

        <form
          className="mb-4"
          onSubmit={(event) => {
            event.preventDefault();
            updateMe.mutate(
              { ntfy_topic_override: topicOverride || null },
              { onSuccess: () => notify('Notification settings saved') },
            );
          }}
        >
          <label className="mb-1 block text-sm font-medium">ntfy topic override</label>
          <div className="flex gap-2">
            <input
              className="input-base max-w-xs"
              placeholder="Default topic when empty"
              value={topicOverride}
              onChange={(event) => setTopicOverride(event.target.value)}
            />
            <button type="submit" className="btn-secondary" disabled={updateMe.isPending}>
              Save
            </button>
          </div>
        </form>

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
    </div>
  );
}
