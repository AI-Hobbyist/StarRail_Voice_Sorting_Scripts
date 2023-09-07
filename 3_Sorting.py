import json
import os
import re
import argparse
import tqdm as tq
from shutil import copy

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=str, help='未整理数据集目录', required=True)
parser.add_argument('--index', type=str, help='索引路径', required=True)
parser.add_argument('--dest', type=str, help='目标路径', required=True)
parser.add_argument('--lang', type=str, help='语言（可选CHS/EN/JP/KR，默认为CHS）', default="CHS")
args = parser.parse_args()

source = str(args.source)
dest = str(args.dest)
index = str(args.index)
lang = str(args.lang)
filter = 'fetter|battle|life|monster'

renameDict = {}

def is_in(full_path, regx):
    if re.findall(regx, full_path):
        return True
    else:
        return False

def is_file(full_path):
    if os.path.exists(full_path):
        return True
    else:
        return  False

def has_vaild_content(text):
    pattern = r'[\u4e00-\u9fa5\u3040-\u309f\u30a0-\u30ff\u1100-\u11ff\u3130-\u318f\uac00-\ud7afa-zA-Z0-9]+'
    if re.search(pattern, text):
        return True
    else:
        return False

def ren_player(player,lang):
    p_name = player
    if p_name == "playerboy" or p_name == "playergirl":
        if p_name == "playerboy":
            if lang == "CHS":
                p_name = "开拓者(男)"
            if lang == "EN":
                p_name = "Trailblazer(M)"
            if lang == "JP":
                p_name = "開拓者(男)"
            if lang == "KR":
                p_name = "개척자(남)"
        if p_name == "playergirl":
            if lang == "CHS":
                p_name = "开拓者(女)"
            if lang == "EN":
                p_name = "Trailblazer(F)"
            if lang == "JP":
                p_name = "開拓者(女)"
            if lang == "KR":
                p_name = "개척자(여)"
    else:
        p_name = player
    return p_name

f = open(index, encoding='utf8')
data = json.load(f)
for k in tq.tqdm(data.keys()):
    try:
        text = data.get(k).get('ContentText')
        char_name = data.get(k).get('Speaker')
        title_text = data.get(k).get('TitleText')
        if char_name is not None:
            char_name = ren_player(char_name,lang)
        else:
            char_name = ren_player(title_text,lang)
        if char_name in renameDict:
            char_name = renameDict[char_name]
        path = data.get(k).get('VoiceName')
        wav_source = source + '/' + path
        wav_file = os.path.basename(path)
        if has_vaild_content(text) == True and char_name is not None:
            dest_dir = dest + '/' + char_name
            wav_path = dest_dir + '/' + wav_file
            if is_in(path, filter) == False and is_file(wav_source) == True:
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                copy(wav_source, wav_path)
    except:
        pass
f.close()