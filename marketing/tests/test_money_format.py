from __future__ import annotations

from decimal import Decimal

import pytest

from marketing.money_format import (
    COMPACT,
    FULL,
    RIAL,
    TOMAN,
    format_money,
    format_money_full,
    unit_label,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("84276543010"), "84,276,543,010"),
        (84276543010, "84,276,543,010"),
        (Decimal("500"), "500"),
        (None, "0"),
    ],
)
def test_format_money_full(value, expected):
    assert format_money_full(value) == expected


def test_format_money_compact_english_billions():
    assert format_money(Decimal("84276543010"), COMPACT, "en") == "84.3B"


def test_format_money_compact_english_millions():
    assert format_money(Decimal("2500000"), COMPACT, "en") == "2.5M"


def test_format_money_compact_english_thousands():
    assert format_money(Decimal("1500"), COMPACT, "en") == "1.5K"


def test_format_money_compact_persian_billions():
    assert format_money(Decimal("84276543010"), COMPACT, "fa") == "84.3 میلیارد"


def test_format_money_compact_persian_trillions_use_hemmat_in_toman():
    # 13 trillion Rial -> 1.3 trillion Toman at the trillion tier.
    assert format_money(Decimal("13000000000000"), COMPACT, "fa", TOMAN) == "1.3 همت"


def test_format_money_compact_persian_trillions_use_trillion_label_in_rial():
    assert format_money(Decimal("2500000000000"), COMPACT, "fa", RIAL) == "2.5 تریلیون"


def test_format_money_full_rial_unchanged_for_large_values():
    assert format_money(Decimal("2500000000000"), FULL, "fa", RIAL) == "2,500,000,000,000"


def test_money_display_title_explains_hemmat_as_hezar_milliard_toman():
    from marketing.money_format import money_display_title

    title = money_display_title(
        Decimal("13000000000000"),
        unit=TOMAN,
        lang="fa",
        compact_formatted="1.3 همت",
    )
    assert "تومان" in title
    assert "هزار میلیارد" in title


def test_split_fa_compact_amount():
    from marketing.money_format import split_fa_compact_amount

    assert split_fa_compact_amount("25 میلیون") == ("25", "میلیون")
    assert split_fa_compact_amount("84.3 میلیارد") == ("84.3", "میلیارد")
    assert split_fa_compact_amount("2.5 همت") == ("2.5", "همت")
    assert split_fa_compact_amount("2.5 تریلیون") == ("2.5", "تریلیون")
    assert split_fa_compact_amount("1,000,000") is None


def test_format_money_compact_small_values_stay_full():
    assert format_money(Decimal("999"), COMPACT, "en") == "999"


def test_format_money_full_mode_ignores_lang():
    assert format_money(Decimal("1000000"), FULL, "fa") == "1,000,000"


def test_toman_unit_divides_by_ten_in_full_mode():
    assert format_money(Decimal("84276543010"), FULL, "en", TOMAN) == "8,427,654,301"


def test_toman_unit_works_in_compact_mode():
    # 84,276,543,010 rial -> 8,427,654,301 toman -> ~8.43B toman
    assert format_money(Decimal("84276543010"), COMPACT, "en", TOMAN) == "8.43B"


def test_rial_unit_is_unchanged_default():
    assert format_money(Decimal("84276543010"), FULL, "en", RIAL) == "84,276,543,010"


def test_format_money_full_respects_toman_unit():
    assert format_money_full(Decimal("100"), TOMAN) == "10"


def test_format_money_compact_negative_persian():
    assert format_money(Decimal("-3300000000000"), COMPACT, "fa", TOMAN) == "-330 میلیارد"


def test_split_fa_compact_amount_negative():
    from marketing.money_format import split_fa_compact_amount, split_signed_prefix

    assert split_fa_compact_amount("-3.3 میلیارد") == ("-3.3", "میلیارد")
    assert split_signed_prefix("-3.3") == (True, "3.3")


def test_money_filter_renders_minus_before_persian_compact_number():
    from django.template import Context, Template

    from marketing.money_format import activate_money_display, reset_money_display

    template = Template("{% load marketing_format %}{{ value|money }}")
    ctx = Context({"value": Decimal("-3300000000000")})
    token = activate_money_display(COMPACT, "fa", TOMAN)
    try:
        html = template.render(ctx)
    finally:
        reset_money_display(token)
    assert 'class="signed-number"' in html
    assert "dir=\"ltr\"" in html
    assert "−330" in html or "-330" in html
    assert "میلیارد" in html
    assert html.index("−" if "−" in html else "-") < html.index("میلیارد")


def test_unit_labels():
    assert unit_label(RIAL, "en") == "IRR"
    assert unit_label(RIAL, "fa") == "ریال"
    assert unit_label(TOMAN, "en") == "Toman"
    assert unit_label(TOMAN, "fa") == "تومان"
