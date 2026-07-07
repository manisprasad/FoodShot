from core.i18n import I18n


def test_i18n_format_success():
    i18n = I18n("en")
    # "ask-bg" contains placeholders: dish, weight, carbs, kcal, confidence
    res = i18n.get(
        "ask-bg",
        dish="Pizza",
        weight=200,
        carbs=30.0,
        kcal=450,
        confidence="High",
    )
    assert "Pizza" in res
    assert "200" in res
    assert "30" in res


def test_i18n_format_missing_key_no_crash():
    i18n = I18n("en")
    # Intentionally omit carbs, kcal, confidence, etc.
    res = i18n.get("ask-bg", dish="Pizza", weight=200)

    # It should not crash, and should preserve the missing key placeholders
    assert "Pizza" in res
    assert "{carbs}" in res
    assert "{kcal}" in res
    assert "{confidence}" in res
