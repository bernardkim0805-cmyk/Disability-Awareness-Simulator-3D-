"""Display-size parsing kept separate so it can be tested without opening Ursina."""


def requested_window_size(args: list[str]) -> tuple[int, int] | None:
    """Return an optional WIDTHxHEIGHT development override."""
    if "--window-size" not in args:
        return None
    try:
        value = args[args.index("--window-size") + 1]
        width, height = (int(part) for part in value.lower().split("x", 1))
        if width < 960 or height < 540:
            raise ValueError
        return width, height
    except (ValueError, IndexError):
        return None


def requested_scenario(args: list[str], valid: set[str]) -> str | None:
    """Return a development scenario override when it names a known scenario."""
    if "--scenario" not in args:
        return None
    try:
        value = args[args.index("--scenario") + 1]
    except IndexError:
        return None
    return value if value in valid else None


def requested_experience(args: list[str], valid: set[str]) -> str | None:
    """Return a validated original-experience development override."""
    if "--experience" not in args:
        return None
    try:
        value = args[args.index("--experience") + 1]
    except IndexError:
        return None
    return value if value in valid else None


def requested_effects(args: list[str], valid: set[str]) -> dict[str, float]:
    """Parse repeatable ``--effect id[:intensity]`` development overrides."""
    effects: dict[str, float] = {}
    for index, item in enumerate(args):
        if item != "--effect" or index + 1 >= len(args):
            continue
        value = args[index + 1]
        effect_id, separator, intensity_text = value.partition(":")
        if effect_id not in valid:
            continue
        try:
            intensity = float(intensity_text) if separator else .6
        except ValueError:
            continue
        effects[effect_id] = max(.05, min(1.0, intensity))
    return effects


def requested_capture(args: list[str]) -> str | None:
    """Return a caller-provided screenshot path for development reviews."""
    if "--capture" not in args:
        return None
    try:
        return args[args.index("--capture") + 1]
    except IndexError:
        return None
