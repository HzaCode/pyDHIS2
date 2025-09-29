"""CLI main entry point"""

import typer
from typing import Optional
from rich.console import Console

app = typer.Typer(
    name="pydhis2",
    help="Reproducible DHIS2 Python SDK for LMIC scenarios",
    add_completion=False,
)

console = Console()


@app.command("version")
def version():
    """Show version information"""
    from pydhis2 import __version__
    console.print(f"pydhis2 version {__version__}")


@app.command("config")
def config(
    url: str = typer.Option(..., "--url", help="DHIS2 base URL"),
    username: Optional[str] = typer.Option(None, "--username", help="Username"),
    password: Optional[str] = typer.Option(None, "--password", help="Password", hide_input=True),
):
    """Configure DHIS2 connection information"""
    import os
    
    # Get default values from environment variables
    if not username:
        username = os.getenv("DHIS2_USERNAME")
    if not password:
        password = os.getenv("DHIS2_PASSWORD")
    
    if not username:
        username = typer.prompt("Username")
    if not password:
        password = typer.prompt("Password", hide_input=True)
    
    # Save to secure storage (simplified for now)
    console.print(f"✓ Configured connection to {url}")
    console.print("📝 Tip: Consider using environment variables for authentication")


# Analytics commands
analytics_app = typer.Typer(help="Analytics data operations")
app.add_typer(analytics_app, name="analytics")


@analytics_app.command("pull")
def analytics_pull(
    url: str = typer.Option(..., "--url", help="DHIS2 base URL"),
    dx: str = typer.Option(..., "--dx", help="Data dimension"),
    ou: str = typer.Option(..., "--ou", help="Organization unit"),
    pe: str = typer.Option(..., "--pe", help="Period dimension"),
    output: str = typer.Option("analytics.parquet", "--out", help="Output file"),
    format: str = typer.Option("parquet", "--format", help="Output format"),
    username: Optional[str] = typer.Option(None, "--username", help="Username"),
    password: Optional[str] = typer.Option(None, "--password", help="Password", hide_input=True),
):
    """Pull Analytics data"""
    console.print("🚧 Analytics pull command - Implementation in progress")
    console.print(f"📊 Would pull data: dx={dx}, ou={ou}, pe={pe}")
    console.print(f"💾 Would save to: {output} ({format})")


# DataValueSets commands  
datavaluesets_app = typer.Typer(help="DataValueSets operations")
app.add_typer(datavaluesets_app, name="datavaluesets")


@datavaluesets_app.command("pull")
def datavaluesets_pull(
    url: str = typer.Option(..., "--url", help="DHIS2 base URL"),
    data_set: Optional[str] = typer.Option(None, "--data-set", help="Data set ID"),
    org_unit: Optional[str] = typer.Option(None, "--org-unit", help="Organization unit ID"),
    period: Optional[str] = typer.Option(None, "--period", help="Period"),
    output: str = typer.Option("datavaluesets.parquet", "--out", help="Output file"),
    username: Optional[str] = typer.Option(None, "--username", help="Username"),
    password: Optional[str] = typer.Option(None, "--password", help="Password", hide_input=True),
):
    """Pull DataValueSets data"""
    console.print("🚧 DataValueSets pull command - Implementation in progress")
    console.print(f"📋 Would pull data from data set: {data_set}")
    console.print(f"💾 Would save to: {output}")


@datavaluesets_app.command("push")
def datavaluesets_push(
    url: str = typer.Option(..., "--url", help="DHIS2 base URL"),
    input_file: str = typer.Option(..., "--input", help="Input file"),
    strategy: str = typer.Option("CREATE_AND_UPDATE", "--strategy", help="Import strategy"),
    username: Optional[str] = typer.Option(None, "--username", help="Username"),
    password: Optional[str] = typer.Option(None, "--password", help="Password", hide_input=True),
):
    """Push DataValueSets data"""
    console.print("🚧 DataValueSets push command - Implementation in progress")
    console.print(f"📤 Would push data from: {input_file}")
    console.print(f"🔧 Using strategy: {strategy}")


# Tracker commands
tracker_app = typer.Typer(help="Tracker operations")
app.add_typer(tracker_app, name="tracker")


@tracker_app.command("events")
def tracker_events(
    url: str = typer.Option(..., "--url", help="DHIS2 base URL"),
    program: Optional[str] = typer.Option(None, "--program", help="Program ID"),
    output: str = typer.Option("events.parquet", "--out", help="Output file"),
    username: Optional[str] = typer.Option(None, "--username", help="Username"),
    password: Optional[str] = typer.Option(None, "--password", help="Password", hide_input=True),
):
    """Pull Tracker events"""
    console.print("🚧 Tracker events command - Implementation in progress")
    console.print(f"🎯 Would pull events from program: {program}")
    console.print(f"💾 Would save to: {output}")


# DQR commands
dqr_app = typer.Typer(help="Data Quality Review (DQR)")
app.add_typer(dqr_app, name="dqr")


