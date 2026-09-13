"""只读原始结果，生成论文 Markdown / LaTeX、数据索引和完整代码附件。"""
from pathlib import Path
import csv
import hashlib
import json
import re
import zipfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
DATES = ['2025-03-20', '2025-06-21', '2025-09-23', '2025-12-21']
Q = {n: json.loads((ROOT / f'results/problem{n}.json').read_text(encoding='utf-8')) for n in range(1, 5)}
TABLES = {}
INDEX = []


def csvrows(name):
    with (ROOT / 'results' / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def num(x, digits=2):
    x = float(x)
    if abs(x) < 0.5 * 10 ** (-digits):
        x = 0
    return f'{x:.{digits}f}'


def table(key, caption, headers, rows, source):
    TABLES[key] = (caption, headers, [[str(x) for x in row] for row in rows])
    INDEX.append({'table_key': key, 'caption': caption, 'source': source})


table('roadmap', '四问的决策条件与模型对应关系', ['问题', '新增条件', '模型', '评价依据'], [
    ['一', '供需曲线给定、日末闭合', '确定性线性规划', '日费用与可行性'],
    ['二', '实际负载和光伏未知', '残差场景日前规划', '实际费用与紧急购电'],
    ['三', '四次光伏预报及调整收费', '追索式计划与滚动调整', '费用、应急量及消融'],
    ['四', '未来实际电价未知', '因果价格预测与滚动优化', '信息对照及波动试验'],
], 'question/C题.pdf；src/problem1.py；src/dispatch_core.py')

table('symbols', '主要符号与单位', ['符号', '含义', '单位'], [
    ['$i,t,k$', '日期、时段及场景下标', '—'],
    [r'$N,\Delta,K$', '日时段数、时长及场景数：144、1/6、10', '—、h、—'],
    ['$P^L,P^G$', '负载功率、光伏功率', 'kW'],
    ['$L,G$', '时段负载电量、光伏电量', 'kWh'],
    [r'$g^0,g^{\tau},g^{\mathrm{fin}}$', '原计划、更新计划、最终计划购电量', 'kWh'],
    ['$c,d$', '问题二至四的微网侧充电量、放电量', 'kWh'],
    [r'$\bar c,\bar d$', '问题一的储能侧充电量、放电量', 'kWh'],
    ['$S$', '储能设备内部存储电量', 'kWh'],
    ['$e,z$', '紧急购电量、未使用余电量', 'kWh'],
    ['$r,x$', '相对原计划的减购量、增购量', 'kWh'],
    [r'$\pi,\widehat\pi$', '实际交易电价、预测电价', '元/kWh'],
    [r'$\eta,E_{\max}$', '单向效率0.9、时段能量上限833.3333', '—、kWh'],
    [r'$v,\epsilon$', '终端储电价值0.42、吞吐引导系数0.001', '元/kWh'],
], '论文构建/02_符号系统.md；src/config.py；src/problem1.py')

q1 = Q[1]
purchase = list(q1['specified_purchase_kwh'].items())
table('q1_purchase', '问题一指定时段购电量及全天费用', ['时间段', '购电量/kWh', '时间段', '购电量/kWh', '时间段', '购电量/kWh'], [
    sum(([k, num(v)] for k, v in purchase[:3]), []),
    sum(([k, num(v)] for k, v in purchase[3:]), []),
    ['全天购电量', num(q1['daily_purchase_kwh']), '全天购电费/元', num(q1['daily_purchase_cost_yuan']), '计量单位', 'kWh、元'],
], 'results/problem1.json:specified_purchase_kwh,daily_purchase_kwh,daily_purchase_cost_yuan')
wins = list(q1['storage_windows_kwh'].items())
rows = []
for j in range(0, 6, 2):
    row = []
    for name, val in wins[j:j + 2]:
        row += [name, num(val['charge_kwh']), num(val['discharge_kwh'])]
    rows.append(row)
rows.append(['0:00储电量', num(q1['soc_0000_kwh']), '—', '24:00储电量', num(q1['soc_2400_kwh']), '—'])
table('q1_storage', '问题一储能侧充放电及首末储电量（kWh）', ['时间段', '充电量', '放电量', '时间段', '充电量', '放电量'], rows, 'results/problem1.json:storage_windows_kwh,soc_0000_kwh,soc_2400_kwh')
sens = csvrows('problem1_sensitivity.csv')
first = list(sens[0])[0]
capkeys = list(sens[0])[1:]
sr = []
for b in [.4, .8, 1., 1.2]:
    row = min(sens, key=lambda r: abs(float(r[first].split('_')[-1]) - b))
    sr.append([num(float(row[first].split('_')[-1]))] + [num(row[min(capkeys, key=lambda x: abs(float(x.split('_')[-1]) - a))]) for a in [.5, .75, 1.]])
table('q1_sensitivity', '容量窗口与储能侧功率系数的费用节选（元）', ['功率系数', '容量系数0.50', '容量系数0.75', '容量系数1.00'], sr, 'results/problem1_sensitivity.csv（121组中节选）')

Q2 = Q[2]['annual']
Q3 = Q[3]['full_scheme']
C4 = {r['scenario']: r for r in csvrows('problem4_comparison.csv')}


def annual_rows(a):
    return [[label, num(a[key], 0 if key in ['days', 'emergency_days'] else 2)] for label, key in [
        ['统计天数/d', 'days'], ['计划购电费/元', 'plan_cost_yuan'], ['调整费/元', 'adjustment_cost_yuan'],
        ['紧急购电费/元', 'emergency_cost_yuan'], ['总费用/元', 'total_cost_yuan'],
        ['0时计划购电量/kWh', 'plan_kwh'], ['最终计划购电量/kWh', 'final_purchase_kwh'],
        ['紧急购电量/kWh', 'emergency_kwh'], ['发生紧急购电天数/d', 'emergency_days'], ['余电量/kWh', 'waste_kwh']]]


table('q2_annual', '问题二统计期实际结果', ['指标', '数值'], annual_rows(Q2), 'results/problem2.json:annual')
table('q3_annual', '问题二与问题三主方案的统计期比较', ['指标', '问题二', '问题三'], [
    [a[0], a[1], b[1]] for a, b in zip(annual_rows(Q2), annual_rows(Q3))
], 'results/problem2.json:annual；results/problem3.json:full_scheme')

fr = csvrows('problem3_forecast_accuracy.csv')
table('forecast', '各发布时间光伏预测MAE（kW；按该次发布剩余时段评价）', ['发布时间', '附件3', '历史预测', '组合预测', '组合后比例修正'], [
    [f'{h}:00'] + [num(r['mae_kw']) for r in fr if int(r['release_hour']) == h] for h in [0, 6, 12, 18]
], 'results/problem3_forecast_accuracy.csv')
abl = csvrows('problem3_ablation.csv')
table('ablation', '更新时点和日前追索的方案比较', ['方案', '总费用/万元', '紧急购电量/kWh', '日前追索'], [
    [r['scheme'].replace('（计划不含追索）', '（无追索）').replace('完美信息下界', '完美信息基准'),
     num(float(r['total_cost_yuan']) / 1e4), num(r['emergency_kwh']),
     '是' if r['scheme'] == '完整追索式计划' else ('—' if r['scheme'] in ['问题2方案', '完美信息下界'] else '否')]
    for r in abl
], 'results/problem3_ablation.csv；src/problem3.py:SCHEMES')

pr = csvrows('problem4_price_forecast_accuracy.csv')
table('price_accuracy', '因果价格预测误差（元/kWh）', ['发布时间', 'MAE', 'RMSE'], [
    [f"{int(float(r['release_hour']))}:00", num(r['mae_yuan_per_kwh'], 5), num(r['rmse_yuan_per_kwh'], 5)] for r in pr
], 'results/problem4_price_forecast_accuracy.csv')
a4, b4 = C4['causal Q4-2'], C4['causal Q4-3']
table('q4_annual', '波动电价下两种因果方案的统计期结果', ['指标', '问题四之二', '问题四之三'], [
    [a[0], a[1], b[1]] for a, b in zip(annual_rows(a4), annual_rows(b4))
], 'results/problem4_comparison.csv:causal Q4-2,causal Q4-3')
table('price_comparison', '统一按实际电价结算的价格信息对照（万元）', ['信息条件', '日前方案', '滚动方案'], [
    [label, num(float(C4[f'{key} Q4-2']['total_cost_yuan']) / 1e4), num(float(C4[f'{key} Q4-3']['total_cost_yuan']) / 1e4)]
    for label, key in [('固定电价决策', 'fixed-price'), ('因果价格预测', 'causal'), ('预知未来电价', 'price-oracle')]]
    + [['完美信息基准', num(float(C4['perfect-information lower bound']['total_cost_yuan']) / 1e4), '同一基准']],
    'results/problem4_comparison.csv')


def payload(q):
    if q in ['42', '43']:
        return Q[4]['typical_days'][f'q4_{q[-1]}']
    return Q[int(q)]['typical_days']


def typical(q):
    data = payload(q)
    tokens = []
    for date in DATES:
        d = data[date]
        m = d['metrics']
        rows = []
        def val(t):
            g0, gf = d['plan_purchase_kwh'][t], d['final_purchase_kwh'][t]
            return num(g0) if q == '2' else f'{num(g0)} / {num(gf)}'
        for hs in [[10, 12, 14], [16, 18, 20]]:
            rows.append(sum(([f'{h:02d}:00–{h:02d}:10', val(h * 6)] for h in hs), []))
        whole = num(m['plan_kwh']) if q == '2' else f"{num(m['plan_kwh'])} / {num(m['final_purchase_kwh'])}"
        rows.append(['全天购电量', whole, '全天总费用/元', num(m['total_cost_yuan']), '单位', 'kWh、元'])
        pk = f'q{q}_{date}_purchase'
        table(pk, f'问题{q}：{date}指定时段购电量与全天费用' + ('（原/终）' if q == '3' else ''),
              ['时间段', '购电量', '时间段', '购电量', '时间段', '购电量'], rows,
              f'results/problem{q}.json:typical_days/{date}/plan_purchase_kwh,final_purchase_kwh,metrics')
        rows = []
        for a in [0, 8, 16]:
            row = []
            for b in [a, a + 4]:
                row += [f'{b:02d}:00–{b+4:02d}:00', num(sum(d['charge_kwh'][b*6:(b+4)*6])), num(sum(d['discharge_kwh'][b*6:(b+4)*6]))]
            rows.append(row)
        rows.append(['0:00储电量', num(d['soc_kwh'][0]), '—', '24:00储电量', num(d['soc_kwh'][-1]), '—'])
        sk = f'q{q}_{date}_storage'
        table(sk, f'问题{q}：{date}储能充放电与首末储电量（kWh）', ['时间段', '充电量', '放电量', '时间段', '充电量', '放电量'], rows,
              f'results/problem{q}.json:typical_days/{date}/charge_kwh,discharge_kwh,soc_kwh')
        tokens += [f'@@TABLE:{pk}@@', f'@@TABLE:{sk}@@']
    return '\n\n'.join(tokens)


def emergency_groups(arr):
    groups = []
    i = 0
    def tm(j):
        return f'{j//6:02d}:{j%6*10:02d}'
    while i < 144:
        if arr[i] <= 1e-8:
            i += 1
            continue
        j = i + 1
        while j < 144 and arr[j] > 1e-8:
            j += 1
        groups.append((f'{tm(i)}–{tm(j)}', sum(arr[i:j])))
        i = j
    return groups


def emergency(q):
    tokens = []
    for mode in (['42', '43'] if q == '4' else [q]):
        d = payload(mode)
        grouped = {date: emergency_groups(d[date]['emergency_kwh']) for date in DATES}
        rows = []
        for j in range(max(1, max(map(len, grouped.values())))):
            row = []
            for date in DATES:
                if j < len(grouped[date]):
                    seg, val = grouped[date][j]
                    row += [seg, num(val)]
                else:
                    row += ['无' if j == 0 else '—', '0.00' if j == 0 else '—']
            rows.append(row)
        rows.append(sum((['合计', num(sum(d[date]['emergency_kwh']))] for date in DATES), []))
        key = f'emergency_{mode}'
        name = {'42': '问题四之二', '43': '问题四之三', '2': '问题二', '3': '问题三'}[mode]
        table(key, f'{name}四个典型日紧急购电（kWh）', sum(([x[5:], '购电量'] for x in DATES), []), rows,
              f'results/problem{4 if len(mode)==2 else mode}.json:typical_days；合并相邻非零10分钟时段')
        tokens.append(f'@@TABLE:{key}@@')
    return '\n\n'.join(tokens)


rows = []
for date in DATES:
    for mode, name in [('42', '日前'), ('43', '滚动')]:
        m = payload(mode)[date]['metrics']
        rows.append([date[5:], name, num(m['plan_kwh']), num(m['final_purchase_kwh']), num(m['total_cost_yuan']), num(m['emergency_kwh'])])
table('q4_typical', '波动电价下典型日购电与费用汇总', ['日期', '方案', '原计划/kWh', '最终计划/kWh', '总费用/元', '紧急购电/kWh'], rows, 'results/problem4.json:typical_days')
rows = []
for h in [10, 12, 14, 16, 18, 20]:
    for mode, name in [('42', '日前'), ('43', '滚动')]:
        rows.append([f'{h:02d}:00–{h:02d}:10', name] + [num(payload(mode)[d]['final_purchase_kwh'][h*6]) for d in DATES])
table('q4_slots', '波动电价下指定10分钟时段最终购电量（kWh）', ['时间段', '方案'] + [x[5:] for x in DATES], rows, 'results/problem4.json:typical_days/*/final_purchase_kwh')
rows = []
for h in range(0, 24, 4):
    for mode, name in [('42', '日前'), ('43', '滚动')]:
        rows.append([f'{h:02d}:00–{h+4:02d}:00', name] + [num(sum(payload(mode)[d]['charge_kwh'][h*6:(h+4)*6])) + ' / ' + num(sum(payload(mode)[d]['discharge_kwh'][h*6:(h+4)*6])) for d in DATES])
for mode, name in [('42', '日前'), ('43', '滚动')]:
    rows.append(['日初 / 日末', name] + [num(payload(mode)[d]['soc_kwh'][0]) + ' / ' + num(payload(mode)[d]['soc_kwh'][-1]) for d in DATES])
table('q4_storage', '波动电价下典型日储能量（充电/放电；末两行为首末储电量，kWh）', ['时间段', '方案'] + [x[5:] for x in DATES], rows, 'results/problem4.json:typical_days/*/charge_kwh,discharge_kwh,soc_kwh')

vr = csvrows('problem4_price_volatility_sensitivity.csv')
table('volatility', '保持日均价格的波动试验', [r'$\lambda$', '日内CV均值', '日前费用/万元', '滚动费用/万元', '节约/万元', '节约率'], [
    [num(r['volatility_factor']), num(r['mean_daily_price_cv'], 3), num(float(r['q4_2_total_cost_yuan'])/1e4), num(float(r['q4_3_total_cost_yuan'])/1e4),
     num((float(r['q4_2_total_cost_yuan'])-float(r['q4_3_total_cost_yuan']))/1e4),
     num(100*(1-float(r['q4_3_total_cost_yuan'])/float(r['q4_2_total_cost_yuan'])))+'%'] for r in vr
], 'results/problem4_price_volatility_sensitivity.csv')
table('validation', '实际运行与数值结果核验', ['检验项目', '结果', '结论范围'], [
    ['问题一原记录最大平衡残差', r'$2.27\times10^{-13}$ kWh', '给定确定性实例'],
    ['问题二至四原记录最大平衡残差', r'$2.27\times10^{-13}$ kWh', '主方案实际运行'],
    ['独立重算电量平衡最大残差', r'$4.55\times10^{-13}$ kWh', '全部23份缓存'],
    ['独立重算SOC递推最大残差', r'$9.09\times10^{-13}$ kWh', '全部23份缓存'],
    ['储电量物理范围', '1200—10800 kWh', '主方案及已计算对照'],
    ['问题二至四时段充放电上限', '833.3333 kWh', '微网侧'],
    ['同时充放电时段数', '0', '实际运行轨迹'],
    ['跨日储电量', '连续衔接', '含1月预热段'],
    ['工作簿购电量与缓存最大差', r'$4.55\times10^{-13}$ kWh', '四份统计期结果'],
    ['波动试验每日均价最大误差', r'$1.23\times10^{-15}$ 元/kWh以内', '五种波动情形'],
], 'results/problem*.json；build/c_spec_cache/*.npz；result*.xlsx；只读核验')

# 生成标准 Markdown，并记录实际图表编号。
source = (OUT / '正文源稿.md').read_text(encoding='utf-8')
source = re.sub(r'@@TYPICAL:(\d+)@@', lambda m: typical(m[1]), source)
source = re.sub(r'@@EMERGENCY:(\d+)@@', lambda m: emergency(m[1]), source)
tn = 0
fn = 1
figures = [{'number': 1, 'source': '论文成稿/构建论文.py（TikZ流程图）', 'caption': '四问的模型递进与共同评价流程', 'type': 'diagram'}]
def expand_table(m):
    global tn
    tn += 1
    key = m[1]
    cap, heads, rows = TABLES[key]
    for entry in INDEX:
        if entry['table_key'] == key:
            entry['number'] = tn
    grid = ['| ' + ' | '.join(heads) + ' |', '| ' + ' | '.join(['---'] * len(heads)) + ' |']
    grid += ['| ' + ' | '.join(r) + ' |' for r in rows]
    return f'表{tn} {cap}\n\n' + '\n'.join(grid)


def expand_figure(m):
    global fn
    fn += 1
    name, caption, height = m[1], m[2], m[3]
    p = ROOT / 'new_figures_main' / (name + '.png')
    assert p.exists(), p
    figures.append({'number': fn, 'source': p.relative_to(ROOT).as_posix(), 'caption': caption, 'height_cm': float(height)})
    return f'![图{fn} {caption}](../new_figures_main/{name}.png)'


md = re.sub(r'@@TABLE:(.*?)@@', expand_table, source)
md = re.sub(r'@@FIG:([^|]+)\|([^|]+)\|([^@]+)@@', expand_figure, md)
md = md.replace('@@FLOW@@', '''```mermaid
flowchart LR
    Q1[问题一：确定性线性规划] --> Q2[问题二：残差场景日前规划]
    Q2 --> Q3[问题三：预报组合与滚动调整]
    Q3 --> Q4[问题四：因果价格预测]
    Q2 --> E[实际轨迹与费用结算]
    Q3 --> E
    Q4 --> E
```

图1 四问的模型递进与共同评价流程。历史信息生成预测与场景，实际运行后再计算费用。''')
assert '@@' not in md
(OUT / '微网电力调控策略_论文.md').write_text(md, encoding='utf-8')
(OUT / '图表数据引用索引.json').write_text(json.dumps({'tables': sorted(INDEX, key=lambda x: x['number']), 'figures': figures}, ensure_ascii=False, indent=2), encoding='utf-8')


def escape(text):
    return ''.join({'\\': '\\textbackslash{}', '&': '\\&', '%': '\\%', '$': '\\$', '#': '\\#', '_': '\\_', '{': '\\{', '}': '\\}', '~': '\\textasciitilde{}', '^': '\\textasciicircum{}'}.get(c, c) for c in text)


def inline(text):
    # 保留数学表达式与超链接，普通文本做 TeX 转义。
    chunks = re.split(r'(\$[^$]+\$|\[[^\]]+\]\(https?://[^)]+\)|\*\*[^*]+\*\*)', text)
    result = []
    for s in chunks:
        if s.startswith('$') and s.endswith('$'):
            result.append(s)
        elif s.startswith('**'):
            result.append('\\textbf{' + escape(s[2:-2]) + '}')
        elif re.match(r'\[[^\]]+\]\(https?://', s):
            link = re.fullmatch(r'\[([^\]]+)\]\(([^)]+)\)', s)
            result.append('\\href{' + link[2] + '}{' + escape(link[1]) + '}')
        else:
            result.append(escape(s))
    return ''.join(result)


header = r'''\documentclass[UTF8,a4paper,zihao=-4,fontset=windows]{ctexart}
\usepackage[margin=2.3cm,top=2.2cm,bottom=2.2cm]{geometry}
\usepackage{amsmath,amssymb,graphicx,booktabs,array,adjustbox,caption,float,needspace}
\usepackage[unicode,hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning}
\setmainfont{Times New Roman}
\setlength{\parindent}{2em}
\linespread{1.16}
\setlength{\parskip}{0pt}
\setlength{\abovedisplayskip}{7pt}
\setlength{\belowdisplayskip}{7pt}
\setlength{\textfloatsep}{9pt}
\setlength{\intextsep}{9pt}
\captionsetup{font=small,labelsep=space,skip=4pt}
\ctexset{section={format=\Large\heiti,beforeskip=12pt,afterskip=6pt},subsection={format=\large\heiti,beforeskip=9pt,afterskip=5pt}}
\pagestyle{fancy}\fancyhf{}\fancyfoot[C]{\thepage}\renewcommand{\headrulewidth}{0pt}
\setlength{\headheight}{14pt}
\setcounter{secnumdepth}{0}
\emergencystretch=2em
\begin{document}
'''
tex = [header]
lines = md.splitlines()
i = 0
figidx = 1
while i < len(lines):
    line = lines[i]
    if not line.strip():
        i += 1
        continue
    if line.startswith('# '):
        tex.append(r'\thispagestyle{empty}\begin{center}{\zihao{2}\heiti ' + inline(line[2:]) + r'}\end{center}')
    elif line == '## 摘要':
        tex.append(r'\begin{center}\large\bfseries 摘\quad 要\end{center}')
    elif line.startswith('## '):
        if line.startswith('## 1 '):
            tex.append(r'\clearpage\setcounter{page}{1}')
        if line.startswith('## 参考文献'):
            tex.append(r'\clearpage')
        tex.append(r'\section{' + inline(line[3:]) + '}')
    elif line.startswith('### '):
        tex.append(r'\subsection{' + inline(line[4:]) + '}')
    elif line == '```mermaid':
        i += 1
        while lines[i] != '```':
            i += 1
        tex.append(r'''\begin{figure}[H]\centering
\begin{tikzpicture}[box/.style={draw,rounded corners=2pt,text width=3.35cm,minimum height=1.0cm,align=center,font=\small},>=Stealth]
\node[box] (a) at (0,0) {问题一\\确定性线性规划};
\node[box] (b) at (4,0) {问题二\\残差场景日前规划};
\node[box] (c) at (8,0) {问题三\\预报组合与滚动调整};
\node[box] (d) at (12,0) {问题四\\因果价格预测};
\draw[->] (a)--(b);\draw[->] (b)--(c);\draw[->] (c)--(d);
\node[draw,rounded corners=2pt,align=center,text width=11.6cm,font=\small] (e) at (8,-1.55) {历史信息生成预测与场景\quad{}→\quad{}因果执行\quad{}→\quad{}按实际电价结算};
\draw[->] (b.south)--(4,-.9)--(e.north -| b.south);
\draw[->] (c.south)--(e.north);
\draw[->] (d.south)--(12,-.9)--(e.north -| d.south);
\end{tikzpicture}
\caption{四问的模型递进与共同评价流程。历史信息生成预测与场景，实际运行后再计算费用。}
\end{figure}''')
    elif line.startswith('图1 四问'):
        pass
    elif line == '$$':
        eq = []
        i += 1
        while lines[i] != '$$':
            eq.append(lines[i]); i += 1
        tex.append('\\begin{equation}\n' + '\n'.join(eq) + '\n\\end{equation}')
    elif re.match(r'^表\d+ ', line):
        cap = re.sub(r'^表\d+ ', '', line)
        i += 1
        while not lines[i].strip():
            i += 1
        grid = []
        while i < len(lines) and lines[i].startswith('|'):
            cells = [x.strip() for x in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-+:?', x) for x in cells):
                grid.append(cells)
            i += 1
        i -= 1
        ncols = len(grid[0])
        # 单个表格不拆页；在位置不足时整体移到下一页。
        alignment = 'l' + 'c' * (ncols-1)
        tex.append(r'\begin{table}[H]\centering\caption{' + inline(cap) + '}')
        tex.append(r'\fontsize{9.5}{12}\selectfont\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.12}')
        tex.append(r'\begin{adjustbox}{max width=\linewidth}\begin{tabular}{' + alignment + r'}\toprule')
        tex.append(' & '.join(inline(c) for c in grid[0]) + r'\\\midrule')
        for row in grid[1:]:
            tex.append(' & '.join(inline(c) for c in row) + r'\\')
        tex.append(r'\bottomrule\end{tabular}\end{adjustbox}\end{table}')
    elif line.startswith('!['):
        f = figures[figidx]; figidx += 1
        p = ROOT / f['source']
        if p.with_suffix('.pdf').exists():
            p = p.with_suffix('.pdf')
        tex.append(r'\begin{figure}[H]\centering')
        tex.append(r'\includegraphics[width=\linewidth,height=' + str(f['height_cm']) + r'cm,keepaspectratio]{../' + p.relative_to(ROOT).as_posix() + '}')
        tex.append(r'\caption{' + inline(f['caption']) + r'}\end{figure}')
    elif re.match(r'^\[\d+\]', line):
        tex.append(r'{\small\noindent\hangindent=2em ' + inline(line) + r'\par}\vspace{4pt}')
    else:
        tex.append(inline(line) + '\n' + r'\par')
    i += 1
tex.append(r'\end{document}')
(OUT / '微网电力调控策略_论文.tex').write_text('\n'.join(tex), encoding='utf-8')

# 提供原封不动的完整代码，避免将旧结果写回仓库。
codefiles = [ROOT/'run_all.py', ROOT/'plot_style.py', ROOT/'requirements-final.txt'] + sorted((ROOT/'src').glob('*.py'))
appendix = ['# 附录 B 完整源代码', '', '以下文件从原仓库逐字读取。本文写作没有修改或运行这些模型文件。依赖与输入数据保存在随附压缩包中；如需重算，请在独立解压目录运行，避免覆盖原有结果。', '']
for p in codefiles:
    appendix += ['## ' + p.relative_to(ROOT).as_posix(), '', '```' + ('python' if p.suffix=='.py' else 'text'), p.read_text(encoding='utf-8-sig').rstrip(), '```', '']
(OUT/'附录B_完整源代码.md').write_text('\n'.join(appendix), encoding='utf-8')
zipfiles = codefiles + sorted((ROOT/'data').rglob('*.xlsx')) + sorted(ROOT.glob('result*.xlsx')) + [ROOT/'question/C题.pdf']
zipfiles += sorted((ROOT/'results').glob('*.json')) + sorted((ROOT/'results').glob('*.csv'))
zipfiles += [ROOT/'README.md', ROOT/'START_HERE.md']
specfile = next(ROOT.glob('2026 CUMCM C 题*建模说明.txt'))
zipfiles += [specfile, ROOT/'SOURCE_HASHES.md', ROOT/'FINAL_DELIVERY_AUDIT.md']
with zipfile.ZipFile(OUT/'原始程序与结果.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for p in dict.fromkeys(zipfiles):
        z.write(p, p.relative_to(ROOT).as_posix())
    z.writestr('c建模说明与结果.txt', specfile.read_bytes())
    z.writestr('复现说明.txt', '这是原始程序、输入附件和既有结果的逐文件复制。模型版本 c-spec-v1-2026-09-12。请在独立目录解压。安装 requirements-final.txt 所列依赖后，运行入口为 run_all.py。运行会重写解压目录中的结果，因此不要在唯一原件上重算。本次论文写作未重新执行优化器；文中数值取既有正式结果。压缩包另加 c建模说明与结果.txt，为现有完整名称建模说明文件的逐字节别名副本，供原清单脚本旧路径读取；没有修改原仓库或模型代码。原独立制图脚本可能含旧路径；它不属于 run_all.py 模型计算入口。正文新增文档不改变模型计量侧及任何原始数组。')

base = json.loads((OUT/'原文件校验基线.json').read_text(encoding='utf-8'))
changed = [f for f, digest in base.items() if not (ROOT/f).exists() or hashlib.sha256((ROOT/f).read_bytes()).hexdigest() != digest]
assert not changed, changed
print(json.dumps({'tables': tn, 'figures': fn, 'chinese_characters': len(re.findall('[\u4e00-\u9fff]', md)), 'source_files_unchanged': len(base), 'code_files': len(codefiles)}, ensure_ascii=False))
