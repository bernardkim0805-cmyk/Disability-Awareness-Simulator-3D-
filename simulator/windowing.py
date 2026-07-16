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
