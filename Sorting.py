from glob import glob
from pathlib import Path
import argparse
import subprocess
import re, os

parser = argparse.ArgumentParser(description="数据集一键整理")
parser.add_argument("-ver","--version", type=str, help="版本", required=True)
parser.add_argument("-lang","--language", type=str, help="语言（可选CHS/JP/EN/KR）", required=True)
args = parser.parse_args()

lang = args.language
ver = args.version

def is_in(full_path, regx):
    if re.findall(regx, full_path):
        return True
    else:
        return False

def get_support_lang(lang):
    indexs = glob('./Indexs/*.xlsx')
    path = ['中文 - Chinese', '英语 - English',  '日语 - Japanese', '韩语 - Korean']
    support_langs = []
    for langs in indexs:
        lang_code = Path(langs).name.replace(".xlsx","")
        support_langs.append(lang_code)
    if lang in support_langs:
        langcodes = support_langs
        i = langcodes.index(lang)
        dest_path = path[i]
    else:
        print("不支持的语言")
        exit()
    return lang, dest_path

lang_code, dest_path = get_support_lang(lang)

def run_commands(commands):
    for i, command in enumerate(commands):
        process = subprocess.Popen(command,shell=True)
        process.wait()

# 指令列表
commands = [
    f'echo 1. 正在进行解包，该步骤需要较长时间，请耐心等待...', 
    f'python 1_Unpack.py', 
    f'echo 2. 正在整理...',
    f'python 2_Sorting.py -l {lang_code}',
    f'echo 3. 正在二次整理语音...',
    f'python 3_Second_Sorting.py -lang {lang_code}',
    f'echo 4. 正在清洗标注中的html标签...',
    f'python 4_Clean_Html_Tags.py -lang {lang_code}',
    f'echo 解包、分类并清洗完成！'
    ]

# 运行指令
run_commands(commands)