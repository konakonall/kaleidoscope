kaleidoscope
--------

一个 Android 发布工具，可以通过文件配置工作流。支持的操作包括：

1. 发布 binary 到 Bintry
2. 同步代码到 git 仓库
3. 二进制文件打包上传到 COS


使用说明：

1. 首先确保电脑上已经安装 python 2.7和 pip
2. 下载代码，在根目录执行 pip install .
3. 按照格式和你的需求，写好 workflow 的 yaml 描述文件。yaml 格式请参考示例。
4. 安装描述文件，执行 kal install <yaml_file>
5. 进入你的 Android 工程目录下，执行 kal start <workflow_name>，如果是继续执行上次未完成的任务，可以添加参数 --contine


usage: kal <command> <args>

The most commonly used commands are:
   install    Install your project workflow description file
   start      Start a pre-installed workflow

Android Project Publish Tool

positional arguments:
  command     Subcommand to run

optional arguments:
  -h, --help  show this help message and exit