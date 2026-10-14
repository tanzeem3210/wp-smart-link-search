
import re
from datetime import datetime


MESSAGE_PATTERNS = [
    # Example: 12/31/25, 10:30 PM - Alex: Hello
    re.compile(
        r"^(?P<date>\d{1,2}/\d{1,2}/\d{2,4}), "
        r"(?P<time>\d{1,2}:\d{2}\s?[APap][Mm]) - "
        r"(?P<body>.*)$"
    ),
    # Example: [12/31/25, 22:30] Alex: Hello
    re.compile(
        r"^\[(?P<date>\d{1,2}/\d{1,2}/\d{2,4}), "
        r"(?P<time>\d{1,2}:\d{2})\] "
        r"(?P<body>.*)$"
    ),
    re.compile(
    r"^(?P<date>\d{1,2}/\d{1,2}/\d{2,4}), "
    r"(?P<time>\d{1,2}:\d{2}) - (?P<body>.*)$"
),
]

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def parse_timestamp(date_text: str, time_text: str) -> str:
    formats = [
        "%m/%d/%y %I:%M %p",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%y %H:%M",
        "%m/%d/%Y %H:%M",
        "%d/%m/%y %H:%M",
        "%d/%m/%Y %H:%M",
    ]

    value = f"{date_text} {time_text.strip()}"

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).isoformat(
                sep=" ", timespec="minutes"
            )
        except ValueError:
            continue

    return value


def parse_chat(content: str) -> list[dict]:
    messages = []
    current = None

    for line in content.splitlines():
        match = next(
            (pattern.match(line) for pattern in MESSAGE_PATTERNS
             if pattern.match(line)),
            None,
        )

        if match:
            if current:
                messages.append(current)

            body = match.group("body")
            sender, separator, text = body.partition(": ")

            current = {
                "timestamp": parse_timestamp(
                    match.group("date"), match.group("time")
                ),
                "sender": sender if separator else None,
                "text": text if separator else body,
            }
        elif current is not None:
            # WhatsApp messages can span multiple lines.
            current["text"] += "\n" + line

    if current:
        messages.append(current)

    for message in messages:
        message["links"] = [
            url.rstrip(".,!?)]}")
            for url in URL_PATTERN.findall(message["text"])
        ]

    return messages
