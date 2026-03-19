import ctypes
import os
import shutil
import struct
import subprocess
import threading
import time
from ctypes import wintypes

# --- Win32 Constants & Types ---
kernel32 = ctypes.windll.kernel32

HPCON = wintypes.HANDLE
LPHANDLE = ctypes.POINTER(wintypes.HANDLE)
HRESULT = ctypes.c_long

PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
EXTENDED_STARTUPINFO_PRESENT = 0x00080000

class COORD(ctypes.Structure):
    _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]

class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]

class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [
        ("StartupInfo", STARTUPINFOW),
        ("lpAttributeList", wintypes.LPVOID),
    ]

# --- API Definitions ---
CreatePseudoConsole = kernel32.CreatePseudoConsole
CreatePseudoConsole.argtypes = [COORD, wintypes.HANDLE, wintypes.HANDLE, wintypes.DWORD, LPHANDLE]
CreatePseudoConsole.restype = HRESULT

ClosePseudoConsole = kernel32.ClosePseudoConsole
ClosePseudoConsole.argtypes = [HPCON]
ClosePseudoConsole.restype = None

ResizePseudoConsole = kernel32.ResizePseudoConsole
ResizePseudoConsole.argtypes = [HPCON, COORD]
ResizePseudoConsole.restype = HRESULT

InitializeProcThreadAttributeList = kernel32.InitializeProcThreadAttributeList
InitializeProcThreadAttributeList.argtypes = [wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t)]
InitializeProcThreadAttributeList.restype = wintypes.BOOL

UpdateProcThreadAttribute = kernel32.UpdateProcThreadAttribute
UpdateProcThreadAttribute.argtypes = [
    wintypes.LPVOID, wintypes.DWORD, ctypes.c_size_t, 
    wintypes.LPVOID, ctypes.c_size_t, wintypes.LPVOID, wintypes.LPVOID
]
UpdateProcThreadAttribute.restype = wintypes.BOOL

DeleteProcThreadAttributeList = kernel32.DeleteProcThreadAttributeList
DeleteProcThreadAttributeList.argtypes = [wintypes.LPVOID]
DeleteProcThreadAttributeList.restype = None

# Process Information structure
class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]

class PTY:
    def __init__(self, cols=120, rows=30):
        self.hpcon = HPCON()
        self.h_in_pipe_read = wintypes.HANDLE()
        self.h_in_pipe_write = wintypes.HANDLE()
        self.h_out_pipe_read = wintypes.HANDLE()
        self.h_out_pipe_write = wintypes.HANDLE()
        self.pid = None
        self.process_handle = None
        self.output_thread = None
        self.on_output = None # Callback(text)
        self.buffer = ""
        self.running = False

        # Create pipes
        kernel32.CreatePipe(ctypes.byref(self.h_in_pipe_read), ctypes.byref(self.h_in_pipe_write), None, 0)
        kernel32.CreatePipe(ctypes.byref(self.h_out_pipe_read), ctypes.byref(self.h_out_pipe_write), None, 0)

        # Create Pseudo Console
        size = COORD(cols, rows)
        res = CreatePseudoConsole(size, self.h_in_pipe_read, self.h_out_pipe_write, 0, ctypes.byref(self.hpcon))
        if res != 0:
            raise Exception(f"Failed to create Pseudo Console: {res}")

    def spawn(self, command_line, cwd=None, env=None):
        attr_size = ctypes.c_size_t()
        InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(attr_size))
        
        attr_list = ctypes.create_string_buffer(attr_size.value)
        InitializeProcThreadAttributeList(attr_list, 1, 0, ctypes.byref(attr_size))
        
        UpdateProcThreadAttribute(
            attr_list, 0, PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
            self.hpcon, ctypes.sizeof(self.hpcon), None, None
        )

        si = STARTUPINFOEXW()
        si.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
        si.lpAttributeList = ctypes.cast(attr_list, wintypes.LPVOID)
        
        pi_real = PROCESS_INFORMATION()
        
        # Prepare command line
        if isinstance(command_line, list):
            command_line = subprocess.list2cmdline(command_line)
        
        success = kernel32.CreateProcessW(
            None, command_line, None, None, False,
            EXTENDED_STARTUPINFO_PRESENT, 
            None, cwd, ctypes.byref(si.StartupInfo), ctypes.byref(pi_real)
        )

        if not success:
            err = kernel32.GetLastError()
            DeleteProcThreadAttributeList(attr_list)
            raise Exception(f"CreateProcessW failed with error {err}")

        self.pid = pi_real.dwProcessId
        self.process_handle = pi_real.hProcess
        self.running = True
        
        # Clean up attribute list
        DeleteProcThreadAttributeList(attr_list)
        
        # Close handles we don't need anymore
        kernel32.CloseHandle(pi_real.hThread)
        kernel32.CloseHandle(self.h_in_pipe_read)
        kernel32.CloseHandle(self.h_out_pipe_write)

        # Start output reader thread
        self.output_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.output_thread.start()
        
        return self.pid

    def _read_loop(self):
        buf = ctypes.create_string_buffer(4096)
        while self.running:
            read = wintypes.DWORD()
            success = kernel32.ReadFile(self.h_out_pipe_read, buf, 4096, ctypes.byref(read), None)
            if not success or read.value == 0:
                break
            
            data = buf.raw[:read.value]
            try:
                # ConPTY usually sends UTF-8
                text = data.decode('utf-8', errors='replace')
                self.buffer += text
                if self.on_output:
                    self.on_output(text)
            except Exception as e:
                print(f"PTY Read Error: {e}")
        
        self.running = False

    def write(self, text):
        if not self.running: return
        data = text.encode('utf-8')
        written = wintypes.DWORD()
        kernel32.WriteFile(self.h_in_pipe_write, data, len(data), ctypes.byref(written), None)

    def resize(self, cols, rows):
        if self.hpcon:
            ResizePseudoConsole(self.hpcon, COORD(cols, rows))

    def close(self):
        self.running = False
        if self.hpcon:
            try: ClosePseudoConsole(self.hpcon)
            except: pass
        
        if self.h_in_pipe_write:
            try: kernel32.CloseHandle(self.h_in_pipe_write)
            except: pass
        if self.h_out_pipe_read:
            try: kernel32.CloseHandle(self.h_out_pipe_read)
            except: pass
            
        if self.process_handle:
            kernel32.TerminateProcess(self.process_handle, 1)
            kernel32.CloseHandle(self.process_handle)

if __name__ == "__main__":
    # Simple test
    pty = PTY()
    def printer(t): print(t, end="", flush=True)
    pty.on_output = printer
    print("Spawning powershell...")
    pty.spawn("powershell.exe -NoLogo")
    time.sleep(2)
    print("\nSending 'dir'...")
    pty.write("dir\r\n")
    time.sleep(2)
    pty.close()
    print("\nDone.")