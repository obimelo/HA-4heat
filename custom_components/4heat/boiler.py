"""Wire values and validation for the opt-in boiler profile."""

from decimal import Decimal, InvalidOperation

BOILER_TARGET_RANGE = (60, 80)
BOILER_MINIMUM_IDS = ("20205", "20005")
BOILER_MAXIMUM_IDS = ("20206", "20006")

COMBUSTION_POWER_VALUES = {"Auto": 6, **{f"P{level}": level for level in range(5, 0, -1)}}
_COMBUSTION_POWER_OPTIONS = {
    value: option for option, value in COMBUSTION_POWER_VALUES.items()
}
_COMBUSTION_POWER_OPTIONS[7] = "Auto"


def combustion_power_option(value: int | None) -> str | None:
    """Decode a setting reported by the five-level stove."""
    return _COMBUSTION_POWER_OPTIONS.get(value)


def decimal_value(value) -> Decimal | None:
    """Parse numeric text without losing precision."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def whole_value(value, minimum: int, maximum: int) -> int | None:
    """Return a finite whole value within bounds without rounding or truncating."""
    number = decimal_value(value)
    if (
        number is None
        or not number.is_finite()
        or not minimum <= number <= maximum
        or number != number.to_integral_value()
    ):
        return None
    return int(number)
