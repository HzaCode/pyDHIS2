

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
  
  <!-- Test Status -->
  <a href="https://github.com/HzaCode/pydhis2/actions/workflows/ci.yml">
    <img src="https://github.com/HzaCode/pydhis2/actions/workflows/ci.yml/badge.svg" alt="CI">
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

<details>
<summary><strong>🚀 Getting Started</strong></summary>

**1. Installation**

```bash
pip install pydhis2
```

**2. Run the Quick Demo**

Use the CLI to run a quick demo that connects to a live DHIS2 server and fetches some data. This is the best way to verify your installation.

```bash
# Check installation
py -m pydhis2 version

# Run quick demo
py -m pydhis2 demo quick
```

You should see output confirming a successful connection and data retrieval:

```
============================================================
pydhis2 Quick Demo
============================================================
=== Testing: https://demos.dhis2.org/dq ===
   Found working API endpoint!
   System: Data Quality
   Version: 2.38.4.3
Found working server: https://demos.dhis2.org/dq

2. Querying Analytics data...
Retrieved 1 data records
...
Demo completed successfully!
```
</details>

<details>
<summary><strong>📖 Basic Usage</strong></summary>

Here's how to use `pydhis2` in your own script. Create a file named `examples/my_analysis.py`:

```python
import asyncio
import sys
from pydhis2 import get_client, DHIS2Config
from pydhis2.core.types import AnalyticsQuery

# Get client classes
AsyncDHIS2Client, SyncDHIS2Client = get_client()

async def main():
    # 1. Configure connection (using a working demo server)
    config = DHIS2Config(
        base_url="https://demos.dhis2.org/dq",
        auth=("demo", "District1#")
    )
  
    async with AsyncDHIS2Client(config) as client:
        # 2. Define query parameters
        query = AnalyticsQuery(
            dx=["b6mCG9sphIT"],   # Data element: ANC 1 Outlier Threshold
            ou="qzGX4XdWufs",    # Org unit: A-1 District Hospital
            pe="2023"            # Period: Year 2023
        )

        # 3. Fetch data and convert to a Pandas DataFrame
        df = await client.analytics.to_pandas(query)

        # 4. Analyze and display
        print("Data fetched successfully!")
        print(f"Retrieved {len(df)} records.")
        print("\n--- Data Preview ---")
        print(df.head())

if __name__ == "__main__":
    # Fix for asyncio on Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
```

Run your script from the terminal:

```bash
py examples/my_analysis.py
```
</details>

<details>
<summary><strong>🔧 DHIS2 Server Configuration</strong></summary>

The examples use public DHIS2 demo servers by default. To connect to your own server, you can configure it in one of the following ways:

**1. Environment Variables (Recommended)**
```bash
set DHIS2_URL=https://your-dhis2-server.com
set DHIS2_USERNAME=your_username
set DHIS2_PASSWORD=your_password

# Then run any script
py examples/my_analysis.py
```

**2. In Your Script**
```python
config = DHIS2Config(
    base_url="https://your-dhis2-server.com",  
    auth=("your_username", "your_password")
)
```

**3. Using the CLI**
```bash
py -m pydhis2 config --url "https://your-dhis2-server.com" --username "your_username"
```
</details>

<details>
<summary><strong>📚 More Examples</strong></summary>

The repository includes several scripts demonstrating different use cases:

| Script | Description |
|--------|-------------|
| `quick_demo.py` | Basic functionality and connection testing |
| `demo_test.py` | Comprehensive API testing with HTML reports |
| `real_health_data_demo.py` | Health data analysis with quality metrics |
| `my_analysis.py` | A template for your own custom analysis |

You can run any of them using the CLI or as standalone scripts:

```bash
# Run a specific demo via CLI
py -m pydhis2 demo health

# Or run the Python script directly
py examples/real_health_data_demo.py
```
</details>

<details>
<summary><strong>🖥️ Command Line Interface</strong></summary>

`pydhis2` provides a powerful CLI for common data operations.

**Data Operations (Implementation in Progress):**
```bash
# Pull analytics data
py -m pydhis2 analytics pull --dx "b6mCG9sphIT" --ou "qzGX4XdWufs" --pe "2023" --out analytics.parquet

# Pull tracker events
py -m pydhis2 tracker events --program "program_id" --out events.parquet

# Run data quality review
py -m pydhis2 dqr analyze --input analytics.parquet --html dqr_report.html --json dqr_summary.json
```

For detailed CLI usage, run `py -m pydhis2 --help`.
</details>

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

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details. Also, have a look at our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## 📞 Support

*   📖 **[Documentation](https://pydhis2.readthedocs.io)**
*   🐛 **[Issues](https://github.com/pydhis2/pydhis2/issues)**
*   💬 **[Discussions](https://github.com/pydhis2/pydhis2/discussions)**
