# Google Calendar

Print today's agenda (or upcoming days/week) using a **private ICS link**. No OAuth.

## Setup

### 1. Get secret ICS URL

**Sidebar method (often easiest):**

1. [Google Calendar](https://calendar.google.com) on **desktop**
2. Left sidebar → hover your calendar → **⋮** → **Settings and sharing**
3. **Integrate calendar** → copy **Secret address in iCal format**

**Or:** Settings → **Settings for my calendars** → your calendar → **Integrate calendar**

Direct link (replace email):

`https://calendar.google.com/calendar/u/0/r/settings/calendar/YOUR@gmail.com`

Use the **secret** URL (`private-...`), not the public one.

### 2. Add to `.env`

```env
GOOGLE_CALENDAR_ICS_URL=https://calendar.google.com/calendar/ical/.../private-.../basic.ics
GOOGLE_CALENDAR_TIMEZONE=America/Sao_Paulo
```

## Commands

```bash
printime agenda --today --preview      # explicit today
printime agenda --preview              # today (default)
printime agenda --yes                  # print today
printime agenda --days 3 --preview     # today + 2 days
printime agenda --days 7 --preview     # this week from today
printime agenda --next-week --preview  # upcoming Mon–Sun week
printime agenda --next-week --yes
printime agenda --ics-url 'https://...'  # override .env
```

Printed agendas include a generated `YYYY-MM-DD HH:MM` line below the title. Events include time, title, location, and notes/details from the calendar description when present.

## Example on paper

```
================================================
           TODAY — MONDAY, MAY 26
              2026-05-25 12:21
================================================
17:00   Meeting
         Location: Google Meet
         Discuss blockers

21:30   Gym

------------------------------------------------
              Google Calendar
================================================
```

## Morning cron

```cron
0 7 * * 1-5 /home/oriel/.local/bin/printime agenda --yes
```

Combine with Anytype:

```cron
0 7 * * 1-5 /home/oriel/.local/bin/printime agenda --yes && /home/oriel/.local/bin/printime anytype print "Today" --yes
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Set GOOGLE_CALENDAR_ICS_URL` | Add URL to `.env` in repo root |
| Wrong times | Set `GOOGLE_CALENDAR_TIMEZONE` |
| Empty today but events exist | Events may be on another calendar — use its ICS URL |
| Can't find secret URL | Use desktop browser; work accounts may hide it |

## Privacy

Treat the ICS URL like a password. Never commit `.env`.
