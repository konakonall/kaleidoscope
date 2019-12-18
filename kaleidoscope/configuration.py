# -*- coding: utf-8 -*-
import yaml
import os
from task.upload_bin import BinUploader
from task.archive import Archiver
from task.sync_codebase import CodebaseSync

def load(yaml_file):
    f = open(yaml_file)
    dict = yaml.load(f)
    return Configuration(dict)


class Configuration(object) :

    def __init__(self, dict):
        self.app = dict['app']
        if 'env' not in self.app:
            self.app['env'] = {}
        self.workflows = dict['workflows']
    
    def get_work(self, name):
        work = self.workflows[name]
        if work is None:
            raise ValueError("unknown work name :" + name)

        steps = work['steps']
        if steps is None or len(steps) < 1:
            raise ValueError('no steps for work : ' + name)

        tasks = []
        for step in steps:
            step_name = step.keys()[0]
            step_conf = step[step_name]
            if step_name == 'upload':
                tasks.append(BinUploader(step_conf, self.app))
            elif step_name == 'archive':
                tasks.append(Archiver(step_conf, self.app))
            elif step_name == 'sync':
                tasks.append(CodebaseSync(step_conf, self.app))

        return tasks



    



