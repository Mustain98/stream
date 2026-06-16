import os


PLATFORM_FEE_PERCENT = int(os.getenv("PLATFORM_FEE_PERCENT", "10"))
assert 0 < PLATFORM_FEE_PERCENT <= 50, f"PLATFORM_FEE_PERCENT must be between 1 and 50, got {PLATFORM_FEE_PERCENT}"


def calculate_platform_fee(amount: int) -> int:
    """
    Amount is in smallest currency unit.
    Example: 499 means $4.99 if currency is USD.
    """
    if amount <= 0:
        return 0

    return int(amount * PLATFORM_FEE_PERCENT / 100)


def calculate_broadcaster_amount(amount: int, platform_fee_amount: int) -> int:
    return max(amount - platform_fee_amount, 0)