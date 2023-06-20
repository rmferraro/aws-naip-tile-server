from click.testing import CliRunner

from aws_naip_tile_server.admin.commands.cache import seed


def test_seed_cache_missing_to_zoom():
    runner = CliRunner()
    result = runner.invoke(seed, [])
    assert result.exit_code == 2
    assert "Missing option '--to_zoom'" in result.stdout


def test_seed_cache_missing_invalid_from_zoom():
    runner = CliRunner()
    result = runner.invoke(seed, ["--from_zoom", 10, "--to_zoom", 8])
    assert result.exit_code == 2
    assert "Invalid value: from_zoom must be less that to_zoom" in result.stdout


def test_seed_cache_single_year():
    runner = CliRunner()
    result = runner.invoke(seed, ["--to_zoom", 10, "--years", 2011, "--dry-run"])
    assert result.exit_code == 0


def test_seed_cache_multiple_years():
    runner = CliRunner()
    result = runner.invoke(seed, ["--to_zoom", 10, "-y", 2011, "-y", 2012, "--dry-run"])
    assert result.exit_code == 0


def test_seed_cache_invalid_coverage_wkt():
    runner = CliRunner()
    result = runner.invoke(seed, ["--to_zoom", 10, "-y", 2011, "--coverage", "foo", "--dry-run"])
    assert result.exit_code == 2
