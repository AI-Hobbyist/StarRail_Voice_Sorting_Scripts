# StarRail Voice Sorting Scripts

星穹铁道语音的解包、转码、整理、分类、标签清理和数据统计工具。

## 脚本

- `Voice_Sorting.py`：统一处理流程，整合原先 1～5 步。
- `6_Merge_Language_Xlsx.py`：独立合并同语言索引 XLSX。
- `Deprecated/`：旧分步脚本备份，不再作为推荐入口。

## 安装

```powershell
python -m pip install -r .\requirements.txt
```

项目自带以下工具，无需单独安装：`quickbms.exe`、`wwise_pck_extractor.bms`、`vgmstream-cli.exe`。

## 目录约定

```text
Data/
  pcks/                 # 待解包的 PCK
  raw/                  # 解包后的 WEM；支持 chinese(prc) 等子目录
  wav/                  # 平铺的普通 WEM 转码输出：<哈希>.wav
  sorted/               # 第一次按角色整理的中间结果
  second_sorted/        # 最终分类结果
  Sorted.json           # 普通语音二次分类规则
Indexs/
  CHS.xlsx EN.xlsx JP.xlsx KR.xlsx
数据统计_模板.xlsx
```

battle 语音在索引中使用 `AudioEvent_MediaID` 文件名。转码后其来源文件为 `MediaID.wav`，与普通语音统一放在 `Data/wav/`。

## 先执行 dry-run

不会解包、转码、复制、移动或创建整理结果，仅检查输入和目标路径：

```powershell
python .\Voice_Sorting.py -l CHS --skip-unpack --dry-run
```

若索引不在当前 `Indexs`，可明确指定：

```powershell
python .\Voice_Sorting.py -l CHS --skip-unpack --dry-run `
  --index "..\Indexs\CHS.xlsx"
```

## 完整处理流程

```powershell
python .\Voice_Sorting.py -l CHS `
  --game "StarRail" `
  --version "4.4"
```

该命令依次执行：PCK 解包、递归 WEM 转 WAV、按 XLSX 整理、二次分类、清理 LAB 中的 HTML 标签，并输出：

```text
StarRail_4.4_数据统计.xlsx
```

常用参数：

- `--skip-unpack`：跳过 PCK 解包，只处理已有 WEM。
- `--mode cp|mv`：整理时复制或移动 WAV，默认 `cp`。
- `--wem`、`--wav`：覆盖 WEM 输入与 WAV 输出目录。
- `--final`：覆盖最终分类输出目录。
- `--stats-dir`：指定统计 XLSX 输出目录。

## 合并上级索引 XLSX

将上级索引目录的同语言 XLSX 合并，并输出到本项目 `Indexs/`：

```powershell
python .\6_Merge_Language_Xlsx.py `
  --source-index-dir "..\Indexs" `
  --output-dir ".\Indexs" `
  --languages CHS EN JP KR
```

合并器兼容旧版四列索引和当前包含“是否为战斗语音”的六列索引；同一 battle 事件与 MediaID 的重复行会去重。

## 相关资料

[星穹铁道语音包下发规则](docs/sr_audio_dispatch.md)
