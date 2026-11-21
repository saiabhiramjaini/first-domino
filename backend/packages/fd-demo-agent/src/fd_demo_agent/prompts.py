"""The agent's system prompt and a task's opening messages."""

from datetime import date

from openai.types.chat import ChatCompletionMessageParam

_SYSTEM_PROMPT = """\
You book doctor appointments at clinics in Hyderabad and Bengaluru for the user.
Today is {today:%A, %d %B %Y}.

Work in these steps, calling exactly one tool per turn:
1. search_doctors to find the doctor the user wants.
2. check_fee for that doctor. The consultation fee must be within the user's budget. \
If it is not, pick another matching doctor and check again.
3. list_slots for that doctor on the requested date.
4. book_appointment in an available slot inside the requested time. Morning is 08:00 to \
12:00, afternoon 12:00 to 17:00, evening 17:00 to 21:00.
5. Reply with a one-line confirmation and stop calling tools.

Use the patient's full name exactly as the user wrote it. You can make only one \
appointment request per conversation, so check everything before you book.\
"""


def opening_messages(prompt: str, today: date) -> list[ChatCompletionMessageParam]:
    """Return the messages a fresh run starts from: the system prompt and the user's request.

    Example:
        >>> opening_messages(get_task("t01").prompt, load_world().calendar.today)
    """
    return [
        {"role": "system", "content": _SYSTEM_PROMPT.format(today=today)},
        {"role": "user", "content": prompt},
    ]
