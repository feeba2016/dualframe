#!/usr/bin/env python3
"""Create an isolated intake; never invent or confirm a topic."""
import argparse
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def save(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--font', type=Path, help='Path to a Chinese/English font; may be filled in later.')
    args = parser.parse_args()
    jobs = args.root.resolve() / '视频任务'
    jobs.mkdir(parents=True, exist_ok=True)
    state_file = jobs / '状态.json'
    if state_file.exists():
        state = json.loads(state_file.read_text(encoding='utf-8'))
        if state.get('status') not in ('idle', 'completed'):
            existing = Path(state['current_job'])
            if not existing.is_dir():
                raise SystemExit('Current job directory is missing; inspect state before creating another task.')
            print(json.dumps({'reused': True, **state}, ensure_ascii=False))
            return
    now = datetime.now().astimezone()
    job = jobs / f'{now:%Y%m%d-%H%M%S}-{uuid4().hex[:6]}'
    (job / 'source').mkdir(parents=True)
    save(job / 'brief.json', {'status': 'awaiting_topic', 'created_at': now.isoformat(),
                              'question': '这次想比较哪两个人，或围绕什么主题？可以给人物、关键词或视频链接，也可以让我推荐选题。',
                              'user_request': '', 'confirmation': ''})
    save(job / 'manifest.json', {'title': '', 'brief': {'status': 'draft', 'confirmation': '', 'confirmed_at': ''},
                                  'font': str(args.font.expanduser().resolve()) if args.font else '',
                                  'source_label': '', 'max_duration_difference_ratio': .10,
                                  'speakers': {}, 'phases': []})
    state = {'status': 'awaiting_topic', 'current_job': str(job), 'updated_at': now.isoformat()}
    save(state_file, state)
    print(json.dumps({'reused': False, **state}, ensure_ascii=False))


if __name__ == '__main__':
    main()
