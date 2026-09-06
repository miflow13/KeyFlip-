"""Optional cached sound playback through the already-required libcanberra."""
import ctypes
from pathlib import Path


class SoundPlayer:
    def __init__(self):
        self.context = ctypes.c_void_p()
        self.library = None
        try:
            library = ctypes.CDLL('libcanberra.so.0')
            library.ca_context_create.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
            library.ca_context_destroy.argtypes = [ctypes.c_void_p]
            library.ca_context_play.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            if library.ca_context_create(ctypes.byref(self.context)) == 0:
                self.library = library
        except OSError:
            pass

    def play(self, path):
        if self.library is not None:
            self.library.ca_context_play(
                self.context, 0,
                ctypes.c_char_p(b'media.filename'), ctypes.c_char_p(str(Path(path)).encode()),
                ctypes.c_char_p(b'canberra.cache-control'), ctypes.c_char_p(b'permanent'),
                ctypes.c_char_p(b'application.name'), ctypes.c_char_p(b'KeyFlip'),
                ctypes.c_void_p(),
            )

    def close(self):
        if self.library is not None:
            self.library.ca_context_destroy(self.context)
            self.library = None
