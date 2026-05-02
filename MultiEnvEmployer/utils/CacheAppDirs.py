import os
import sys
from pathlib import Path


class CacheAppDirs:
    def __init__(self, appname: str = None, version: str = None):
        self.appname = appname
        self.version = version

    def _append_app_name_and_version(self, path: str) -> str:
        if self.appname:
            path = os.path.join(path, self.appname)
            if self.version:
                path = os.path.join(path, self.version)
        return path

    @property
    def user_cache_dir(self) -> str:
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        elif sys.platform == "darwin":
            base = os.path.expanduser("~/Library/Caches")
        else:  # Unix/Linux
            base = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))

        return self._append_app_name_and_version(base)

    @property
    def user_cache_path(self) -> Path:
        return Path(self.user_cache_dir)

