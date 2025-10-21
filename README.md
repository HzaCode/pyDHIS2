

<div align="center">
  <img src="image.png" alt="pydhis2 logo" width="220"/>

  <h1>pydhis2</h1>

  <p>
    <strong>A modern Python SDK for DHIS2, designed for robust and reproducible scientific workflows.</strong>
  </p>

<p align="center">
  <!-- Pepy Weekly Downloads -->
  <a href="https://pepy.tech/project/pydhis2">
    <img src="https://img.shields.io/pepy/dt/pydhis2?style=for-the-badge&color=306998&label=Downloads&logo=python" alt="Total Downloads on Pepy">
  </a>
  <!-- PyPI Version -->
  <a href="https://pypi.org/project/pydhis2">
    <img src="https://img.shields.io/pypi/v/pydhis2.svg?style=for-the-badge" alt="PyPI version">
  </a>
  <!-- Python Version -->
  <a href="https://pypi.org/project/pydhis2/">
    <img src="https://img.shields.io/pypi/pyversions/pydhis2.svg?style=for-the-badge" alt="Supported Python versions">
  </a>
  <!-- Test Status -->
  <a href="https://github.com/HzaCode/pydhis2/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/HzaCode/pydhis2/ci.yml?style=for-the-badge&logo=github" alt="CI Test Status">
  </a>
  <!-- License -->
  <a href="https://opensource.org/licenses/Apache-2.0">
    <img src="https://img.shields.io/badge/License-Apache%202.0-green.svg?style=for-the-badge" alt="License: Apache 2.0">
  </a>
  <!-- Ruff -->
  <a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=for-the-badge" alt="Code style: Ruff">
  </a>
</p>
</div>

