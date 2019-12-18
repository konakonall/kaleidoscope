# -*- coding: utf-8 -*-
import configuration
import os
import json
from os.path import expanduser
import shutil
import traceback

def reset():
    wf_list = __load_data()

    version = wf_list['wf_version']
    wf_list = { 'wf_version' : version }

    __save_data(wf_list)


def install(yaml_file):
    config = configuration.load(yaml_file)

    wf_list = __load_data()
    abs_file = yaml_file if os.path.isabs(yaml_file) else os.path.abspath(yaml_file)

    for work_name in config.workflows.keys():
        if work_name in wf_list:
            raise ValueError("workflow '" + work_name + "' already installed")
    
    for work_name in config.workflows.keys():
        wf_list[work_name] = { 'conf' : abs_file }
        print 'Successfully installed workflow : ' + work_name

    __save_data(wf_list)
    

def start(workflow_name, is_continue = False):
    
    wf_list = __load_data()

    if workflow_name not in wf_list:
        raise ValueError("workflow '" + workflow_name + "' is not installed")

    wf_data = wf_list[workflow_name]
    tmp_dir = os.path.join(expanduser('~'), 'Downloads', 'kaleido')

    config = configuration.load(wf_data['conf'])
    config.app['env']['project_root'] = os.getcwd()
    config.app['env']['tmp_dir'] = tmp_dir
    tasks = config.get_work(workflow_name)

    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    if is_continue and 'steps' in wf_data and wf_data['steps'] != config.workflows[workflow_name]['steps']:
        raise ValueError("The workflow cann't continue because it has been changed since last executed")

    wf_data['steps'] = config.workflows[workflow_name]['steps']

    start_point = wf_data['start_point'] if is_continue and 'start_point' in wf_data else 0

    __save_data(wf_list)
    
    for idx, task in enumerate(tasks):
        if idx < start_point:
            continue
        
        if is_continue:
            task.restore_state(wf_data)
        
        try:
            task.run()
        except Exception as e:
            task.save_state(wf_data)
            print(traceback.format_exc())
            raise e
        else:
            wf_data['start_point'] = idx + 1 if len(tasks) > idx + 1 else 0
        finally:
            __save_data(wf_list)

    shutil.rmtree(tmp_dir)


def __get_wf_data_file():
    return os.path.join(os.path.dirname(__file__), 'wf.dat')

def __save_data(wf_list):
    with open(__get_wf_data_file(), 'wb') as outfile:
        json.dump(wf_list, outfile)

def __load_data():
    with open(__get_wf_data_file()) as infile:
        wf_list = json.load(infile)

    return wf_list
