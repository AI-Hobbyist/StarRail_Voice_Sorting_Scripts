import os
import json
import random
import copy
import argparse
from fnvhash import fnv1_64

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=str, help='Dim 的星穹铁道数据文件路径', required=True)
parser.add_argument('--dest', type=str, help='目标路径，可选，默认为当前目录', default='./')
parser.add_argument('--lang', type=str, help='语言，可选 CHS/EN/JP/KR，默认为 CHS', default='CHS')
args = parser.parse_args()

StarRailData_path = str(args.source)
Dest_Path = str(args.dest)
TextMap_Language = str(args.lang)

cutscene = os.path.join(StarRailData_path, "./ExcelOutput/CutSceneConfig.json")
atlas = os.path.join(StarRailData_path, "./ExcelOutput/VoiceAtlas.json")
dialogue = os.path.join(StarRailData_path, "./ExcelOutput/TalkSentenceConfig.json")
voiceconfig = os.path.join(StarRailData_path, "./ExcelOutput/VoiceConfig.json")
avatarconfig = os.path.join(StarRailData_path, "./ExcelOutput/AvatarConfig.json")
textmap = os.path.join(StarRailData_path, f"./TextMap/TextMap{TextMap_Language}.json")

with open(textmap, encoding="utf-8") as f:
    textmap_data = json.load(f)

if TextMap_Language == "CHS":
    Voice_Language = "Chinese(PRC)"
if TextMap_Language == "EN":
    Voice_Language = "English"
if TextMap_Language == "JP":
    Voice_Language = "Japanese"
if TextMap_Language == "KR":
    Voice_Language = "Korean"

def get_dialogue_content():
    output_data = {}
    with open(dialogue, encoding="utf-8") as f:
        parsed_data = json.load(f)

    for key in parsed_data:
        if "VoiceID" in parsed_data[key]:
            voice_id = parsed_data[key]["VoiceID"]
            title_hash = parsed_data[key]["TextmapTalkSentenceName"]["Hash"]
            content_hash = parsed_data[key]["TalkSentenceText"]["Hash"]
            title_text = textmap_data.get(str(title_hash))
            content_text = textmap_data.get(str(content_hash))
            output_data[voice_id] = {"VoiceID": voice_id,
                                    #  "TitleHash": title_hash,
                                    #  "ContentHash": content_hash,
                                     "TitleText": title_text,
                                     "ContentText": content_text}
    return output_data

def get_atlas_content():
    output_data = {}
    with open(atlas, encoding="utf-8") as f:
        parsed_data = json.load(f)
    with open(avatarconfig, encoding="utf-8") as f:
        avatar_data = json.load(f)

    for avatar_id in parsed_data:
        avater_hash = avatar_data[avatar_id]["AvatarName"]["Hash"]
        avater_text = textmap_data.get(str(avater_hash))
        for main_id in parsed_data[avatar_id]:
            current_dict = parsed_data[avatar_id][main_id]
            if "AudioID" in current_dict:
                voice_id = current_dict["AudioID"]
                title_hash = current_dict["VoiceTitle"]["Hash"]
                content_hash = current_dict["Voice_M"]["Hash"]
                title_text = textmap_data.get(str(title_hash))
                content_text = textmap_data.get(str(content_hash))
                output_data[voice_id] = {"VoiceID": voice_id,
                                        #  "TitleHash": title_hash,
                                        #  "ContentHash": content_hash,
                                         "Speaker": avater_text,
                                         "TitleText": title_text,
                                         "ContentText": content_text}
    return output_data

def get_cutscene_content():
    output_data = {}
    with open(cutscene, encoding="utf-8") as f:
        parsed_data = json.load(f)

    for key in parsed_data:
        current_dict = parsed_data[key]
        if "VoiceID" in current_dict:
            voice_id = current_dict["VoiceID"]
        if bool(current_dict.get("CaptionPath")):
            content_path = os.path.join(
                StarRailData_path,
                current_dict["CaptionPath"]
                )
            with open(content_path) as f:
                content_data = json.load(f)
            content_hash = []
            content_text = []
            for caption in content_data["CaptionList"]:
                content_hash.append(caption["CaptionTextID"]["Hash"])
                content_text.append(
                    textmap_data.get(str(caption["CaptionTextID"]["Hash"]))
                    )
            output_data[voice_id] = {"VoiceID": voice_id,
                                    #  "TitleHash": None,
                                    #  "ContentHash": content_hash,
                                     "TitleText": None,
                                     "ContentText": content_text}
    return output_data

