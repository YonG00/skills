# 本地运行与音色档案

当前个人版脚本为本仓库自行维护的编排，不复制未附许可证的上游脚本。运行依赖 `mlx-audio`、`mlx-whisper`、`soundfile`、`numpy`、`scipy`、`opencc-python-reimplemented` 和 ffmpeg。已验证的主要版本为 mlx-audio 0.6.2、mlx-whisper 0.4.3；依赖环境与模型放在本地资料项目中，不进 Git。

当前模型：Qwen3-TTS-12Hz-0.6B-Base-4bit、Whisper-small-mlx、DeepFilterNet-mlx v3。只需要克隆时不下载 CustomVoice；用官方预置声音时才另选 CustomVoice。具体模型资源是否就绪要读本地文件，不能凭技能说明猜测已下载。

## profile.json

以下为结构示意；实际文件、声纹和路径留在私人资料目录：

```json
{
  "id": "knowledge-male-clean-v1",
  "reference_audio": "reference.wav",
  "reference_text": "reference.txt",
  "reference_sha256": "由实际文件计算",
  "tts_model": "/本地模型目录",
  "asr_model": "/本地识别模型目录",
  "denoiser_model": "/本地降噪模型根目录",
  "speed": 1.08,
  "temperature": 0.65,
  "top_p": 0.9,
  "repetition_penalty": 1.15,
  "ai_generated": true
}
```

`reference.wav` 是用户认可音色所用的净化参考，不是合成成品反复克隆。`reference.txt` 须对应同一时间段；备份两者、profile、认可样片。原始素材如保留，仍在本地，不公开。

解析顺序：命令 `--profile` → 环境变量 `QWEN_TTS_PROFILE` → 技能目录 `local_config.json` → 当前工作区 `资料/音色库/默认音色.json`。指针文件结构为 `{"profile": "本地profile路径"}`，本地指针不可公开。

模型已有时使用本地目录，不触发 Hugging Face 完整快照检查，也不自动联网。迁移资料后检查 profile 中的绝对模型路径和虚拟环境入口；参考音频变了就更新哈希并重新让用户确认音色。

## 长稿状态

`prepare` 固定源稿、实际读法、参考哈希和参数的 SHA256。`synthesize` 只接受一致的批准摘要；摘要不是用户许可的替代品，仍需对话授权。

`status.json` 逐段记录完成状态、音频哈希和 QA 指标。`partial` 是限段探针完成，`needs_inspection` 是需排查，只有 `complete` 才表示全部核对片段已拼接导出。使用相同计划的 `--resume` 复用已核对音频，不能删掉失败记录后声称全部成功。

每段最多三次生成尝试，仍失败先排查该段，不无限重跑全文。保留原始片段、净化片段和核对文字方便诊断。最终时间表来自实际采样长度，不用字符数估计代替真实音频时长。
