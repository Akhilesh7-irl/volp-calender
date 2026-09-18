import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]

credentials_file = os.environ["GOOGLE_CREDENTIALS_FILE"]
calendar_id = os.environ["GOOGLE_CALENDAR_ID"]

credentials = service_account.Credentials.from_service_account_file(
    credentials_file,
    scopes=SCOPES
)

service = build("calendar", "v3", credentials=credentials)

events = service.events().list(
    calendarId=calendar_id,
    maxResults=2500,
    singleEvents=True
).execute()

items = events.get("items", [])

volp_events = []

for event in items:
    private_properties = event.get("extendedProperties", {}).get("private", {})

    if "volp_assignment_id" in private_properties:
        volp_events.append(event)

print(f"VOLP events found: {len(volp_events)}")
print()

for event in volp_events:
    print("Event ID:", event.get("id"))
    print("Title:", event.get("summary"))
    print("Start:", event.get("start"))
    print("End:", event.get("end"))
    print(
        "VOLP ID:",
        event.get("extendedProperties", {})
        .get("private", {})
        .get("volp_assignment_id")
    )
    print("-" * 50)