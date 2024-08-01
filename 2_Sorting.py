import json
import re
import os
import argparse
import pandas as pd
from tqdm import tqdm
from pathlib import Path
from glob import glob
from shutil import copy, move
from pathlib import Path

def crean_text(text):
    html_tag = re.compile(r'<.*?>')
    text = re.sub(html_tag,'',text)
    text = text.replace('\n',' ')
    return text

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

def sorting_voice(src,dst,mode,lang):
    langcode, dest_path = get_support_lang(lang)
    df = pd.read_excel(f"./Indexs/{langcode}.xlsx")
    for i, row in tqdm(df.iterrows(),desc="正在整理数据集...",total=len(df)):
        character = row['角色']
        voice_hash = row['语音哈希']
        voice_file = row['语音文件名']
        text = str(row['语音文本'])
        src_path = f"{src}/{voice_hash}.wav"
        
        if Path(src_path).exists() == True:

            if text != "" or text != None:
            
                if Path(f"{dst}/{dest_path}/{character}").exists() == False:
                    Path(f"{dst}/{dest_path}/{character}").mkdir(parents=True, exist_ok=True)
                
                dst_path = f"{dst}/{dest_path}/{character}/{voice_file}.wav"
                
                if mode == "cp":
                    copy(src_path,dst_path)
                elif mode == "mv":
                    move(src_path,dst_path)
                else:
                    print("模式选择错误！")
                    exit()
                    
                lab_file_path = f"{dst}/{dest_path}/{character}/{voice_file}.lab"
                cleaned_lab = crean_text(text)
                Path(lab_file_path).write_text(cleaned_lab,encoding='utf-8')
        else:
            tqdm.write(f"语音文件{voice_hash}.wav不存在！已跳过！")
    print("数据集整理完成！")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="数据集整理工具")
    parser.add_argument("-src","--source", type=str, default="./Data/wav", help="解包后的语音数据路径.")
    parser.add_argument("-dst","--output", type=str, default="./Data/sorted", help="整理后的语音数据路径.")
    parser.add_argument("-l","--language", type=str, help="语言选择", required=True)
    parser.add_argument("-m","--mode", type=str, default="cp", help="模式选择，cp:复制，mv:移动.")
    args = parser.parse_args()
    
    sorting_voice(args.source,args.output,args.mode.lower(),args.language.upper())


