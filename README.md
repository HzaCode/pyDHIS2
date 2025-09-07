

<div align="center">
  <img src="image.png" alt="pydhis2 logo" width="220"/>

  <p>
    <a href="https://pypi.org/project/pydhis2"><img src="https://img.shields.io/pypi/v/pydhis2?style=for-the-badge" alt="PyPI"></a>
    <a href="https://pypi.org/project/pydhis2/"><img src="https://img.shields.io/badge/python-≥3.9-blue.svg?style=for-the-badge" alt="Python"></a>
    <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/license-Apache%202.0-green.svg?style=for-the-badge" alt="License"></a>
    <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge" alt="Black"></a>
  </p>

  <p>
    <strong>Modern Python SDK for DHIS2, designed for LMIC scenarios with reproducible workflows</strong>
  </p>
</div>

---

## 🚀 Quick Start

### 📦 Installation

```bash
pip install pydhis2
```

Run the examples directly:

```bash
python quick_start.py
```

**✨ Expected output:**

```
✅ Connection successful! DHIS2 version: 2.41.1

📊 Retrieved 144 data records

Data preview:
   dataElement    period organisationUnit  value
0  Uvn6LCg7dVU   202301      fdc6uOvgoji    189
1  Uvn6LCg7dVU   202301      ImspTQPwCqd   3503
2  Uvn6LCg7dVU   202301      O6uvpzGd5pu    436
3  Uvn6LCg7dVU   202301      kJq2mPyFEHo    560
4  Uvn6LCg7dVU   202301      Vth0fbpFcsO    243

📈 Data statistics:
   Total: 59,326
   Average: 412.0
   Maximum: 3,503
   Minimum: 39
```

```bash
python quick_demo.py
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

**Or run the comprehensive examples:**

```bash
# Run the paper experiment script
python paper.py

# Run the health data demo
python real_health_data_demo.py
```
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

---

*pydhis2: Quite possibly the most complete toolkit for DHIS2.*