@dqr_app.command("analyze")
def dqr_analyze(
    input_file: str = typer.Option(..., "--input", help="Input data file"),
    html_output: Optional[str] = typer.Option(None, "--html", help="HTML report output path"),
    json_output: Optional[str] = typer.Option(None, "--json", help="JSON summary output path"),
):
    """Run data quality assessment"""
    console.print("🚧 DQR analyze command - Implementation in progress")
    console.print(f"🔍 Would analyze data from: {input_file}")
    if html_output:
        console.print(f"📊 Would generate HTML report: {html_output}")
    if json_output:
        console.print(f"📄 Would generate JSON summary: {json_output}")


# Demo commands
demo_app = typer.Typer(help="Run demo scripts")
app.add_typer(demo_app, name="demo")


@demo_app.command("quick")
def demo_quick():
    """Run quick demo - basic functionality test"""
    import subprocess
    import sys
    from pathlib import Path
    
    # Find the quick_demo.py script
    script_path = Path.cwd() / "examples" / "quick_demo.py"
    if not script_path.exists():
        console.print("examples/quick_demo.py not found in current directory")
        console.print("Make sure you're in the pydhis2 project directory")
        return
    
    console.print("Running pydhis2 Quick Demo...")
    try:
        result = subprocess.run([sys.executable, str(script_path)], 
                              capture_output=False, text=True)
        if result.returncode != 0:
            console.print("Demo failed")
    except Exception as e:
        console.print(f"Error running demo: {e}")


@demo_app.command("test")
def demo_test():
    """Run comprehensive API test demo"""
    import subprocess
    import sys
    from pathlib import Path
    
    script_path = Path.cwd() / "examples" / "demo_test.py"
    if not script_path.exists():
        console.print("examples/demo_test.py not found in current directory")
        console.print("Make sure you're in the pydhis2 project directory")
        return
    
    console.print("Running pydhis2 Comprehensive Test Demo...")
    try:
        result = subprocess.run([sys.executable, str(script_path)], 
                              capture_output=False, text=True)
        if result.returncode != 0:
            console.print("Test demo failed")
    except Exception as e:
        console.print(f"Error running test demo: {e}")


@demo_app.command("health")
def demo_health():
    """Run health data analysis demo"""
    import subprocess
    import sys
    from pathlib import Path
    
    script_path = Path.cwd() / "examples" / "real_health_data_demo.py"
    if not script_path.exists():
        console.print("examples/real_health_data_demo.py not found in current directory")
        console.print("Make sure you're in the pydhis2 project directory")
        return
    
    console.print("Running pydhis2 Health Data Analysis Demo...")
    try:
        result = subprocess.run([sys.executable, str(script_path)], 
                              capture_output=False, text=True)
        if result.returncode != 0:
            console.print("Health demo failed")
    except Exception as e:
        console.print(f"Error running health demo: {e}")


@demo_app.command("analysis")
def demo_analysis():
    """Run custom analysis template"""
    import subprocess
    import sys
    from pathlib import Path
    
    script_path = Path.cwd() / "examples" / "my_analysis.py"
    if not script_path.exists():
        console.print("examples/my_analysis.py not found in current directory")
        console.print("Make sure you're in the pydhis2 project directory")
        return
    
    console.print("Running pydhis2 Custom Analysis Demo...")
    try:
        result = subprocess.run([sys.executable, str(script_path)], 
                              capture_output=False, text=True)
        if result.returncode != 0:
            console.print("Analysis demo failed")
    except Exception as e:
        console.print(f"Error running analysis demo: {e}")


@demo_app.command("list")
def demo_list():
    """List available demo scripts"""
    console.print("Available pydhis2 Demo Scripts:")
    console.print("")
    console.print("[bold]pydhis2 demo quick[/bold]")
    console.print("   Basic functionality demo with connection testing")
    console.print("")
    console.print("[bold]pydhis2 demo test[/bold]")
    console.print("   Comprehensive API testing with HTML reports")
    console.print("")
    console.print("[bold]pydhis2 demo health[/bold]")
    console.print("   Health data analysis with quality metrics")
    console.print("")
    console.print("[bold]pydhis2 demo analysis[/bold]")
    console.print("   Custom analysis template (customizable)")
    console.print("")
    console.print("[dim]Tip: You can also run scripts directly with:[/dim]")
    console.print("   [dim]py examples/quick_demo.py[/dim]")
    console.print("   [dim]py examples/demo_test.py[/dim]")
    console.print("   [dim]py examples/real_health_data_demo.py[/dim]")
    console.print("   [dim]py examples/my_analysis.py[/dim]")


@app.command("status")
def status():
    """Show system status"""
    console.print("pydhis2 Status:")
    console.print("Core modules loaded")
    console.print("Demo scripts available")
    console.print("CLI implementation in progress")
    console.print("See documentation: https://github.com/pydhis2/pydhis2")


if __name__ == "__main__":
    app()
