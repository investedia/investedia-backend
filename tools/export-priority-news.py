"""Export only saved news payloads and local photo assets; never financial ledgers."""
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
NEWS = ('news-live.json', 'news-48h.json', 'news-archive.json', 'news-status.json', 'connections.json')


def export(frontend, backend=ROOT):
    source = backend/'assets/globe'
    destination = frontend.resolve()/'assets/globe'
    if not (frontend/'scripts/sync-snapshots.py').is_file():
        raise ValueError('Choose the frontend checkout')
    pending = [(source/name, destination/name) for name in NEWS]
    photos = source/'photos'
    pending += [(path, destination/'photos'/path.name) for path in photos.iterdir()
                if path.is_file() and path.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.avif', '.json')]
    # Validate the complete list before copying; reject symlinks and path escapes.
    for src, target in pending:
        if src.is_symlink() or not src.is_file() or not src.resolve().is_relative_to(source.resolve()):
            raise ValueError('Missing or unsafe news source')
        if target.is_symlink() or not target.resolve().is_relative_to(frontend.resolve()):
            raise ValueError('Unsafe news destination')
    for src, target in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    return len(pending)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frontend', type=Path, required=True)
    args = parser.parse_args()
    print(f'Copied {export(args.frontend)} saved news/photo files without changing their timestamps.')
