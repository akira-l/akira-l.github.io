"""
rebuild_site.py
One-shot script that:
1) Rewrites dist/css/screen.css with beautiful styles
2) Rewrites publications/index.html (card layout, correct links)
3) Rewrites every publications/<slug>/index.html with FULL markdown content + images
4) Fixes index.html links to point to ./publications/<slug>/index.html
All links use relative paths + explicit index.html for file:// compatibility.
"""
import os, re, html as ht
from pathlib import Path

REPO = Path(r'C:\Users\liang\Documents\code\akira-l.github.io')
MD_ROOT = Path(r'C:\Users\liang\Documents\pr_draft\pr_seo_scripts')

# ============================================================
# Slug -> markdown files mapping
# ============================================================
SLUGS = {
    'maal': {
        'title': 'MAAL：为什么机器人知道"物体是什么"，却不知道"该怎么用"？',
        'subtitle': 'ICCV 2023 · Multimodality-Aware Autoencoder-based Affordance Learning for 3D Articulated Objects',
        'tags': ['Affordance', '3D Articulated Objects', 'Autoencoder', 'ICCV 2023'],
        'mds': ['zhihu-为什么机器人知道"物体是什么"，却不知道"该怎么用"？MAAL论文解读.md'],
        'links': [],
        'desc': 'MAAL（ICCV 2023）中文解读：用多模态感知 + Memory Autoencoder 思路做 3D affordance learning。',
    },
    'seeg': {
        'title': 'SEEG：从节奏模仿到语义表达——提升语音驱动手势生成能力',
        'subtitle': 'CVPR 2022 · Semantic Energized Co-Speech Gesture Generation',
        'tags': ['Co-speech Gesture', 'Speech-to-Motion', 'Disentanglement', 'CVPR 2022'],
        'mds': ['zhihu-从节奏模仿到语义表达：提升语音驱动手势生成能力.md'],
        'links': [],
        'desc': 'SEEG（CVPR 2022）中文解读：把 co-speech gesture 分解为节奏手势与语义手势。',
    },
    'elp': {
        'title': 'ELP：高置信度预测是否代表高质量特征？',
        'subtitle': 'CVPR 2022 · A Simple Episodic Linear Probe Improves Visual Recognition in the Wild',
        'tags': ['Generalization', 'Representation', 'Regularization', 'CVPR 2022'],
        'mds': ['zhihu-高置信度预测是否代表高质量特征？Episodic Linear Probe方法解析未命名.md'],
        'links': [],
        'desc': 'ELP（CVPR 2022）中文解读：用周期性重置的弱分类器在线测量特征可分性。',
    },
    'vrr-vg': {
        'title': 'VrR-VG：纯靠猜？视觉关系模型"看都不用看图"？',
        'subtitle': 'ICCV 2019 · Refocusing Visually-Relevant Relationships',
        'tags': ['Scene Graph', 'Bias', 'Debias Learning', 'ICCV 2019'],
        'mds': ['zhihu-纯靠猜？视觉关系模型"看都不用看图"？.md'],
        'links': [],
        'desc': 'VrR-VG（ICCV 2019）中文解读：视觉关系数据里存在大量偏差。',
    },
    'anteval': {
        'title': 'AntEval：为什么多个 AI Agent 聊天总像在客套？',
        'subtitle': 'AntEval: Quantitatively Evaluating Informativeness and Expressiveness of Agent Social Interactions',
        'tags': ['Multi-Agent', 'Evaluation', 'TRPG'],
        'mds': ['zhihu-为什么多个 AI Agent 聊天总像在客套？AntEval 量化 AI 的社交能力.md'],
        'links': [],
        'desc': 'AntEval 中文解读：多 Agent 对话信息量与表现力评估。',
    },
    'icocap': {
        'title': 'IcoCap：噪声真的都是坏的吗？用"正激励噪声"提升视频理解',
        'subtitle': 'IcoCap: Improving Video Captioning by Compounding Images (TMM 2023)',
        'tags': ['Video Captioning', 'Data Compounding', 'pi-noise', 'TMM 2023'],
        'mds': ['zhihu-噪声真的都是坏的吗？IcoCap 用"正激励噪声"提升视频理解能力.md'],
        'links': [],
        'desc': 'IcoCap 中文解读：用正激励噪声视角理解 Image-Video Compounding。',
    },
    'mhem': {
        'title': 'MHEM：为什么深度学习越关注"困难样本"，反而越容易过拟合？',
        'subtitle': 'TNNLS 2022 · Penalizing the Hard Example But Not Too Much',
        'tags': ['Hard Example Mining', 'Overfitting', 'FGVC', 'TNNLS 2022'],
        'mds': ['zhihu-为什么深度学习越关注"困难样本"，反而越容易过拟合？.md'],
        'links': [],
        'desc': 'MHEM（TNNLS 2022）中文解读：困难样本要罚但不能罚太狠。',
    },
    'uni-inter': {
        'title': 'Uni-Inter：面向动作交互的大一统模型',
        'subtitle': 'SIGGRAPH Asia 2025 · Unifying 3D Human Motion Synthesis Across Diverse Interaction Contexts',
        'tags': ['Motion Synthesis', 'Human Interaction', 'Unified Representation', 'SIGGRAPH Asia 2025'],
        'mds': ['xhs-Uni-Inter：面向动作交互的大一统模型.md'],
        'links': [],
        'desc': 'Uni-Inter 中文解读：统一 3D 交互动作生成。',
    },
    'teleboost': {
        'title': 'TeleBoost：视频模型后训练意味着什么？',
        'subtitle': 'arXiv 2026 · A Systematic Alignment Framework for High-Fidelity, Controllable, and Robust Video Generation',
        'tags': ['Video Generation', 'Post-training', 'Alignment', 'arXiv 2026'],
        'mds': ['xhs-视频模型：后训练何意味？不崩给你看不错了.md'],
        'links': [('arXiv', 'https://arxiv.org/abs/2602.07595'), ('PDF', 'https://arxiv.org/pdf/2602.07595')],
        'desc': 'TeleBoost 中文解读：视频生成的系统化后训练与对齐。',
    },
    'teleworld': {
        'title': 'TeleWorld：走向 4D 闭环世界模型的多模态生成',
        'subtitle': 'arXiv 2025 · Towards Dynamic Multimodal Synthesis with a 4D World Model',
        'tags': ['World Model', '4D Representation', 'Long-term Consistency', 'arXiv 2025'],
        'mds': [],
        'links': [('arXiv', 'https://arxiv.org/abs/2601.00051'), ('PDF', 'https://arxiv.org/pdf/2601.00051')],
        'desc': 'TeleWorld 中文解读：4D 闭环世界模型。',
    },
}

