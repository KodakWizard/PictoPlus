"""Read-only Azahar process check through Windows, without a command shell."""
import ctypes
from ctypes import wintypes

def is_running(executable,kernel32=None):
 class Entry(ctypes.Structure):
  _fields_=[('dwSize',wintypes.DWORD),('cntUsage',wintypes.DWORD),('th32ProcessID',wintypes.DWORD),('th32DefaultHeapID',ctypes.c_size_t),('th32ModuleID',wintypes.DWORD),('cntThreads',wintypes.DWORD),('th32ParentProcessID',wintypes.DWORD),('pcPriClassBase',wintypes.LONG),('dwFlags',wintypes.DWORD),('szExeFile',wintypes.WCHAR*260)]
 api=kernel32 or ctypes.WinDLL('kernel32',use_last_error=True)
 api.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD];api.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
 for name in ('Process32FirstW','Process32NextW'):
  fn=getattr(api,name);fn.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)];fn.restype=wintypes.BOOL
 api.CloseHandle.argtypes=[wintypes.HANDLE];api.CloseHandle.restype=wintypes.BOOL
 handle=api.CreateToolhelp32Snapshot(2,0)
 if handle is None or handle==ctypes.c_void_p(-1).value:return True # Fail closed before modifying emulator files.
 try:
  entry=Entry();entry.dwSize=ctypes.sizeof(entry)
  success=api.Process32FirstW(handle,ctypes.byref(entry))
  if not success:return True
  while success:
   if entry.szExeFile.casefold()==executable.casefold():return True
   success=api.Process32NextW(handle,ctypes.byref(entry))
  # ERROR_NO_MORE_FILES is the only expected enumeration end.
  return ctypes.get_last_error()!=18
 finally:api.CloseHandle(handle)
