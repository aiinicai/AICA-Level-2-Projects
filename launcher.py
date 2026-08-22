import webview
import os
import sys


def resource_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


html_file = resource_path('IncomeTaxCalculator_SB.html')
url = 'file:///' + html_file.replace('\\', '/')

webview.create_window(
    title='Income Tax Calculator | Tax Comp',
    url=url,
    width=1280,
    height=800,
    resizable=True,
    min_size=(900, 600),
)

webview.start()
