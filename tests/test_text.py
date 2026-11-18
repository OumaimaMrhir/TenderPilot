from tenderpilot.text import Quantity, check_constraints, quantities


def test_quantities_understand_digits_words_and_percent():
    assert Quantity(48, "heures") in quantities("collectés sous 48 heures")
    assert Quantity(3, "fois") in quantities("au minimum trois fois par semaine")
    assert Quantity(75, "%") in quantities("au moins 75 % des déchets")


def test_delay_constraint_lower_is_better():
    assert check_constraints("sous 48 heures", "sous 72 heures") == ["exigé : 48 heures, proposé : 72 heures"]
    assert check_constraints("sous 72 heures", "sous 48 heures") == []


def test_quantity_constraint_higher_is_better():
    assert check_constraints("au moins 12 bennes", "40 bennes disponibles") == []
    assert check_constraints("au moins 75 %", "taux de 60 %") != []
