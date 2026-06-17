# PDF Persian / RTL rendering

Reference for ReportLab PDF exports (`marketing/reports/pdf.py`, `marketing/reports/pdf_fonts.py`).

## Rule: shape once

ReportLab draws text left-to-right in storage order. Persian requires:

1. `arabic_reshaper.reshape()` — join letters (initial/medial/final forms)
2. `python-bidi` `get_display()` — reorder mixed RTL/LTR runs for display

Both steps must run **exactly once** on the **full logical string** before it goes into a `Paragraph`.

### What went wrong (2026-06 overhaul)

Headers used `shape_pdf_parts()` that shaped **each fragment separately**, then concatenated. Filter lines were shaped in `_filter_line`, then shaped **again** in `_header_story` with `shaped=True`. That double pass turned labels like `خط کسب‌وکار` into isolated reversed letters (e.g. `راکوب‌س‌ک‌ط‌خ`) when mixed with English filter values such as `Business`.

### Correct pattern

```python
# Build logical text (Persian labels + English data values + punctuation)
line = f"{label('filters', locale)}: {filter_line}"

# Shape once inside _paragraph / _cell
Paragraph(escape(shape_pdf_text(line, locale)), style)
```

Never:

- Shape substrings and join
- Pass `shaped=True` to skip shaping when text already contains Persian
- Call `shape_pdf_text` twice on the same content

## Fonts

Vazirmatn Regular/Bold are embedded when files exist under `marketing/reports/fonts/`. Used for all PDF locales so Persian vendor names render in English exports too.

## Tests

- `test_shape_pdf_parts_runs_single_bidi_pass_for_mixed_text`
- `test_persian_pdf_filter_header_mixed_english_value`
- `test_persian_vendor_pdf_keeps_rtl_words_in_logical_order`

Run: `uv run pytest marketing/tests/test_reference_and_pdf.py -q`
