# {{ cookiecutter.project_name }}

{{ cookiecutter.project_description }}

## Project Structure

```
{{ cookiecutter.project_slug }}/
├── configs/          # Configuration files
├── data/            # Data files
├── notebooks/       # Jupyter notebooks
├── pipelines/       # Data pipeline configurations
├── reports/         # Generated reports
├── scripts/         # Script files
└── requirements.txt # Python dependencies
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure DHIS2 Connection

Copy `.env.example` to `.env` and fill in your DHIS2 connection details:

```bash
cp .env.example .env
```

Edit the `.env` file:

```
DHIS2_URL={{ cookiecutter.dhis2_url }}
DHIS2_USERNAME=your_username
DHIS2_PASSWORD=your_password
```

### 3. Test Connection

```bash
pydhis2 login
```

### 4. Run Example Pipeline

```bash
pydhis2 pipeline run --recipe pipelines/example.yml
```

## Usage Guide

### Data Pulling

Pull Analytics data:
```bash
pydhis2 analytics pull --dx "indicator_id" --ou "org_unit_id" --pe "2023Q1:2023Q4" --out data/analytics.parquet
```

Pull Tracker events:
```bash
pydhis2 tracker pull --program "program_id" --status COMPLETED --out data/events.parquet
```

### Data Quality Review

Run DQR analysis:
```bash
pydhis2 dqr run --input data/analytics.parquet --html reports/dqr_report.html --json reports/dqr_summary.json
```

### Jupyter Notebooks

{% if cookiecutter.use_notebooks == "yes" -%}
Start Jupyter Lab:
```bash
jupyter lab
```

Example notebooks:
- `01_data_exploration.ipynb` - Data Exploration
- `02_quality_assessment.ipynb` - Data Quality Assessment
- `03_analysis_and_visualization.ipynb` - Analysis and Visualization
{%- endif %}

## Configuration Details

### DHIS2 Configuration (`configs/dhis2.yml`)

```yaml
# DHIS2 connection configuration
connection:
  base_url: "{{ cookiecutter.dhis2_url }}"
  rps: 8                    # Requests per second
  concurrency: 8            # Concurrent connections
  timeouts: [10, 60, 120]   # Connect/read/total timeout

# Retry configuration
retry:
  max_attempts: 5
  base_delay: 0.5
  max_delay: 60.0
```

{% if cookiecutter.use_dqr == "yes" -%}
### DQR Configuration (`configs/dqr.yml`)

```yaml
# Data quality rules
completeness:
  thresholds:
    reporting_completeness_pass: 0.90
    reporting_completeness_warn: 0.70

consistency:
  thresholds:
    outlier_threshold: 3.0
    variance_threshold: 0.5

timeliness:
  thresholds:
    submission_timeliness_pass: 0.80
    max_delay_days: 30
```
{%- endif %}

{% if cookiecutter.use_pipeline == "yes" -%}
### Pipeline Configuration (`pipelines/example.yml`)

```yaml
name: "Example Data Analysis Pipeline"
description: "Pull data, assess quality, generate reports"

steps:
  - type: analytics_pull
    name: "Pull Analytics Data"
    dx: "indicator_id"
    ou: "org_unit_id" 
    pe: "2023Q1:2023Q4"
    output: "analytics.parquet"

  - type: dqr
    name: "Data Quality Review"
    input: "analytics.parquet"
    html_output: "dqr_report.html"
    json_output: "dqr_summary.json"
```
{%- endif %}

## License

{% if cookiecutter.license == "Apache-2.0" -%}
Apache License 2.0
{%- elif cookiecutter.license == "MIT" -%}
MIT License
{%- else -%}
BSD 3-Clause License
{%- endif %}

## Author

{{ cookiecutter.author_name }} ({{ cookiecutter.author_email }})
