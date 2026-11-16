from pywinauto import Desktop
from pywinauto.uia_defines import IUIA

U = IUIA()
D = Desktop(backend="uia")
for w in D.windows():
    n = w.element_info.name
    if n and ("AICA" in n or "Project" in n or "Export" in n):
        print("TOP:", repr(n), w.element_info.control_type, w.is_visible())
w = D.window(title_re=".*AICA Folder Storage Manager$", control_type="Window").wrapper_object()
for c in w.descendants():
    ei = c.element_info
    if ei.control_type in ("Window", "Button", "Text", "Table", "ListItem"):
        e = ei.element
        try:
            fd = e.GetCurrentPropertyValue(30159)
        except Exception:
            fd = "?"
        print(ei.control_type, "|", repr(ei.name)[:70], "| help:", repr(e.CurrentHelpText)[:40], "| fulldesc:", repr(fd)[:40],
              "| offscreen:", e.CurrentIsOffscreen)
