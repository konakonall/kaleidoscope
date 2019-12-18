import sys
sys.path.append("../")
from kaleidoscope import configuration
import os

def main():
    conf = configuration.load(os.path.join(os.getcwd(), 'yaml/kaleido.yaml'))
    print conf.workflows
    print conf.app
    print conf.get_work('test')

if __name__ == '__main__':
    main()

    print os.path.basename('https://github.com/tencentyun/qcloud-documents.git')