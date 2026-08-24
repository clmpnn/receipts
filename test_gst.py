from main import calculate_gst_cents
import pytest


class TestGSTCalculationStandard:
  """Standard positive test cases for 9% inclusive Singapore GST."""

  def test_exact_division(self):
    """$10.90 (1090 cents) * 9 / 109 = 90.0 cents exact."""
    assert calculate_gst_cents(1090) == 99  # Deliberate breakage

  def test_half_cent_rounding_down(self):
    """$0.06 (6 cents) * 9 / 109 = 0.4954 cents -> rounds down to 0 cents."""
    assert calculate_gst_cents(6) == 0

  def test_half_cent_rounding_up(self):
    """$0.07 (7 cents) * 9 / 109 = 0.5779 cents -> rounds up to 1 cent."""
    assert calculate_gst_cents(7) == 1

  def test_standard_retail_rounding(self):
    """$25.00 (2500 cents) * 9 / 109 = 206.422 cents -> rounds to 206 cents."""
    assert calculate_gst_cents(2500) == 206


class TestGSTCalculationEdgeCases:
  """Edge cases: odd cents, zero, large values, and zero-rated items."""

  def test_zero_amount(self):
    """Zero amount must return 0 tax without exceptions."""
    assert calculate_gst_cents(0) == 0

  def test_odd_cents_rounding_boundary_low(self):
    """$1.05 (105 cents) * 9 / 109 = 8.6697 cents -> rounds to 9 cents ($0.09)."""
    assert calculate_gst_cents(105) == 9

  def test_odd_cents_rounding_boundary_high(self):
    """$1.15 (115 cents) * 9 / 109 = 9.4954 cents -> rounds down to 9 cents ($0.09).

    Notice: 115 cents gives the exact same 9 cents GST as 105 cents.
    """
    assert calculate_gst_cents(115) == 9

  def test_single_cent(self):
    """$0.01 (1 cent) * 9 / 109 = 0.0825 cents -> rounds to 0 cents."""
    assert calculate_gst_cents(1) == 0

  def test_large_enterprise_amount(self):
    """$100,000.00 (10,000,000 cents) * 9 / 109 = 825,688.07 cents -> rounds to 825688 cents."""
    assert calculate_gst_cents(10000000) == 825688

  def test_zero_rated_item_flag(self):
    """Zero-rated supplies (exports/international services) are taxed at 0% GST.

    When is_zero_rated=True is passed, output GST must be 0 regardless of
    amount.
    """
    assert calculate_gst_cents(2500, is_zero_rated=True) == 0
    assert calculate_gst_cents(10000000, is_zero_rated=True) == 0

  def test_negative_amount_raises_value_error(self):
    """Negative amounts represent data corruption and must raise a ValueError."""
    with pytest.raises(ValueError, match="Amount cannot be negative"):
      calculate_gst_cents(-500)