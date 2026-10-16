#!/usr/bin/env python3
"""Exercise intake, confirmation gates and a four-turn render with synthetic media."""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from render_video import Renderer


HERE = Path(__file__).resolve().parent


def run(*args):
    return subprocess.check_output([str(arg) for arg in args], text=True, encoding='utf-8')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def rejects(manifest, label):
    try:
        Renderer(manifest, None)
    except ValueError:
        return
    raise RuntimeError(f'Expected rejection: {label}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', type=Path, required=True)
    args = parser.parse_args()
    font = args.font.expanduser().resolve()
    require(font.is_file(), 'Provide an existing Chinese/English font.')
    with tempfile.TemporaryDirectory(prefix='dualframe-') as directory:
        project = Path(directory) / "双帧 project's test"
        first = json.loads(run(sys.executable, HERE/'new_job.py', '--root', project, '--font', font))
        second = json.loads(run(sys.executable, HERE/'new_job.py', '--root', project))
        require(not first['reused'] and second['reused'], 'An unfinished intake must be reused.')
        require(first['current_job'] == second['current_job'], 'Intake directory changed unexpectedly.')
        job = Path(first['current_job'])
        manifest = job/'manifest.json'
        rejects(manifest, 'draft without a user confirmation')
        for side, hz in [('top', 440), ('bottom', 660)]:
            run('ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i',
                'testsrc2=size=720x400:rate=30:duration=4', '-f', 'lavfi', '-i',
                f'sine=frequency={hz}:sample_rate=48000:duration=4', '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', job/f'source/{side}.mp4')
        cfg = {
            'title': 'DualFrame 合成测试',
            'brief': {'status': 'confirmed', 'confirmation': 'Synthetic fixture only; not a real user confirmation.',
                      'confirmed_at': '2026-01-01T00:00:00+00:00'},
            'font': str(font), 'source_label': 'SYNTHETIC TEST / 非真实发言',
            'speakers': {}, 'phases': []
        }
        for side, label in [('top', '甲'), ('bottom', '乙')]:
            cfg['speakers'][side] = {
                'name_en': f'Test {side}', 'name_zh': f'合成人物{label}', 'date': 'TEST',
                'file': f'source/{side}.mp4', 'url': f'https://example.org/synthetic-{side}',
                'crop': [720, 400, 0, 0]
            }
        for i, side in enumerate(['top', 'bottom', 'top', 'bottom']):
            start = 0 if i < 2 else 2
            cfg['phases'].append({
                'name': f'{i+1:02}-{side}', 'speaker': side, 'start': start, 'end': start+2,
                'ends_after': 'Synthetic timing fixture; no speech or semantic claim.',
                'boundary_reviewed': True, 'hold_zh': '测试图与提示音。',
                'hold_en': 'Test pattern and tone.',
                'cues': [[start, start+2, '测试图与提示音。', 'Test pattern and tone.']]
            })
        def save():
            manifest.write_text(json.dumps(cfg, ensure_ascii=False), encoding='utf-8')
        save()
        cfg['phases'][0]['boundary_reviewed'] = False
        save()
        rejects(manifest, 'missing boundary review')
        cfg['phases'][0]['boundary_reviewed'] = True
        cfg['phases'][0]['cues'].append([1, 2, '重叠字幕', 'Overlapping cue'])
        save()
        rejects(manifest, 'overlapping subtitles')
        cfg['phases'][0]['cues'].pop()
        save()
        Renderer(manifest, None).render()
        output = job/'output'
        report = json.loads((output/'qa/report.json').read_text(encoding='utf-8'))
        require(report['status'] == 'pass', 'Freeze/motion check failed.')
        require(len(report['phases']) == 4, 'Expected four alternating phases.')
        srt = (output/'字幕_中英双语.srt').read_text(encoding='utf-8')
        require(srt.count(' --> ') == 4, 'Expected four bilingual subtitle cues.')
        timeline = json.loads((output/'timeline.json').read_text(encoding='utf-8'))
        require(timeline['source_duration_by_speaker'] == {'top': 4.0, 'bottom': 4.0},
                'Source duration changed.')
        state_path = project/'视频任务/状态.json'
        state = json.loads(state_path.read_text(encoding='utf-8'))
        state['status'] = 'completed'
        state_path.write_text(json.dumps(state), encoding='utf-8')
        next_round = json.loads(run(sys.executable, HERE/'new_job.py', '--root', project))
        require(not next_round['reused'] and next_round['current_job'] != first['current_job'],
                'A completed round must not be silently reused.')
    print('PASS: intake reuse, confirmation gate, boundary review, cue overlap, four-turn render, SRT, freeze/motion, full decode, next-round isolation.')


if __name__ == '__main__':
    main()
