"""One-off local conversion of stage-one styles to the requested Radix semantics."""
from pathlib import Path
import json
import re

root = Path(__file__).resolve().parents[1] / "frontend"
package = json.loads((root / "package.json").read_text())
package["dependencies"]["@radix-ui/colors"] = "^3.0.0"
(root / "package.json").write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
css = (root / "src/style.css").read_text(encoding="utf-8")
css = css.replace("@import url('');", '\n'.join('@import "@radix-ui/colors/' + name + '-dark.css";' for name in ['slate', 'gold', 'red', 'green']))
colors = {
    '#101113':'slate-1', '#191b1f':'slate-2', '#21242a':'slate-3', '#30333a':'slate-6',
    '#e8e9ec':'slate-12', '#979da9':'slate-11', '#c5aa7a':'gold-11', '#302b23':'gold-3',
    '#ff9e9e':'red-11', '#a0c3aa':'green-11', '#2b2e35':'slate-4', '#555b66':'slate-8',
    '#191815':'gold-1', '#131518':'slate-1', '#b9bec7':'slate-11', '#bac0ca':'slate-11',
    '#c6cbd3':'slate-12', '#15171a':'slate-2', '#746447':'gold-7', '#ffffff08':'slate-6',
    '#41443e':'green-6', '#222924':'green-3', '#bacdbb':'green-11', '#24272d':'slate-6',
    '#141619':'slate-2', '#626874':'slate-11', '#17191d':'slate-2', '#202329':'slate-3',
    '#88744f':'gold-8', '#28261f':'gold-3', '#111316':'slate-1', '#32363e':'slate-6',
    '#535b68':'slate-11', '#8d949f':'slate-11', '#101214':'slate-1', '#1a1d21':'slate-3',
    '#262a30':'slate-6', '#89919e':'slate-11', '#e4e6e9':'slate-12', '#30343b':'slate-5',
    '#090a0c':'slate-1', '#23262d':'slate-6', '#4c5059':'slate-7', '#545965':'slate-11',
    '#c9ced7':'slate-12', '#656d7a':'slate-11', '#b3bac4':'slate-11', '#363b44':'slate-6',
    '#4c535f':'slate-11', '#747d8b':'slate-11', '#8d96a3':'slate-11', '#191b20':'slate-2',
    '#17191c':'slate-2', '#22262b':'slate-3', '#343943':'slate-7', '#2b2821':'gold-3',
    '#c1c8d2':'slate-12', '#8f98a4':'slate-11', '#726344':'gold-7', '#24231f':'gold-3',
    '#796847':'gold-7', '#69707d':'slate-11', '#1a1d22':'slate-3', '#656d79':'slate-11',
}
css = re.sub(r'box-shadow:[^;}]+[;]?', '', css)
css = re.sub(r'transition:[^;}]+[;]?', '', css)
for color, token in colors.items():
    css = css.replace(color, f'var(--{token})')
css = re.sub(r'font-size:(\d+)px', lambda m: 'font-size:' + str(12 if int(m[1]) <= 13 else 14 if int(m[1]) <= 19 else 20 if int(m[1]) <= 26 else 28) + 'px', css)
css = css.replace('font:11px/', 'font:12px/')
css = re.sub(r'(border(?:-[a-z]+)?:)([12])px', r'\g<1>0.5px', css)
css = css.replace('border-radius:50%', 'border-radius:50%')
css += '\n.primary{background:var(--gold-9);color:var(--gold-12)}.primary:hover{background:var(--gold-10)}.save-state{min-height:19px}.editor{min-width:0}\n'
assert not re.search(r'#[0-9a-fA-F]{3,8}\b', css), 'Unmapped color'
(root / 'src/style.css').write_text(css, encoding='utf-8')
html = (root / 'index.html').read_text(encoding='utf-8').replace('<html lang="zh-CN">','<html lang="zh-CN" class="dark">')
(root / 'index.html').write_text(html.replace(' · ', ' '), encoding='utf-8')
for path in (root / 'src').rglob('*.tsx'):
    text = path.read_text(encoding='utf-8').replace(' · ', ' / ')
    text = text.replace('从一集故事开始，让每个镜头都有据可循。','')
    text = text.replace('准备好镜头内容后，下一阶段将在这里比较与采用画面。','暂无画面候选')
    text = text.replace('先完成右侧镜头描述与资产引用。','编辑镜头内容')
    text = text.replace('先在故事与导演页完成剧本、镜头和资产引用。','')
    path.write_text(text, encoding='utf-8')
