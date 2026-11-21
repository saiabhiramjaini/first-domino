"""Demo tasks and their expected outcomes.

Today is Saturday 21 Nov 2026, so "tomorrow" is Sunday 22 Nov and "this Friday" is 27 Nov.
"""

from datetime import date, time

from pydantic import BaseModel, ConfigDict


class TimeWindow(BaseModel):
    """A part of the day: `start` is inclusive, `end` exclusive."""

    model_config = ConfigDict(frozen=True)

    start: time
    end: time

    def contains(self, at: time) -> bool:
        """Return whether a slot time falls inside the window."""
        return self.start <= at < self.end


MORNING = TimeWindow(start=time(8), end=time(12))
AFTERNOON = TimeWindow(start=time(12), end=time(17))
EVENING = TimeWindow(start=time(17), end=time(21))
AFTER_FIVE = TimeWindow(start=time(17), end=time(23, 59))


class ExpectedBooking(BaseModel):
    """What a correct booking for a task looks like.

    `doctor_ids` already reflects the task's fee limit: a doctor over budget is not listed.
    """

    model_config = ConfigDict(frozen=True)

    doctor_ids: frozenset[str]
    date: date
    window: TimeWindow
    patient_name: str


class DemoTask(BaseModel):
    """One user request and the booking that satisfies it."""

    model_config = ConfigDict(frozen=True)

    task_id: str
    prompt: str
    expected: ExpectedBooking


def _task(
    task_id: str, prompt: str, doctor_ids: set[str], day: date, window: TimeWindow, patient: str
) -> DemoTask:
    expected = ExpectedBooking(
        doctor_ids=frozenset(doctor_ids), date=day, window=window, patient_name=patient
    )
    return DemoTask(task_id=task_id, prompt=prompt, expected=expected)


TASKS: tuple[DemoTask, ...] = (
    _task(
        "t01",
        "Book Dr. Mehta at Arogya Kukatpally for tomorrow morning, under ₹1000, "
        "for my father Ramesh Rao.",
        {"d-anil-mehta-kph"},
        date(2026, 11, 22),
        MORNING,
        "Ramesh Rao",
    ),
    _task(
        "t02",
        "I need a dermatologist in Indiranagar, Bengaluru this Friday evening for "
        "Lakshmi Iyer. Keep it under ₹600.",
        {"d-priya-nair-ind"},
        date(2026, 11, 27),
        EVENING,
        "Lakshmi Iyer",
    ),
    _task(
        "t03",
        "Book a paediatrician at Lotus Banjara Hills on the 26th, afternoon, "
        "for my son Akhilesh Kumar.",
        {"d-anjali-varma-bjh"},
        date(2026, 11, 26),
        AFTERNOON,
        "Akhilesh Kumar",
    ),
    _task(
        "t04",
        "My mother Lakshmi Devi needs a cardiologist in Hyderabad on Monday morning. "
        "Fee below ₹1000, please.",
        {"d-anil-mehta-mdp"},
        date(2026, 11, 23),
        MORNING,
        "Lakshmi Devi",
    ),
    _task(
        "t05",
        "Book Dr. Rao, the ENT at Nandi Whitefield, the day after tomorrow, any time "
        "after 5 pm, for Ramesh Babu.",
        {"d-venkat-rao-wfd"},
        date(2026, 11, 23),
        AFTER_FIVE,
        "Ramesh Babu",
    ),
    _task(
        "t06",
        "Orthopaedic consultation for Akhilesh Sharma in Jayanagar this Wednesday "
        "morning, budget ₹700.",
        {"d-arjun-rao-jyn"},
        date(2026, 11, 25),
        MORNING,
        "Akhilesh Sharma",
    ),
    _task(
        "t07",
        "Book a general physician at Arogya Madhapur tomorrow evening for Lakshmi Prasanna.",
        {"d-kiran-goud-mdp"},
        date(2026, 11, 22),
        EVENING,
        "Lakshmi Prasanna",
    ),
    _task(
        "t08",
        "My wife Lakshmi Narayanan needs a gynaecologist at Nandi Jayanagar on the 24th, "
        "morning please, under ₹900.",
        {"d-kavitha-murthy-jyn"},
        date(2026, 11, 24),
        MORNING,
        "Lakshmi Narayanan",
    ),
    _task(
        "t09",
        "Book Dr. Farhan Qureshi at Lotus Banjara Hills this Friday morning for Akhilesh Reddy.",
        {"d-farhan-qureshi-bjh"},
        date(2026, 11, 27),
        MORNING,
        "Akhilesh Reddy",
    ),
    _task(
        "t10",
        "Book the cheapest dermatologist in Hyderabad for tomorrow afternoon, for Lakshmi Menon.",
        {"d-ravi-teja-bjh"},
        date(2026, 11, 22),
        AFTERNOON,
        "Lakshmi Menon",
    ),
)

_BY_ID = {task.task_id: task for task in TASKS}


def get_task(task_id: str) -> DemoTask:
    """Return the task with this id.

    Raises:
        KeyError: No task has this id.
    """
    return _BY_ID[task_id]
