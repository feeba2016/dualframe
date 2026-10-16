#!/usr/bin/env python3
"""Render a confirmed two-speaker manifest and verify its media output."""
import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

INK, WHITE, MUTED = '#071521', '#F4F3EC', '#9CADBD'
Y = {'top': 160, 'bottom': 1060}
CY = {'top': (805, 891), 'bottom': (1705, 1791)}
COLORS = {'top': '#85BFFF', 'bottom': '#82DDC6'}


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_format',
                                               '-show_streams', '-of', 'json', str(path)]))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def stamp(t, ass=False):
    ms = round(t * 1000)
    if ass:
        return f'{ms//3600000}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000//10:02}'
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'


class Renderer:
    def __init__(self, manifest, output):
        self.manifest = manifest.resolve()
        self.base = self.manifest.parent
        self.cfg = json.loads(self.manifest.read_text(encoding='utf-8'))
        self.output = output.resolve() if output else self.base / 'output'
        self.work = self.output / 'assets'
        self.font = self.resolve(self.cfg.get('font', ''))
        self.check()
        self.family = ImageFont.truetype(str(self.font), 40).getname()[0]

    def resolve(self, value):
        path = Path(value).expanduser()
        return path if path.is_absolute() else self.base / path

    def width(self, text, size):
        return ImageFont.truetype(str(self.font), size).getlength(text)

    def wrap(self, text, size):
        lines = []
        for paragraph in text.splitlines():
            units = paragraph.split() if size == 28 else list(paragraph)
            sep, line = (' ' if size == 28 else ''), ''
            for unit in units:
                if self.width(unit, size) > 1000:
                    raise ValueError(f'Unbreakable subtitle token: {unit}')
                candidate = line + (sep if line else '') + unit
                if self.width(candidate, size) > 1000:
                    lines.append(line)
                    line = unit
                else:
                    line = candidate
            if line:
                lines.append(line)
        if not lines or len(lines) > (2 if size == 36 else 3):
            raise ValueError(f'Split this cue at an actual word boundary: {text}')
        return '\n'.join(lines)

    def check(self):
        brief = self.cfg.get('brief', {})
        if brief.get('status') != 'confirmed' or not brief.get('confirmation') or not brief.get('confirmed_at'):
            raise ValueError('This round requires an actual user topic confirmation before rendering.')
        if not self.font.is_file():
            raise ValueError('Set font to an installed font supporting both Chinese and English.')
        for field, size, width in [('title', 37, 750), ('source_label', 25, 1008)]:
            if not self.cfg.get(field) or self.width(self.cfg[field], size) > width:
                raise ValueError(f'{field} is empty or too wide for the fixed layout.')
        speakers = self.cfg.get('speakers', {})
        if set(speakers) != {'top', 'bottom'}:
            raise ValueError('Exactly top and bottom speakers are required.')
        self.infos = {}
        for key, speaker in speakers.items():
            for field in ('name_en', 'name_zh', 'date', 'file', 'url', 'crop'):
                if not speaker.get(field):
                    raise ValueError(f'{key}.{field} is required.')
            if self.width(speaker['name_en'], 39) > 810 or self.width(speaker['name_zh']+' / '+speaker['date'], 27) > 810:
                raise ValueError(f'Shorten the display name of {key}.')
            info = probe(self.resolve(speaker['file']))
            video = next(s for s in info['streams'] if s['codec_type'] == 'video')
            if not any(s['codec_type'] == 'audio' for s in info['streams']):
                raise ValueError(f'{key} has no original audio.')
            w, h, x, y = speaker['crop']
            if min(w, h) <= 0 or min(x, y) < 0 or x+w > video['width'] or y+h > video['height'] or abs(w/h-1.8) > .03:
                raise ValueError(f'Invalid or distorted crop for {key}.')
            self.infos[key] = info
        phases = self.cfg.get('phases', [])
        if len(phases) < 2:
            raise ValueError('At least one complete turn per speaker is required.')
        seen, totals, last_end, previous = set(), dict(top=0., bottom=0.), {}, None
        for p in phases:
            name, speaker, start, end = p['name'], p['speaker'], p['start'], p['end']
            if not re.fullmatch(r'[a-z0-9-]+', name) or name in seen:
                raise ValueError('Phase names must be unique lowercase ASCII identifiers.')
            seen.add(name)
            if speaker not in speakers or speaker == previous:
                raise ValueError('Phases must alternate between top and bottom.')
            if not p.get('boundary_reviewed') or not p.get('ends_after'):
                raise ValueError(f'{name}: review the full semantic ending against original audio.')
            media_duration = float(self.infos[speaker]['format']['duration'])
            if not 0 <= start < end <= media_duration or start < last_end.get(speaker, 0)-.001:
                raise ValueError(f'{name}: invalid, overlapping, or out-of-order source range.')
            cues = p.get('cues', [])
            if not cues:
                raise ValueError(f'{name}: bilingual cues are required.')
            cue_end = start
            for a, b, zh, en in cues:
                if not start-.001 <= a < b <= end+.001 or a < cue_end-.001:
                    raise ValueError(f'{name}: invalid or overlapping cue times.')
                self.wrap(zh, 36)
                self.wrap(en, 28)
                cue_end = b
            self.wrap(p['hold_zh'], 36)
            self.wrap(p['hold_en'], 28)
            totals[speaker] += end-start
            last_end[speaker], previous = end, speaker
        if min(totals.values()) <= 0:
            raise ValueError('Both speakers must have a speaking excerpt.')
        difference = (max(totals.values())-min(totals.values()))/max(totals.values())
        limit = self.cfg.get('max_duration_difference_ratio', .10)
        if not 0 <= limit <= 1:
            raise ValueError('max_duration_difference_ratio must be between 0 and 1.')
        if difference > limit:
            raise ValueError(f'Unbalanced source durations {totals}; choose complete excerpts of similar length.')
        self.totals = {k: round(v, 3) for k, v in totals.items()}

    def crop(self, speaker):
        w, h, x, y = self.cfg['speakers'][speaker]['crop']
        return f'crop={w}:{h}:{x}:{y},scale=1080:600:flags=lanczos,setsar=1'

    def put(self, draw, xy, text, size, color):
        draw.text(xy, text, fill=color, font=ImageFont.truetype(str(self.font), size))

    def background(self, active, paused, at, file):
        frame = self.work / 'paused.png'
        run(['ffmpeg', '-y', '-v', 'error', '-ss', str(at), '-i',
             str(self.resolve(self.cfg['speakers'][paused]['file'])), '-vf', self.crop(paused),
             '-frames:v', '1', str(frame)])
        image = Image.new('RGB', (1080, 1920), INK)
        d = ImageDraw.Draw(image)
        self.put(d, (36, 18), self.cfg['title'], 37, WHITE)
        self.put(d, (824, 28), '原声对照', 26, MUTED)
        d.line((36, 955, 1044, 955), fill='#344350', width=2)
        for speaker in ('top', 'bottom'):
            s, offset, playing = self.cfg['speakers'][speaker], (0 if speaker == 'top' else 900), speaker == active
            self.put(d, (36, 78+offset), s['name_en'], 39, COLORS[speaker])
            self.put(d, (36, 129+offset), s['name_zh']+' / '+s['date'], 27, MUTED)
            d.rounded_rectangle((872,85+offset,1044,140+offset),radius=14,fill=COLORS[speaker] if playing else '#263644')
            self.put(d,(903,93+offset),'播放中' if playing else '暂停',29,INK if playing else MUTED)
        image.paste(Image.open(frame).convert('RGB'), (0,Y[paused]))
        self.put(d, (36,1881), self.cfg['source_label'],25,MUTED)
        image.save(file)

    def ass(self, phase, paused, held, file):
        text = '[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\n'
        text += 'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
        for language,size in [('zh',36),('en',28)]:
            for state,color in [('Speech','&H00ECF3F4'),('Paused','&H00BDAD9C')]:
                text += f'Style: {state}-{language},{self.family},{size},{color},&H000000FF,&H00211507,&H00211507,0,0,0,0,100,100,0,0,1,1,0,5,35,35,0,1\n'
        text += '\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
        start = phase['start']
        events = [(a-start,b-start,'Speech',phase['speaker'],zh,en) for a,b,zh,en in phase['cues']]
        if held:
            events.append((0,phase['end']-start,'Paused',paused,*held))
        for a,b,state,speaker,zh,en in events:
            for i,(lang,value,size) in enumerate([('zh',zh,36),('en',en,28)]):
                value = self.wrap(value,size).replace('\\','\\\\').replace('{','｛').replace('}','｝').replace('\n','\\N')
                text += f'Dialogue: 0,{stamp(a,True)},{stamp(b,True)},{state}-{lang},,0,0,0,,{{\\an5\\pos(540,{CY[speaker][i]})}}{value}\n'
        file.write_text(text, encoding='utf-8')

    def render(self):
        self.work.mkdir(parents=True, exist_ok=True)
        # A local font directory avoids FFmpeg filter escaping of arbitrary host paths.
        font_copy = self.work / ('subtitle-font'+self.font.suffix)
        font_copy.write_bytes(self.font.read_bytes())
        phases = self.cfg['phases']
        last = {s: next(p['start'] for p in phases if p['speaker']==s) for s in Y}
        held, timeline, subtitles, cursor = dict(top=None,bottom=None), [], [], 0.
        for p in phases:
            name,active = p['name'],p['speaker']
            paused = 'bottom' if active=='top' else 'top'
            duration = p['end']-p['start']
            self.background(active,paused,last[paused],self.work/f'{name}.png')
            self.ass(p,paused,held[paused],self.work/f'{name}.ass')
            graph = f'[1:v]{self.crop(active)},fps=30[v];[0:v][v]overlay=0:{Y[active]}:shortest=1,ass={name}.ass:fontsdir=.[out]'
            print(f'Rendering {name}: {duration:.2f}s',flush=True)
            with (self.work/f'{name}.log').open('w') as log:
                run(['ffmpeg','-y','-hide_banner','-loglevel','warning','-loop','1','-framerate','30','-i',f'{name}.png',
                     '-ss',str(p['start']),'-i',str(self.resolve(self.cfg['speakers'][active]['file'])),
                     '-filter_complex',graph,'-map','[out]','-map','1:a:0','-af','apad',
                     '-t',str(duration),'-r','30','-c:v','libx264','-preset','medium','-crf','16','-threads','4',
                     '-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-ac','2','-b:a','192k','-movflags','+faststart',f'{name}.mp4'],
                    cwd=self.work,stdout=log,stderr=subprocess.STDOUT,timeout=600)
            info = probe(self.work/f'{name}.mp4')
            actual = float(next(s['duration'] for s in info['streams'] if s['codec_type']=='video'))
            offset = self.cfg['speakers'][active].get('source_offset',0)
            timeline.append(dict(phase=name,speaker=active,start=cursor,duration=actual,source_start=p['start']+offset,
                                 source_end=p['end']+offset,ends_after=p['ends_after'],paused_speaker=paused))
            subtitles.extend((cursor+a-p['start'],cursor+min(b-p['start'],actual),zh,en) for a,b,zh,en in p['cues'])
            cursor += actual
            last[active],held[active] = p['end']-1/30,(p['hold_zh'],p['hold_en'])
        (self.work/'concat.txt').write_text(''.join(f"file '{p['name']}.mp4'\n" for p in phases), encoding='utf-8')
        final = self.output/'成片_中英双语.mp4'
        run(['ffmpeg','-y','-v','warning','-f','concat','-safe','0','-i',str(self.work/'concat.txt'),'-c:v','copy',
             '-c:a','aac','-b:a','192k','-ar','48000','-af','aresample=async=1:first_pts=0','-movflags','+faststart',str(final)])
        (self.output/'字幕_中英双语.srt').write_text('\n\n'.join(f'{i}\n{stamp(a)} --> {stamp(b)}\n{zh}\n{en}' for i,(a,b,zh,en) in enumerate(subtitles,1))+'\n', encoding='utf-8')
        save(self.output/'timeline.json',dict(phases=timeline,source_duration_by_speaker=self.totals))
        self.verify(final,timeline,subtitles)
        # Preserve ASS and backgrounds for review; remove redundant encodes/logs/font copies.
        for phase in phases:
            for suffix in ('.mp4', '.log'):
                (self.work / (phase['name'] + suffix)).unlink(missing_ok=True)
        for path in (font_copy, self.work/'paused.png', self.work/'concat.txt'):
            path.unlink(missing_ok=True)
        print(f'VIDEO_FILE={final}\nQA_FILE={self.output / "qa/report.json"}',flush=True)

    def frame(self, final, at):
        raw = subprocess.check_output(['ffmpeg','-v','error','-ss',str(at),'-i',str(final),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'])
        return np.frombuffer(raw,dtype=np.uint8).reshape(1920,1080,3)

    def verify(self, final, timeline, subtitles):
        qa = self.output/'qa'
        qa.mkdir(exist_ok=True)
        info = probe(final)
        save(qa/'media-info.json',info)
        video = next(s for s in info['streams'] if s['codec_type'] == 'video')
        if (video['width'], video['height'], video['avg_frame_rate']) != (1080, 1920, '30/1'):
            raise ValueError('Delivery must be 1080x1920 at 30 fps.')
        previous_end = 0
        for a, b, _, _ in subtitles:
            if round(a*1000) < previous_end or round(b*1000) <= round(a*1000):
                raise ValueError('Delivered SRT has overlapping or empty cues.')
            previous_end = round(b*1000)
        if previous_end > round(float(info['format']['duration'])*1000):
            raise ValueError('Delivered SRT exceeds media duration.')
        checks=[]
        board = Image.new('RGB',(270*len(timeline),480),INK)
        for i,p in enumerate(timeline):
            a = self.frame(final,p['start']+p['duration']*.20)
            b = self.frame(final,p['start']+p['duration']*.65)
            diff = {s:np.abs(a[y:y+600].astype(float)-b[y:y+600].astype(float)) for s,y in Y.items()}
            delta = {s:float(d.mean()) for s,d in diff.items()}
            # H.264 can requantize the same still across GOPs. Ignore small codec noise;
            # require meaningful changed pixels in the active pane, near zero in the other.
            changed = {s:float((d.max(axis=2)>20).mean()) for s,d in diff.items()}
            passed = changed[p['paused_speaker']]<.005 and changed[p['speaker']]>changed[p['paused_speaker']]+.002
            checks.append(dict(phase=p['phase'],pixel_difference=delta,changed_pixel_ratio=changed,
                               pause_check='pass' if passed else 'needs_review'))
            image=Image.fromarray(b)
            board.paste(image.resize((270,480)),(i*270,0))
            if i==len(timeline)-1:
                image.save(qa/'preview.jpg')
        board.save(qa/'contact-sheet.jpg')
        run(['ffmpeg','-v','error','-i',str(final),'-f','null','-'],timeout=600)
        passed=all(c['pause_check']=='pass' for c in checks)
        save(qa/'report.json',dict(status='pass' if passed else 'needs_review',full_decode='pass',canvas='1080x1920@30',subtitle_timing='pass',
                                   source_duration_by_speaker=self.totals,phases=checks,
                                   semantic_boundary_review='Recorded in manifest; requires human/agent source review.'))
        if not passed:
            raise ValueError('Inspect qa/report.json; a motion or freeze check needs review before delivery.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    renderer=Renderer(args.manifest,args.output_dir)
    if args.check_only:
        print(json.dumps(dict(status='valid',source_duration_by_speaker=renderer.totals),ensure_ascii=False))
    else:
        renderer.render()


if __name__=='__main__':
    main()
