"""User-initiated Windows Common Item Dialog, without an extra GUI runtime."""

from __future__ import annotations

import ctypes
import os
import uuid
from pathlib import Path


def available():
    return os.name == "nt"


class GUID(ctypes.Structure):
    _fields_ = [
        ("first", ctypes.c_uint32),
        ("second", ctypes.c_uint16),
        ("third", ctypes.c_uint16),
        ("last", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def parse(cls, value):
        return cls.from_buffer_copy(uuid.UUID(value).bytes_le)


def check(result):
    if result < 0:
        raise OSError(f"Windows folder picker failed (0x{result & 0xFFFFFFFF:08x})")


def choose(initial: str, title: str, *, probe=False):
    """Return a filesystem directory or None on cancel; probe never shows UI."""
    if not available():
        raise OSError("Native folder selection is available on Windows; use the manual path")
    pointer = ctypes.c_void_p
    ole = getattr(ctypes, "WinDLL")("ole32")
    shell = getattr(ctypes, "WinDLL")("shell32")
    ole.CoInitializeEx.argtypes = [pointer, ctypes.c_uint32]
    ole.CoInitializeEx.restype = ctypes.c_int32
    ole.CoCreateInstance.argtypes = [
        ctypes.POINTER(GUID),
        pointer,
        ctypes.c_uint32,
        ctypes.POINTER(GUID),
        ctypes.POINTER(pointer),
    ]
    ole.CoCreateInstance.restype = ctypes.c_int32
    ole.CoTaskMemFree.argtypes = [pointer]
    ole.CoUninitialize.argtypes = []
    shell.SHCreateItemFromParsingName.argtypes = [
        ctypes.c_wchar_p,
        pointer,
        ctypes.POINTER(GUID),
        ctypes.POINTER(pointer),
    ]
    shell.SHCreateItemFromParsingName.restype = ctypes.c_int32
    check(ole.CoInitializeEx(None, 2 | 4))  # STA, disable OLE1 DDE.
    dialog, folder, selected, text = pointer(), pointer(), pointer(), pointer()

    def call(instance, slot, types=(), values=()):
        table = ctypes.cast(instance, ctypes.POINTER(ctypes.POINTER(pointer))).contents
        method = getattr(ctypes, "WINFUNCTYPE")(ctypes.c_int32, pointer, *types)(table[slot])
        return method(instance, *values)

    try:
        clsid = GUID.parse("dc1c5a9c-e88a-4dde-a5a1-60f82a20aef7")
        iid = GUID.parse("d57c7288-d4ad-4768-be02-9d969532d960")
        shell_iid = GUID.parse("43826d1e-e718-42ee-bc55-a1e261c37bfe")
        check(
            ole.CoCreateInstance(
                ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(dialog)
            )
        )
        options = ctypes.c_uint32()
        check(call(dialog, 10, (ctypes.POINTER(ctypes.c_uint32),), (ctypes.byref(options),)))
        # PICKFOLDERS, FORCEFILESYSTEM, PATHMUSTEXIST, NOCHANGEDIR, DONTADDTORECENT.
        check(
            call(
                dialog,
                9,
                (ctypes.c_uint32,),
                (options.value | 0x20 | 0x40 | 0x800 | 8 | 0x2000000,),
            )
        )
        check(call(dialog, 17, (ctypes.c_wchar_p,), (title,)))
        check(call(dialog, 18, (ctypes.c_wchar_p,), ("Choose folder",)))
        start = Path(initial).expanduser()
        while not start.is_dir() and start != start.parent:
            start = start.parent
        if start.is_dir():
            check(
                shell.SHCreateItemFromParsingName(
                    str(start), None, ctypes.byref(shell_iid), ctypes.byref(folder)
                )
            )
            check(call(dialog, 12, (pointer,), (folder,)))
        if probe:
            return None
        result = call(dialog, 3, (pointer,), (None,))
        if result & 0xFFFFFFFF == 0x800704C7:  # HRESULT_FROM_WIN32(ERROR_CANCELLED)
            return None
        check(result)
        check(call(dialog, 20, (ctypes.POINTER(pointer),), (ctypes.byref(selected),)))
        # IShellItem::GetDisplayName(SIGDN_FILESYSPATH).
        check(
            call(
                selected,
                5,
                (ctypes.c_uint32, ctypes.POINTER(pointer)),
                (0x80058000, ctypes.byref(text)),
            )
        )
        return ctypes.wstring_at(text)
    finally:
        if text:
            ole.CoTaskMemFree(text)
        for instance in [selected, folder, dialog]:
            if instance:
                call(instance, 2)
        ole.CoUninitialize()


if __name__ == "__main__":
    choose(str(Path.cwd()), "TrogloDAW folder picker", probe=True)
    print("Native folder picker initialized and released without displaying a dialog.")
