import subprocess
import io
import re
import os
import math
import shutil
import zipfile
import xml.etree.cElementTree as ET



INTERNAL_MAVEN_URL = "//maven.oa.com"
LIBRARY_PLUGIN = 'apply plugin: \'com.android.library\''
APPLICATION_PLUGIN = 'apply plugin: \'com.android.application\''
VERSION_NAME = "versionName\s+(\S+)"
JCENTER = 'jcenter()'
DISTRIBUTION_URL = 'distributionUrl=https\://services.gradle.org/distributions/'




# maven dependency
class MavenLibrary(object):

    def __init__(self, group, name, version):
        self.group = group
        self.name = name
        self.version = version

    @classmethod
    def from_module(self, module):
        group, name, version = module.split(':')
        return MavenLibrary(group, name, version)

    def set_version(self, version):
        self.version = version

'''
basic method
'''


def get_project_home_dir():
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))


def call_shell(dir, gradle_cmd):
    ret = subprocess.call("cd " + dir + " && " + gradle_cmd, shell=True)
    if (ret == 1):
        raise ValueError('execute %s error' % gradle_cmd)

def get_shell_output(dir, cmd):
    return subprocess.check_output("cd " + dir + " && " + cmd, shell=True)

def open_file(file, func, content=None):
    with io.open(file, 'wt', encoding='utf-8', errors='ignore') as f:
        func(fo = f, content = content)


def load_file(file):
    with io.open(file, encoding='utf-8', errors='ignore') as f:
        return f.read(None)

def write_file(file, content):
    with io.open(file, 'w', encoding='utf-8', errors='ignore') as f:
        return f.write(content)

def read_property(property_file, key):
    H = dict(line.strip().split('=') for line in open(property_file))
    return H[key]


def replace_string(file, pattern, new_string, check_pattern=None, check_match=True):
    reg_pattern = re.compile(pattern)
    content = load_file(file)

    if check_pattern != None:
        reg_check_pattern = re.compile(check_pattern)
        if re.search(reg_check_pattern, content) == check_match:
            return

    with io.open(file, 'w', encoding='utf-8', errors='ignore') as f:
        replace = re.sub(reg_pattern, new_string, content)
        f.write(replace)

def search_string(file, pattern, check_pattern=None, check_match=True):
    reg_pattern = re.compile(pattern)
    content = load_file(file)
    if check_pattern != None:
        reg_check_pattern = re.compile(check_pattern)
        if re.search(reg_check_pattern, content) == check_match:
            return None

    return re.search(reg_pattern, content)

'''
business method
'''

def extract_library(file_to_unzip, target_dir, jar_name=None):
    zip_ref = zipfile.ZipFile(file_to_unzip, 'r')

    for file in zip_ref.namelist():
        if file.startswith('jni/') or file.startswith('res/') or file.startswith('assets/') \
                or file.startswith('libs/') or file == 'classes.jar':
            zip_ref.extract(file, target_dir)
    zip_ref.close()

    # copy jar in libs
    lib_dir = os.path.join(target_dir, 'libs')
    remove_classes_jar = False
    if os.path.exists(lib_dir):
        for root, folders, files in os.walk(lib_dir):
            for file in files:
                remove_classes_jar = True
                os.rename(os.path.join(root, file), os.path.join(target_dir, file))

    classes_jar = os.path.join(target_dir, 'classes.jar')
    if remove_classes_jar or os.path.getsize(classes_jar) < 1000: # small than 1000KB
        os.remove(classes_jar)
    elif jar_name:
        os.rename(classes_jar, os.path.join(target_dir, jar_name))


def zip_library(dir_to_zip, target_zip_file, embed = []):
    zip_ref = zipfile.ZipFile(target_zip_file, 'w')

    embed = tuple([os.path.join(dir_to_zip, s) for s in embed])

    for root, folders, files in os.walk(dir_to_zip):
        for file in files:
            if os.path.join(root, file).startswith(embed) or file.endswith(".jar") or file.endswith(".aar"):
                zip_ref.write(os.path.join(root, file),
                              os.path.relpath(os.path.join(root, file), os.path.join(dir_to_zip, '..')))
    zip_ref.close()


def read_dependencies_in_pom(pom_file):
    tree = ET.parse(pom_file)
    root = tree.getroot()
    POM_NS = "{http://maven.apache.org/POM/4.0.0}"
    dependencies = []

    parent_version = None
    parent_node = root.find('%sparent' % (POM_NS))
    if parent_node:
        parent_version_node = parent_node.find('%sversion' % POM_NS)
        if parent_version_node:
            parent_version = parent_version_node.text

    for child in root.iter('%sdependency' % (POM_NS)):
        scope = child.find('%sscope' % POM_NS)
        if scope == None or scope.text == 'compile':
            group = child.find('%sgroupId' % POM_NS).text
            name = child.find('%sartifactId' % POM_NS).text
            version_node = child.find('%sversion' % POM_NS)
            if version_node is not None:
                dependencies.append(MavenLibrary(group, name, version_node.text))
            elif parent_version is not None:
                dependencies.append(MavenLibrary(group, name, parent_version))

    return dependencies


def find_all_library_module_gradle_files_in_project(project_dir):
    gradle_files = []
    for root, dirs, files in os.walk(project_dir):
        for name in files:
            if name == 'build.gradle':
                file = os.path.join(root, name)
                if search_string(file, LIBRARY_PLUGIN):
                    gradle_files.append(file)
    return gradle_files


def find_all_dependencies_in_gradle(build_gradle_file):
    reg_pattern = re.compile("(implementation|compile)\s*\"(.+)\"")
    content = load_file(file)
    dependencies = []
    for match in re.findall(reg_pattern, content):
        dependency = match[1]
        group, name, version = dependency.split(':')
        dependencies.append(MavenLibrary(group, name, version))

    return dependencies



# https://yrom.net/blog/2015/02/07/change-gradle-maven-repo-url/
def use_official_maven(project_dir):
    replace_string(os.path.join(project_dir, 'build.gradle'), "maven\s*\{[^\{]+maven.oa.com[^\}]+\}", JCENTER, LIBRARY_PLUGIN, False)
    replace_string(os.path.join(project_dir, 'gradle/wrapper/gradle-wrapper.properties'), "distributionUrl=http\\\://android.oa.com/gradle/",
                   DISTRIBUTION_URL)


def remove_publish_gradle(build_gradle_file):
    replace_string(build_gradle_file, "apply from: '../../publish.gradle'", "")


def set_version(build_gradle_file, version_name):
    replace_string(build_gradle_file, VERSION_NAME, "versionName \"" + version_name + "\"")
    replace_string(build_gradle_file, "versionCode\s+\d+", "versionCode " + str(__get_version_code(version_name)))

def set_dependency_version(build_gradle_file, dependency, version_name):
    replace_string(build_gradle_file, dependency + ":(\S+)\"", dependency + ":{}\"".format(version_name))

def get_module_name(build_gradle_file) :
    return os.path.basename(os.path.dirname(build_gradle_file))


def __get_version_code(version_name):
    version_code = 0
    for index, item in enumerate(reversed(version_name.split(".")), start=0):
        version_code += math.pow(100, index) * int(item)

    return int(version_code)