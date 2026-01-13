

import os
from .controller import ChargePointController
import webview

print('__main__.py: in __main__ block')
print('__main__.py: before controller')
controller = ChargePointController()
print('__main__.py: after controller')
print('__main__.py: before html_path')
html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'view/index.html'))
print('__main__.py: after html_path:', html_path)
print('__main__.py: before create_window')
window = webview.create_window('ChargePoint Session Analytics', html_path, js_api=controller)
print('__main__.py: after create_window')
print('__main__.py: before webview.start')
webview.start(debug=True, gui='cocoa')
print('__main__.py: after webview.start (should not happen unless window closed)')
