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

Click any plant in these lists to jump to its detail page.

## Locations

Locations are the rooms or areas where your plants live (e.g. "Living room",
"Kitchen windowsill"). On the **Locations** page you can:

- **Add** a location with a name and optional description.
- **Rename** a location (pencil icon).
- **Delete** a location (trash icon). Plants in a deleted location are kept —
  they simply become "no location".

Each location shows how many plants it currently holds.

## Plants

### Adding a plant

Click **+ Add plant** on the Plants page. Fields:

- **Name** (required) — your name for the plant, e.g. "Kitchen Monstera".
- **Species** — start typing to search [FloraCodex](administration.md#floracodex-species-lookup-optional);
  pick a match to auto-fill the species and scientific name, or just type freely.
  (If species lookup isn't configured, the search returns nothing and you can
  still type a name manually.)
- **Scientific name** — e.g. *Monstera deliciosa*.
- **Location** — choose an existing location, or leave as "No location".
- **Tags** — comma-separated, e.g. `tropical, low-light`. Used for filtering.
- **Notes** — free text.
- **Photo** — optionally attach one photo at creation; you can add more later.

### Browsing and filtering

The **Plants** page shows a card per plant with its cover photo (or a
placeholder), name, species, location, tags, and a "watered X days ago"
indicator. You can:

- **Search** by name or species.
- **Filter by location**.
- **Filter by tag** (the dropdown lists every tag currently in use).

### Plant detail

Open a plant to see everything about it and to take action:

- **Header** — cover photo, name, scientific name, location, tags, notes.
- **Edit** — change any plant field.
- **Delete** — removes the plant **and** its photos, care logs and reminders.
- **Care summary** — days since last Watered / Fertilised / Repotted.
- **Quick-log buttons** — **Water**, **Fertilise**, **Repot**, or **+ Custom**
  for any other event type. Logging shows a confirmation and updates the summary
  immediately.
- **Photos** — upload images, set any photo as the **cover** (star icon), or
  delete photos. Deleting the cover photo just clears the cover.
- **Care log** — a timeline of all events, filterable by type and paginated.
  Delete individual entries with the trash icon.
- **Reminders** — list, add, enable/disable, and delete reminders for the plant.

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

## Calendar

The **Calendar** shows a month at a time. Days with upcoming care show a count
badge; overdue items appear on today. Click a day to list exactly which plants
are due and for what. Use the arrows to change month.

## Notifications (Profile)

On the **Profile** page:

- **Account** — your display name and email (read-only; managed by SSO).
- **Send me ntfy push notifications** — toggle to receive overdue-reminder
  pushes. Off by default.
- **ntfy topic override** — by default notifications go to the server's
  configured topic; set your own topic here to receive them on a personal
  channel.
- **Send test notification** — verifies your notification setup end to end.

### Receiving notifications

Notifications are delivered through [ntfy](https://ntfy.sh):

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
  the interval) or disable/delete the reminder.
