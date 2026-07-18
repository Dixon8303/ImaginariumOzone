"""Entry point: fetch current Marvel Studios release data, diff it against the
last known state, keep the iCloud calendar in sync, and notify on anything
new or changed.

Run as: python -m marvel_tracker.tracker
"""

import json
import os

import yaml

from . import calendar_client, config, notifier, tmdb_client


def load_tracked_ids():
    if not os.path.exists(config.TRACKED_IDS_FILE):
        return {}
    with open(config.TRACKED_IDS_FILE) as f:
        return yaml.safe_load(f) or {}


def load_state():
    if not os.path.exists(config.STATE_FILE):
        return {}
    with open(config.STATE_FILE) as f:
        return json.load(f)


def save_state(state):
    with open(config.STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def diff_items(items, state):
    """Return (new_items, changed_items) versus the last known state."""
    new_items = []
    changed_items = []
    for item in items:
        previous = state.get(item["item_id"])
        if previous is None:
            new_items.append(item)
        elif previous.get("date") != item["date"]:
            changed_items.append((item, previous.get("date")))
    return new_items, changed_items


def describe(item):
    label = {"movie": "Movie", "episode": "Episode", "special": "Special"}[item["kind"]]
    date = item["date"] or "no date yet"
    return f"{label}: {item['title']} — {date}"


def main():
    config.validate()

    tracked_ids = load_tracked_ids()
    state = load_state()

    items = tmdb_client.fetch_all_items(tracked_ids)
    new_items, changed_items = diff_items(items, state)

    if new_items or changed_items:
        principal = calendar_client.connect()
        calendar = calendar_client.get_or_create_calendar(principal)

        lines = []
        for item in new_items:
            calendar_client.upsert_event(
                calendar, item["item_id"], item["title"], item["date"]
            )
            lines.append(f"NEW — {describe(item)}")

        for item, previous_date in changed_items:
            calendar_client.upsert_event(
                calendar, item["item_id"], item["title"], item["date"]
            )
            lines.append(
                f"UPDATED — {describe(item)} (was {previous_date or 'no date'})"
            )

        message = "\n".join(lines)
        print(message)
        notifier.notify(title=f"Marvel Tracker: {len(lines)} update(s)", message=message)
    else:
        print("No new or changed Marvel Studios releases.")

    for item in items:
        state[item["item_id"]] = {"title": item["title"], "date": item["date"]}
    save_state(state)


if __name__ == "__main__":
    main()
