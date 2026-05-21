"""Parser helpers in levels.py: row tokenisation, variant + pair-id
extraction. Pure functions, no pygame needed beyond import."""
from levels import _cell_variant, _pair_id, _split_cells

# --- _split_cells: dense vs whitespace ----------------------------------

def test_split_cells_dense_row():
    # Legacy format — no internal whitespace, each char is one cell.
    assert _split_cells("####") == ["#", "#", "#", "#"]


def test_split_cells_dense_with_mixed_glyphs():
    assert _split_cells(".p#G") == [".", "p", "#", "G"]


def test_split_cells_tokenised_row():
    # Any internal whitespace -> whitespace-separated tokens.
    assert _split_cells("T1 T2 T3") == ["T1", "T2", "T3"]


def test_split_cells_tokenised_preserves_multi_char_tokens():
    assert _split_cells("# T3 P2 G1") == ["#", "T3", "P2", "G1"]


def test_split_cells_trailing_whitespace_dense():
    # Trailing newline/whitespace must not flip a dense row into the
    # tokenised branch.
    assert _split_cells("abc\n") == ["a", "b", "c"]


# --- _cell_variant -------------------------------------------------------

def test_cell_variant_defaults_to_one():
    # No trailing digits -> variant 1 (the base tile).
    assert _cell_variant("T") == 1
    assert _cell_variant("#") == 1


def test_cell_variant_reads_trailing_digits():
    assert _cell_variant("T3") == 3
    assert _cell_variant("P12") == 12


def test_cell_variant_ignores_non_digit_tail():
    # Only fully-numeric tails count as a variant.
    assert _cell_variant("Tx") == 1


# --- _pair_id ------------------------------------------------------------

def test_pair_id_none_when_no_digits():
    # Distinct from _cell_variant: no explicit pair id -> None, meaning
    # "pair by reading order".
    assert _pair_id("L") is None
    assert _pair_id("P") is None


def test_pair_id_reads_trailing_digits():
    assert _pair_id("L1") == 1
    assert _pair_id("G7") == 7
    assert _pair_id("P12") == 12
