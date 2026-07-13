# User Guide

How to use Green Thumb day to day. For installation and configuration, see
[setup.md](setup.md) and [administration.md](administration.md).

> **Shared instance.** Everyone who can sign in shares the same plants,
> locations, logs and reminders. Changes you make are visible to all other
> users.

## Signing in

Green Thumb uses single sign-on (SSO). When you open the app you're redirected
to your organisation's Zitadel login page; after signing in you land on the
**Dashboard**. There is no separate Green Thumb password — your account is
created automatically on first login.

To sign out, use **Sign out** at the bottom of the sidebar. This clears your
session and returns you to the login page.

## Dashboard

The landing page summarises what needs attention:

- **Overdue** — reminders whose plants haven't been cared for within their
  interval (or have no matching care event yet).
- **Next 7 days** — reminders coming due soon.
- **Recently watered** — the latest waterings across all plants.
- **Counts** — total plants and locations.

Each row shows the event type as a colored chip (blue = watering, violet =
fertilising, orange = repotting) so you can tell at a glance what's due, even
on a phone.

Click any plant in these lists to jump to its detail page — or act right
here: every overdue/upcoming row has a **Done** button that logs the care
event, an **alarm-clock** button that snoozes the reminder (see
[Reminders](#reminders)), and when several plants have overdue watering a
**Water all** button logs them in one go.

## Locations

Locations are the rooms or areas where your plants live (e.g. "Living room",
"Kitchen windowsill"). On the **Locations** page you can:

- **Add** a location with a name and optional description.
- **Rename** a location (pencil icon).
- **Delete** a location (trash icon). Plants in a deleted location are kept —
  they simply become "no location".

Each location shows how many plants it currently holds.

## Species

Species hold the care knowledge that is shared by every plant of the same
kind, so you enter it once instead of per plant. On the **Species** page you
can add, search, edit and delete species. A species stores:

- **Name** and **scientific name**.
- **Care advice** — light, watering, soil & repotting hints.
- **Deadheading** — whether the species needs it, with an optional hint.
- **Toxicity** — e.g. "Toxic to cats and dogs" (shown as a red badge).
- **Common issues** — free text describing typical illnesses and how to spot
  them (e.g. "Spider mites: fine webbing under leaves").
- **Default care plan** — default reminder intervals (watering, fertilising,
  repotting).

Linking a plant to a species shows all of this as a **Care guide** on the
plant's detail page. When you create a plant with a species, the species'
default care plan is materialised as that plant's reminders automatically;
you can still tune every interval per plant afterwards — changing the species
never touches existing plants' reminders. For older plants, use **Apply
default care plan** in the care guide (it only adds what's missing).

Deleting a species keeps its plants; they just lose the link.

## Plants

### Adding a plant

Click **+ Add plant** on the Plants page. Fields:

- **Name** (required) — your name for the plant, e.g. "Kitchen Monstera".
- **Species** — pick one from your species library, create one inline with
  **New**, or leave it empty and use the free-text species fields instead.
- **Location** — choose an existing location, or leave as "No location".
- **Tags** — comma-separated, e.g. `tropical, low-light`. Used for filtering.
- **Notes** — free text.
- **Photo** — optionally attach one photo at creation; you can add more later.

### Browsing and filtering

The **Plants** page shows a card per plant with its cover photo (or a
placeholder), name, species, location, tags, and a "watered X days ago"
indicator. When a care action is due, the card shows a colored chip (e.g.
**Water due**), so you can spot what a plant needs even when browsing a
single room or tag. You can:

- **Search** by name or species (including the linked species' names).
- **Filter by location**.
- **Filter by tag** (the dropdown lists every tag currently in use).
- **Sort** by name, longest-unwatered first, or recently-watered first.

### Plant detail

Open a plant to see everything about it and to take action:

- **Header** — cover photo, name, species/scientific name, location, tags, notes.
- **Edit** — change any plant field.
- **Delete** — removes the plant **and** its photos, care logs and reminders.
- **Care guide** — the linked species' advice (light, watering, soil,
  deadheading, toxicity, common issues) plus **Apply default care plan**.
- **Care cards** — one tappable card per standard care type (**Water**,
  **Fertilise**, **Repot**) showing when it was last done and, if a reminder
  is configured, whether it's due or snoozed. Tap the card to log the event;
  the confirmation toast offers **Undo** in case of an accidental tap. Use
  **+ Custom** for any other event type.
- **Photos** — upload one or several images at once, set any photo as the
  **cover** (star icon), or delete photos (asks for confirmation). Deleting
  the cover photo just clears the cover.
- **Growth journal** — photos and care events merged into one month-by-month
  timeline of the plant's life.
- **Care log** — a timeline of all events, filterable by type and paginated.
  Deleting an entry offers **Undo** in the confirmation toast.
- **Reminders** — list, add, enable/disable, snooze, and delete reminders.
  Each reminder shows when it next fires ("due in 3 days", "due today",
  overdue, or "snoozed until …"). The event picker offers the standard types;
  choose **Custom…** for anything else. Deleting offers **Undo**.

## Logging care

Use the quick-log buttons on a plant's detail page for the common events
(watering, fertilising, repotting). For anything else, use **+ Custom** and
enter your own event type (e.g. "misting", "pruning") plus optional notes.

Logged events default to "now", but a custom entry lets you set a date/time, so
you can **backdate** events you forgot to record.

## Reminders

A reminder watches one event type on one plant and a number of days
(`interval_days`). The plant becomes **overdue** when:

- there is no matching care event yet, **or**
- the most recent matching event is older than the interval.

Overdue and upcoming reminders appear on the **Dashboard** and **Calendar**.
If you've enabled notifications (below), you also get a push when a reminder is
overdue. Disable a reminder (uncheck "enabled") to keep it without it firing.

Example: a watering reminder with an interval of 7 days notifies you once the
plant hasn't been watered for more than a week.

### Snoozing

Sometimes a reminder is due but the action isn't actually needed — the soil
is still wet, say. Instead of logging a watering that never happened, use the
**alarm-clock** button (on a dashboard row or in the plant's reminders
section) to **snooze** the reminder for one interval. A snoozed reminder
leaves the overdue list, stops notifying, and reappears under "Next 7 days"
labeled **snoozed** so it doesn't silently vanish. Logging the care event, or
the snooze expiring, brings the reminder back to its normal schedule; the
alarm-clock-off button cancels a snooze early.

## Calendar

The **Calendar** shows a month at a time. Days with upcoming care show a count
badge; overdue items appear on today. Click a day to list exactly which plants
are due and for what. Use the arrows to change month.

## Installing the app (PWA)

Green Thumb is an installable web app: add it to your phone's home screen (or
install it from the browser menu on desktop) and it opens full-screen like a
native app, with the shell available even while briefly offline. On iPhone use
Safari's **Share → Add to Home Screen** — this is also required for push
notifications on iOS.

## Notifications (Profile)

On the **Profile** page:

- **Account** — your display name and email (read-only; managed by SSO).
- **Push notifications on this device** — **Enable on this device** to get
  native notifications on this browser/phone, no extra app needed. Shown only
  when the administrator has configured Web Push. Disable it again on the
  same device at any time.
- **Send me ntfy push notifications** — toggle to receive overdue-reminder
  pushes via ntfy. Off by default.
- **ntfy topic override** — by default notifications go to the server's
  configured topic; set your own topic here to receive them on a personal
  channel.
- **Send test notification** — verifies your notification setup end to end,
  over every channel you have enabled.

### Native push (Web Push)

1. On iPhone: install the app to your home screen first (see above), then
   open it from there. Android and desktop browsers work directly.
2. Tap **Enable on this device** on the Profile page and allow notifications.
3. **Send test notification** to confirm.

### ntfy

Notifications can also be delivered through [ntfy](https://ntfy.sh):

1. Install the ntfy app (iOS/Android) or open the ntfy web app.
2. Subscribe to the topic — either the server's default topic (ask your
   administrator) or your personal **topic override**.
3. Enable notifications on the Profile page and click **Send test
   notification** to confirm.

If the test fails, notifications aren't configured on the server side — see
[administration.md](administration.md#ntfy-push-notifications).

## Tips & FAQ

- **"watered today" vs the summary** — the plant card's indicator and the detail
  page's care summary both come from your logged care events; log a watering and
  they update right away.
- **I deleted a location by mistake** — recreate it and reassign the plants
  (edit each plant's location). Plants are never deleted with a location.
- **Why can I see someone else's plants?** — this is a shared household instance
  by design; everyone signed in manages the same collection.
- **A reminder won't stop notifying** — log the relevant care event (that resets
  the interval), snooze it if the action isn't needed yet, or disable/delete
  the reminder.
