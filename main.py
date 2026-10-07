"""Command-line entry point for the Spanish IRPF estimator."""

from __future__ import annotations

import csv
from io import StringIO
import json
from numbers import Real

from calcnook.countries.es import income_tax


def _result_dict_to_csv(result_dict: dict, *, delimiter: str = ",", decimal_comma: bool = False) -> str:
	bracket_breakdown = result_dict.get("bracket_breakdown", [])
	summary = {
		key: value
		for key, value in result_dict.items()
		if key != "bracket_breakdown"
	}

	rows = [
		{**summary, **bracket_detail}
		for bracket_detail in bracket_breakdown
	]
	if not rows:
		rows = [summary]

	output = StringIO()
	writer = csv.DictWriter(output, fieldnames=rows[0].keys(), delimiter=delimiter)
	writer.writeheader()
	writer.writerows(_format_row(row, decimal_comma=decimal_comma) for row in rows)
	return output.getvalue()


def _format_row(row: dict, *, decimal_comma: bool) -> dict:
	if not decimal_comma:
		return row
	return {
		key: _format_decimal_comma(value)
		for key, value in row.items()
	}


def _format_decimal_comma(value: object) -> object:
	if isinstance(value, bool) or not isinstance(value, Real):
		return value
	return str(value).replace(".", ",")


if __name__ == "__main__":
	try:
		state_first_child = 2_400.0 / 2
		state_second_child = 2_700.0 / 2
		regional_first_child = 2_575.92 / 2
		regional_second_child = 2_897.91 / 2
		children = 2
		personal_minimum = income_tax.STATE_PERSONAL_MINIMUM + sum((state_first_child, state_second_child)[:children])
		regional_personal_minimum = income_tax.MADRID_PERSONAL_MINIMUM + sum((regional_first_child, regional_second_child)[:children])
		net_working_income = 110_037.07
		real_estate_income = 108.61 + 4_278.31
		retirement_contributions = 5_750.51
		savings_income = 5_604.65
		capital_gains_and_losses = max(-1_604.43, -savings_income*0.25)  # max. 25% of the total savings income 
		result = income_tax.calculate(
			general_base=net_working_income + real_estate_income - retirement_contributions,  # working income + real estate income - retirement contributions
			savings_base=savings_income + capital_gains_and_losses, # savings income + capital gains and losses (max. 25% of the total)
			comunidad_autonoma="Madrid",
			year=2025,
			personal_minimum=personal_minimum, # National personal minimum + 2 dependents
			regional_personal_minimum=regional_personal_minimum, # Regional personal minimum + 2 dependents
		)
	except ValueError as error:
		print(f"Error: {error}")
	else:
		result_dict = result.to_dict()
		print(json.dumps(result_dict, indent=2))
		print()
		print(_result_dict_to_csv(result_dict, delimiter=";", decimal_comma=True), end="")
