K_FACTOR = 20


def calculate_expected(rating_a: int, rating_b: int) -> tuple[float, float]:
    ea = 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400))
    eb = 1.0 / (1.0 + 10 ** ((rating_a - rating_b) / 400))
    return ea, eb


def calculate_elo_change(
    rating_a: int, rating_b: int, winner: str
) -> tuple[int, int]:
    """Calculate new ELO ratings. Returns (change_a, change_b)."""
    ea, eb = calculate_expected(rating_a, rating_b)

    if winner == "a":
        sa, sb = 1.0, 0.0
    elif winner == "b":
        sa, sb = 0.0, 1.0
    else:  # tie
        sa, sb = 0.5, 0.5

    change_a = round(K_FACTOR * (sa - ea))
    change_b = round(K_FACTOR * (sb - eb))

    return change_a, change_b
