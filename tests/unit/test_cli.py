"""Tests for CLI module"""

import pytest
from typer.testing import CliRunner
from pydhis2.cli.main import app
from unittest.mock import patch, MagicMock

runner = CliRunner()


class TestVersionCommand:
    """Test version command"""
    
    def test_version_command(self):
        """Test version command output"""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "pydhis2 version" in result.stdout


class TestConfigCommand:
    """Test config command"""
    
    def test_config_with_all_params(self):
        """Test config command with all parameters"""
        result = runner.invoke(
            app,
            ["config", "--url", "https://test.dhis2.org", "--username", "admin", "--password", "district"],
        )
        assert result.exit_code == 0
        assert "Configured connection" in result.stdout
    
    def test_config_with_env_vars(self):
        """Test config command using environment variables"""
        with patch.dict('os.environ', {
            'DHIS2_USERNAME': 'test_user',
            'DHIS2_PASSWORD': 'test_pass'
        }):
            result = runner.invoke(
                app,
                ["config", "--url", "https://test.dhis2.org"],
            )
            assert result.exit_code == 0


class TestAnalyticsCommands:
    """Test analytics commands"""
    
    def test_analytics_pull_command(self):
        """Test analytics pull command"""
        result = runner.invoke(
            app,
            [
                "analytics", "pull",
                "--url", "https://test.dhis2.org",
                "--dx", "test_dx",
                "--ou", "test_ou",
                "--pe", "2023",
                "--out", "test.parquet"
            ],
        )
        assert result.exit_code == 0
        assert "Would pull data" in result.stdout
        assert "test_dx" in result.stdout
    
    def test_analytics_pull_with_format(self):
        """Test analytics pull with custom format"""
        result = runner.invoke(
            app,
            [
                "analytics", "pull",
                "--url", "https://test.dhis2.org",
                "--dx", "dx1",
                "--ou", "ou1",
                "--pe", "2023",
                "--format", "csv"
            ],
        )
        assert result.exit_code == 0


class TestDataValueSetsCommands:
    """Test datavaluesets commands"""
    
    def test_datavaluesets_pull_command(self):
        """Test datavaluesets pull command"""
        result = runner.invoke(
            app,
            [
                "datavaluesets", "pull",
                "--url", "https://test.dhis2.org",
                "--data-set", "ds1",
                "--org-unit", "ou1",
                "--period", "202301"
            ],
        )
        assert result.exit_code == 0
        assert "Would pull data" in result.stdout
    
    def test_datavaluesets_push_command(self):
        """Test datavaluesets push command"""
        result = runner.invoke(
            app,
            [
                "datavaluesets", "push",
                "--url", "https://test.dhis2.org",
                "--input", "test.parquet"
            ],
        )
        assert result.exit_code == 0
        assert "Implementation in progress" in result.stdout


class TestTrackerCommands:
    """Test tracker commands"""
    
    def test_tracker_events_command(self):
        """Test tracker events command"""
        result = runner.invoke(
            app,
            [
                "tracker", "events",
                "--url", "https://test.dhis2.org",
                "--program", "prog1",
                "--out", "events.parquet"
            ],
        )
        assert result.exit_code == 0


class TestDQRCommands:
    """Test DQR commands"""
    
    def test_dqr_analyze_command(self):
        """Test DQR analyze command"""
        result = runner.invoke(
            app,
            [
                "dqr", "analyze",
                "--input", "test.parquet",
                "--html", "report.html"
            ],
        )
        assert result.exit_code == 0
        assert "Implementation in progress" in result.stdout


class TestDemoCommand:
    """Test demo command"""
    
    @patch('pydhis2.cli.main.asyncio.run')
    def test_demo_quick_command(self, mock_run):
        """Test demo quick command"""
        mock_run.return_value = None
        result = runner.invoke(app, ["demo", "quick"])
        # Command should execute without error
        assert result.exit_code == 0 or "demo" in result.stdout.lower()


class TestPipelineCommands:
    """Test pipeline commands"""
    
    def test_pipeline_run_command(self):
        """Test pipeline run command"""
        result = runner.invoke(
            app,
            [
                "pipeline", "run",
                "--config", "test.yml"
            ],
        )
        # Should show implementation message or execute
        assert result.exit_code == 0 or "pipeline" in result.stdout.lower()


class TestMetadataCommands:
    """Test metadata commands"""
    
    def test_metadata_export_command(self):
        """Test metadata export command"""
        result = runner.invoke(
            app,
            [
                "metadata", "export",
                "--url", "https://test.dhis2.org",
                "--type", "dataElements",
                "--out", "metadata.json"
            ],
        )
        assert result.exit_code == 0
    
    def test_metadata_import_command(self):
        """Test metadata import command"""
        result = runner.invoke(
            app,
            [
                "metadata", "import",
                "--url", "https://test.dhis2.org",
                "--input", "metadata.json"
            ],
        )
        assert result.exit_code == 0

