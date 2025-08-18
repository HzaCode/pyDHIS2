
<div align="center">
  <img src="image.png" alt="pydhis2 logo" width="180"/>

[![PyPI](https://img.shields.io/pypi/v/pydhis2?style=flat-square)](https://pypi.org/project/pydhis2)
[![Python](https://img.shields.io/badge/python-≥3.9-blue.svg?style=flat-square)](https://pypi.org/project/pydhis2/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg?style=flat-square)](https://opensource.org/licenses/Apache-2.0)
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/psf/black)

---

***A reproducible DHIS2 Python SDK for LMIC scenarios***

</div>


## ✨ Core Features

- 🚀 **Async-First**: Built on `aiohttp` with connection pooling, session reuse, and exponential backoff retry  
- 📊 **First-Class Data Support**: One-click conversion to Pandas/Arrow for core endpoints, streaming support  
- ⚡ **Rate Limiting & Retry**: Configurable rate limits, smart backoff, respects `Retry-After` headers  
- 🌐 **LMIC Optimized**: Conservative defaults, resumable transfers, optimized for low-bandwidth environments  
- 🛠️ **CLI Support**: Command-line tools for common operations  
- 📈 **Observability**: Built-in metrics collection and structured logging  

---

## 🚀 Quick Start

### Installation

```bash
pip install pydhis2
````

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

---

<p align="center"><i>pydhis2 — Making DHIS2 data analysis simpler and more reliable</i></p>

