# Third-party components

The application uses Python, PySide6/Qt, pandas/NumPy, requests and dependencies, feedparser, tzdata, windows-toasts/WinRT and keyring. PyInstaller produces the executable. Exact installed versions are in requirements-lock.txt. Dependency metadata and available licence texts are copied into docs/licenses by scripts/collect_notices.py.

PySide6/Qt has open-source and commercial licensing options, with conditions that depend on the actual modules distributed. This build uses dynamically linked Qt Core, Gui, Widgets and SVG functionality; unused web and chart modules are excluded. Preserve applicable notices and users' rights concerning the Qt libraries when redistributing. Review the exact bundled components and their licence texts before commercial distribution. The presence of PySide6 does not grant rights to financial data.

No project-wide third-party licence is assigned to Finstock's original source. The project owner must choose its release licence. The source package accompanies this build; dependency source availability and other distribution obligations still require release review. Icons are original project artwork. System Segoe UI fonts were used for screenshot capture and are not copied into the distribution.