# ============================================================
# Helper: markdown -> HTML with image placeholders
# ============================================================
IMG_RE = re.compile(r'!\[[^\]]*\]\(([^\)]+)\)')

def inline_fmt(text):
    text = ht.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    return text

def md_to_html(md_text, slug):
    """Convert markdown to HTML. Returns (html_string, [image_urls])."""
    lines = md_text.splitlines()
    parts = []
    images = []
    in_list = False

    for line in lines:
        s = line.strip()
        if not s:
            if in_list:
                parts.append('</ul>')
                in_list = False
            continue
        # skip annotation placeholder
        if '添加图片注释' in s:
            continue
        if s == '---':
            if in_list:
                parts.append('</ul>')
                in_list = False
            continue
        # image
        m = IMG_RE.search(s)
        if m and s.startswith('!['):
            url = m.group(1)
            if 'fe-static.xhscdn.com' in url:
                continue  # skip xhs emoji
            images.append(url)
            idx = len(images)
            parts.append(f'<figure class="note-figure"><img src="{{IMG:{idx}}}" alt="{slug} figure {idx}" loading="lazy" /></figure>')
            continue
        if s.startswith('### '):
            if in_list:
                parts.append('</ul>')
                in_list = False
            parts.append(f'<h3>{inline_fmt(s[4:])}</h3>')
            continue
        if s.startswith('## '):
            if in_list:
                parts.append('</ul>')
                in_list = False
            parts.append(f'<h2>{inline_fmt(s[3:])}</h2>')
            continue
        if s.startswith('# ') and not s.startswith('## '):
            if in_list:
                parts.append('</ul>')
                in_list = False
            parts.append(f'<h2>{inline_fmt(s[2:])}</h2>')
            continue
        if s.startswith('- '):
            if not in_list:
                parts.append('<ul>')
                in_list = True
            parts.append(f'<li>{inline_fmt(s[2:])}</li>')
            continue
        if in_list:
            parts.append('</ul>')
            in_list = False
        parts.append(f'<p>{inline_fmt(s)}</p>')

    if in_list:
        parts.append('</ul>')
    return '\n          '.join(parts), images


