# -*- coding: utf-8 -*-
import os
import shutil
from kaleidoscope import util
from git import Repo
import errno
from kal_task import KalTask

class CodebaseSync(KalTask):

    def __init__(self, task_conf, app):
        self.__conf = task_conf
        self.__env = app['env']
        self.__tmp_github_dir = os.path.join(self.__env['tmp_dir'], 'remote_git')

    def run(self):
        src_dir = self.__env['project_root']
        remote_repository = self.__conf['repository']
        message = self.__conf['commit_message']

        project_name = os.path.basename(remote_repository).replace('.git', '')

        repo = Repo.clone_from(remote_repository, self.__tmp_github_dir)

        remote_dir = os.path.join(self.__tmp_github_dir, project_name)
        try:
            if os.path.exists(remote_dir):
                shutil.rmtree(remote_dir)
            shutil.copytree(src_dir, remote_dir, ignore=self.__ignore_path_common)
        except OSError as exc:  # python >2.5
            if exc.errno == errno.ENOTDIR:
                shutil.copy(src_dir, remote_dir)
            else:
                raise exc

        util.use_official_maven(remote_dir)
        project_module_gradle_files = util.find_all_library_module_gradle_files_in_project(remote_dir)
        for build_gradle_file in project_module_gradle_files:
            util.remove_publish_gradle(build_gradle_file)

        repo.git.add(A=True)
        repo.index.commit(message=message)

        repo.remotes.origin.push()

        if os.path.exists(self.__tmp_github_dir):
            shutil.rmtree(self.__tmp_github_dir)
    

    def __ignore_path_common(self, dir, files):
        ignore = []
        if dir.find('\\build\\') > 0:
            return [dir]
        for file in files:
            full_path = os.path.join(dir, file)
            if full_path.find('\\build\\') > 0:
                ignore.append(file)

        return ignore