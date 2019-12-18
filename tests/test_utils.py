import sys
sys.path.append("../")
from kaleidoscope import util
import os

if __name__ == '__main__':
    print util.get_shell_output('/Users/wjielai/Workspace/QCloudAndroid/library/TencentAppCloud', 
    './gradlew :foundation:properties | grep projectDir')