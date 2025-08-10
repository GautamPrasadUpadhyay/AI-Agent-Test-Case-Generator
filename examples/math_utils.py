def add(a, b):
    return a + b


def divide(a, b):
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return a / b


def clamp(value, low=0, high=100):
    if value < low:
        return low
    if value > high:
        return high
    return value


