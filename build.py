import sys
import traceback
import zipfile
from collections import defaultdict
from distutils.version import LooseVersion
from shutil import copy2
import xml.etree.ElementTree as ET
from zipfile import ZipFile
import os


def add_file(list_of_processed_files, full_path, filename):
    if full_path not in list_of_processed_files:
        # excluded from adding to list
        excluded_files = ['build.py', '.idea', '.git', 'xbmc.py', 'xbmcaddon.py',
                          'xbmcgui.py', 'xbmcplugin.py', 'xbmcvfs.py', 'sh.exe.stackdump', 'addon_leia.xml',
                          'addon_matrix.xml']

        if os.path.basename(filename) not in excluded_files:
            list_of_processed_files.append(full_path)


def look_inside(origin_path, path, list_of_files):
    if '.git' in path or '.pytest_cache' in path or '.idea' in path or 'venv' in path:
        return
    for files in os.listdir(path):
        y = os.path.join(path, files)
        if os.path.isfile(y):
            file_path = str(y).replace(origin_path, '..')
            add_file(list_of_files, y, file_path)
        elif os.path.isdir(y):
            look_inside(origin_path, y, list_of_files)


def get_all_file_paths(directory):
    # initializing empty file paths list
    file_paths = []

    # check hash file (wipe)
    check_file = os.path.join(directory, 'resources', 'hash.sfv')
    if os.path.exists(check_file):
        os.remove(check_file)

    # iterate over ALL files make list of those for zip and calculate hash
    # crawling through directory and subdirectories
    look_inside(directory, directory, file_paths)

    # returning all file paths
    return file_paths


shokodi_directory = ['plugin.video.shokodi']
addon_xml_leia = 'addon_leia.xml'
addon_xml_matrix = 'addon_matrix.xml'


def get_news(path):
    changelog_txt_path = os.path.join(path, 'changelog.txt')
    fstream = open(changelog_txt_path, 'r')
    changelog = defaultdict(list)
    current_version = None
    for line in fstream.readlines():
        try:
            line = line.strip()
            if line == '':
                continue
            if line.startswith('#'):
                continue
            if line.startswith('!--'):
                try:
                    current_version = LooseVersion(line.replace('!--', '').strip())
                    # current line is version so go to next line
                    continue
                except:
                    pass
            if current_version is None:
                continue
            changelog[current_version.vstring].append(line)
        except:
            pass
    changelog.default_factory = None

    # build the text based on previous version.
    # This is important, as someone might open kodi for the first time in a while and skip several versions
    max_version = (LooseVersion('0'), list())
    for k, v in changelog.items():
        if LooseVersion(k) > max_version[0]:
            max_version = (LooseVersion(k), list(v))

    changelog_text = 'Version ' + max_version[0].vstring
    changelog_values = max_version[1]
    for line in changelog_values:
        changelog_text += '[CR]- ' + line

    return changelog_text


def replace_news(addon_xml_path):
    replace_me = '{NEWS REPLACE ME}'
    news = get_news(os.path.dirname(addon_xml_path))
    root_path = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

    copy2(addon_xml_path, root_path)

    with open(addon_xml_path) as f:
        s = f.read()
        if replace_me not in s:
            return

    with open(addon_xml_path, 'w') as f:
        print('Adding news to ')
        s = s.replace(replace_me, news)
        f.write(s)


def restore_backup(addon_xml_path):
    root_path = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
    addon_xml_path_temp = os.path.join(root_path, os.path.basename(addon_xml_path))

    copy2(addon_xml_path_temp, addon_xml_path)
    os.remove(addon_xml_path_temp)


def main():
    root_path = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

    for directory in shokodi_directory:
        try:
            replace_news(os.path.join(root_path, directory, addon_xml_leia))
            replace_news(os.path.join(root_path, directory, addon_xml_matrix))
        except:
            pass
        try:
            plugin_path = os.path.join(root_path, directory)
            file_paths = get_all_file_paths(plugin_path)

            # printing the list of all files to be zipped
            print('Following files will be zipped:')
            for file_name in file_paths:
                print(file_name)

            out = os.path.join(root_path, 'build')
            if not os.path.exists(out):
                os.mkdir(out)

            # Writing files to a zipfile for Leia
            addon_path = os.path.join(root_path, directory, addon_xml_leia)
            version = get_addon_version(addon_path)
            out_leia = os.path.join(out, 'plugin.video.shokodi-'+version+'.zip')
            if os.path.exists(out_leia):
                os.remove(out_leia)
            with ZipFile(out_leia, 'w') as zip_file:
                # writing each file one by one
                for file_path in file_paths:
                    rel_path = os.path.relpath(file_path, root_path)
                    zip_file.write(file_path, rel_path, zipfile.ZIP_DEFLATED)

                zip_file.write(addon_path, os.path.join(directory, 'addon.xml'), zipfile.ZIP_DEFLATED)

            print('Zipped ' + directory + ' for Leia successfully!')

            # Restoring the backup addon.xml file for Matrix
            restore_backup(os.path.join(root_path, directory, addon_xml_leia))

            # Writing files to a zipfile for Matrix
            addon_path = os.path.join(root_path, directory, addon_xml_matrix)
            version = get_addon_version(addon_path)
            out_matrix = os.path.join(out, 'plugin.video.shokodi-' + version + '.zip')
            if os.path.exists(out_matrix):
                os.remove(out_matrix)
            with ZipFile(out_matrix, 'w') as zip_file:
                # writing each file one by one
                for file_path in file_paths:
                    rel_path = os.path.relpath(file_path, root_path)
                    zip_file.write(file_path, rel_path, zipfile.ZIP_DEFLATED)

                zip_file.write(addon_path, os.path.join(directory, 'addon.xml'), zipfile.ZIP_DEFLATED)

            print('Zipped ' + directory + ' for Matrix successfully!')
            restore_backup(os.path.join(root_path, directory, addon_xml_matrix))
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            if exc_type is not None and exc_obj is not None and exc_tb is not None:
                print(str(exc_type) + " at line " + str(exc_tb.tb_lineno) + " in file " + str(
                    os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]))
                traceback.print_exc()


def get_addon_version(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    if root.tag == 'addon':
        addon_element = root
    else:
        addon_element = root.find('addon')
    version = addon_element.get('version')
    return version


if __name__ == '__main__':
    main()
