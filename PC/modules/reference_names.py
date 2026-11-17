"""Display names stay separate from video filenames and pose data."""
import json
import os
import tempfile
from modules.file_manager import get_reference_path


def name_path(filename):
    return get_reference_path(filename).with_suffix('.name.json')


def get_reference_name(filename):
    try:
        name = json.loads(name_path(filename).read_text(encoding='utf-8'))['name']
        return name if isinstance(name, str) and name.strip() else filename
    except (OSError, ValueError, KeyError, TypeError):
        return filename


def set_reference_name(filename, name):
    if not isinstance(name, str):
        raise ValueError('Enter a reference name')
    name = name.strip()
    if not name or len(name) > 120 or any(ord(c) < 32 for c in name):
        raise ValueError('Use a name between 1 and 120 characters without control characters')
    target = name_path(filename)
    descriptor, temporary = tempfile.mkstemp(dir=target.parent, suffix='.tmp')
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump({'name': name}, stream, ensure_ascii=False)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return name
