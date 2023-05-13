import json
import os
import argparse
import tqdm as tq
from pathlib import Path
from pypinyin import lazy_pinyin, load_phrases_dict

parser = argparse.ArgumentParser()
parser.add_argument('--index', type=str, help='索引路径', required=True)
parser.add_argument('--dest', type=str, help='目标路径', required=True)
args = parser.parse_args()

dest = str(args.dest)
index = str(args.index)

personalized_dict = {
    '嗯': [['en']]
}

renameDict = {
    'none': 'none',
}

load_phrases_dict(personalized_dict)

f = open(index, encoding='utf8')
data = json.load(f)
for k in tq.tqdm(data.keys()):
    try:
        text = data.get(k).get('ContentText')
        char_name = data.get(k).get('Speaker')
        if char_name is not None:
            char_name = char_name
        else:
            char_name = data.get(k).get('TitleText')
        path = data.get(k).get('VoiceName')
        wav_file = os.path.basename(path)
        if text is not None and char_name is not None:
            dest_dir = dest + '/' + char_name
            pinyin = " ".join(lazy_pinyin(text, errors='ignore'))
            lab_path = dest_dir + '/' + wav_file
            lab_path = lab_path.replace(".wav",".lab")
            if text is not None:
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                Path(lab_path).write_text(pinyin, encoding='utf-8')
    except:
        pass
f.close()
