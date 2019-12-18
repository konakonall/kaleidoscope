# -*- coding: utf-8 -*-
from kaleidoscope import util
import os
from kal_task import KalTask
import requests

class BinUploader(KalTask):

    __next = None

    def __init__(self, task_conf, app):
        self.__conf = task_conf
        self.__env = app['env']
        if self.__conf['modules'] == '*':
            self.__modules = app['modules']
        else:
            self.__modules = {}
            for m in self.__conf['modules']:
                self.__modules[m] = app['modules'][m]
        
        self.__mapping_files = []

    def run(self):
        repository = self.__conf['repository']
        project_root = self.__env['project_root']

        if repository == 'mavenLocal':
            self.__exec(project_root, 'install')
        elif repository == 'bintray':
            self.__exec(project_root, 'bintrayUpload')
        else:
            raise ValueError("unknown repository: " + repository)

        print ("##### upload libraries to {} complete ".format(repository))

        if 'mappings' in self.__conf and self.__conf['mappings']['type'] == 'merge' and self.__conf['mappings']['dest'] == 'bugly':
            self.__upload_merged_mapping_file_to_bugly()


    def save_state(self, wf_data):
        wf_data['state'] = {
            'modules': self.__modules,
            'next': self.__next
        }

    def restore_state(self, wf_data):
        if 'state' in wf_data:
            if 'next' in wf_data['state']:
                self.__next = wf_data['state']['next']
            if 'modules' in wf_data['state'] and wf_data['state']['modules'] != self.__modules:
                raise ValueError("Upload Task can't restore state because moduels is different")

    def __exec(self, project_root, cmd):
        skip = self.__next is not None

        for module_name in self.__modules:
            if skip and module_name != self.__next:
                continue
            skip = False
            self.__next = module_name

            maven_name = self.__modules[module_name]
            maven_library = util.MavenLibrary.from_module(maven_name)

            build_gradle_file = os.path.join(project_root, module_name, 'build.gradle')
            if os.path.exists(build_gradle_file):
                util.set_version(build_gradle_file, maven_library.version)
            else:
                project_dir = util.get_shell_output(project_root, "./gradlew :foundation:properties | grep projectDir")
                dir = project_dir.replace('projectDir: ', '').strip()
                build_gradle_file = os.path.join(dir, 'build.gradle')
                util.set_version(build_gradle_file, maven_library.version)

            bintray_user = self.__env.get('bintray_user')
            bintray_apikey = self.__env.get('bintray_apikey')
            override = self.__conf.get('override')
            proguard = str(self.__conf.get('proguard')) if self.__conf.get('proguard') else 'true'

            util.call_shell(project_root, "./gradlew :{}:clean :{}:{} -Puser={} -Pkey={} -Poverride={} -Pdebug={}".format(
                                    module_name, module_name, cmd, bintray_user, bintray_apikey,
                                    'true' if override else 'false', proguard))

            self.__mapping_files.append(os.path.join(os.path.dirname(build_gradle_file), 'build/outputs/mapping/release/mapping.txt'))

            print ("##### upload {} complete ".format(module_name))

    
    def __upload_merged_mapping_file_to_bugly(self):
        bugly_appkey = self.__env['bugly_appkey']
        bugly_appid = self.__env['bugly_appid']
        ver = self.__conf['mapping']['ver']
        pkg = self.__conf['mapping']['pkg']
        
        full_content = ''
        for file in self.__mapping_files:
            content = util.load_file(file=file)
            full_content += content

        merged_file = os.path.join(self.__env['tmp_dir'], 'mapping.txt')
        util.write_file(merged_file, full_content)

        url = 'https://api.bugly.qq.com/openapi/file/upload/symbol?app_key={}&app_id={}'.format(
            bugly_appkey, bugly_appid)
        data = {}
        data['api_version']= 1
        data['app_id']= bugly_appid
        data['app_key']= bugly_appkey
        data['symbolType']= 1 # mapping
        data['bundleId']= pkg
        data['productVersion']= ver
        data['fileName']= 'mapping.txt'
        files = {'file': ('mapping.txt', open(merged_file, 'rb'), 'text/plain')}

        response = requests.post(url=url, data=data, files=files)

        print 'upload symbol file : ' + response.content.decode("unicode-escape")

        if response.status_code >= 200 and response.status_code < 300:
            os.remove(merged_file)