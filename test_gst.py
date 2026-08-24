from main import calculate_gst_cents
import pytest


def test_gst_exact_division():
  """Exact division: $10.90 (1,090 cents) * 9 / 109 = 90 cents ($0.90 GST)."""
  assert calculate_gst_cents(1090) == 90


def test_gst_half_cent_rounding_down():
  """Fractional cent strictly below 0.5 rounds down ($0.06 -> 0 cents)."""
  assert calculate_gst_cents(6) == 0


def test_gst_half_cent_rounding_up():
  """Fractional cent >= 0.5 rounds up ($0.07 -> 1 cent, $25.00 -> 206 cents)."""
  assert calculate_gst_cents(7) == 1
  assert calculate_gst_cents(2500) == 206


def test_gst_large_enterprise_amount():
  """High value transaction ($10,000.00 -> 82,569 cents GST)."""
  assert calculate_gst_cents(1000000) == 82569


def test_gst_zero_cents():
  """Zero transaction produces zero tax."""
  assert calculate_gst_cents(0) == 0