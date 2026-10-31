"""Release helpers for the Shokodi Kodi repository.

  bump      bump the version in addon_matrix.xml, set <news>, prepend to changelog.txt
  package   build dist/ zips for the plugin and the repository addon
  index     regenerate addons.xml + addons.xml.md5 for a Kodi repository tree

Stdlib only, so it runs on a stock GitHub runner.
"""
import argparse
import hashlib
import os
import re
import sys
import zipfile
from urllib.parse import quote
from xml.sax.saxutils import escape

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
PLUGIN_ID = 'plugin.video.shokodi'
REPO_ID = 'repository.shokodi'
PLUGIN_DIR = os.path.join(ROOT, PLUGIN_ID)
REPO_DIR = os.path.join(ROOT, REPO_ID)
# The addon.xml that ships in the zip is the Matrix one; Leia is no longer released.
ADDON_XML = os.path.join(PLUGIN_DIR, 'addon_matrix.xml')
CHANGELOG = os.path.join(PLUGIN_DIR, 'changelog.txt')

EXCLUDED_FILES = {'build.py', 'xbmc.py', 'xbmcaddon.py', 'xbmcgui.py', 'xbmcplugin.py', 'xbmcvfs.py',
                  'addon_leia.xml', 'addon_matrix.xml', 'sh.exe.stackdump'}
EXCLUDED_DIRS = {'.git', '.idea', '.pytest_cache', '__pycache__', 'venv', '.venv'}

VERSION_RE = re.compile(r'(<addon\b[^>]*?\sversion=")([^"]+)(")')
NEWS_RE = re.compile(r'<news>.*?</news>', re.S)


def version_key(version):
    return tuple(int(x) for x in re.findall(r'\d+', version))


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def write(path, text):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def get_version(xml_path):
    return VERSION_RE.search(read(xml_path)).group(2)


def set_output(name, value):
    path = os.environ.get('GITHUB_OUTPUT')
    if path:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f'{name}={value}\n')
    print(f'{name}={value}')


def bump(args):
    current = get_version(ADDON_XML)
    if args.version:
        new = args.version
    else:
        parts = list(version_key(current))
        parts += [0] * (3 - len(parts))
        idx = {'major': 0, 'minor': 1, 'patch': 2}[args.part]
        parts[idx] += 1
        parts[idx + 1:] = [0] * (len(parts) - idx - 1)
        new = '.'.join(str(p) for p in parts)
    if version_key(new) <= version_key(current):
        sys.exit(f'New version {new} must be greater than {current}')

    news_lines = [l.strip() for l in (args.news or '').splitlines() if l.strip()] or ['Bug fixes and improvements']

    xml = read(ADDON_XML)
    xml = VERSION_RE.sub(lambda m: m.group(1) + new + m.group(3), xml, count=1)
    xml = NEWS_RE.sub(lambda _m: '<news>' + escape('[CR]'.join(news_lines)) + '</news>', xml, count=1)
    write(ADDON_XML, xml)

    # changelog.txt: the new section goes above the first existing "!-- x.y.z" header
    log = read(CHANGELOG)
    section = f'!-- {new}\n' + '\n'.join(news_lines) + '\n\n'
    m = re.search(r'^!--', log, re.M)
    log = log[:m.start()] + section + log[m.start():] if m else log.rstrip('\n') + '\n\n' + section
    write(CHANGELOG, log)

    set_output('version', new)


def iter_plugin_files():
    for dirpath, dirnames, filenames in os.walk(PLUGIN_DIR):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
        for name in sorted(filenames):
            if name in EXCLUDED_FILES or name.endswith('.pyc'):
                continue
            yield os.path.join(dirpath, name)


def make_zip(out_path, src_dir, addon_id, files, addon_xml=None):
    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in files:
            if os.path.basename(path) == 'addon.xml':
                continue
            z.write(path, f'{addon_id}/' + os.path.relpath(path, src_dir).replace(os.sep, '/'))
        z.write(addon_xml or os.path.join(src_dir, 'addon.xml'), f'{addon_id}/addon.xml')