def resolve_images(html_str, images, slug):
    """Replace {IMG:N} with actual local paths."""
    img_dir = REPO / 'img' / 'notes' / slug
    # build mapping: figure index -> local file
    # images from zhihu are fig-01, fig-02... (downloaded earlier)
    for i in range(1, len(images) + 1):
        local = f'../../img/notes/{slug}/fig-{i:02d}.webp'
        actual = img_dir / f'fig-{i:02d}.webp'
        if actual.exists():
            html_str = html_str.replace(f'{{IMG:{i}}}', local)
        else:
            # image download may have failed; remove figure
            html_str = html_str.replace(
                f'<figure class="note-figure"><img src="{{IMG:{i}}}" alt="{slug} figure {i}" loading="lazy" /></figure>',
                ''
            )
    return html_str


# ============================================================
# 1) Rewrite screen.css
# ============================================================
css = r'''/* screen.css — publication pages styling (works WITH bootstrap) */

/* ---- Note page layout ---- */
.note-container {
  max-width: 780px;
  margin: 60px auto 40px;
  padding: 0 20px 40px;
}

.note-breadcrumb {
  font-size: 13px;
  color: #999;
  margin-bottom: 18px;
}
.note-breadcrumb a { color: #666; text-decoration: none; }
.note-breadcrumb a:hover { color: #0f766e; }
.note-breadcrumb span { margin: 0 6px; color: #ccc; }

.note-header { margin-bottom: 20px; }
.note-header .kicker {
  display: inline-block;
  font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.12em;
  color: #0f766e;
  background: rgba(15,118,110,0.08);
  padding: 3px 10px; border-radius: 3px;
  margin-bottom: 10px;
}
.note-header h1 {
  font-size: 26px; font-weight: 700; line-height: 1.25;
  margin: 0 0 8px; color: #222;
}
.note-header .subtitle {
  font-size: 15px; color: #666; line-height: 1.55; margin: 0;
}

.note-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 18px; }
.note-tags .tag {
  font-size: 12px; font-weight: 600;
  padding: 3px 10px; border-radius: 4px;
  border: 1px solid #e0e0e0; color: #666; background: #fff;
}

/* Cover image */
.note-cover-wrap {
  margin-bottom: 22px; border-radius: 6px; overflow: hidden;
  border: 1px solid #e0e0e0; background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.note-cover-wrap img { display: block; width: 100%; height: auto; }

/* Inline figures */
.note-figure {
  margin: 18px 0; border-radius: 6px; overflow: hidden;
  border: 1px solid #e0e0e0; background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.note-figure img { display: block; width: 100%; height: auto; }

/* Article body */
.note-body {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
  padding: 28px 28px 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  line-height: 1.8;
}
.note-body h2 {
  font-size: 19px; font-weight: 700; margin: 30px 0 12px; color: #222;
  padding-bottom: 6px; border-bottom: 1px solid #e8e8e8;
}
.note-body h2:first-child { margin-top: 0; }
.note-body h3 { font-size: 16px; font-weight: 600; margin: 22px 0 8px; color: #333; }
.note-body p { margin: 0 0 14px; color: #333; }
.note-body ul, .note-body ol { margin: 0 0 14px 20px; }
.note-body li { margin-bottom: 4px; color: #333; }
.note-body a { color: #0f766e; text-decoration: none; }
.note-body a:hover { text-decoration: underline; }
.note-body code {
  background: #f4f4f4; padding: 2px 6px; border-radius: 3px;
  font-size: 13px; color: #c7254e;
}

/* TL;DR callout */
.note-callout {
  background: rgba(15,118,110,0.06);
  border-left: 4px solid #0f766e;
  border-radius: 0 6px 6px 0;
  padding: 16px 18px; margin: 0 0 22px;
}
.note-callout strong { display: block; font-size: 14px; color: #0f766e; margin-bottom: 6px; }
.note-callout p { margin: 0; font-size: 14px; line-height: 1.7; color: #333; }

.note-divider { height: 1px; background: #e8e8e8; margin: 28px 0; }

.note-links { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.note-links a {
  display: inline-block; font-size: 12px; font-weight: 600;
  padding: 6px 14px; border-radius: 4px; text-decoration: none;
  border: 1px solid #e0e0e0; color: #333; background: #fff;
  transition: all .15s;
}
.note-links a:hover { border-color: #0f766e; color: #0f766e; }
.note-links a.primary { background: #0f766e; color: #fff; border-color: #0f766e; }
.note-links a.primary:hover { opacity: 0.85; color: #fff; }

/* Footer */
.pub-page-footer {
  margin-top: 28px; padding-top: 14px;
  border-top: 1px solid #e0e0e0;
  font-size: 13px; color: #999;
}
.pub-page-footer a { color: #0f766e; text-decoration: none; }
.pub-page-footer a:hover { text-decoration: underline; }

/* ---- Publications list page ---- */
.pub-container { max-width: 900px; margin: 60px auto 40px; padding: 0 20px 40px; }
.pub-page-header { margin-bottom: 22px; }
.pub-page-header h1 { font-size: 26px; font-weight: 700; margin: 0 0 6px; }
.pub-page-header p { color: #666; margin: 0; font-size: 14px; }

.pub-search-bar { display: flex; gap: 10px; margin-bottom: 22px; }
.pub-search-input {
  flex: 1; padding: 8px 14px;
  border: 1px solid #ddd; border-radius: 4px;
  font-size: 14px; outline: none;
}
.pub-search-input:focus { border-color: #0f766e; box-shadow: 0 0 0 3px rgba(15,118,110,0.1); }
.pub-search-count { font-size: 13px; color: #999; white-space: nowrap; line-height: 38px; }

.pub-year-section { margin-bottom: 24px; }
.pub-year-title {
  font-size: 18px; font-weight: 700; margin: 0 0 12px;
  padding-bottom: 6px; border-bottom: 2px solid #e0e0e0;
}
.pub-year-title .badge { font-weight: 400; font-size: 13px; color: #999; }
.pub-year-title a { color: inherit; text-decoration: none; }

.pub-list { display: flex; flex-direction: column; gap: 10px; }

.paper-card {
  background: #fff; border: 1px solid #e8e8e8; border-radius: 10px;
  padding: 16px 18px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  transition: transform .2s, box-shadow .2s;
}
.paper-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.1);
}
.paper-card h3 { font-size: 15px; font-weight: 600; margin: 0 0 5px; line-height: 1.35; color: #222; }
.paper-card .meta { font-size: 13px; color: #888; margin-bottom: 8px; }
.paper-card .links { display: flex; flex-wrap: wrap; gap: 6px; }
.paper-card .links a {
  display: inline-block; font-size: 12px; font-weight: 600;
  padding: 4px 12px; border-radius: 4px; text-decoration: none;
  border: 1px solid #e0e0e0; color: #333; background: #fff;
  transition: all .15s;
}
.paper-card .links a:hover { border-color: #0f766e; color: #0f766e; }
.paper-card .links a.primary { background: #0f766e; color: #fff; border-color: #0f766e; }
.paper-card .links a.primary:hover { opacity: 0.85; color: #fff; text-decoration: none; }

@media (max-width: 600px) {
  .note-body { padding: 18px 14px 16px; }
  .note-header h1 { font-size: 21px; }
  .pub-container, .note-container { padding: 0 12px 30px; }
}
'''

