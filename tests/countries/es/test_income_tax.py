import pytest

from calcnook.countries.es import income_tax


def test_madrid_default_general_base():
    result = income_tax.calculate(30_000)

    assert result.comunidad_autonoma == "Madrid"
    assert result.year == 2025
    assert result.state_general_tax == pytest.approx(3_055.50)
    assert result.regional_general_tax == pytest.approx(2_640.618675)
    assert result.income_tax == pytest.approx(5_696.118675)
    assert result.income_after_irpf == pytest.approx(24_303.881325)


def test_personal_minimum_can_use_general_and_savings_bases():
    result = income_tax.calculate(3_000, savings_base=4_000)

    assert result.state_general_tax == 0.0
    assert result.regional_general_tax == 0.0
    assert result.state_savings_tax == pytest.approx(137.75)
    assert result.regional_savings_tax == pytest.approx(99.11825)


def test_savings_income_uses_savings_scale():
    result = income_tax.calculate(0, savings_base=50_000)

    assert result.state_savings_tax == pytest.approx(4_662.75)
    assert result.regional_savings_tax == pytest.approx(4_624.11825)


def test_custom_family_minimums_are_applied():
    result = income_tax.calculate(
        20_000,
        personal_minimum=7_950,
        regional_personal_minimum=8_500,
    )

    assert result.state_minimum_used == 7_950
    assert result.regional_minimum_used == 8_500
    assert result.income_tax < income_tax.calculate(20_000).income_tax


def test_zero_income():
    result = income_tax.calculate(0)

    assert result.income_tax == 0.0
    assert result.effective_rate == 0.0
    assert result.general_marginal_rate == 0.0
    assert result.savings_marginal_rate == 0.0


def test_general_and_savings_marginal_rates_are_separate():
    result = income_tax.calculate(30_000, savings_base=4_000)

    assert result.general_marginal_rate == pytest.approx(0.278)
    assert result.savings_marginal_rate == pytest.approx(0.19)


def test_savings_marginal_rate_uses_remaining_minimums():
    result = income_tax.calculate(3_000, savings_base=2_700)

    assert result.general_marginal_rate == 0.0
    assert result.savings_marginal_rate == pytest.approx(0.095)


def test_madrid_name_is_normalized():
    result = income_tax.calculate(30_000, comunidad_autonoma="Comunidad de Madrid")

    assert result.comunidad_autonoma == "Madrid"


def test_all_common_regime_regions_are_supported():
    for comunidad_autonoma in income_tax.SUPPORTED_COMUNIDADES_AUTONOMAS:
        result = income_tax.calculate(30_000, comunidad_autonoma=comunidad_autonoma)

        assert result.comunidad_autonoma == comunidad_autonoma
        assert result.regional_general_tax > 0


@pytest.mark.parametrize(
    ("alias", "normalized"),
    [
        ("Catalunya", "Cataluña"),
        ("Castilla y Leon", "Castilla y León"),
        ("Murcia", "Región de Murcia"),
        ("Comunidad Valenciana", "Comunitat Valenciana"),
    ],
)
def test_regional_aliases_are_normalized(alias, normalized):
    result = income_tax.calculate(30_000, comunidad_autonoma=alias)

    assert result.comunidad_autonoma == normalized


def test_region_default_personal_minimum_is_applied():
    andalucia = income_tax.calculate(5_700, comunidad_autonoma="Andalucía")
    aragon = income_tax.calculate(5_700, comunidad_autonoma="Aragón")

    assert andalucia.regional_general_tax == 0.0
    assert aragon.regional_general_tax > 0


def test_to_dict():
    result = income_tax.calculate(30_000)
    data = result.to_dict()

    assert data["income_tax"] == round(result.income_tax, 2)
    assert data["general_marginal_rate"] == round(result.general_marginal_rate, 6)
    assert data["savings_marginal_rate"] == round(result.savings_marginal_rate, 6)
    assert data["bracket_breakdown"]


@pytest.mark.parametrize("income", [-1, float("nan"), float("inf")])
def test_invalid_income(income):
    with pytest.raises(ValueError, match="finite"):
        income_tax.calculate(income)


def test_invalid_minimum():
    with pytest.raises(ValueError, match="minimum"):
        income_tax.calculate(30_000, personal_minimum=-1)


def test_unsupported_year():
    with pytest.raises(ValueError, match="year"):
        income_tax.calculate(30_000, year=2024)


def test_unsupported_comunidad_autonoma():
    with pytest.raises(ValueError, match="Unsupported comunidad_autonoma"):
        income_tax.calculate(30_000, comunidad_autonoma="Navarra")
