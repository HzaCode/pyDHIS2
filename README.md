
<div align="center">
  <img src="image.png" alt="pydhis2 logo" width="180"/>

[![PyPI](https://img.shields.io/pypi/v/pydhis2?style=flat-square)](https://pypi.org/project/pydhis2)
[![Python](https://img.shields.io/badge/python-≥3.9-blue.svg?style=flat-square)](https://pypi.org/project/pydhis2/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg?style=flat-square)](https://opensource.org/licenses/Apache-2.0)
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/psf/black)



***Built for Real-World LMIC Conditions***

</div>




---

## 🚀 Quick Start

### Installation

```bash
pip install pydhis2
````
Run directly:
```bash
python quick_start.py
```

**Expected output:**
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

**Expected output:**
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
---

## 📊 Supported Endpoints

| Endpoint       | Read | Write | DataFrame | Pagination | Streaming |
| -------------- | ---- | ----- | --------- | ---------- | --------- |
| Analytics      | ✅    | -     | ✅         | ✅          | ✅         |
| DataValueSets  | ✅    | ✅     | ✅         | ✅          | ✅         |
| Tracker Events | ✅    | ✅     | ✅         | ✅          | ✅         |
| Metadata       | ✅    | ✅     | ✅         | -          | -         |

---

## 📋 Compatibility

* **Python**: ≥ 3.9
* **DHIS2**: ≥ 2.36
* **Platforms**: Windows, Linux, macOS

---

## 📄 License

Apache License 2.0 - see [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## 📞 Support

* 📖 [Documentation](https://pydhis2.readthedocs.io)
* 🐛 [Issues](https://github.com/pydhis2/pydhis2/issues)
* 💬 [Discussions](https://github.com/pydhis2/pydhis2/discussions)