`pydhis2` is a next-generation Python library for interacting with [DHIS2](https://www.dhis2.org/), the world's largest health information management system. It provides a clean, modern, and efficient API for data extraction, analysis, and management, with a strong emphasis on creating reproducible workflows—a critical need in scientific research and public health analysis, especially in Low and Middle-Income Country (LMIC) contexts.

---

## ✨ Why `pydhis2`?

*   🚀 **Modern & Asynchronous:** Built with `asyncio` for high-performance, non-blocking I/O, making it ideal for large-scale data operations. A synchronous client is also provided for simplicity in smaller scripts.
*    reproducible **Reproducible by Design:** From project templates to a powerful CLI, `pydhis2` is built to support standardized, shareable, and verifiable data analysis pipelines.
*   🐼 **Seamless DataFrame Integration:** Natively convert DHIS2 analytics data into Pandas DataFrames with a single method call (`.to_pandas()`), connecting you instantly to the PyData ecosystem.
*   🔧 **Powerful Command Line Interface:** Automate common tasks like data pulling and configuration directly from your terminal.


## 🚀 Getting Started

### 1. Installation

Install `pydhis2` directly from PyPI:

```bash
pip install pydhis2
```

### 2. Verify Your Installation

Use the built-in CLI to run a quick demo. This will connect to a live DHIS2 server, fetch data, and confirm that your installation is working correctly.

```bash
# Check the installed version
pydhis2 version

# Run the quick demo
pydhis2 demo quick
```

A successful run will produce the following output:
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

## 📖 Basic Usage

Here is a simple example of how to use `pydhis2` in a Python script to fetch analytics data and load it into a Pandas DataFrame.

Create a file named `my_analysis.py`:

```python
import asyncio
import sys
from pydhis2 import get_client, DHIS2Config
from pydhis2.core.types import AnalyticsQuery

# pydhis2 provides both an async and a sync client
AsyncDHIS2Client, _ = get_client()

async def main():
    # 1. Configure the connection to a DHIS2 server
    config = DHIS2Config(
        base_url="https://demos.dhis2.org/dq",
        auth=("demo", "District1#")
    )
  
    async with AsyncDHIS2Client(config) as client:
        # 2. Define the query parameters
        query = AnalyticsQuery(
            dx=["b6mCG9sphIT"],   # Data element: ANC 1 Outlier Threshold
            ou="qzGX4XdWufs",    # Org unit: A-1 District Hospital
            pe="2023"            # Period: Year 2023
        )

        # 3. Fetch data and convert it directly to a Pandas DataFrame
        df = await client.analytics.to_pandas(query)

        # 4. Analyze and display the results
        print("✅ Data fetched successfully!")
        print(f"Retrieved {len(df)} records.")
        print("\n--- Data Preview ---")
        print(df.head())

if __name__ == "__main__":
    # Standard fix for asyncio on Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
```

Run your script from the terminal:
```bash
python my_analysis.py
```

## 🔧 Server Configuration

While you can pass credentials directly in your script, we recommend using environment variables for better security and flexibility.

**1. Environment Variables (Recommended)**
```bash
export DHIS2_URL="https://your-dhis2-server.com"
export DHIS2_USERNAME="your_username"
export DHIS2_PASSWORD="your_password"
```
`pydhis2` will automatically detect and use these variables.

**2. In-Script Configuration**
```python
from pydhis2 import DHIS2Config

config = DHIS2Config(
    base_url="https://your-dhis2-server.com",  
    auth=("your_username", "your_password")
)
```

**3. Using the CLI**
The CLI provides a convenient way to set and cache your credentials.
```bash
pydhis2 config --url "https://your-dhis2-server.com" --username "your_username"
```

## 🏗️ A Reproducible Workflow: Project Templates

Beyond being a library, `pydhis2` promotes a standardized workflow that is essential for scientific research. To jumpstart your analysis, we provide a project template powered by [Cookiecutter](https://cookiecutter.readthedocs.io/).

**Why use the template?**

*   **Standardization**: Ensures every project starts with a clean, logical structure.
*   **Rapid Start**: Generate a fully functional project skeleton in a single command.
*   **Best Practices**: Includes pre-configured settings for DHIS2 connections, data quality pipelines, and environment management.
*   **Focus on Analysis**: Spend less time on boilerplate setup and more time on your research.

### How to Use

1.  **Install Cookiecutter:**
    ```bash
    pip install cookiecutter
    ```

2.  **Generate your project:**
    Point Cookiecutter to the `pydhis2` template. It will prompt you for project details.

    ```bash
    cookiecutter gh:HzaCode/pydhis2 --directory pydhis2/templates
    ```

    You'll be prompted for details like your project name and author:
    ```
    project_name [My DHIS-2 Analysis Project]: Malaria Analysis Malawi
    project_slug [malaria_analysis_malawi]:
    author_name [Your Name]: Dr. Evans
    ```

3.  **Get a complete, ready-to-use project structure:**
    ```
    malaria-analysis-malawi/
    ├── configs/          # DHIS-2 & DQR configurations
    ├── data/             # Raw and processed data
    ├── pipelines/        # Analysis pipeline definitions
    ├── scripts/          # Runner scripts
    ├── .env.example      # Environment variable template
    └── README.md         # A dedicated README for your new project
    ```

You can now `cd` into your new project directory and begin your analysis immediately!

## 🖥️ Command Line Interface

`pydhis2` provides a powerful CLI for common data operations. *(Note: Implementation is in progress)*

```bash
# Pull analytics data and save as Parquet
pydhis2 analytics pull --dx "b6mCG9sphIT" --ou "qzGX4XdWufs" --pe "2023" --out analytics.parquet

# Pull tracker events
pydhis2 tracker events --program "program_id" --out events.parquet

# Run a data quality review
pydhis2 dqr analyze --input analytics.parquet --html dqr_report.html
```

For a full list of commands, run `pydhis2 --help`.

## 📊 Supported Endpoints

| Endpoint | Read | Write | DataFrame | Pagination | Streaming |
| :--- | :--: | :--: | :----: | :--: | :----: |
| **Analytics** | ✅ | - | ✅ | ✅ | ✅ |
| **DataValueSets** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Tracker Events** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Metadata** | ✅ | ✅ | ✅ | - | - |

## 📋 Compatibility

*   **Python**: ≥ 3.9
*   **DHIS2**: ≥ 2.36
*   **Platforms**: Windows, Linux, macOS

## 🤝 Contributing

Contributions are welcome and highly encouraged! `pydhis2` is a community-driven project, and we believe that collaboration is key to building robust and useful tools for the open-science community.

Please see our [**Contributing Guide**](CONTRIBUTING.md) for details on how to get started. Also, be sure to review our [**Code of Conduct**](CODE_OF_CONDUCT.md).

## 📞 Community & Support

*   📖 **[Documentation](https://pydhis2.readthedocs.io)**: For in-depth guides and API references.
*   🐛 **[GitHub Issues](https://github.com/pydhis2/pydhis2/issues)**: To report bugs or request new features.
*   💬 **[GitHub Discussions](https://github.com/pydhis2/pydhis2/discussions)**: For questions, ideas, and community conversation.

## 📄 License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for details.
