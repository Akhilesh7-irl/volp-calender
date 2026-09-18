import os

from datetime import timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = [
    "https://www.googleapis.com/auth/calendar"
]

TIMEZONE = "Asia/Kolkata"


class CalendarClient:

    def __init__(self):

        credentials_file = os.environ[
            "GOOGLE_CREDENTIALS_FILE"
        ]

        calendar_id = os.environ[
            "GOOGLE_CALENDAR_ID"
        ]

        credentials = (
            service_account.Credentials
            .from_service_account_file(
                credentials_file,
                scopes=SCOPES
            )
        )

        self.service = build(
            "calendar",
            "v3",
            credentials=credentials
        )

        self.calendar_id = calendar_id

    def get_event(self, assignment_id):
        event_id = make_event_id(assignment_id)

        try:
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            if event.get("status") == "cancelled":
                return None

            return event

        except HttpError as error:
            if error.resp.status == 404:
                return None
            raise

    def create_event(self, assignment):

        assignment_id = assignment["ass_id"]

        due = assignment["due_datetime"]

        start = due - timedelta(
            minutes=15
        )

        title = (
            f"{assignment['course']} - "
            f"{assignment['topic']}"
        )

        description = (
            f"Course: {assignment['course']}\n\n"
            f"Topic: {assignment['topic']}\n\n"
            f"Assignment:\n"
            f"{assignment['assignment_text']}\n\n"
            f"VOLP Assignment ID: {assignment_id}"
        )

        event = {
            "id": make_event_id(
                assignment_id
            ),

            "summary": title,

            "description": description,

            "start": {
                "dateTime": start.isoformat(),
                "timeZone": TIMEZONE
            },

            "end": {
                "dateTime": due.isoformat(),
                "timeZone": TIMEZONE
            },

            "reminders": {
                "useDefault": False,

                "overrides": [
                    {
                        "method": "popup",
                        "minutes": 24 * 60
                    },
                    {
                        "method": "popup",
                        "minutes": 60
                    }
                ]
            },

            "extendedProperties": {
                "private": {
                    "volp_assignment_id":
                        assignment_id
                }
            }
        }

        return (
            self.service.events()
            .insert(
                calendarId=self.calendar_id,
                body=event
            )
            .execute()
        )

    def update_event(
        self,
        existing_event,
        assignment
    ):

        assignment_id = assignment["ass_id"]

        due = assignment["due_datetime"]

        start = due - timedelta(
            minutes=15
        )

        title = (
            f"{assignment['course']} - "
            f"{assignment['topic']}"
        )

        description = (
            f"Course: {assignment['course']}\n\n"
            f"Topic: {assignment['topic']}\n\n"
            f"Assignment:\n"
            f"{assignment['assignment_text']}\n\n"
            f"VOLP Assignment ID: {assignment_id}"
        )

        existing_event["summary"] = title

        existing_event["description"] = (
            description
        )

        existing_event["start"] = {
            "dateTime": start.isoformat(),
            "timeZone": TIMEZONE
        }

        existing_event["end"] = {
            "dateTime": due.isoformat(),
            "timeZone": TIMEZONE
        }

        existing_event["reminders"] = {
            "useDefault": False,

            "overrides": [
                {
                    "method": "popup",
                    "minutes": 24 * 60
                },
                {
                    "method": "popup",
                    "minutes": 60
                }
            ]
        }

        return (
            self.service.events()
            .update(
                calendarId=self.calendar_id,
                eventId=existing_event["id"],
                body=existing_event
            )
            .execute()
        )

    def sync_assignment(self, assignment):

        assignment_id = assignment["ass_id"]

        existing_event = self.get_event(
            assignment_id
        )

        if existing_event is None:

            event = self.create_event(
                assignment
            )

            return "created", event

        if event_needs_update(
            existing_event,
            assignment
        ):

            event = self.update_event(
                existing_event,
                assignment
            )

            return "updated", event

        return "unchanged", existing_event


def event_needs_update(
    event,
    assignment
):

    due = assignment["due_datetime"]

    start = due - timedelta(
        minutes=15
    )

    expected_title = (
        f"{assignment['course']} - "
        f"{assignment['topic']}"
    )

    expected_description = (
        f"Course: {assignment['course']}\n\n"
        f"Topic: {assignment['topic']}\n\n"
        f"Assignment:\n"
        f"{assignment['assignment_text']}\n\n"
        f"VOLP Assignment ID: "
        f"{assignment['ass_id']}"
    )

    current_start = (
        event.get("start", {})
        .get("dateTime")
    )

    current_end = (
        event.get("end", {})
        .get("dateTime")
    )

    current_title = event.get(
        "summary",
        ""
    )

    current_description = event.get(
        "description",
        ""
    )

    expected_start = start.isoformat()
    expected_end = due.isoformat()

    if current_title != expected_title:
        return True

    if current_description != expected_description:
        return True

    if current_start != expected_start:
        return True

    if current_end != expected_end:
        return True

    return False


def make_event_id(assignment_id):

    value = str(assignment_id)

    event_id = (
        "volp2" +
        value.encode().hex()
    )

    return event_id