css_path = REPO / 'dist' / 'css' / 'screen.css'
css_path.write_text(css, encoding='utf-8')
print('Wrote screen.css')

# ============================================================
# 2) Build each note page
# ============================================================
NAV_TPL = '''<nav class="navbar navbar-inverse navbar-fixed-top">
  <div class="container">
    <div class="navbar-header">
      <a class="navbar-brand" href="../../index.html"><b>Yuanzhi Liang</b></a>
    </div>
    <div id="navbar" class="collapse navbar-collapse">
      <ul class="nav navbar-nav">
        <li><a href="../../index.html#about"><b>Biography</b></a></li>
        <li class="active"><a href="../index.html"><b>Publications</b></a></li>
        <li><a href="../../index.html#publication"><b>Highlights</b></a></li>
      </ul>
    </div>
  </div>
</nav>'''

for slug, info in SLUGS.items():
    # Read markdown
    md_combined = ''
    for md_name in info['mds']:
        md_path = MD_ROOT / md_name
        if md_path.exists():
            raw = md_path.read_text(encoding='utf-8')
            # clean
            lines = [l.rstrip() for l in raw.splitlines() if '添加图片注释' not in l]
            cleaned = '\n'.join(lines).strip()
            if md_combined:
                md_combined += '\n\n---\n\n'
            md_combined += cleaned

    if md_combined:
        body_html, images = md_to_html(md_combined, slug)
        body_html = resolve_images(body_html, images, slug)
    else:
        body_html = '<p>解读内容即将补充。</p>'

    tags_html = '\n      '.join([f'<span class="tag">{t}</span>' for t in info['tags']])

    links_html = ''
    for label, url in info.get('links', []):
        cls = 'primary' if label == 'arXiv' else ''
        links_html += f'<a class="{cls}" href="{url}" target="_blank" rel="noopener">{label}</a>\n'

    page = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{ht.escape(info["title"])} | Yuanzhi Liang</title>
  <meta name="description" content="{ht.escape(info['desc'])}" />
  <link rel="canonical" href="https://akira-l.github.io/publications/{slug}/" />
  <link rel="stylesheet" href="../../dist/css/bootstrap.css" />
  <link rel="stylesheet" href="../../dist/css/screen.css" />
