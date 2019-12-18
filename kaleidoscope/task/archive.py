import os
from os.path import expanduser
import shutil
from kaleidoscope import util
import urllib2
from kal_task import KalTask
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client

local_maven_repository = os.path.join(expanduser('~'), ".m2", 'repository')
jcenter_maven_repository = 'http://jcenter.bintray.com/'
google_maven_repository = 'https://dl.google.com/dl/android/maven2/'

class Archiver(KalTask):

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

        if self.__conf['dest'] == 'file':
            self.__archive_dir = os.path.expanduser(self.__conf['path'])
        else:
            self.__archive_dir = os.path.join(self.__env['tmp_dir'], 'archive')

    def run(self):
        skip = self.__next is not None

        for module_name in self.__modules:
            if skip and module_name != self.__next:
                continue
            skip = False
            self.__next = module_name

            maven_library = util.MavenLibrary.from_module(self.__modules[module_name])

            module_tmp_dir = os.path.join(self.__archive_dir, maven_library.name + '-' + maven_library.version)
            if not os.path.exists(module_tmp_dir):
                os.makedirs(module_tmp_dir)

            print ("##### zip module: " + maven_library.name)

            self.__assemble_libraries_to_temp_dir(local_maven_repository, maven_library, module_tmp_dir)

            download_tmp_dir = os.path.join(module_tmp_dir, 'tmp')
            if os.path.exists(download_tmp_dir):
                shutil.rmtree(download_tmp_dir)

            zip_file = os.path.join(self.__archive_dir, maven_library.name + '.zip')
            util.zip_library(module_tmp_dir, zip_file)
            shutil.rmtree(module_tmp_dir)

            print ("##### zip end: " + zip_file)

        if self.__conf['dest'] == 'cos':
            self.__upload_module_to_cos()
            shutil.rmtree(self.__archive_dir)

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
                raise ValueError("Archive Task can't restore state because moduels is different")


    def __assemble_libraries_to_temp_dir(self, repository, library, tmp_dir):
        if os.path.isdir(repository):
            module_local_dir = os.path.join(repository, library.group.replace('.', os.sep), library.name,
                                            library.version)
        else:
            module_local_dir = self.__download_remote_jcenter_library(repository, library, tmp_dir)

        module_jar_uri = os.path.join(module_local_dir, library.name + '-' + library.version + '.jar')
        module_aar_uri = os.path.join(module_local_dir, library.name + '-' + library.version + '.aar')
        if os.path.exists(module_jar_uri):
            shutil.copyfile(module_jar_uri, os.path.join(tmp_dir, library.name + '-' + library.version + '.jar'))
        elif os.path.exists(module_aar_uri):
            shutil.copyfile(module_aar_uri, os.path.join(tmp_dir, library.name + '-' + library.version + '.aar'))

        module_pom_file = os.path.join(module_local_dir, library.name + '-' + library.version + '.pom')

        for dependency_module in util.read_dependencies_in_pom(module_pom_file):
            if os.path.exists(os.path.join(local_maven_repository, dependency_module.group.replace('.', os.sep), 
            dependency_module.name, dependency_module.version)):
                next_repository = local_maven_repository
            elif dependency_module.group.startswith('com.android.') or dependency_module.group.startswith('androidx.'):
                next_repository = google_maven_repository
            else:
                next_repository = jcenter_maven_repository

            self.__assemble_libraries_to_temp_dir(next_repository, dependency_module, tmp_dir)


    def __download_remote_jcenter_library(self, repository, maven_library, tmp_dir):
        remote_folder = repository + maven_library.group.replace('.', '/') + '/' + maven_library.name + '/' + maven_library.version
        module_jar_url = remote_folder + '/' + maven_library.name + '-' + maven_library.version + '.jar'
        module_aar_url = remote_folder + '/' + maven_library.name + '-' + maven_library.version + '.aar'
        module_pom_url = remote_folder + '/' + maven_library.name + '-' + maven_library.version + '.pom'

        download_temp_dir = os.path.join(tmp_dir, "tmp")
        if not os.path.exists(download_temp_dir):
            os.makedirs(download_temp_dir)

        try:
            filedata = urllib2.urlopen(module_jar_url)
            datatowrite = filedata.read()
            print ("##### download dependency : " + module_jar_url)

            with open(os.path.join(download_temp_dir, maven_library.name + '-' + maven_library.version + '.jar'), 'wb') as f:
                f.write(datatowrite)
        except Exception as e:
            print ("##### download {} ERROR BY: {}".format(module_jar_url, e))
            try:
                filedata = urllib2.urlopen(module_aar_url)
                datatowrite = filedata.read()
                print ("##### download dependency : " + module_aar_url)

                with open(os.path.join(download_temp_dir, maven_library.name + '-' + maven_library.version + '.aar'), 'wb') as f:
                    f.write(datatowrite)
            except Exception as e:
                print ("##### download {} ERROR BY: {}".format(module_aar_url, e))
                

        filedata = urllib2.urlopen(module_pom_url)
        datatowrite = filedata.read()
        print ("##### download dependency pom : " + module_pom_url)

        with open(os.path.join(download_temp_dir, maven_library.name + '-' + maven_library.version + '.pom'), 'wb') as f:
            f.write(datatowrite)

        return download_temp_dir


    def __upload_module_to_cos(self):
        region = self.__conf['region']
        bucket = self.__conf['bucket']
        path_prefix = self.__conf.get('path_prefix') or ''
        cos_secret_id = self.__env['cos_secret_id']
        cos_secret_key = self.__env['cos_secret_key']

        config = CosConfig(Secret_id=cos_secret_id, Secret_key=cos_secret_key, Region=region)
        client = CosS3Client(config)

        for filename in os.listdir(self.__archive_dir):
            if filename.endswith('.zip'):
                file = os.path.join(self.__archive_dir, filename)
                with open(file, 'rb') as fp:
                    response = client.put_object(
                        Bucket=bucket,
                        Body=fp,
                        Key=path_prefix + filename,
                        ContentDisposition=filename
                    )
                print 'upload {} to cos done, etag is {}'.format(filename, response['ETag'])

        