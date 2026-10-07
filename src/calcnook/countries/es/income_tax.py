"""Spanish IRPF estimator for the 2025 tax year, defaulting to Madrid.

Inputs are the general and savings taxable bases after deductions and base
reductions, before applying the personal and family minimum. The minimum is
taxed at zero by subtracting the tax calculated on it from each applicable
state and autonomous-community scale.

This core estimate excludes tax credits, withholding, joint filing, and the
calculation of taxable bases from gross income. Personal and family minimums
can be supplied explicitly for dependents, age, or disability.

Reference: Ley 35/2006, especially Articles 56-63, as published in the BOE.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from unicodedata import normalize


SUPPORTED_YEAR = 2025
DEFAULT_COMUNIDAD_AUTONOMA = "Madrid"

STATE_PERSONAL_MINIMUM = 5_550.0
DEFAULT_REGIONAL_PERSONAL_MINIMUM = STATE_PERSONAL_MINIMUM
MADRID_PERSONAL_MINIMUM = 5_956.65

TaxBracket = tuple[float, float, str]


@dataclass(frozen=True)
class RegionalTaxScale:
	"""Autonomous-community scale and default contributor minimum."""

	name: str
	general_brackets: tuple[TaxBracket, ...]
	personal_minimum: float = DEFAULT_REGIONAL_PERSONAL_MINIMUM

STATE_GENERAL_BRACKETS: tuple[TaxBracket, ...] = (
	(12_450.0, 0.095, "state_general_1"),
	(20_200.0, 0.12, "state_general_2"),
	(35_200.0, 0.15, "state_general_3"),
	(60_000.0, 0.185, "state_general_4"),
	(300_000.0, 0.225, "state_general_5"),
	(float("inf"), 0.245, "state_general_6"),
)

STATE_SAVINGS_BRACKETS: tuple[TaxBracket, ...] = (
	(6_000.0, 0.095, "state_savings_1"),
	(50_000.0, 0.105, "state_savings_2"),
	(200_000.0, 0.115, "state_savings_3"),
	(300_000.0, 0.135, "state_savings_4"),
	(float("inf"), 0.15, "state_savings_5"),
)

REGIONAL_SAVINGS_BRACKETS: tuple[TaxBracket, ...] = (
	(6_000.0, 0.095, "regional_savings_1"),
	(50_000.0, 0.105, "regional_savings_2"),
	(200_000.0, 0.115, "regional_savings_3"),
	(300_000.0, 0.135, "regional_savings_4"),
	(float("inf"), 0.15, "regional_savings_5"),
)

REGIONAL_TAX_SCALES: dict[str, RegionalTaxScale] = {
	"Andalucía": RegionalTaxScale(
		"Andalucía",
		(
			(13_000.0, 0.095, "andalucia_general_1"),
			(21_100.0, 0.12, "andalucia_general_2"),
			(35_200.0, 0.15, "andalucia_general_3"),
			(60_000.0, 0.185, "andalucia_general_4"),
			(float("inf"), 0.225, "andalucia_general_5"),
		),
		5_790.0,
	),
	"Aragón": RegionalTaxScale(
		"Aragón",
		(
			(13_072.50, 0.095, "aragon_general_1"),
			(21_210.0, 0.12, "aragon_general_2"),
			(36_960.0, 0.15, "aragon_general_3"),
			(52_500.0, 0.185, "aragon_general_4"),
			(60_000.0, 0.205, "aragon_general_5"),
			(80_000.0, 0.23, "aragon_general_6"),
			(90_000.0, 0.24, "aragon_general_7"),
			(130_000.0, 0.25, "aragon_general_8"),
			(float("inf"), 0.255, "aragon_general_9"),
		),
	),
	"Asturias": RegionalTaxScale(
		"Asturias",
		(
			(12_450.0, 0.09, "asturias_general_1"),
			(17_707.20, 0.12, "asturias_general_2"),
			(33_007.20, 0.14, "asturias_general_3"),
			(53_407.20, 0.192, "asturias_general_4"),
			(70_000.0, 0.215, "asturias_general_5"),
			(90_000.0, 0.225, "asturias_general_6"),
			(175_000.0, 0.25, "asturias_general_7"),
			(float("inf"), 0.26, "asturias_general_8"),
		),
		6_105.0,
	),
	"Illes Balears": RegionalTaxScale(
		"Illes Balears",
		(
			(10_000.0, 0.09, "illes_balears_general_1"),
			(18_000.0, 0.1125, "illes_balears_general_2"),
			(30_000.0, 0.1425, "illes_balears_general_3"),
			(48_000.0, 0.175, "illes_balears_general_4"),
			(70_000.0, 0.19, "illes_balears_general_5"),
			(90_000.0, 0.2175, "illes_balears_general_6"),
			(120_000.0, 0.2275, "illes_balears_general_7"),
			(175_000.0, 0.2375, "illes_balears_general_8"),
			(float("inf"), 0.2475, "illes_balears_general_9"),
		),
	),
	"Canarias": RegionalTaxScale(
		"Canarias",
		(
			(13_748.0, 0.09, "canarias_general_1"),
			(19_422.0, 0.115, "canarias_general_2"),
			(35_924.0, 0.14, "canarias_general_3"),
			(57_566.0, 0.185, "canarias_general_4"),
			(93_268.0, 0.235, "canarias_general_5"),
			(123_745.0, 0.25, "canarias_general_6"),
			(float("inf"), 0.26, "canarias_general_7"),
		),
		5_606.0,
	),
	"Cantabria": RegionalTaxScale(
		"Cantabria",
		(
			(13_000.0, 0.085, "cantabria_general_1"),
			(21_000.0, 0.11, "cantabria_general_2"),
			(35_200.0, 0.145, "cantabria_general_3"),
			(60_000.0, 0.18, "cantabria_general_4"),
			(90_000.0, 0.225, "cantabria_general_5"),
			(float("inf"), 0.245, "cantabria_general_6"),
		),
	),
	"Castilla-La Mancha": RegionalTaxScale(
		"Castilla-La Mancha",
		(
			(12_450.0, 0.095, "castilla_la_mancha_general_1"),
			(20_200.0, 0.12, "castilla_la_mancha_general_2"),
			(35_200.0, 0.15, "castilla_la_mancha_general_3"),
			(60_000.0, 0.185, "castilla_la_mancha_general_4"),
			(float("inf"), 0.225, "castilla_la_mancha_general_5"),
		),
	),
	"Castilla y León": RegionalTaxScale(
		"Castilla y León",
		(
			(12_450.0, 0.09, "castilla_y_leon_general_1"),
			(20_200.0, 0.12, "castilla_y_leon_general_2"),
			(35_200.0, 0.14, "castilla_y_leon_general_3"),
			(53_407.20, 0.185, "castilla_y_leon_general_4"),
			(float("inf"), 0.215, "castilla_y_leon_general_5"),
		),
	),
	"Cataluña": RegionalTaxScale(
		"Cataluña",
		(
			(12_500.0, 0.095, "cataluna_general_1"),
			(22_000.0, 0.125, "cataluna_general_2"),
			(33_000.0, 0.16, "cataluna_general_3"),
			(53_000.0, 0.19, "cataluna_general_4"),
			(90_000.0, 0.215, "cataluna_general_5"),
			(120_000.0, 0.235, "cataluna_general_6"),
			(175_000.0, 0.245, "cataluna_general_7"),
			(float("inf"), 0.255, "cataluna_general_8"),
		),
	),
	"Extremadura": RegionalTaxScale(
		"Extremadura",
		(
			(12_450.0, 0.08, "extremadura_general_1"),
			(20_200.0, 0.10, "extremadura_general_2"),
			(24_200.0, 0.16, "extremadura_general_3"),
			(35_200.0, 0.175, "extremadura_general_4"),
			(60_000.0, 0.21, "extremadura_general_5"),
			(80_200.0, 0.235, "extremadura_general_6"),
			(99_200.0, 0.24, "extremadura_general_7"),
			(120_200.0, 0.245, "extremadura_general_8"),
			(float("inf"), 0.25, "extremadura_general_9"),
		),
	),
	"Galicia": RegionalTaxScale(
		"Galicia",
		(
			(12_985.35, 0.09, "galicia_general_1"),
			(21_068.60, 0.1165, "galicia_general_2"),
			(35_200.0, 0.149, "galicia_general_3"),
			(60_000.0, 0.184, "galicia_general_4"),
			(float("inf"), 0.225, "galicia_general_5"),
		),
		5_789.0,
	),
	"Madrid": RegionalTaxScale(
		"Madrid",
		(
			(13_362.22, 0.085, "madrid_general_1"),
			(19_004.63, 0.107, "madrid_general_2"),
			(35_425.68, 0.128, "madrid_general_3"),
			(57_320.40, 0.174, "madrid_general_4"),
			(float("inf"), 0.205, "madrid_general_5"),
		),
		MADRID_PERSONAL_MINIMUM,
	),
	"Región de Murcia": RegionalTaxScale(
		"Región de Murcia",
		(
			(12_450.0, 0.095, "region_de_murcia_general_1"),
			(20_200.0, 0.112, "region_de_murcia_general_2"),
			(34_000.0, 0.133, "region_de_murcia_general_3"),
			(60_000.0, 0.179, "region_de_murcia_general_4"),
			(float("inf"), 0.225, "region_de_murcia_general_5"),
		),
	),
	"La Rioja": RegionalTaxScale(
		"La Rioja",
		(
			(12_450.0, 0.08, "la_rioja_general_1"),
			(20_200.0, 0.106, "la_rioja_general_2"),
			(35_200.0, 0.136, "la_rioja_general_3"),
			(40_000.0, 0.178, "la_rioja_general_4"),
			(50_000.0, 0.183, "la_rioja_general_5"),
			(60_000.0, 0.19, "la_rioja_general_6"),
			(120_000.0, 0.245, "la_rioja_general_7"),
			(float("inf"), 0.27, "la_rioja_general_8"),
		),
	),
	"Comunitat Valenciana": RegionalTaxScale(
		"Comunitat Valenciana",
		(
			(12_000.0, 0.09, "comunitat_valenciana_general_1"),
			(22_000.0, 0.12, "comunitat_valenciana_general_2"),
			(32_000.0, 0.15, "comunitat_valenciana_general_3"),
			(42_000.0, 0.175, "comunitat_valenciana_general_4"),
			(52_000.0, 0.20, "comunitat_valenciana_general_5"),
			(62_000.0, 0.225, "comunitat_valenciana_general_6"),
			(72_000.0, 0.25, "comunitat_valenciana_general_7"),
			(100_000.0, 0.265, "comunitat_valenciana_general_8"),
			(150_000.0, 0.275, "comunitat_valenciana_general_9"),
			(200_000.0, 0.285, "comunitat_valenciana_general_10"),
			(float("inf"), 0.295, "comunitat_valenciana_general_11"),
		),
		6_105.0,
	),
	"Ceuta": RegionalTaxScale(
		"Ceuta",
		(
			(12_450.0, 0.095, "ceuta_general_1"),
			(20_200.0, 0.12, "ceuta_general_2"),
			(35_200.0, 0.15, "ceuta_general_3"),
			(60_000.0, 0.185, "ceuta_general_4"),
			(float("inf"), 0.225, "ceuta_general_5"),
		),
	),
	"Melilla": RegionalTaxScale(
		"Melilla",
		(
			(12_450.0, 0.095, "melilla_general_1"),
			(20_200.0, 0.12, "melilla_general_2"),
			(35_200.0, 0.15, "melilla_general_3"),
			(60_000.0, 0.185, "melilla_general_4"),
			(float("inf"), 0.225, "melilla_general_5"),
		),
	),
}


def _normalization_key(value: str) -> str:
	ascii_value = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
	return " ".join(ascii_value.casefold().replace(".", "").split())


_REGIONAL_ALIASES = {
	_normalization_key(alias): region
	for region, aliases in {
		"Andalucía": ("andalucia", "comunidad autonoma de andalucia"),
		"Aragón": ("aragon", "comunidad autonoma de aragon"),
		"Asturias": ("asturias", "principado de asturias", "comunidad autonoma del principado de asturias"),
		"Illes Balears": ("illes balears", "islas baleares", "balears", "baleares"),
		"Canarias": ("canarias", "islas canarias"),
		"Cantabria": ("cantabria",),
		"Castilla-La Mancha": ("castilla-la mancha", "castilla la mancha"),
		"Castilla y León": ("castilla y leon", "castilla y león"),
		"Cataluña": ("cataluna", "cataluña", "catalunya"),
		"Extremadura": ("extremadura",),
		"Galicia": ("galicia",),
		"Madrid": ("madrid", "comunidad de madrid"),
		"Región de Murcia": ("region de murcia", "región de murcia", "murcia"),
		"La Rioja": ("la rioja", "rioja"),
		"Comunitat Valenciana": ("comunitat valenciana", "comunidad valenciana", "valencia", "valenciana"),
		"Ceuta": ("ceuta",),
		"Melilla": ("melilla",),
	}.items()
	for alias in (region, *aliases)
}

SUPPORTED_COMUNIDADES_AUTONOMAS = tuple(REGIONAL_TAX_SCALES)


@dataclass(frozen=True)
class ESBracketDetail:
	"""Tax contributed by one jurisdiction and income-base bracket."""

	jurisdiction: str
	name: str
	rate: float
	income_in_band: float
	tax_in_band: float

	def to_dict(self) -> dict[str, str | float]:
		return {
			"jurisdiction": self.jurisdiction,
			"name": self.name,
			"rate": self.rate,
			"income_in_band": round(self.income_in_band, 2),
			"tax_in_band": round(self.tax_in_band, 2),
		}


@dataclass(frozen=True)
class ESIncomeTaxResult:
	"""Estimated IRPF quota before tax credits and withholding."""

	general_base: float
	savings_base: float
	comunidad_autonoma: str
	year: int
	state_minimum_used: float
	regional_minimum_used: float
	state_general_tax: float
	regional_general_tax: float
	state_savings_tax: float
	regional_savings_tax: float
	income_tax: float
	effective_rate: float
	general_marginal_rate: float
	savings_marginal_rate: float
	income_after_irpf: float
	bracket_breakdown: tuple[ESBracketDetail, ...]

	def to_dict(self) -> dict[str, str | int | float | list[dict[str, str | float]]]:
		return {
			"general_base": round(self.general_base, 2),
			"savings_base": round(self.savings_base, 2),
			"comunidad_autonoma": self.comunidad_autonoma,
			"year": self.year,
			"state_minimum_used": round(self.state_minimum_used, 2),
			"regional_minimum_used": round(self.regional_minimum_used, 2),
			"state_general_tax": round(self.state_general_tax, 2),
			"regional_general_tax": round(self.regional_general_tax, 2),
			"state_savings_tax": round(self.state_savings_tax, 2),
			"regional_savings_tax": round(self.regional_savings_tax, 2),
			"income_tax": round(self.income_tax, 2),
			"effective_rate": round(self.effective_rate, 6),
			"general_marginal_rate": round(self.general_marginal_rate, 6),
			"savings_marginal_rate": round(self.savings_marginal_rate, 6),
			"income_after_irpf": round(self.income_after_irpf, 2),
			"bracket_breakdown": [detail.to_dict() for detail in self.bracket_breakdown],
		}


def _tax_after_minimum(
	base: float,
	minimum: float,
	brackets: tuple[TaxBracket, ...],
	jurisdiction: str,
) -> tuple[float, tuple[ESBracketDetail, ...]]:
	minimum_to_offset = min(base, minimum)
	lower = 0.0
	tax = 0.0
	details: list[ESBracketDetail] = []

	for upper, rate, name in brackets:
		band_income = max(0.0, min(base, upper) - max(minimum_to_offset, lower))
		if band_income:
			band_tax = band_income * rate
			tax += band_tax
			details.append(
				ESBracketDetail(
					jurisdiction=jurisdiction,
					name=name,
					rate=rate,
					income_in_band=band_income,
					tax_in_band=band_tax,
				)
			)
		if base <= upper:
			break
		lower = upper

	return tax, tuple(details)


def _marginal_rate(base: float, minimum: float, brackets: tuple[TaxBracket, ...]) -> float:
	if base < minimum:
		return 0.0
	for upper, rate, _ in brackets:
		if base < upper:
			return rate
	return brackets[-1][1]


def calculate(
	general_base: float,
	savings_base: float = 0.0,
	*,
	comunidad_autonoma: str = DEFAULT_COMUNIDAD_AUTONOMA,
	year: int = SUPPORTED_YEAR,
	personal_minimum: float = STATE_PERSONAL_MINIMUM,
	regional_personal_minimum: float | None = None,
) -> ESIncomeTaxResult:
	"""Estimate resident IRPF using the state and autonomous-community tax scales.

	Args:
		general_base: Annual general taxable base in EUR, before the personal
			and family minimum is applied.
		savings_base: Annual savings taxable base in EUR, before any unused
			personal and family minimum is applied.
		comunidad_autonoma: Autonomous community or autonomous city.
		year: Only the 2025 tax-year scales are currently available.
		personal_minimum: State personal and family minimum in EUR. Increase
			this for applicable age, descendant, ascendant, or disability amounts.
		regional_personal_minimum: Regional personal and family minimum in EUR.
			Defaults to the selected community's ordinary contributor minimum.

	Returns:
		An ``ESIncomeTaxResult`` with state and regional quotas before credits.

	Raises:
		ValueError: if a base/minimum is negative or non-finite, or if the
			requested year or autonomous community is unsupported.

	Example:
		>>> result = calculate(30_000)
		>>> round(result.income_tax, 2)
		5696.12
	"""
	region_key = _REGIONAL_ALIASES.get(_normalization_key(comunidad_autonoma))
	if region_key is None:
		supported = ", ".join(SUPPORTED_COMUNIDADES_AUTONOMAS)
		raise ValueError(f"Unsupported comunidad_autonoma={comunidad_autonoma!r}; supported: {supported}")
	region = REGIONAL_TAX_SCALES[region_key]
	regional_minimum = (
		region.personal_minimum
		if regional_personal_minimum is None
		else regional_personal_minimum
	)

	values = (general_base, savings_base, personal_minimum, regional_minimum)
	if any(not isfinite(value) or value < 0 for value in values):
		raise ValueError("income bases and personal minimums must be finite and >= 0")
	if year != SUPPORTED_YEAR:
		raise ValueError(f"Only year={SUPPORTED_YEAR} scales are available")

	state_minimum_used = min(general_base, personal_minimum)
	regional_minimum_used = min(general_base, regional_minimum)

	state_general_tax, state_general_details = _tax_after_minimum(
		general_base, personal_minimum, STATE_GENERAL_BRACKETS, "state"
	)
	regional_general_tax, regional_general_details = _tax_after_minimum(
		general_base, regional_minimum, region.general_brackets, region.name
	)

	state_savings_minimum = max(0.0, personal_minimum - general_base)
	regional_savings_minimum = max(0.0, regional_minimum - general_base)
	state_savings_tax, state_savings_details = _tax_after_minimum(
		savings_base, state_savings_minimum, STATE_SAVINGS_BRACKETS, "state"
	)
	regional_savings_tax, regional_savings_details = _tax_after_minimum(
		savings_base, regional_savings_minimum, REGIONAL_SAVINGS_BRACKETS, region.name
	)

	income_tax = (
		state_general_tax
		+ regional_general_tax
		+ state_savings_tax
		+ regional_savings_tax
	)
	total_base = general_base + savings_base
	effective_rate = income_tax / total_base if total_base else 0.0

	general_marginal_rate = _marginal_rate(
		general_base, personal_minimum, STATE_GENERAL_BRACKETS
	) + _marginal_rate(general_base, regional_minimum, region.general_brackets)
	savings_marginal_rate = _marginal_rate(
		savings_base, state_savings_minimum, STATE_SAVINGS_BRACKETS
	) + _marginal_rate(
		savings_base,
		regional_savings_minimum,
		REGIONAL_SAVINGS_BRACKETS,
	)

	return ESIncomeTaxResult(
		general_base=general_base,
		savings_base=savings_base,
		comunidad_autonoma=region.name,
		year=year,
		state_minimum_used=state_minimum_used,
		regional_minimum_used=regional_minimum_used,
		state_general_tax=state_general_tax,
		regional_general_tax=regional_general_tax,
		state_savings_tax=state_savings_tax,
		regional_savings_tax=regional_savings_tax,
		income_tax=income_tax,
		effective_rate=effective_rate,
		general_marginal_rate=general_marginal_rate,
		savings_marginal_rate=savings_marginal_rate,
		income_after_irpf=total_base - income_tax,
		bracket_breakdown=(
			state_general_details
			+ regional_general_details
			+ state_savings_details
			+ regional_savings_details
		),
	)
