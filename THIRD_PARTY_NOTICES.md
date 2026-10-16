# Acknowledgments & Third-party Notices

## MoneyPrinterTurbo and its original Skill

Thank you to **Harry / harry0703** and the contributors to
[MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo).
DualFrame grew out of hands-on use of the original
[MoneyPrinterTurbo video Skill](https://github.com/harry0703/MoneyPrinterTurbo/blob/v1.3.8/docs/skill/SKILL.md).
Its executable workflow and focus on delivering a finished video inspired this project.
The local production setup originally reused its Python environment and font path.

DualFrame's intake helper and split-screen renderer are maintained separately.
They do not call MoneyPrinterTurbo's service, and this repository does not bundle its
source code, fonts, media, or credentials. This is an independent project, not an official
MoneyPrinterTurbo release. The upstream version consulted was v1.3.8,
commit `fafec0fbf3142ad5ad7212c2e17996bf247c360a`.

For clear attribution, the upstream MIT license is reproduced below:

```text
MIT License

Copyright (c) 2024 Harry

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Runtime tools

- [FFmpeg](https://ffmpeg.org/): decoding, cropping, compositing, subtitles and encoding.
  Its license depends on the build; FFmpeg is not redistributed here.
- [Pillow](https://python-pillow.github.io/) and [NumPy](https://numpy.org/): layout and frame checks.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp): optional source metadata and media acquisition.

Install these tools separately under their own licenses. Source footage and fonts retain
their respective owners' rights; DualFrame's MIT license covers the code and documentation
in this repository, not footage or fonts obtained for a production.
