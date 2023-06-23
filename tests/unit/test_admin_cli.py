from click.testing import CliRunner

from src.admin_cli.commands.cache import seed


def test_seed_cache_missing_required_params():
    """Test confirms that if required parameters are not provided, CLI will signal usage error."""
    runner = CliRunner()
    result = runner.invoke(seed, [])
    assert result.exit_code == 2


def test_seed_cache_missing_invalid_from_zoom():
    """Test confirms that if from_zoom is less than to_zoom, CLI will signal a usage error."""
    runner = CliRunner()
    result = runner.invoke(seed, ["--from_zoom", 10, "--to_zoom", 8])
    assert result.exit_code == 2


def test_seed_cache_single_year():
    """Test confirms with valid required parameters, CLI executes without error."""
    runner = CliRunner()
    result = runner.invoke(seed, ["--to_zoom", 10, "--years", 2011, "--dry-run"])
    assert result.exit_code == 0


def test_seed_cache_multiple_years():
    """Test confirms that CLI can properly handle multiple years."""
    runner = CliRunner()
    result = runner.invoke(seed, ["--to_zoom", 10, "-y", 2011, "-y", 2012, "--dry-run"])
    assert result.exit_code == 0


def test_seed_cache_invalid_coverage_wkt():
    """Test confirms that an invalid WKT CLI will signal a usage error."""
    runner = CliRunner()
    result = runner.invoke(seed, ["--to_zoom", 10, "-y", 2011, "--coverage", "foo", "--dry-run"])
    assert result.exit_code == 2
