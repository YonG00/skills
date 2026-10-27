#!/usr/bin/env python3
"""Reviewable, resumable local narration with a private reference voice profile."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(data):
    return sha(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())


def save(path, data):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def resolve_profile(argument=None):
    import os
    candidate = argument or os.environ.get('QWEN_TTS_PROFILE')
    if candidate:
        return Path(candidate).expanduser().resolve()
    for pointer in [Path(__file__).resolve().parents[1] / 'local_config.json',
                    Path.cwd() / '资料/音色库/默认音色.json']:
        if pointer.exists():
            value = Path(json.loads(pointer.read_text())['profile'])
            return (value if value.is_absolute() else pointer.parent / value).resolve()
    raise ValueError('No private voice profile configured; ask the user before selecting a voice')


def load_profile(path):
    path = Path(path).resolve()
    profile = json.loads(path.read_text(encoding='utf-8'))
    for key in ('reference_audio', 'reference_text', 'tts_model', 'asr_model', 'denoiser_model'):
        value = Path(profile[key]).expanduser()
        profile[key] = str((value if value.is_absolute() else path.parent / value).resolve())
        if not Path(profile[key]).exists():
            raise ValueError(f'Missing local profile resource: {key}')
    if sha(Path(profile['reference_audio']).read_bytes()) != profile['reference_sha256']:
        raise ValueError('Reference audio changed; obtain approval for the new voice')
    if not Path(profile['reference_text']).read_text().strip():
        raise ValueError('Reference transcript is empty')
    return profile


def split_text(text, limit=280):
    """Keep every character; prefer paragraph and sentence boundaries."""
    if limit < 100:
        raise ValueError('Segment limit must be at least 100 characters')
    if re.search(r'\$\$|^\s*\|.+\||https?://|```', text, re.M):
        raise ValueError('Prepare an oral script first: remove formulas, tables, URLs and code fences')
    pieces = re.split(r'(?<=[。！？!?；;])|(?<=\n)', text)
    segments, current = [], ''
    for piece in pieces:
        while len(piece) > limit:
            if current.strip():
                segments.append(current)
            current = ''
            cuts = [m.end() for m in re.finditer(r'[，,：:、\s]', piece[:limit])]
            cut = cuts[-1] if cuts else limit
            segments.append(piece[:cut])
            piece = piece[cut:]
        if current and len(current) + len(piece) > limit:
            segments.append(current)
            current = ''
        current += piece
    if current:
        segments.append(current)
    if ''.join(segments) != text:
        raise ValueError('Segmentation must preserve the full script')
    return [segment for segment in segments if segment.strip()]


def chinese_number(match):
    number = int(match.group())
    if number == 0:
        return '零'
    if number >= 100000000:
        return ''.join('零一二三四五六七八九'[int(d)] for d in match.group())
    def below(value):
        result, zero = '', False
        for power, unit in [(1000, '千'), (100, '百'), (10, '十'), (1, '')]:
            digit, value = divmod(value, power)
            if digit:
                if zero:
                    result += '零'
                result += ('零一二三四五六七八九'[digit] + unit)
                zero = False
            elif result and value:
                zero = True
        return result[1:] if result.startswith('一十') else result
    if number < 10000:
        return below(number)
    high, low = divmod(number, 10000)
    return below(high) + '万' + (('零' if low < 1000 else '') + below(low) if low else '')


def spoken(text):
    text = re.sub(r'(?<=\d),(?=\d{3}(?:\D|$))', '', text)
    text = re.sub(r'\d+\.\d+', lambda m: re.sub(r'\d+', chinese_number, m.group().split('.')[0]) + '点' +
                  ''.join('零一二三四五六七八九'[int(c)] for c in m.group().split('.')[1]), text)
    text = re.sub(r'\d+', chinese_number, text)
    return text.replace('Agent', '智能体').replace('知识性的问题', '知识类的问题')


def prepare(text_path, profile_path, out, limit):
    text_path, profile_path, out = Path(text_path).resolve(), Path(profile_path).resolve(), Path(out).resolve()
    profile = load_profile(profile_path)
    text = text_path.read_text(encoding='utf-8')
    if not text.strip():
        raise ValueError('Empty narration script')
    parts = split_text(text, limit)
    payload = {'schema': 1, 'source': str(text_path), 'source_sha256': sha(text.encode()),
               'profile_path': str(profile_path), 'profile_digest': digest(profile),
               'reference_text_sha256': sha(Path(profile['reference_text']).read_bytes()),
               'voice_id': profile['id'], 'speed': profile.get('speed', 1.08),
               'segments': [{'index': i + 1, 'source_text': part, 'text': spoken(part)} for i, part in enumerate(parts)]}
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'status.json').exists():
        raise ValueError('Use a new output directory or resume the existing approved plan')
    plan = {'sha256': digest(payload), 'payload': payload}
    save(out / 'plan.json', plan)
    (out / '口播原稿.txt').write_text(text, encoding='utf-8')
    (out / '实际配音文本.txt').write_text('\n\n'.join(x['text'].strip() for x in payload['segments']), encoding='utf-8')
    return {'sha256': plan['sha256'], 'segments': len(parts), 'characters': len(text), 'plan': str(out / 'plan.json')}


def validate_plan(path, approved):
    document = json.loads(Path(path).read_text(encoding='utf-8'))
    payload = document['payload']
    if digest(payload) != document['sha256'] or approved != document['sha256']:
        raise ValueError('Approval digest does not match this script and voice')
    if sha(Path(payload['source']).read_bytes()) != payload['source_sha256']:
        raise ValueError('Source changed; prepare and approve again')
    profile = load_profile(payload['profile_path'])
    if digest(profile) != payload['profile_digest'] or sha(Path(profile['reference_text']).read_bytes()) != payload['reference_text_sha256']:
        raise ValueError('Voice profile changed; prepare and approve again')
    return document, profile


def generate(plan_path, approved, resume=False, stop_after=None):
    # Approval and asset validation deliberately precede heavy imports and synthesis.
    document, profile = validate_plan(plan_path, approved)
    out = Path(plan_path).resolve().parent
    state_path = out / 'status.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else None
    if state and (not resume or state['sha256'] != approved):
        raise ValueError('Existing state requires --resume with the same approved digest')
    if state and state['state'] == 'complete':
        return state
    import os, gc, time
    os.environ['HF_HUB_OFFLINE'] = '1'
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly
    import mlx.core as mx
    from opencc import OpenCC
    import mlx_whisper
    from mlx_audio.tts.utils import load
    from mlx_audio.sts.models.deepfilternet.model import DeepFilterNetModel
    cc = OpenCC('t2s')
    def norm(text):
        return re.sub(r'[^a-z0-9\u4e00-\u9fff]', '', cc.convert(spoken(text)).lower())
    def transcribe(audio, words=False):
        return mlx_whisper.transcribe(str(audio), path_or_hf_repo=profile['asr_model'], language='zh',
                    temperature=(0., .2, .4, .6), condition_on_previous_text=False, word_timestamps=words)
    def metrics(expected, actual):
        import difflib
        a, b = norm(expected), norm(actual)
        score = difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
        return score, a[-6:] in b[-24:]
    started = time.time()
    state = state or {'sha256': approved, 'voice_id': profile['id'], 'state': 'running', 'segments': {}}
    state['state'] = 'running'
    save(state_path, state)
    files = out / 'segments'; files.mkdir(exist_ok=True)
    model = load(profile['tts_model'])
    enhancer = DeepFilterNetModel.from_pretrained(profile['denoiser_model'], version=3)
    ref, sr = sf.read(profile['reference_audio'], dtype='float32')
    ref = resample_poly(ref, 24000, sr).astype(np.float32)
    ref_text = Path(profile['reference_text']).read_text().strip()
    completed_this_run = 0
    try:
        for segment in document['payload']['segments']:
            index = segment['index']; key = str(index)
            wav = files / f'{index:03d}.wav'
            old = state['segments'].get(key)
            if old and old.get('state') == 'verified' and wav.exists() and sha(wav.read_bytes()) == old['audio_sha256']:
                continue
            state['current_segment'] = index
            save(state_path, state)
            accepted = False
            for attempt in range(3):
                mx.random.seed(131 + index * 13 + attempt * 101)
                pieces = [np.array(result.audio) for result in model.generate(
                    text=segment['text'], ref_audio=mx.array(ref), ref_text=ref_text, lang_code='chinese',
                    temperature=profile.get('temperature', .65), top_p=profile.get('top_p', .9),
                    repetition_penalty=profile.get('repetition_penalty', 1.15), max_tokens=1400, verbose=False)]
                audio = np.concatenate(pieces)
                if not np.isfinite(audio).all() or not .5 < len(audio) / 24000 < 115:
                    continue
                sf.write(files / f'{index:03d}_raw.wav', audio, 24000, subtype='PCM_24')
                result = enhancer.generate(resample_poly(audio, 2, 1).astype(np.float32), sample_rate=48000)
                clean = resample_poly(np.array(result.audio), 1, 2).astype(np.float32)
                trial = files / f'{index:03d}_trial.wav'
                sf.write(trial, clean, 24000, subtype='PCM_24')
                transcript = transcribe(trial)
                actual = transcript['text']
                # ICL may leak the final word of the reference. Trim only a proven extra prefix.
                expected_head = norm(segment['text'])[:6]
                position = norm(actual).find(expected_head)
                if 0 < position <= 8:
                    first = files / f'{index:03d}_head.wav'
                    sf.write(first, clean[:24000 * 12], 24000)
                    alignment = transcribe(first, words=True)
                    words = [w for s in alignment['segments'] for w in s.get('words', [])]
                    accumulated = ''
                    for word in words:
                        remaining = norm(actual)[len(accumulated):]
                        if remaining.startswith(expected_head):
                            cut = max(0, float(word['start']) - .025)
                            clean = clean[int(cut * 24000):]
                            # Rescore the cleaned waveform, not the guessed text offset.
                            sf.write(trial, clean, 24000, subtype='PCM_24')
                            transcript = transcribe(trial); actual = transcript['text']
                            break
                        accumulated += norm(word['word'])
                score, tail_ok = metrics(segment['text'], actual)
                save(files / f'{index:03d}_check.json', {'attempt': attempt + 1, 'text': actual, 'similarity': score, 'tail_present': tail_ok})
                if score >= .65 and tail_ok:
                    accepted = True
                    break
                print(json.dumps({'segment': index, 'retry': attempt + 1, 'similarity': round(score, 3), 'tail_present': tail_ok}), flush=True)
            if not accepted:
                raise ValueError(f'Segment {index} failed content verification; inspect local checks before resuming')
            # Speed adjustment is real DSP: Base does not implement its speed argument.
            paced = files / f'{index:03d}_paced.wav'
            subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(trial), '-af',
                f"atempo={profile.get('speed', 1.08)},highpass=f=65", '-ar', '24000', '-c:a', 'pcm_f32le', str(paced)], check=True)
            clean, _ = sf.read(paced, dtype='float32')
            if not np.isfinite(clean).all() or np.max(np.abs(clean)) < .001:
                raise ValueError(f'Segment {index}: invalid cleaned waveform')
            n = 480; frame = clean[:len(clean)//n*n].reshape(-1, n)
            rms = np.sqrt(np.mean(frame*frame, axis=1))
            active = rms[rms > max(.003, np.percentile(rms, 60)*.2)]
            gain = min(.11 / max(float(np.sqrt(np.mean(active**2))), 1e-8), .87 / float(np.max(np.abs(clean))))
            clean *= gain
            # Short fades only at waveform edges; no continuously pumping noise gate.
            fade = min(240, len(clean)//10)
            clean[:fade] *= np.linspace(0, 1, fade); clean[-fade:] *= np.linspace(1, 0, fade)
            sf.write(wav, clean, 24000, subtype='PCM_24')
            state['segments'][key] = {'state': 'verified', 'audio_sha256': sha(wav.read_bytes()),
                'duration': len(clean)/24000, 'similarity': score, 'gain': gain, 'attempts': attempt + 1}
            state['elapsed_this_run'] = round(time.time() - started, 1)
            save(state_path, state)
            print(json.dumps({'segment': index, 'total': len(document['payload']['segments']), 'duration': round(len(clean)/24000, 2), 'similarity': round(score, 3)}), flush=True)
            gc.collect(); mx.clear_cache()
            completed_this_run += 1
            if stop_after and completed_this_run >= stop_after:
                state['state'] = 'partial'; save(state_path, state); return state
        timeline, cursor = [], 0
        with sf.SoundFile(out / 'voice.wav', 'w', samplerate=24000, channels=1, subtype='PCM_24') as final:
            for segment in document['payload']['segments']:
                audio, sr = sf.read(files / f"{segment['index']:03d}.wav", dtype='float32')
                start = cursor / 24000; final.write(audio); cursor += len(audio)
                timeline.append({'index': segment['index'], 'start': start, 'end': cursor/24000,
                                 'text': segment['source_text'].strip(), 'spoken_text': segment['text'].strip()})
                if segment['index'] != len(document['payload']['segments']):
                    silence = np.zeros(4320, dtype=np.float32); final.write(silence); cursor += len(silence)
        save(out / 'segments.json', timeline)
        subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(out / 'voice.wav'),
            '-c:a', 'libmp3lame', '-q:a', '2', '-metadata', 'artist=AI合成', '-metadata', 'title=知识分享口播（AI合成）', str(out / 'voice.mp3')], check=True)
        (out / 'motion_handoff.md').write_text(
            '# motion-video 交接\n\n人声：voice.wav（24kHz、单声道、24bit PCM，无配乐，AI合成）。\n\n'
            f'总时长：{cursor/24000:.3f}秒。段落时间和正文见 segments.json；它不是逐字时间轴。\n\n'
            '口播稿见口播原稿.txt，实际读法见实际配音文本.txt。公式和表格画面沿用原稿配套资料。\n\n'
            '后续视频面向B站知识分享，建议16:9；制作、配乐与发布仍需用户另行许可。'
            '不能把已授权配音当作已授权制作或发布视频。\n', encoding='utf-8')
        state.update(state='complete', duration_seconds=cursor/24000, ai_generated=True,
                     wav_sha256=sha((out/'voice.wav').read_bytes()))
        save(state_path, state)
        return state
    except Exception as error:
        state.update(state='needs_inspection', error_type=type(error).__name__, error=str(error))
        save(state_path, state)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--text', required=True); prep.add_argument('--profile'); prep.add_argument('--out', required=True)
    prep.add_argument('--max-chars', type=int, default=280)
    run = sub.add_parser('synthesize')
    run.add_argument('--plan', required=True); run.add_argument('--approved-sha256', required=True)
    run.add_argument('--resume', action='store_true'); run.add_argument('--stop-after', type=int)
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare(args.text, resolve_profile(args.profile), args.out, args.max_chars)
    else:
        result = generate(args.plan, args.approved_sha256, args.resume, args.stop_after)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
