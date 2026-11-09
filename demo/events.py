import argparse
import json
import os
from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field

DEMO = Path(__file__).resolve().parent
RECORDING = DEMO / "event_recording.json"


class Event(BaseModel):
    title: str
    start_date: date
    end_date: date | None
    venue: str
    start_time: str | None = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")


PROMPT = (
    "Extract the event from the supplied Visiting Jogja title and agenda text. "
    "Remove the parenthesized date from the title. Use event dates, not the publication date. "
    "Use null for end_date unless the agenda gives a date range. "
    "Use local 24-hour HH:MM for start_time or null if no time is stated. "
    "Keep the venue wording from the source."
)


def record(sources, provider):
    import instructor

    client = instructor.from_provider(provider)
    events = [
        client.create(
            response_model=Event,
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": json.dumps(source, ensure_ascii=False)},
            ],
        ).model_dump(mode="json")
        for source in sources
    ]
    RECORDING.write_text(
        json.dumps({"provider": provider, "events": events}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description="Record or replay the Visiting Jogja extraction demo.")
    parser.add_argument("--record", action="store_true", help="Call the configured Instructor provider.")
    args = parser.parse_args()
    sources = json.loads((DEMO / "events.json").read_text(encoding="utf-8"))
    expected = json.loads((DEMO / "event_expected.json").read_text(encoding="utf-8"))
    if args.record:
        provider = os.environ.get("INSTRUCTOR_PROVIDER")
        if not provider:
            parser.error("Set INSTRUCTOR_PROVIDER and configure credentials for that provider.")
        record(sources, provider)

    if RECORDING.exists():
        recording = json.loads(RECORDING.read_text(encoding="utf-8"))
        label = f"Instructor recording ({recording['provider']})"
        outputs = recording["events"]
    else:
        label = "Hand-checked reference output"
        outputs = expected

    print(label)
    for source, output, reference in zip(sources, outputs, expected, strict=True):
        print(f"\n{source['title']} (published {source['published']})")
        print(source["text"])
        result = Event.model_validate(output).model_dump(mode="json")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result != reference:
            print("This result differs from the hand-checked reference.")


if __name__ == "__main__":
    main()
