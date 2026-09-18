import json

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from volp_client import VolpClient
from calendar_client import CalendarClient


SYNC_FILE = Path(
    "synced_assignments.json"
)

TIMEZONE = ZoneInfo(
    "Asia/Kolkata"
)


def load_synced():

    if not SYNC_FILE.exists():
        return {}

    try:

        with open(
            SYNC_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return {}


def save_synced(synced):

    with open(
        SYNC_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            synced,
            file,
            indent=4
        )


def main():

    print(
        "Starting VOLP Calendar Sync..."
    )

    print()

    volp = VolpClient()

    assignments = (
        volp.get_all_assignments()
    )

    print()

    print(
        f"Total assignments found: "
        f"{len(assignments)}"
    )

    calendar = CalendarClient()

    synced = load_synced()

    now = datetime.now(
        TIMEZONE
    )

    created = 0
    updated = 0
    unchanged = 0
    skipped = 0
    failed = 0

    for assignment in assignments:

        assignment_id = assignment[
            "ass_id"
        ]

        due = assignment[
            "due_datetime"
        ]

        print()

        print(
            f"{assignment['course']}"
        )

        print(
            f"  {assignment['topic']}"
        )

        print(
            f"  Due: {due}"
        )

        # Ignore assignments whose deadline
        # has already passed.
        if due <= now:

            print(
                "  Skipping - deadline passed"
            )

            skipped += 1

            continue

        try:

            status, event = (
                calendar.sync_assignment(
                    assignment
                )
            )

            if status == "created":

                print(
                    "  Added to Google Calendar"
                )

                created += 1

            elif status == "updated":

                print(
                    "  Updated Google Calendar event"
                )

                updated += 1

            else:

                print(
                    "  Already up to date"
                )

                unchanged += 1

            synced[assignment_id] = {
                "course": assignment[
                    "course"
                ],

                "topic": assignment[
                    "topic"
                ],

                "due": due.isoformat(),

                "google_event_id": event[
                    "id"
                ]
            }

        except Exception as error:

            print(
                f"  Failed: {error}"
            )

            failed += 1

    save_synced(synced)

    print()

    print("=" * 50)

    print("Sync complete")

    print(
        f"Created:   {created}"
    )

    print(
        f"Updated:   {updated}"
    )

    print(
        f"Unchanged:  {unchanged}"
    )

    print(
        f"Skipped:    {skipped}"
    )

    print(
        f"Failed:     {failed}"
    )

    print("=" * 50)


if __name__ == "__main__":

    main()