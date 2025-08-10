import math_utils

import pytest
from temp import add, divide, clamp

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0

def test_divide():
    assert divide(10, 2) == 5.0
    assert divide(1, 1) == 1.0
    with pytest.raises(ZeroDivisionError) as excinfo:
        divide(1, 0)
    assert str(excinfo.value) == "division by zero"

def test_clamp_normal():
    assert clamp(50, 0, 100) == 50
    assert clamp(50) == 50
    assert clamp(50, 10, 90) == 50


def test_clamp_low():
    assert clamp(-10, 0, 100) == 0
    assert clamp(-10) == 0
    assert clamp(-10, -20, 100) == -10

def test_clamp_high():
    assert clamp(110, 0, 100) == 100
    assert clamp(110, 0, 100) == 100
    assert clamp(110, 0, 1000) == 100

def test_clamp_edge():
    assert clamp(0,0,100) == 0
    assert clamp(100,0,100) == 100
    assert clamp(0,-100, 100) == 0
    assert clamp(100,-100, 100) == 100

def test_clamp_error_handling():
    # no specific error handling is defined, tests cover edge cases instead.
    pass