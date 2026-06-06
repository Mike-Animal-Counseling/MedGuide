import re

DOSAGE_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|mL|units?|%)\b",
    re.IGNORECASE,
)
INSTRUCTION_MARKERS = ("take ", "use ", "apply ", "inject ", "directions:")
FREQUENCY_MARKERS = (
    "daily",
    "weekly",
    "every ",
    "once ",
    "twice ",
    "times a day",
    "as needed",
)
NON_NAME_MARKERS = (
    "rx only",
    "directions",
    "pharmacy",
    "refill",
    "quantity",
    "prescriber",
)


def parse_label_text(text: str) -> dict[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    fields: dict[str, str] = {}
    for line in lines:
        lowered = line.casefold()
        if "dosage" not in fields and DOSAGE_PATTERN.search(line):
            fields["dosage"] = line
        if "instructions" not in fields and any(
            marker in lowered for marker in INSTRUCTION_MARKERS
        ):
            fields["instructions"] = line
        if "frequency" not in fields and any(marker in lowered for marker in FREQUENCY_MARKERS):
            fields["frequency"] = line
    for line in lines:
        lowered = line.casefold()
        if (
            len(line) <= 120
            and not DOSAGE_PATTERN.search(line)
            and not any(marker in lowered for marker in NON_NAME_MARKERS)
            and not any(marker in lowered for marker in INSTRUCTION_MARKERS)
        ):
            fields["medication_name"] = line
            break
    return fields
