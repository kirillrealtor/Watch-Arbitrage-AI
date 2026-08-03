import pytest

from chronoarb.domain.ulid import generate_ulid


class TestUlidGeneration:
    def test_generated_ulid_starts_with_prefix(self):
        ulid = generate_ulid("org")
        assert ulid.startswith("org_")

    def test_generated_ulid_length_is_consistent(self):
        ulid = generate_ulid("usr")
        parts = ulid.split("_")
        assert len(parts) == 2
        assert len(parts[1]) == 28

    def test_generated_ulid_is_unique_across_iterations(self):
        ulids = {generate_ulid("lst") for _ in range(1000)}
        assert len(ulids) == 1000

    def test_generated_ulid_is_string(self):
        ulid = generate_ulid("opp")
        assert isinstance(ulid, str)

    def test_generated_ulid_uses_valid_base32_chars(self):
        ulid = generate_ulid("trc")
        encoded = ulid.split("_")[1]
        valid_chars = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
        assert all(c in valid_chars for c in encoded)

    def test_generated_ulids_have_monotonic_timestamps(self):
        ulids = [generate_ulid("evt") for _ in range(100)]
        timestamps = [ulid.split("_")[1][:10] for ulid in ulids]
        assert timestamps == sorted(timestamps)


class TestUlidPrefixValidation:
    def test_empty_prefix_raises(self):
        with pytest.raises(ValueError, match="1-5"):
            generate_ulid("")

    def test_prefix_too_long_raises(self):
        with pytest.raises(ValueError, match="1-5"):
            generate_ulid("toolong")

    def test_uppercase_prefix_raises(self):
        with pytest.raises(ValueError, match="lowercase"):
            generate_ulid("ORG")

    def test_single_char_prefix_works(self):
        ulid = generate_ulid("x")
        assert ulid.startswith("x_")