def add_voice_speaker(voicepath: dict):
    avatar_listmap = []
    avatar_dictmap = {}
    with open(avatarconfig, encoding="utf-8") as f:
        parsed_data = json.load(f)
    
    for _, value in parsed_data.items():
        sp_tag = value.get("AvatarVOTag")
        sp_NameHash = value["AvatarName"]["Hash"]
        sp_NameText = textmap_data.get(str(sp_NameHash))
        avatar_listmap.append(sp_tag)
        avatar_dictmap[str(sp_tag)] = sp_NameText
    
    # Parse character name from string(VoicePath)
    voice_filename = str(voicepath.get('VoicePath'))
    voice_filename_piece = voice_filename.split("_")
    for p in voice_filename_piece:
        # non-player character name with voice's language tag
        if p in avatar_listmap:
            speaker_name = avatar_dictmap[str(p)]
            voicepath.update(Speaker=speaker_name)
            break
        elif p == "player":
            if voice_filename.endswith("_m"):
                speaker_name = "playerboy"
            elif voice_filename.endswith("_f"):
                speaker_name = "playergirl"
            else:
                speaker_name = "Unknown"
            voicepath.update(Speaker=speaker_name)
            break
        else:
            continue
    return voicepath

def merge_voice_info(content: dict, path: dict):
    path_for_girl = {}
    for v_id, v_path in path.items():
        if int(v_id) not in content:
            continue
        if bool(v_path.get("IsPlayerInvolved")):
            # Copy playergirl VoicePath
            # Calculate hash in the subsequent for loop
            # Add random number to avoid duplicate keys in content dict
            rand_num = int(random.randint(10, 99))
            copy_v_id = f"{v_id}{rand_num}"
            # Deepcopy to avoid object nesting
            path_for_girl[int(copy_v_id)] = copy.deepcopy(path[v_id])
            path_for_girl[int(copy_v_id)]['VoicePath'] = f"{path_for_girl[int(copy_v_id)]['VoicePath']}_f"
            content[int(copy_v_id)] = copy.deepcopy(content[int(v_id)])
            # Calculate playerboy Hash
            v_path['VoicePath'] = f"{v_path['VoicePath']}_m"
        add_voice_speaker(v_path)
        voice_filename = f"{v_path['VoicePath']}.wem"
        voice_readable_name = f"{v_path['VoicePath']}.wav"
        voice_hash_source = f"{Voice_Language}/Voice/{voice_filename}"
        voice_hash_string = format(fnv1_64(bytes(voice_hash_source.lower(), "utf-8")), "016x")
        voice_hashed_name = f"{voice_hash_string}.wav"
        v_path.update(
            VoiceName=voice_readable_name,
            VoiceHashName=voice_hashed_name
        )
        v_path.pop('VoicePath')
        content[int(v_id)].update(v_path)
        content[str(voice_hash_string)] = content.pop(int(v_id))

    for v_id, v_path in path_for_girl.items():
        add_voice_speaker(v_path)
        voice_filename = f"{v_path['VoicePath']}.wem"
        voice_readable_name = f"{v_path['VoicePath']}.wav"
        voice_hash_source = f"{Voice_Language}/Voice/{voice_filename}"
        voice_hash_string = format(fnv1_64(bytes(voice_hash_source.lower(), "utf-8")), "016x")
        voice_hashed_name = f"{voice_hash_string}.wav"
        v_path.update(
            VoiceName=voice_readable_name,
            VoiceHashName=voice_hashed_name
        )
        v_path.pop('VoicePath')
        content[int(v_id)].update(v_path)
        content[str(voice_hash_string)] = content.pop(int(v_id))

    return content

def main():
    content_dict = {}
    content_dict.update(get_dialogue_content())
    content_dict.update(get_atlas_content())
    content_dict.update(get_cutscene_content())

    with open(voiceconfig) as f:
        voiceconfig_dict = json.load(f)
    output = merge_voice_info(content_dict, voiceconfig_dict)

    output_json_path = Dest_Path + '/' + Voice_Language + '.json'
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

main()
