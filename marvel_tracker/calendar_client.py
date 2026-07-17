"""Create/update events on a dedicated iCloud calendar via CalDAV.

Writing directly to iCloud (rather than publishing a subscribed .ics feed)
gets real, editable calendar events that sync to the iPhone through the
normal iCloud path, and lets a later run edit an event in place — by a
stable UID — when Marvel changes a release date.
"""

import datetime as dt

import caldav
from caldav.lib.error import NotFoundError
from icalendar import Calendar, Event

from . import config


def connect():
    client = caldav.DAVClient(
        url=config.ICLOUD_CALDAV_URL,
        username=config.ICLOUD_APPLE_ID,
        password=config.ICLOUD_APP_SPECIFIC_PASSWORD,
    )
    return client.principal()


def get_or_create_calendar(principal, name=None):
    name = name or config.ICLOUD_CALENDAR_NAME
    for calendar in principal.calendars():
        if calendar.name == name:
            return calendar
    return principal.make_calendar(name=name)


def _build_ical(uid, title, date_str, description):
    calendar = Calendar()
    calendar.add("prodid", "-//marvel_tracker//ImaginariumOzone//EN")
    calendar.add("version", "2.0")

    event = Event()
    event.add("uid", uid)
    event.add("summary", title)
    event.add("dtstart", dt.date.fromisoformat(date_str))
    event.add("dtstamp", dt.datetime.utcnow())
    if description:
        event.add("description", description)

    calendar.add_component(event)
    return calendar.to_ical()


def upsert_event(calendar, item_id, title, date_str, description=""):
    """Create the event if it's new, or move/rename it in place if changed.

    Returns "created", "updated", or "skipped" (no date yet to put on a
    calendar).
    """
    if not date_str:
        return "skipped"

    uid = f"marvel-tracker-{item_id}@imaginariumozone"
    try:
        existing = calendar.event_by_uid(uid)
    except NotFoundError:
        existing = None

    ical = _build_ical(uid, title, date_str, description)
    if existing is None:
        calendar.save_event(ical)
        return "created"

    existing.data = ical
    existing.save()
    return "updated"
