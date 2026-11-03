"""Bounded source-file dependencies for reusable resolved geometry products."""
from contextvars import ContextVar
from contextlib import contextmanager
from pathlib import Path

ACTIVE=ContextVar('geometry_input_files',default=None)
MAX_FILES=8192


def paths(values):
    state=ACTIVE.get()
    if state is None:return
    for value in values:
        if len(state['files'])>=MAX_FILES:state['overflow']=True;return
        state['files'].add(str(Path(value).absolute()))


def stamp(path):
    try:
        stat=Path(path).stat();return stat.st_size,stat.st_mtime_ns
    except FileNotFoundError:return None


def snapshot(state):
    if state['overflow']:return None
    try:return tuple((path,stamp(path)) for path in sorted(state['files']))
    except OSError:return None


def current(records):
    if records is None or len(records)>MAX_FILES:return False
    try:return all(stamp(path)==(tuple(saved) if saved is not None else None) for path,saved in records)
    except OSError:return False


@contextmanager
def capture():
    state={'files':set(),'overflow':False};token=ACTIVE.set(state)
    try:yield state
    finally:ACTIVE.reset(token)
