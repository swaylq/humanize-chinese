#!/usr/bin/env python3
"""
Download and deploy the full DomainWordsDict JSON cache.

Three deployment modes — pick the one that fits your environment:

  1. Download pre-sorted ZIP (recommended):
     python scripts/download_full_dict.py
     → Downloads from GitHub releases, extracts to scripts/data/DomainWordsDict/

  2. Build from txt source:
     python scripts/download_full_dict.py --from-txt <DomainWordsDict_dir>
     → Same as: python scripts/humanize_cn.py --build-dict-cache <dir>

  3. Copy from local directory:
     python scripts/download_full_dict.py --from-local <path_to_json_dir>

After deployment, the protection layer auto-upgrades from mini mode to
full domain-aware mode on next --protect invocation.
"""

import os
import sys
import json
import zipfile
import shutil
import argparse
from urllib.request import urlopen, Request
from io import BytesIO

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data', 'DomainWordsDict')

# Default download URL — update this to your release asset URL.
# Generate a release on GitHub, upload the sorted JSONs as a zip,
# then set this to the direct download URL of that zip asset.
_DEFAULT_URL = (
    'https://github.com/Asami-Lilith/humanize-chinese/releases/download/'
    'Resources/DomainWordsDict.zip'
)


def _download(url):
    """Download bytes from url with progress indicator."""
    print(f'Downloading {url} ...')
    req = Request(url, headers={'User-Agent': 'humanize-chinese-downloader/1.0'})
    try:
        with urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get('Content-Length', 0))
            chunks = []
            received = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                received += len(chunk)
                if total:
                    pct = received * 100 // total
                    mb = received / (1024 * 1024)
                    total_mb = total / (1024 * 1024)
                    print(f'\r  {pct}%  {mb:.1f} / {total_mb:.1f} MB', end='')
            print()
            return b''.join(chunks)
    except Exception as e:
        print(f'\nDownload failed: {e}')
        return None


def _verify_sorted(json_dir):
    """Check that JSON files are sorted and bisect-compatible."""
    ok = 0
    bad = 0
    for fname in sorted(os.listdir(json_dir)):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(json_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            terms = [t[0] for t in data.get('terms', [])]
            if terms == sorted(terms):
                ok += 1
            else:
                bad += 1
                print(f'  WARNING: {fname} is not sorted')
        except Exception as e:
            bad += 1
            print(f'  WARNING: {fname} parse error: {e}')
    return ok, bad


def _extract_zip(zip_bytes, dest_dir):
    """Extract zip to dest_dir, creating it if needed."""
    os.makedirs(dest_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            json_count = sum(1 for n in names if n.endswith('.json'))
            print(f'Extracting {json_count} JSON files to {dest_dir} ...')
            zf.extractall(dest_dir)
        return True
    except Exception as e:
        print(f'Extraction failed: {e}')
        return False


def _build_from_txt(src_dir):
    """Convert .txt files to sorted .json via _domain_dict_convert."""
    try:
        from _domain_dict_convert import convert
    except ImportError:
        sys.path.insert(0, SCRIPT_DIR)
        from _domain_dict_convert import convert
    convert(src_dir)


def main():
    parser = argparse.ArgumentParser(
        description='Download and deploy full DomainWordsDict JSON cache')
    parser.add_argument(
        '--url', metavar='URL',
        help=f'Download URL for pre-sorted ZIP (default: GitHub release)')
    parser.add_argument(
        '--from-local', metavar='DIR',
        help='Copy pre-sorted JSONs from local directory')
    parser.add_argument(
        '--from-txt', metavar='DIR',
        help='Build from DomainWordsDict txt source files')
    parser.add_argument(
        '--no-verify', action='store_true',
        help='Skip sort verification after deployment')
    parser.add_argument(
        '--force', action='store_true',
        help='Overwrite existing files in data/DomainWordsDict/')
    args = parser.parse_args()

    if os.path.isdir(DATA_DIR) and os.listdir(DATA_DIR) and not args.force:
        print(f'Full dictionary already exists at {DATA_DIR}')
        print('Use --force to re-download.')
        ok, bad = _verify_sorted(DATA_DIR)
        print(f'Verification: {ok} sorted, {bad} issues')
        if bad:
            return 1
        return 0

    if args.from_txt:
        _build_from_txt(args.from_txt)
    elif args.from_local:
        src = args.from_local
        if not os.path.isdir(src):
            print(f'error: {src} is not a directory')
            return 1
        json_files = [f for f in os.listdir(src) if f.endswith('.json')]
        if not json_files:
            print(f'error: no .json files found in {src}')
            return 1
        os.makedirs(DATA_DIR, exist_ok=True)
        for fname in json_files:
            shutil.copy2(os.path.join(src, fname),
                         os.path.join(DATA_DIR, fname))
        print(f'Copied {len(json_files)} JSON files from {src}')
    else:
        url = args.url or _DEFAULT_URL
        if not url:
            print('No download URL configured.')
            print()
            print('Options:')
            print('  1. Set --url to a hosted ZIP of sorted DomainWordsDict JSONs')
            print('  2. Use --from-txt <DomainWordsDict_txt_dir> to build from source')
            print('  3. Use --from-local <path> to copy from existing JSONs')
            return 1
        zip_bytes = _download(url)
        if zip_bytes is None:
            print()
            print('Tip: you can also build from source txt files:')
            print('  python scripts/download_full_dict.py --from-txt <DomainWordsDict_dir>')
            return 1
        os.makedirs(DATA_DIR, exist_ok=True)
        if not _extract_zip(zip_bytes, DATA_DIR):
            return 1

    if not os.listdir(DATA_DIR):
        print('error: no files deployed')
        return 1

    if not args.no_verify:
        print('Verifying sort order ...')
        ok, bad = _verify_sorted(DATA_DIR)
        print(f'  {ok} sorted, {bad} issues')
        if bad:
            print('\nWARNING: Some files are not sorted — bisect may fail.')
            print('Re-run with --from-txt to regenerate correctly sorted files.')
            return 1

    total_count = len([f for f in os.listdir(DATA_DIR) if f.endswith('.json')])
    print(f'\nDone! {total_count} domains deployed to {DATA_DIR}')
    print('Full domain-aware protection is now active on next --protect run.')


if __name__ == '__main__':
    sys.exit(main())
