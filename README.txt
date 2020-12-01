# pyid800
### Python 3.6 (32-bit Windows only)
ctypes based library for the IDQuantique id800 time-to-digital converter (TDC)

You will need these shared libraries:

* nhconnect.dll
* nhconnect.lib
* tdcbase.dll
* tdcbase.lib
* libusb0.dll (32-bit only)

If opening a TDC object don't forget to close connection to the id800 with TDC.close()