</head>
<body>
  {NAV_TPL}
  <div class="note-container">
    <div class="note-breadcrumb">
      <a href="../../index.html">Home</a><span>/</span><a href="../index.html">Publications</a><span>/</span>{slug}
    </div>

    <div class="note-header">
      <div class="kicker">Paper Note</div>
      <h1>{ht.escape(info["title"])}</h1>
      <p class="subtitle">{ht.escape(info["subtitle"])}</p>
    </div>

    <div class="note-tags">
      {tags_html}
    </div>

    <article class="note-body">
      {body_html}

      <div class="note-divider"></div>
      <h2>Links</h2>
      <div class="note-links">
        {links_html}
        <a href="../index.html">Back to Publications</a>
      </div>
    </article>

    <footer class="pub-page-footer">
      <p><a href="../index.html">Back to Publications</a> · <a href="../../index.html">Home</a></p>
    </footer>
  </div>
</body>
</html>
'''
    out = REPO / 'publications' / slug / 'index.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding='utf-8')
    print(f'Wrote {slug}/index.html')


# ============================================================
# 3) Rewrite publications/index.html
# ============================================================
PUB_NAV = '''<nav class="navbar navbar-inverse navbar-fixed-top">
  <div class="container">
    <div class="navbar-header">
      <a class="navbar-brand" href="../index.html"><b>Yuanzhi Liang</b></a>
    </div>
    <div id="navbar" class="collapse navbar-collapse">
      <ul class="nav navbar-nav">
        <li><a href="../index.html#about"><b>Biography</b></a></li>
        <li class="active"><a href="./index.html"><b>Publications</b></a></li>
        <li><a href="../index.html#publication"><b>Highlights</b></a></li>
      </ul>
    </div>
  </div>
</nav>'''

papers = [
    ('2026', 'TeleBoost: A Systematic Alignment Framework for High-Fidelity, Controllable, and Robust Video Generation', 'arXiv (2026) · Yuanzhi Liang et al.', 'teleboost', 'video generation post-training alignment', [('arXiv', 'https://arxiv.org/abs/2602.07595'), ('PDF', 'https://arxiv.org/pdf/2602.07595')]),
    ('2025', 'TeleWorld: Towards Dynamic Multimodal Synthesis with a 4D World Model', 'arXiv (2025) · Yabo Chen, Yuanzhi Liang, et al.', 'teleworld', 'world model 4D video generation', [('arXiv', 'https://arxiv.org/abs/2601.00051')]),
    ('2025', 'Uni-Inter: Unifying 3D Human Motion Synthesis Across Diverse Interaction Contexts', 'SIGGRAPH Asia (2025) · Sheng Liu, Yuanzhi Liang, et al.', 'uni-inter', '3D motion interaction unified', []),
    ('2023', 'MAAL: Multimodality-Aware Autoencoder-based Affordance Learning for 3D Articulated Objects', 'ICCV (2023) · Yuanzhi Liang et al.', 'maal', 'affordance learning 3D autoencoder', []),
    ('2022', 'A Simple Episodic Linear Probe Improves Visual Recognition in the Wild', 'CVPR (2022) · Yuanzhi Liang et al.', 'elp', 'generalization representation probe', []),
    ('2022', 'SEEG: Semantic Energized Co-Speech Gesture Generation', 'CVPR (2022) · Yuanzhi Liang et al.', 'seeg', 'co-speech gesture disentanglement', []),
    ('2022', 'Penalizing the Hard Example But Not Too Much (MHEM)', 'TNNLS (2022) · Yuanzhi Liang et al.', 'mhem', 'hard example mining overfitting', []),
    ('2019', 'VrR-VG: Refocusing Visually-Relevant Relationships', 'ICCV (2019) · Yuanzhi Liang et al.', 'vrr-vg', 'scene graph bias debias', []),
    ('misc', 'AntEval: Quantitatively Evaluating Agent Social Interactions', 'Paper note · Multi-agent evaluation', 'anteval', 'agent evaluation multi-agent', []),
    ('misc', 'IcoCap: Image-Video Compounding for Video Understanding', 'TMM (2023) · Paper note', 'icocap', 'video captioning pi-noise', []),
]

# Group by year
from collections import OrderedDict
years = OrderedDict()
for yr, title, meta, slug, kw, ext_links in papers:
    years.setdefault(yr, []).append((title, meta, slug, kw, ext_links))

cards_html = ''
for yr, items in years.items():
    yr_label = yr if yr != 'misc' else 'Notes'
    cards_html += f'''
    <section class="pub-year-section" id="y{yr}">
      <h2 class="pub-year-title"><a href="#y{yr}">{yr_label}</a> <span class="badge">({len(items)})</span></h2>
      <div class="pub-list">
