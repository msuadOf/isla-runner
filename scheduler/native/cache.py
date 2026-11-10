"""按 stat 复用内容校验；源文件复制成不可变对象，不硬链接源工作文件。"""
from contextlib import closing
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading

class Cache:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.objects = self.directory / 'objects'
        self.objects.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with closing(self.connect()) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, stamp TEXT, digest TEXT, size INTEGER, mode INTEGER)')

    def connect(self):
        return sqlite3.connect(self.directory / 'index.sqlite', timeout=60)

    @staticmethod
    def stamp(path):
        s = path.stat()
        return json.dumps([s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode])

    def freeze(self, source):
        source = Path(source).resolve(strict=True)
        if not source.is_file():
            raise ValueError(f'输入不是普通文件：{source}')
        with self.lock, (self.directory / 'freeze.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            stamp = self.stamp(source)
            with closing(self.connect()) as db, db:
                row = db.execute('SELECT stamp,digest,size,mode FROM files WHERE path=?', (str(source),)).fetchone()
                if row and row[0] == stamp and (self.objects / row[1]).is_file():
                    return dict(digest=row[1], size=row[2], mode=row[3], source=str(self.objects / row[1]))
                fd, temporary = tempfile.mkstemp(dir=self.objects, prefix='.partial-')
                try:
                    digest = hashlib.sha256()
                    size = 0
                    with os.fdopen(fd, 'wb') as target, source.open('rb') as stream:
                        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                            digest.update(chunk)
                            target.write(chunk)
                            size += len(chunk)
                    if self.stamp(source) != stamp:
                        raise RuntimeError(f'冻结期间输入变化，请重试：{source}')
                    mode = 0o555 if os.access(source, os.X_OK) else 0o444
                    # 执行权限属于对象身份，防止同内容数据与程序互相覆盖权限。
                    key = digest.hexdigest() + ('-x' if mode == 0o555 else '-r')
                    os.chmod(temporary, mode)
                    if not (self.objects / key).exists():
                        os.replace(temporary, self.objects / key)
                    db.execute('INSERT OR REPLACE INTO files VALUES(?,?,?,?,?)',
                               (str(source), stamp, key, size, mode))
                    return dict(digest=key, size=size, mode=mode, source=str(self.objects / key))
                finally:
                    Path(temporary).unlink(missing_ok=True)
