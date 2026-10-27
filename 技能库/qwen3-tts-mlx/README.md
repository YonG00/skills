# Qwen3-TTS MLX：口播整理与纯人声

个人维护版 1.3.0：先请求许可，按需整理公式、表格与讲述衔接，再用本地保存的参考音色配音。支持长稿断点生成、逐段内容核对、统一降噪及 motion-video 交接；生成音频不代表获准制作或发布视频。

- [执行规范](SKILL.md)
- [口播整理](references/speech-prep.md)
- [运行环境与私人音色档案](references/runtime.md)
- [版本记录与上游来源](CHANGELOG.md)

Python 脚本见 `scripts/narrate.py`。私人音色、原稿、参考转写、模型与成品放在忽略的 `资料/`；通过本地 profile 引用，不打包进技能。依赖模型保持本地推理，不自动调用云端演示。

在仓库根目录运行检查：

```bash
python3 scripts/check.py
python3 -m unittest discover -s 技能库/qwen3-tts-mlx/tests -v
```

安装时同步本目录到运行时技能目录；另在运行时配置本地 `local_config.json` 指向 profile。该文件不能随源码提交。音色档案和模型资源需要独立保留，不能只备份 SKILL 就声称备份了声音。