'''
    for title, meta, slug, kw, ext_links in items:
        ext_html = ''
        for label, url in ext_links:
            ext_html += f'<a href="{url}" target="_blank" rel="noopener">{label}</a>\n'
        cards_html += f'''
        <article class="paper-card" data-title="{ht.escape(title)}" data-keywords="{kw}">
          <h3>{ht.escape(title)}</h3>
          <div class="meta">{ht.escape(meta)}</div>
          <div class="links">
            <a class="primary" href="./{slug}/index.html">中文解读</a>
            {ext_html}
          </div>
        </article>
'''
    cards_html += '      </div>\n    </section>\n'

pub_page = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Publications | Yuanzhi Liang</title>
  <meta name="description" content="Yuanzhi Liang 的论文与中文解读（面向 AI 检索与 SEO 友好）：按年份整理。" />
  <link rel="canonical" href="https://akira-l.github.io/publications/" />
  <link rel="stylesheet" href="../dist/css/bootstrap.css" />
  <link rel="stylesheet" href="../dist/css/screen.css" />
</head>
<body>
  {PUB_NAV}
  <div class="pub-container">
    <div class="pub-page-header">
      <h1>Publications</h1>
      <p>论文列表 + 中文解读。点击"中文解读"进入每篇论文的详细解读页。</p>
    </div>

    <div class="pub-search-bar">
      <input id="pubSearch" class="pub-search-input" type="search" placeholder="搜索论文标题 / 关键词" />
      <span id="pubCount" class="pub-search-count">显示全部</span>
    </div>

    {cards_html}

    <footer class="pub-page-footer">
      <p><a href="../index.html">返回主页</a></p>
    </footer>
  </div>

  <script>
  (function(){{
    var input=document.getElementById("pubSearch");
    var count=document.getElementById("pubCount");
    var cards=[].slice.call(document.querySelectorAll(".paper-card"));
    var secs=[].slice.call(document.querySelectorAll(".pub-year-section"));
    function norm(s){{return(s||"").toLowerCase().replace(/\\s+/g," ").trim()}}
    function filter(){{
      var q=norm(input.value),shown=0;
      cards.forEach(function(c){{
        var hay=norm((c.getAttribute("data-title")||"")+" "+(c.getAttribute("data-keywords")||""));
        var ok=!q||hay.indexOf(q)!==-1;
        c.style.display=ok?"":"none";
        if(ok)shown++;
      }});
      count.textContent=q?"匹配 "+shown+" 篇":"显示全部";
      secs.forEach(function(s){{
        var vis=s.querySelectorAll(".paper-card");
        var n=0;for(var i=0;i<vis.length;i++)if(vis[i].style.display!=="none")n++;
        s.style.display=n?"":"none";
      }});
    }}
    if(input)input.addEventListener("input",filter);
  }})();
  </script>
</body>
</html>
'''

pub_path = REPO / 'publications' / 'index.html'
pub_path.write_text(pub_page, encoding='utf-8')
print('Wrote publications/index.html')


# ============================================================
# 4) Fix main index.html links
# ============================================================
idx_path = REPO / 'index.html'
idx_text = idx_path.read_text(encoding='utf-8')

# Fix: ./publications/slug/ -> ./publications/slug/index.html
idx_text = re.sub(
    r'href="\.\/publications\/([^"]+)\/"',
    r'href="./publications/\1/index.html"',
    idx_text
)
# Fix: ./publications/" -> ./publications/index.html"
idx_text = idx_text.replace('href="./publications/"', 'href="./publications/index.html"')

idx_path.write_text(idx_text, encoding='utf-8')
print('Fixed index.html links')

print('\n=== ALL DONE ===')
