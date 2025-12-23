import pickle
import hashlib
from collections import deque

from MultiEnvEmployer.utils.CacheAppDirs import CacheAppDirs


class FileCache:
    def __init__(self, app_name="MultiEnvEmployer", version=None, max_items=50, picle_protocol=4):
        dirs = CacheAppDirs(appname=app_name, version=version)
        self.cache_dir = dirs.user_cache_path
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_items = max_items
        self._load_index()
        self.picle_protocol = picle_protocol

    def _load_index(self):
        """Индекс хранит порядок добавления для удаления старых"""
        self.index_file = self.cache_dir / "index.pkl"
        if self.index_file.exists():
            with open(self.index_file, "rb") as f:
                self.index = pickle.load(f)
        else:
            self.index = deque()

    def _save_index(self):
        with open(self.index_file, "wb") as f:
            pickle.dump(self.index, f, protocol=self.picle_protocol)

    def _make_file_path(self, key):
        return self.cache_dir / f"{key}.pkl"

    def make_key(self, module_name, func_name, *args, **kwargs):
        payload = (module_name, func_name, args, kwargs)
        b = pickle.dumps(payload, protocol=self.picle_protocol)
        return hashlib.sha256(b).hexdigest()

    def set(self, key, value):
        path = self._make_file_path(key)
        with open(path, "wb") as f:
            pickle.dump(value, f, protocol=self.picle_protocol)

        if key not in self.index:
            self.index.append(key)

        # удаляем старое при превышении лимита
        while len(self.index) > self.max_items:
            old_key = self.index.popleft()
            old_path = self._make_file_path(old_key)
            if old_path.exists():
                old_path.unlink()

        self._save_index()

    def get(self, key):
        path = self._make_file_path(key)
        if not path.exists():
            return None
        with open(path, "rb") as f:
            return pickle.load(f)

    def exists(self, key):
        return self._make_file_path(key).exists()

    def clear(self):
        """Полное очищение кэша"""
        for key in self.index:
            path = self._make_file_path(key)
            if path.exists():
                path.unlink()
        self.index.clear()
        self._save_index()
