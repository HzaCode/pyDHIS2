

<div align="center">
  <img src="image.png" alt="pydhis2 logo" width="220"/>

<p align="center">
  <!-- Pepy Weekly Downloads -->
  <a href="https://pepy.tech/project/pydhis2">
    
   [![Total Downloads](https://img.shields.io/pepy/dt/pydhis2?style=for-the-badge&color=306998&label=Downloads&logo=python)](https://pepy.tech/project/pydhis2)

  
  
  <!-- PyPI Version -->
  <a href="https://pypi.org/project/pydhis2">
    <img src="https://img.shields.io/pypi/v/pydhis2" alt="PyPI">
  </a>
  
  <!-- Python Version -->
  <a href="https://pypi.org/project/pydhis2/">
    <img src="https://img.shields.io/badge/python-≥3.9-blue" alt="Python">
  </a>
  
  <!-- License -->
  <a href="https://opensource.org/licenses/Apache-2.0">
    <img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="License">
  </a>
  
  <!-- Ruff -->
  <a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff">
  </a>
  
  <!-- In Submission -->
  <a href="#">
    <img src="https://img.shields.io/badge/status-in%20submission-lightgrey" alt="in submission">
  </a>
</p>


<p style="font-size:1.15rem; line-height:1.6;">
  <strong>Quite possibly the most complete python toolkit <em>for</em> DHIS2<br>— a modern SDK designed for reproducible workflows in LMIC scenarios.</strong>
</p>
</div>

---
## 🎉 `pydhis2` is officially released!

Get started in seconds.

### 📦 Installation

```bash
pip install pydhis2
```

Run the examples directly:

```bash
py quick_demo.py
```

**✨ Expected output:**

```
============================================================
pydhis2 Quick Demo
============================================================

1. Testing DHIS2 connection...
✅ Connection successful!
   System: DHIS2 Demo
   Version: 2.41.1
   URL: https://play.dhis2.org

2. Querying Analytics data...
✅ Retrieved 12 data records

3. Data preview:
------------------------------------------------------------
dataElement period organisationUnit  value
Uvn6LCg7dVU 202301      ImspTQPwCqd    335
Uvn6LCg7dVU 202302      ImspTQPwCqd    298
Uvn6LCg7dVU 202303      ImspTQPwCqd    343
Uvn6LCg7dVU 202304      ImspTQPwCqd    365
Uvn6LCg7dVU 202305      ImspTQPwCqd    416

4. Data statistics:
------------------------------------------------------------
   Total records: 12
   Sum of values: 3,789
   Average: 315.8
   Maximum: 498
   Minimum: 105

5. Monthly trends:
------------------------------------------------------------
   202301: █████████████████████████████████ 335
   202302: █████████████████████████████ 298
   202303: ██████████████████████████████████ 343
   202304: ████████████████████████████████████ 365
   202305: █████████████████████████████████████████ 416
   202306: ███████████████████████████████ 313
```
### Basic Usage in Your Project

Create a file named `my_analysis.py` and add the following code:

```python
import asyncio
from pydhis2 import AsyncDHIS2Client, DHIS2Config
from pydhis2.core.types import AnalyticsQuery

async def main():
    # 1. Configure connection
    config = DHIS2Config(
        base_url="https://play.dhis2.org/stable-2-41-1",
        auth=("admin", "district")
    )
  
    async with AsyncDHIS2Client(config) as client:
        # 2. Define query parameters
        query = AnalyticsQuery(
            dx=["Uvn6LCg7dVU"],  # Indicator: ANC 1st visit
            ou="ImspTQPwCqd",    # Org Unit: Sierra Leone
            pe="LAST_12_MONTHS"  # Period: Last 12 months
        )

        # 3. Fetch data and convert to a Pandas DataFrame
        df = await client.analytics.to_pandas(query)

        # 4. Analyze and display
        print("✅ Data fetched successfully!")
        print(f"Retrieved {len(df)} records.")
        print("\n--- Data Preview ---")
        print(df.head())
        print("\n--- Data Statistics ---")
        print(df['value'].describe())

if __name__ == "__main__":
    asyncio.run(main())
```

Run your script from the terminal:

```bash
py my_analysis.py
```

### 📚 Available Example Scripts

The repository includes several example scripts demonstrating different use cases:

| Script | Description | Usage |
|--------|-------------|-------|
| `quick_demo.py` | Basic functionality demo with connection testing and data analysis | `py quick_demo.py` |
| `demo_test.py` | Comprehensive API testing with data quality reports (HTML output) | `py demo_test.py` |
| `real_health_data_demo.py` | Health data analysis with quality metrics and insights | `py real_health_data_demo.py` |
| `paper.py` | Research paper material generation with visualizations | `py paper.py` |
| `my_analysis.py` | Template for custom analysis projects | `py my_analysis.py` |

**Run comprehensive examples:**

```bash
# Basic demo with connection testing
py quick_demo.py

# Full API testing with DQR report
py demo_test.py

# Health data analysis demo  
py real_health_data_demo.py

# Research paper material generation
py paper.py
```

**Expected outputs:**
- CSV data files with analysis results
- HTML quality reports (`dqr_demo_report.html`)
- Statistical summaries in JSON format
- Visualization charts (PNG format)
- Markdown reports for documentation

### 🖥️ Command Line Interface

`pydhis2` also provides a powerful CLI for common operations:

```bash
# Check version
pydhis2 version

# Configure connection
pydhis2 login --url "https://play.dhis2.org/dev" --username "admin"

# Pull analytics data
pydhis2 analytics pull --dx "Uvn6LCg7dVU" --ou "ImspTQPwCqd" --pe "LAST_12_MONTHS" --out analytics.parquet

# Pull tracker events  
pydhis2 tracker pull --program "program_id" --status COMPLETED --out events.parquet

# Run data quality review
pydhis2 dqr run --input analytics.parquet --html dqr_report.html --json dqr_summary.json

# Execute pipelines
pydhis2 pipeline run --recipe pipeline_config.yml
```

For detailed CLI usage, run `pydhis2 --help` or check individual command help with `pydhis2 <command> --help`.
<details>
<summary><strong>🚀 Reproducible Workflow: Using Project Templates</strong></summary>

Beyond being a library, `pydhis2` promotes a standardized and reproducible workflow crucial for scientific research. To jumpstart your analysis, we provide a project template powered by [Cookiecutter](https://cookiecutter.readthedocs.io/).

**Why use the template?**

*   **Standardization**: Every project starts with the same clean, logical structure. No more guessing where configs or scripts are.
*   **Rapid Start**: Generate a fully functional project skeleton with a single command.
*   **Best Practices**: The template includes pre-configured settings for DHIS2 connection, data quality pipelines, and environment management.
*   **Focus on Analysis**: Spend less time on boilerplate setup and more time on your research.

### Usage

1.  **Install Cookiecutter:**
    ```bash
    pip install cookiecutter
    ```

2.  **Generate your project:**
    Run Cookiecutter and point it to the `pydhis2` template. It will ask you a few questions to personalize your new project.

    ```bash
    # Run from the root of the pydhis2 repository
    cookiecutter pydhis2/templates
    ```

    You'll be prompted for details like your project name and author info:
    ```
    project_name [My DHIS-2 Analysis Project]: Malaria Analysis Malawi
    project_slug [malaria_analysis_malawi]:
    author_name [Your Name]: Dr. Evans
    author_email [your.email@example.com]: evans@who.int
    ```

3.  **Get a complete, ready-to-use project structure:**
    ```
    malaria-analysis-malawi/
    ├── configs/          # DHIS-2 & DQR configurations
    ├── data/             # For raw and processed data
    ├── pipelines/        # Your analysis pipeline definitions
    ├── scripts/          # Runner scripts
    ├── .env.example      # Environment variable template
    └── README.md         # A dedicated README for your new project
    ```

Now you can `cd` into your new project directory and start your analysis immediately!

</details>

---

## 📊 Supported Endpoints

| Endpoint | Read | Write | DataFrame | Pagination | Streaming |
| :--- | :--: | :--: | :----: | :--: | :----: |
| **Analytics** | ✅ | - | ✅ | ✅ | ✅ |
| **DataValueSets** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Tracker Events** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Metadata** | ✅ | ✅ | ✅ | - | - |

---

## 📋 Compatibility

*   **Python**: ≥ 3.9
*   **DHIS2**: ≥ 2.36
*   **Platforms**: Windows, Linux, macOS

---

## 📄 License

**Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## 📞 Support

*   📖 **[Documentation](https://pydhis2.readthedocs.io)**
*   🐛 **[Issues](https://github.com/pydhis2/pydhis2/issues)**
*   💬 **[Discussions](https://github.com/pydhis2/pydhis2/discussions)**
