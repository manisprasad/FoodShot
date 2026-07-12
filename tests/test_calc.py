import pytest

from services.calc import calculate_bolus


def test_calculate_bolus_normal_case():
    # 50g carbs, ICR=10, ISF=50, target=100, current=150
    # carb_dose = 50 / 10 = 5.0
    # correction_dose = (150 - 100) / 50 = 1.0
    # total = 6.0
    result = calculate_bolus(carbs=50, icr=10, isf=50, target_bg=100, current_bg=150)
    assert result == {
        "carb_dose": 5.0,
        "correction_dose": 1.0,
        "total_dose": 6.0,
    }


def test_calculate_bolus_no_correction_needed_low_bg():
    # current_bg < target_bg
    result = calculate_bolus(carbs=50, icr=10, isf=50, target_bg=100, current_bg=80)
    assert result == {
        "carb_dose": 5.0,
        "correction_dose": 0.0,
        "total_dose": 5.0,
    }


def test_calculate_bolus_no_correction_needed_exact_bg():
    # current_bg == target_bg
    result = calculate_bolus(carbs=50, icr=10, isf=50, target_bg=100, current_bg=100)
    assert result == {
        "carb_dose": 5.0,
        "correction_dose": 0.0,
        "total_dose": 5.0,
    }


def test_calculate_bolus_no_current_bg():
    # current_bg is None
    result = calculate_bolus(carbs=50, icr=10, isf=50, target_bg=100, current_bg=None)
    assert result == {
        "carb_dose": 5.0,
        "correction_dose": 0.0,
        "total_dose": 5.0,
    }


def test_calculate_bolus_zero_icr():
    with pytest.raises(ValueError, match="ICR must be greater than 0"):
        calculate_bolus(carbs=50, icr=0, isf=50, target_bg=100, current_bg=150)


def test_calculate_bolus_zero_isf():
    with pytest.raises(ValueError, match="ISF must be greater than 0"):
        calculate_bolus(carbs=50, icr=10, isf=0, target_bg=100, current_bg=150)


def test_calculate_bolus_zero_carbs():
    result = calculate_bolus(carbs=0, icr=10, isf=50, target_bg=100, current_bg=150)
    assert result == {
        "carb_dose": 0.0,
        "correction_dose": 1.0,
        "total_dose": 1.0,
    }
