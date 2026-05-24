#!/usr/bin/env python3
"""Google Calendar integration via private ICS feed."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

USER_AGENT = 'Mozilla/5.0 (compatible; Printime/0.1)'


@dataclass
class CalendarEvent:
    summary: str
    start: datetime
    end: datetime
    all_day: bool
    location: str = ''
    description: str = ''


def _local_timezone() -> ZoneInfo:
    try:
        key = datetime.now().astimezone().tzinfo.key  # type: ignore[attr-defined]
        return ZoneInfo(key)
    except Exception:
        return ZoneInfo('UTC')


def get_calendar_config() -> Dict[str, Optional[str]]:
    from printime.config import get_env, load_env

    load_env()
    return {
        'ics_url': get_env('GOOGLE_CALENDAR_ICS_URL'),
        'timezone': get_env('GOOGLE_CALENDAR_TIMEZONE'),
    }


def fetch_ics(url: str, timeout: int = 30) -> str:
    req = Request(url, headers={'User-Agent': USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or 'utf-8'
    return raw.decode(charset, errors='replace')


def _unfold_ics_lines(text: str) -> List[str]:
    lines: List[str] = []
    for line in text.splitlines():
        if line.startswith((' ', '\t')) and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line.rstrip('\r'))
    return lines


def _parse_ics_property(line: str) -> tuple[str, str, Dict[str, str]]:
    if ':' not in line:
        return line, '', {}
    head, value = line.split(':', 1)
    parts = head.split(';')
    name = parts[0].upper()
    params: Dict[str, str] = {}
    for part in parts[1:]:
        if '=' in part:
            key, param_value = part.split('=', 1)
            params[key.upper()] = param_value
    return name, value, params


def _decode_ics_text(value: str) -> str:
    value = value.replace('\\n', '\n').replace('\\,', ',').replace('\\;', ';').replace('\\\\', '\\')
    return value.strip()


def _parse_ics_datetime(value: str, params: Dict[str, str], tz: ZoneInfo) -> tuple[datetime, bool]:
    if params.get('VALUE') == 'DATE' or re.fullmatch(r'\d{8}', value):
        day = datetime.strptime(value[:8], '%Y%m%d').date()
        start = datetime.combine(day, datetime.min.time(), tzinfo=tz)
        return start, True

    if value.endswith('Z'):
        dt = datetime.strptime(value, '%Y%m%dT%H%M%SZ').replace(tzinfo=ZoneInfo('UTC'))
        return dt.astimezone(tz), False

    tzid = params.get('TZID')
    event_tz = ZoneInfo(tzid) if tzid else tz
    dt = datetime.strptime(value, '%Y%m%dT%H%M%S').replace(tzinfo=event_tz)
    return dt.astimezone(tz), False


def parse_ics_events(ics_text: str, tz: ZoneInfo) -> List[CalendarEvent]:
    events: List[CalendarEvent] = []
    blocks = re.split(r'(?=BEGIN:VEVENT)', ics_text)
    for block in blocks:
        if 'BEGIN:VEVENT' not in block:
            continue

        summary = ''
        location = ''
        description = ''
        start: Optional[datetime] = None
        end: Optional[datetime] = None
        all_day = False
        status = ''

        for line in _unfold_ics_lines(block):
            if not line or line.startswith('BEGIN:') or line.startswith('END:'):
                continue
            name, value, params = _parse_ics_property(line)
            value = _decode_ics_text(value)
            if name == 'SUMMARY':
                summary = value
            elif name == 'LOCATION':
                location = value
            elif name == 'DESCRIPTION':
                description = value
            elif name == 'STATUS':
                status = value.upper()
            elif name == 'DTSTART':
                start, all_day = _parse_ics_datetime(value, params, tz)
            elif name == 'DTEND':
                end, end_all_day = _parse_ics_datetime(value, params, tz)
                all_day = all_day or end_all_day

        if status == 'CANCELLED' or start is None:
            continue
        if not summary:
            summary = '(No title)'
        if end is None:
            end = start + (timedelta(days=1) if all_day else timedelta(hours=1))

        events.append(CalendarEvent(
            summary=summary,
            start=start,
            end=end,
            all_day=all_day,
            location=location,
            description=description,
        ))

    events.sort(key=lambda event: (event.start, event.summary.lower()))
    return events


def _event_on_day(event: CalendarEvent, day: date) -> bool:
    day_start = datetime.combine(day, datetime.min.time(), tzinfo=event.start.tzinfo)
    day_end = day_start + timedelta(days=1)
    if event.all_day:
        event_end = event.end
        if event.end.time() == datetime.min.time() and event.end > event.start:
            event_end = event.end
        return event.start.date() <= day < event.end.date()
    return event.start < day_end and event.end > day_start


def _format_event_time(event: CalendarEvent) -> str:
    if event.all_day:
        return 'All day'
    return event.start.strftime('%H:%M')


def _format_day_title(day: date) -> str:
    if day == date.today():
        return f"Today — {day.strftime('%A, %b %d')}"
    return day.strftime('%A, %b %d')


def next_week_start(today: Optional[date] = None) -> date:
    """Monday that starts the upcoming calendar week."""
    today = today or date.today()
    days_ahead = (7 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def events_for_day(events: List[CalendarEvent], day: date) -> List[CalendarEvent]:
    return [event for event in events if _event_on_day(event, day)]


def agenda_to_context(
    ics_url: str,
    width: int = 48,
    days: int = 1,
    timezone: Optional[str] = None,
    start_day: Optional[date] = None,
) -> Dict[str, Any]:
    tz = ZoneInfo(timezone) if timezone else _local_timezone()
    ics_text = fetch_ics(ics_url)
    events = parse_ics_events(ics_text, tz)

    start = start_day or date.today()
    day_sections: List[Dict[str, Any]] = []

    for offset in range(max(days, 1)):
        day = start + timedelta(days=offset)
        day_events = events_for_day(events, day)
        day_events.sort(key=lambda event: (event.all_day, event.start, event.summary.lower()))
        day_sections.append({
            'date': day.strftime('%A, %B %d, %Y'),
            'label': _format_day_title(day),
            'events': [
                {
                    'time': _format_event_time(event),
                    'title': event.summary,
                    'location': event.location,
                    'all_day': event.all_day,
                }
                for event in day_events
            ],
        })

    if days == 1:
        title = day_sections[0]['label']
    elif days == 7 and start.weekday() == 0:
        end = start + timedelta(days=6)
        title = f"Week of {start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"
    else:
        title = f"Agenda — {day_sections[0]['label']} +{days - 1}d"

    total_events = sum(len(section['events']) for section in day_sections)
    return {
        'template': 'agenda',
        'title': title,
        'days': day_sections,
        'event_count': total_events,
        'empty_message': 'No events scheduled.',
        'source': 'Google Calendar',
    }


def print_agenda(
    preview: bool = False,
    yes: bool = False,
    days: int = 1,
    ics_url: Optional[str] = None,
    timezone: Optional[str] = None,
    start_day: Optional[date] = None,
    config: Optional[Dict[str, Any]] = None,
) -> bool:
    from printime.cli import create_printer, finish_job, load_config, print_rendered, render_for_print
    from printime.preview import confirm, render_template_preview

    cfg = config or load_config()
    cal_cfg = get_calendar_config()
    url = ics_url or cal_cfg.get('ics_url')
    if not url:
        print('Set GOOGLE_CALENDAR_ICS_URL in .env (see docs/GCAL.md)', file=sys.stderr)
        return False

    try:
        context = agenda_to_context(
            url,
            width=cfg['printer']['width'],
            days=days,
            timezone=timezone or cal_cfg.get('timezone'),
            start_day=start_day,
        )
    except Exception as exc:
        print(f'Failed to load calendar: {exc}', file=sys.stderr)
        return False

    if preview:
        rendered = render_template_preview('agenda', context)
        print(rendered)
        if yes or confirm('Print this?'):
            printer = create_printer(cfg)
            try:
                result = render_for_print('agenda', context, cfg)
                if result:
                    print_rendered(printer, result)
                    print(f"Agenda printed ({context['event_count']} events)")
            finally:
                finish_job(printer)
        else:
            print('Cancelled')
        return True

    printer = create_printer(cfg)
    try:
        result = render_for_print('agenda', context, cfg)
        if result:
            print_rendered(printer, result)
            print(f"Agenda printed ({context['event_count']} events)")
    finally:
        finish_job(printer)
    return True
