import os
import re
from zoneinfo import ZoneInfo
import requests
from datetime import datetime
from html import unescape


LOGIN_URL = "https://admin.volp.in/login/process"

COURSE_LIST_URL = (
    "https://learner.volp.in/"
    "learnerCourseDashboard/learnerCourseList"
)

HANDSON_URL = (
    "https://learner.volp.in/"
    "HandOnAssignment/getHandsOnDetails"
)
SUBJECTIVE_URL = "https://learner.volp.in/SubjectiveAssignment/getSubjectiveAssignment_new"


class VolpClient:

    def __init__(self):
        self.username = os.environ["VOLP_USERNAME"]
        self.password = os.environ["VOLP_PASSWORD"]

        self.session = requests.Session()

        self.token = None
        self.uid = None

    def login(self):
        payload = {
            "username": self.username,
            "pwd": self.password
        }

        response = self.session.post(
            LOGIN_URL,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        if data.get("flag") != "YES":
            raise Exception(f"VOLP login failed: {data}")

        self.token = data.get("token")
        self.uid = data.get("uid")

        if not self.token or not self.uid:
            raise Exception("VOLP did not return token or uid")

        print("VOLP login successful")

    def get_headers(self):
        return {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=UTF-8",
            "Device": "Web",
            "Token": self.token,
            "Uid": self.uid,
            "Ut": "Learner",
            "Origin": "https://classroom.volp.in",
            "Referer": "https://classroom.volp.in/"
        }

    def get_courses(self):
        response = self.session.post(
            COURSE_LIST_URL,
            headers=self.get_headers(),
            json={}
        )

        response.raise_for_status()

        data = response.json()

        if data.get("flag") != "YES":
            raise Exception(f"Could not get courses: {data}")

        courses = []

        for course in data.get("col_list", []):

            # Ignore archived/inactive courses
            if course.get("is_archived"):
                continue

            if not course.get("status"):
                continue

            course_id = course.get("crsid")
            learner_course_id = course.get("learnercoffid")

            course_name = (
                course.get("course", {}).get("course_name")
                or course.get("code")
                or "Unknown Course"
            )

            if not course_id or not learner_course_id:
                continue

            courses.append({
                "course_id": course_id,
                "course_offering_learner_id": learner_course_id,
                "name": course_name
            })

        return courses

    def get_assignments(self, course):
        payload = {
            "course_offering_learner_id":
                course["course_offering_learner_id"],

            "courseId":
                course["course_id"],

            "type": "content"
        }

        response = self.session.post(
            HANDSON_URL,
            headers=self.get_headers(),
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        assignments = self.extract_assignments(data)

        result = []

        for assignment in assignments:

            ass_id = assignment.get("ass_id")
            due_date = assignment.get("duedate")

            if not ass_id or not due_date:
                continue

            try:
                date_part, time_part, _ = due_date.split()

                due_datetime = datetime.strptime(
                    f"{date_part} {time_part}",
                    "%d-%m-%Y %H:%M"
                )

                due_datetime = due_datetime.replace(
                    tzinfo=ZoneInfo("Asia/Kolkata")
                )

            except ValueError:
                print(
                    f"Could not parse date: {due_date}"
                )
                continue

            topic = clean_html(
                assignment.get("topic", "")
            )

            assignment_text = clean_html(
                assignment.get("assignment_text", "")
            )

            result.append({
                "ass_id": str(ass_id),
                "course": course["name"],
                "course_id": course["course_id"],
                "topic": topic,
                "assignment_text": assignment_text,
                "due_datetime": due_datetime
            })

        return result
    def get_subjective_assignments(self, course):
        payload = {
            "courseId": course["course_id"],
            "course_offering_learner_id": course["course_offering_learner_id"],
            "type": "content"
        }

        response = self.session.post(
            SUBJECTIVE_URL,
            headers=self.get_headers(),
            json=payload,
            timeout=30
        )

        response.raise_for_status()
        data = response.json()

        result = []

        for assignment in data.get("question_list", []):
            ass_id = assignment.get("ass_id")
            due_date = assignment.get("due_date")

            if not ass_id or not due_date:
                continue

            try:
                date_part, time_part, _ = due_date.split()

                due_datetime = datetime.strptime(
                    f"{date_part} {time_part}",
                    "%d/%m/%Y %H:%M"
                )

                due_datetime = due_datetime.replace(
                    tzinfo=ZoneInfo("Asia/Kolkata")
                )

            except ValueError:
                print(f"Could not parse subjective date: {due_date}")
                continue

            question = clean_html(assignment.get("question", ""))

            result.append({
                "ass_id": str(ass_id),
                "course": course["name"],
                "course_id": course["course_id"],
                "topic": question,
                "assignment_text": question,
                "due_datetime": due_datetime
            })

        return result

    def extract_assignments(self, data):
        """
        VOLP's response structure can change slightly.
        Search recursively for dictionaries containing ass_id
        and duedate.
        """

        assignments = []

        def search(value):

            if isinstance(value, dict):

                if (
                    "ass_id" in value
                    and "duedate" in value
                ):
                    assignments.append(value)

                for child in value.values():
                    search(child)

            elif isinstance(value, list):

                for child in value:
                    search(child)

        search(data)

        return assignments

    def get_all_assignments(self):
        self.login()
        courses = self.get_courses()
        print(f"Courses found: {len(courses)}")

        all_assignments = []

        for course in courses:
            print(f"Checking: {course['name']}")

            try:
                assignments = self.get_assignments(course)
                print(f"  Hands-on assignments: {len(assignments)}")
                all_assignments.extend(assignments)
            except Exception as error:
                print(f"  Hands-on failed: {error}")

            try:
                subjective = self.get_subjective_assignments(course)
                print(f"  Subjective assignments: {len(subjective)}")
                all_assignments.extend(subjective)
            except Exception as error:
                print(f"  Subjective failed: {error}")

        return all_assignments


def clean_html(text):
    if not text:
        return ""

    text = unescape(text)

    # Remove script/style blocks
    text = re.sub(
        r"<(script|style).*?>.*?</\1>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Convert common HTML separators to spaces
    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"</p>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    # Remove remaining tags
    text = re.sub(
        r"<[^>]+>",
        "",
        text
    )

    # Clean whitespace
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n+",
        "\n",
        text
    )

    return text.strip()