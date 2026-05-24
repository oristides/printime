# Google Calendar

Print today's agenda (or the next few days) from Google Calendar using a **private ICS link**. No OAuth setup required.

## One-time setup

### 1. Get your private calendar URL

1. Open [Google Calendar](https://calendar.google.com)
2. Click the **gear** → **Settings**
3. Select your calendar under **Settings for my calendars**
4. Scroll to **Integrate calendar**
5. Copy **Secret address in iCal format** (starts with `https://calendar.google.com/calendar/ical/...`)

Keep this URL private — anyone with it can read your calendar.

### 2. Add to `.env`

```env
GOOGLE_CALENDAR_ICS_URL=https://calendar.google.com/calendar/ical/YOUR_EMAIL/private-SECRET/basic.ics
GOOGLE_CALENDAR_TIMEZONE=America/Sao_Paulo
```

`GOOGLE_CALENDAR_TIMEZONE` is optional; defaults to your system timezone.

## Print today's agenda

```bash
printime agenda --preview
printime agenda --yes
```

Example output on paper:

```
================================================
           TODAY — SATURDAY, MAY 23
================================================
09:00   Team standup
         Google Meet

12:30   Lunch with Ana

15:00   Dentist
         Rua Example 123

------------------------------------------------
              Google Calendar
================================================
```

## Options

```bash
printime agenda --preview              # today, confirm before print
printime agenda --yes                  # today, print immediately
printime agenda --days 3 --preview     # today + next 2 days
printime agenda --ics-url 'https://...'  # override .env URL
```

## Morning automation (cron)

Print your agenda every weekday at 7:00:

```bash
crontab -e
```

```cron
0 7 * * 1-5 /home/oriel/Documents/repos/random_projects/adhd/printime/.venv/bin/printime agenda --yes
```

Combine with Anytype:

```cron
0 7 * * 1-5 /home/oriel/Documents/repos/random_projects/adhd/printime/.venv/bin/printime agenda --yes && /home/oriel/Documents/repos/random_projects/adhd/printime/.venv/bin/printime anytype print "Today" --yes
```

## Multiple calendars

Google's secret ICS URL is usually for **one calendar**. To merge calendars:

1. In Google Calendar settings, create a new calendar called **Print**
2. In each source calendar → **Event settings** → show events from other calendars, or
3. Use Google Calendar's **Import** / subscribe flow, or
4. Put multiple ICS URLs in separate cron lines (future: `printime agenda --all`)

For now, point `GOOGLE_CALENDAR_ICS_URL` at the calendar you care about most (often your primary one already shows everything).

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Set GOOGLE_CALENDAR_ICS_URL` | Add the secret ICS URL to `.env` |
| Wrong times | Set `GOOGLE_CALENDAR_TIMEZONE` |
| Empty agenda but events exist | Events may be on another calendar — use that calendar's ICS URL |
| HTTP 404 | Regenerate the secret link in Google Calendar settings |

## Privacy

- The ICS URL is a long-lived secret — treat it like a password
- Do not commit `.env` to git
- `printime serve` webhooks are separate; this feature only **reads** your calendar
