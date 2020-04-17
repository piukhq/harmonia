def exponential_delay(prior_attempts: int, maximum_delay: int) -> int:
    """
    Calculates the number of seconds to delay based on the number of previous attempts and a maximum delay.
    Based on the common 2^c-1 algorithm.
    """
    prior_attempts = max(1, prior_attempts)
    return min(1 << prior_attempts - 1, maximum_delay)