def package(args):
    os.makedirs(args.out, exist_ok=True)
    plugin_zip = os.path.join(args.out, f'{PLUGIN_ID}-{get_version(ADDON_XML)}.zip')
    make_zip(plugin_zip, PLUGIN_DIR, PLUGIN_ID, list(iter_plugin_files()), addon_xml=ADDON_XML)

    repo_xml = os.path.join(REPO_DIR, 'addon.xml')
    repo_files = [os.path.join(REPO_DIR, f) for f in sorted(os.listdir(REPO_DIR))]
    repo_zip = os.path.join(args.out, f'{REPO_ID}-{get_version(repo_xml)}.zip')
    make_zip(repo_zip, REPO_DIR, REPO_ID, repo_files)
    print('Built', plugin_zip, repo_zip)


def index(args):
    """Rebuild addons.xml from the newest zip of every addon found under args.tree."""
    newest = {}
    for addon_id in sorted(os.listdir(args.tree)):
        folder = os.path.join(args.tree, addon_id)
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            if not name.endswith('.zip'):
                continue
            with zipfile.ZipFile(os.path.join(folder, name)) as z:
                xml = z.read(f'{addon_id}/addon.xml').decode('utf-8-sig')
            version = VERSION_RE.search(xml).group(2)
            if addon_id not in newest or version_key(version) > version_key(newest[addon_id][0]):
                newest[addon_id] = (version, xml)

    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<addons>']
    for _, (_, xml) in sorted(newest.items()):
        body = re.sub(r'^\s*<\?xml[^>]*\?>\s*', '', xml).strip()
        out += ['\t' + line if line.strip() else line for line in body.splitlines()]
    out.append('</addons>')
    data = ('\n'.join(l.rstrip() for l in out) + '\n').encode('utf-8')

    with open(os.path.join(args.tree, 'addons.xml'), 'wb') as f:
        f.write(data)
    with open(os.path.join(args.tree, 'addons.xml.md5'), 'w', newline='') as f:
        f.write(hashlib.md5(data).hexdigest())
    print('Indexed', ', '.join(f'{k} {v[0]}' for k, v in sorted(newest.items())))


def listings(args):
    """
    Write an index.html into args.tree and every folder under it. GitHub Pages doesn't list directories, and
    Kodi's file manager needs a listing to browse a repository source.
    """
    count = 0
    for dirpath, dirnames, filenames in os.walk(args.tree):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith('.'))
        entries = [d + '/' for d in dirnames]
        entries += sorted(n for n in filenames if n != 'index.html' and not n.startswith('.'))
        rel = os.path.relpath(dirpath, args.tree).replace(os.sep, '/')
        title = '/' + ('' if rel == '.' else rel + '/')
        rows = [] if rel == '.' else ['<a href="../">../</a>']
        rows += ['<a href="%s">%s</a>' % (quote(e), escape(e)) for e in entries]
        html = ('<!DOCTYPE html>\n<html>\n<head><meta charset="utf-8"><title>Index of %s</title></head>\n'
                '<body>\n<h1>Index of %s</h1>\n<pre>\n%s\n</pre>\n</body>\n</html>\n'
                % (escape(title), escape(title), '\n'.join(rows)))
        write(os.path.join(dirpath, 'index.html'), html)
        count += 1
    print('Wrote', count, 'directory listings')


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('bump')
    b.add_argument('--part', choices=['major', 'minor', 'patch'], default='patch')
    b.add_argument('--version', help='explicit version; overrides --part')
    b.add_argument('--news', default='')
    b.set_defaults(fn=bump)
    k = sub.add_parser('package')
    k.add_argument('--out', default=os.path.join(ROOT, 'dist'))
    k.set_defaults(fn=package)
    i = sub.add_parser('index')
    i.add_argument('tree')
    i.set_defaults(fn=index)
    l = sub.add_parser('listings')
    l.add_argument('tree')
    l.set_defaults(fn=listings)
    args = p.parse_args()
    args.fn(args)


if __name__ == '__main__':
    main()
