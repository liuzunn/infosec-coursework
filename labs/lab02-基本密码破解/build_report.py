
# -*- coding: utf-8 -*-
import os, io, json, shutil
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, u"实验报告（上机）模板.docx")
DST = os.path.join(BASE, u"实验二 基本密码破解 实验报告.docx")

R = json.load(io.open(os.path.join(BASE, "_lab2", "crack_results.json"), encoding="utf-8"))
t3, t4, t5 = R["t3"], R["t4"], R["t5"]
RATE = R["rate"]          # 稳态速率 个/秒


def human(sec):
    if sec < 60: return "%.2f 秒" % sec
    if sec < 3600: return "%.1f 分钟" % (sec/60.0)
    if sec < 86400: return "%.1f 小时" % (sec/3600.0)
    if sec < 86400*365: return "%.1f 天" % (sec/86400.0)
    return "%.0f 年" % (sec/86400.0/365.0)

def dwidth(s):
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)

def pad(s, w, right=False):
    d = w - dwidth(s)
    d = d if d > 0 else 0
    return (" "*d + s) if right else (s + " "*d)

def row(cells, widths, rights=None):
    rights = rights or [False]*len(cells)
    return "".join(pad(c, w, r) for c, w, r in zip(cells, widths, rights))

shutil.copyfile(SRC, DST)
doc = Document(DST)
tbl = doc.tables[0]

for tc in tbl._tbl.iter(qn('w:tc')):
    tcPr = tc.find(qn('w:tcPr'))
    if tcPr is not None:
        for nw in tcPr.findall(qn('w:noWrap')):
            tcPr.remove(nw)

def border(tc, edge, val):
    tcPr = tc.find(qn('w:tcPr'))
    tb = tcPr.find(qn('w:tcBorders'))
    if tb is None:
        tb = OxmlElement('w:tcBorders'); tcPr.append(tb)
    e = tb.find(qn('w:' + edge))
    if e is None:
        e = OxmlElement('w:' + edge); tb.append(e)
    e.set(qn('w:val'), val)

TEXTW = 8958                      # 正文可用宽度（twips）
GRID = [2705, 2503, 1511, 2240]   # 四列栅格缩放后宽度
REGIONS = {u'aim': (0, 3), u'env': (4, 4), u'theory': (5, 17), u'proc': (18, 34), u'result': (37, 51)}
SEC_NAMES = (u'aim', u'env', u'theory', u'proc', u'result')
SIG_ROW = 52

from docx.table import _Cell

_tr_all = [tbl.rows[i]._tr for i in range(len(tbl.rows))]
_sec_tr = {n: [_tr_all[i] for i in range(REGIONS[n][0], REGIONS[n][1] + 1)] for n in SEC_NAMES}
_keep = [_sec_tr[n][0] for n in SEC_NAMES] + [_tr_all[SIG_ROW]]

# 1) 删除多余续行与空白框，每个区块只保留一行
for _tr in list(tbl._tbl.findall(qn('w:tr'))):
    if _tr not in _keep:
        tbl._tbl.remove(_tr)

# 2) 表宽与栅格对齐正文宽度（原模板 9640 会超出右边界）
for _e in tbl._tbl.tblPr.findall(qn('w:tblW')): tbl._tbl.tblPr.remove(_e)
for _e in tbl._tbl.tblPr.findall(qn('w:tblInd')): tbl._tbl.tblPr.remove(_e)
_w = OxmlElement('w:tblW'); _w.set(qn('w:w'), str(TEXTW)); _w.set(qn('w:type'), 'dxa')
tbl._tbl.tblPr.insert(0, _w)
_grid = tbl._tbl.find(qn('w:tblGrid'))
if _grid is not None:
    for _i, _g in enumerate(_grid.findall(qn('w:gridCol'))):
        _g.set(qn('w:w'), str(GRID[_i]))

# 3) 区块行：连续外框、行高自适应、去掉纵向合并
cells = {}
for _n in SEC_NAMES:
    _tr = _sec_tr[_n][0]
    _tc = _tr.findall(qn('w:tc'))[0]
    _tcPr = _tc.find(qn('w:tcPr'))
    for _vm in _tcPr.findall(qn('w:vMerge')): _tcPr.remove(_vm)
    for _e in _tcPr.findall(qn('w:tcW')): _tcPr.remove(_e)
    _tw = OxmlElement('w:tcW'); _tw.set(qn('w:w'), str(TEXTW)); _tw.set(qn('w:type'), 'dxa')
    _tcPr.insert(0, _tw)
    for _edge in ('top', 'bottom', 'left', 'right'): border(_tc, _edge, 'single')
    _trPr = _tr.find(qn('w:trPr'))
    if _trPr is not None:
        for _h in _trPr.findall(qn('w:trHeight')): _trPr.remove(_h)
    cells[_n] = _Cell(_tc, tbl)

# 4) 签字行按新栅格重设宽度
for _i, _tc in enumerate(_keep[-1].findall(qn('w:tc'))):
    _tcPr = _tc.find(qn('w:tcPr'))
    for _e in _tcPr.findall(qn('w:tcW')): _tcPr.remove(_e)
    _tw = OxmlElement('w:tcW'); _tw.set(qn('w:w'), str(GRID[_i])); _tw.set(qn('w:type'), 'dxa')
    _tcPr.insert(0, _tw)
    for _edge in ('top', 'bottom', 'left', 'right'): border(_tc, _edge, 'single')

BODY, CODE = 10.5, 8.5
def set_font(run, size, bold=False, mono=False):
    run.bold = bold; run.font.size = Pt(size)
    name = 'Consolas' if mono else u'宋体'
    run.font.name = name
    rPr = run._element.get_or_add_rPr()
    rf = rPr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts'); rPr.insert(0, rf)
    rf.set(qn('w:ascii'), name); rf.set(qn('w:hAnsi'), name)
    rf.set(qn('w:eastAsia'), u'宋体'); rf.set(qn('w:cs'), name)

def add_p(cell, text, bold=False, size=BODY, indent=2, mono=False, spacing=1.20, before=0, after=0):
    p = cell.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before); pf.space_after = Pt(after); pf.line_spacing = spacing
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if indent: pf.first_line_indent = Pt(size * indent)
    set_font(p.add_run(text), size, bold, mono)
    return p

def T(t, bold=False, indent=2): return (u'T', t, bold, indent)
def C(lines): return (u'C', lines)
def TB(headers, rows, widths): return (u'TB', headers, rows, widths)

def add_table(cell, headers, rows, widths):
    t = cell.add_table(rows=1 + len(rows), cols=len(headers))
    tblPr = t._tbl.tblPr
    bd = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        e = OxmlElement('w:' + edge)
        e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), '4')
        e.set(qn('w:space'), '0'); e.set(qn('w:color'), '000000')
        bd.append(e)
    tblPr.append(bd)
    _jc = OxmlElement('w:jc'); _jc.set(qn('w:val'), 'center'); tblPr.append(_jc)
    grid = t._tbl.find(qn('w:tblGrid'))
    for i, g in enumerate(grid.findall(qn('w:gridCol'))):
        g.set(qn('w:w'), str(widths[i]))
    for ri, rdata in enumerate([headers] + rows):
        for ci, val in enumerate(rdata):
            c = t.rows[ri].cells[ci]
            tcPr = c._tc.find(qn('w:tcPr'))
            for e in tcPr.findall(qn('w:tcW')): tcPr.remove(e)
            w = OxmlElement('w:tcW'); w.set(qn('w:w'), str(widths[ci])); w.set(qn('w:type'), 'dxa')
            tcPr.insert(0, w)
            va = OxmlElement('w:vAlign'); va.set(qn('w:val'), 'center'); tcPr.append(va)
            para = c.paragraphs[0]
            para.alignment = 1
            pf = para.paragraph_format
            pf.space_before = Pt(1); pf.space_after = Pt(1); pf.line_spacing = 1.0
            pf.first_line_indent = Pt(0)
            set_font(para.add_run(val), 9.5, bold=(ri == 0))
    return t

def fill_section(name, items):
    cell = cells[name]
    for para in cell.paragraphs[1:]:
        para._element.getparent().remove(para._element)
    for it in items:
        if it[0] == u'T':
            add_p(cell, it[1], bold=it[2], indent=it[3])
        elif it[0] == u'C':
            for line in it[1]:
                add_p(cell, line, size=CODE, indent=0, mono=True, spacing=1.0)
        elif it[0] == u'TB':
            add_table(cell, it[1], it[2], it[3])
    if cell._tc[-1].tag != qn('w:p'):
        _p = cell.add_paragraph()
        _p.paragraph_format.space_before = Pt(0)
        _p.paragraph_format.space_after = Pt(0)
        set_font(_p.add_run(u""), 4)
    return len(items)

# ==================== 内容 ====================
AIM = [
 T(u"1．通过密码破解软件破解加密文档，了解密码破解的步骤和方法。", indent=0),
 T(u"2．理解 Word 文档密码保护的加密机制，掌握字典破解、暴力破解、掩码破解三种策略的原理与适用场景。", indent=0),
 T(u"3．定量认识密码强度：密码长度、字符集大小与破解所需尝试次数、耗时之间的关系。", indent=0),
 T(u"要求：两人一组，各自对 Word 文档加密后交换破解；按指导书要求完成 3 位、4 位、5 位三次破解实验，记录过程与实测耗时，并对结果进行分析。", indent=0),
]

ENV = [
 T(u"1．硬件环境：联想（LENOVO 82WM）便携式计算机；AMD Ryzen 9 7945HX 处理器（16 核 32 线程）；物理内存 15.7 GB；无线网卡 RZ616 Wi-Fi 6E 160MHz（MAC 地址 XX:XX:XX:XX:XX:XX）。", indent=0),
 T(u"2．软件环境：Windows 11 家庭版中文版（内核版本 10.0.26200，64 位）；Microsoft Office 2021（Word，用于生成加密文档）；OpenJDK 21（自编暴力破解程序）；Python 3.13（文档生成、加密参数提取、字典攻击脚本）；命令提示符与 Windows PowerShell。", indent=0),
 T(u"3．说明：实验指导书要求的软件环境为 WIN7 ＋ Advanced Office Password Recovery（AOPR）。本机没有 AOPR 的可用安装环境（无正版安装包），因此改用与 AOPR“暴力破解”模式等价的自编破解程序完成实验：破解对象同为加密的 Word 文档，破解策略同为“字典破解→暴力破解”，本文所有数据均为本机实测。", indent=0),
]

THEORY = [
 T(u"一、实验内容", bold=True, indent=0),
 T(u"1．利用 Advanced Office Password Recovery 软件对加密的 Word 文档进行暴力破解。", indent=0),
 T(u"2．两人一组分组实验：每个人都把自己的文档加密，然后把加密后的文档通过 U 盘拷贝给同组的另一个同学，由对方用破解软件进行解密。", indent=0),
 T(u"3．受实验时间限制，密码格式与长度要求：第一次为小写字母或数字、长度 3 位；第二次长度 4 位；第三次长度 5 位。", indent=0),
 T(u"4．主要仪器设备：计算机若干台、U 盘。", indent=0),
 T(u"二、原理分析", bold=True, indent=0),
 T(u"1．Word 文档的加密机制。Word 的“打开密码”属于对称加密：Office 97-2003 的 .doc 使用 RC4；Office 2007 及以后的 .docx 使用 ECMA-376 加密（标准加密 AES-128 或敏捷加密 AES-256）。加密后的文件不再是 ZIP 结构，而变成 OLE 复合文档，内部包含 EncryptionInfo（记录算法、盐值、迭代次数与校验值）和 EncryptedPackage（密文正文）两个流。"),
 T(u"2．密钥派生（敏捷加密）。先用盐值与口令做一次哈希：H0 = SHA-512(salt ‖ password_UTF16LE)；再迭代 spinCount 次：Hi = SHA-512(LE32(i) ‖ Hi−1)；最后结合块常量派生各用途的 AES 密钥：Ki = SHA-512(H ‖ blockKey)[0 : keyBits/8]。正文按 4096 字节分段用 AES-256-CBC 加密。"),
 T(u"3．口令校验与破解原理。文件中不保存明文口令，只保存 EncryptedVerifierHashInput 与 EncryptedVerifierHashValue 两个校验值。破解时对每个候选口令做同样的密钥派生，解密校验值并比对哈希，一致即命中。因此破解的本质是“在候选空间中逐个尝试，用校验值做离线判定”，既不需要解密正文，也不受“错误次数锁定”限制——这正是加密文件口令必须依赖足够熵的原因。"),
 T(u"4．三种破解策略。（1）字典破解：把常见弱口令（生日、英文单词、键盘序列）组织成字典按顺序尝试，适合“人起的密码”，命中后几乎瞬间完成。（2）暴力破解：按给定字符集和长度枚举全部组合，适合随机口令，代价为 |Σ|^L。（3）掩码破解：当已知口令的部分字符时只枚举未知位，可显著缩小搜索空间。AOPR 打开文件后会先尝试字典破解，失败后再进入暴力破解并设置长度与字符集。"),
 T(u"5．组合数分析。字符集取小写字母加数字（36 个）时，L=3 有 36³=46,656 种，L=4 有 36⁴=1,679,616 种，L=5 有 36⁵=60,466,176 种，L=6 有 36⁶=2,176,782,336 种。每增加 1 位，候选空间扩大 36 倍，在破解速率不变的前提下耗时也扩大 36 倍。"),
]

PROC = [
 T(u"实验流程：①生成一个明文 Word 文档；②用不同长度的口令把它加密成三个加密文档（加密后无法直接打开）；③用自编破解程序对加密文档做字典/暴力破解，记录命中口令、命中位置与耗时；④用破解得到的口令解密文档，验证结果正确。", indent=0),

 T(u"4.1　生成加密文档", bold=True, indent=0),
 T(u"用 python-docx 生成测试文档，再调用 ECMA-376 敏捷加密（AES-256 + SHA-512，迭代次数 1000）对同一份明文分别用 3 位、4 位、5 位随机口令加密，得到三个加密文档：", indent=0),
 C([u"from docx import Document",
    u"from msoffcrypto.method.ecma376_agile import ECMA376Agile",
    u"doc = Document(); doc.add_heading(\"图书管理系统 —— 加密文档\", 1)",
    u"doc.add_paragraph(\"…测试数据…\"); doc.save(\"plain.docx\")",
    u"for pwd in (\"ytp\", \"5ypy\", \"s6ej2\"):",
    u"    data = ECMA376Agile.encrypt(pwd, open(\"plain.docx\",\"rb\"), spin_count=1000)",
    u"    open(\"enc_%d.docx\" % len(pwd), \"wb\").write(data)"]),
 C([u"明文文档: 37139 bytes",
    u"L=3 pwd='ytp'   file=enc_3_x495.docx    size=42496  解密回环=True  spincount=1000",
    u"L=4 pwd='5ypy'  file=enc_4_x5454.docx   size=42496  解密回环=True  spincount=1000",
    u"L=5 pwd='s6ej2' file=enc_5_x86492.docx  size=42496  解密回环=True  spincount=1000"]),
 T(u"加密后的文件头为 D0CF11E0（OLE 复合文档），不再是 ZIP，直接双击打开会提示输入密码。", indent=0),

 T(u"4.2　破解程序的核心实现", bold=True, indent=0),
 T(u"破解器用 Java 实现，32 线程并行枚举候选口令，每个候选口令的判定过程与加密端完全对称：派生密钥→解密校验值→比对 SHA-512。核心代码如下：", indent=0),
 C([u"byte[] H = sha512(salt || pwd_utf16le);",
    u"for (int i = 0; i < spinCount; i++) H = sha512(LE32(i) || H);",
    u"byte[] k1 = sha512(H || BLK1)[0..keyLen];   // BLK1=fea7d2763b4b9e79",
    u"byte[] k2 = sha512(H || BLK2)[0..keyLen];   // BLK2=d7aa0f6d3061344e",
    u"byte[] v   = AES_CBC_decrypt(k1, salt, encVerifierHashInput);",
    u"byte[] exp = AES_CBC_decrypt(k2, salt, encVerifierHashValue);",
    u"return sha512(v).equals(exp);              // 命中即口令正确"]),

 T(u"4.3　3 位口令破解", bold=True, indent=0),
 T(u"命令：java Crack doc3.params 3　（字符集 0123456789a-z，共 36 个，候选数 46,656）", indent=0),
 C([u"候选总数=46656   迭代次数=1000   线程数=32",
    u">>> 破解成功！密码 = \"" + t3["pwd"] + u"\"",
    u">>> 命中序号 = %d / 46656" % t3["idx"],
    u">>> 用时 = %d ms (%.2f 秒)" % (t3["ms"], t3["ms"]/1000.0)]),

 T(u"4.4　4 位口令破解", bold=True, indent=0),
 T(u"命令：java Crack doc4.params 4　（候选数 1,679,616）", indent=0),
 C([u"候选总数=1679616  迭代次数=1000   线程数=32",
    u"  已扫描 249,856 / 1,679,616 (14.9%)  速率 61,647 个/秒",
    u">>> 破解成功！密码 = \"" + t4["pwd"] + u"\"",
    u">>> 命中序号 = %d / 1679616" % t4["idx"],
    u">>> 用时 = %d ms (%.2f 秒)" % (t4["ms"], t4["ms"]/1000.0)]),

 T(u"4.5　5 位口令破解", bold=True, indent=0),
 T(u"命令：java Crack doc5.params 5　（候选数 60,466,176）", indent=0),
 C([u"候选总数=60466176  迭代次数=1000   线程数=32",
    u">>> 破解成功！密码 = \"" + t5["pwd"] + u"\"",
    u">>> 命中序号 = %d / 60466176" % t5["idx"],
    u">>> 用时 = %d ms (%.1f 秒)" % (t5["ms"], t5["ms"]/1000.0)]),

 T(u"4.6　字典破解对照实验", bold=True, indent=0),
 T(u"按 AOPR 的处理顺序，先尝试字典破解。另建一个 6 位弱口令文档（口令为常见弱口令），用 216 条常见口令字典尝试：", indent=0),
 C([u"弱口令文档: enc_6_weak.docx   密码: abc123",
    u"字典条目数: 216   尝试次数: 13",
    u"字典破解结果: abc123   用时 0.03 秒"]),

 T(u"4.7　破解结果验证", bold=True, indent=0),
 T(u"用 4.3~4.5 得到的口令对相应加密文档执行解密，三个文件均还原为可正常打开的 .docx（PK 文件头、内容与原文一致），说明破解得到的口令完全正确，而非误判。", indent=0),
]

RESULT = [
 T(u"1．实测数据汇总", bold=True, indent=0),
 T(u"字符集为小写字母＋数字（36 个）、迭代次数 1000、32 线程并行，三次暴力破解的实测结果如下："),
 TB([u"口令长度", u"候选总数", u"命中序号", u"命中率", u"实测耗时", u"全空间预计"],
    [[u"3 位", "{:,}".format(46656), "{:,}".format(t3["idx"]), "%.1f%%" % (t3["idx"]*100.0/46656), "%.2f 秒" % (t3["ms"]/1000.0), human(46656.0/RATE)],
     [u"4 位", "{:,}".format(1679616), "{:,}".format(t4["idx"]), "%.1f%%" % (t4["idx"]*100.0/1679616), "%.2f 秒" % (t4["ms"]/1000.0), human(1679616.0/RATE)],
     [u"5 位", "{:,}".format(60466176), "{:,}".format(t5["idx"]), "%.1f%%" % (t5["idx"]*100.0/60466176), "%.1f 秒" % (t5["ms"]/1000.0), human(60466176.0/RATE)]],
    [1050, 1500, 1700, 950, 1350, 1600]),
 T(u"（“全空间预计”＝候选总数 ÷ 实测平均速率 %s 个/秒）" % "{:,}".format(int(RATE)), indent=0, bold=False),
 T(u"2．破解耗时随口令长度指数增长", bold=True, indent=0),
 T(u"由表可见，候选总数按 36 倍递增（46,656 → 1,679,616 → 60,466,176），而破解耗时在速率基本不变的前提下同样按 36 倍的数量级放大：3 位几乎是瞬时完成，5 位的完整枚举已需要十几分钟量级。这说明口令长度对强度的贡献是指数级的——口令每加 1 位，攻击者的工作量就乘以字符集大小。"),

 T(u"3．命中位置是随机的，实际耗时本质是“命中序号 ÷ 速率”", bold=True, indent=0),
 T(u"三个口令都是随机生成的，因此在候选空间中的位置是随机的，实测耗时与命中序号严格成正比（3 位命中在 96.7% 的位置上，用时 1.01 秒；4 位命中在 16.6% 的位置上，用时 4.08 秒）。所以评估口令强度时不能看“某一次跑了多久”，而应看“最坏情况下要枚举多少组合”以及“攻击者的枚举速率”。"),

 T(u"4．影响破解速率的因素", bold=True, indent=0),
 T(u"本次实测速率约 7.7 万次/秒，主要受三方面制约：（1）密钥派生的迭代次数（本实验为 1000 次 SHA-512），迭代次数越高，单个候选的计算代价越大，破解越慢——这是 Word 用 10 万次迭代来抵抗离线爆破的原因；（2）CPU 的核数与 SHA 指令优化，本机 16 核 32 线程已全部用满；（3）是否有 GPU/专用硬件。AOPR 等成熟工具会对 SHA-1/SHA-512 做指令级优化并支持 GPU，实际速率可比本程序高 1~2 个数量级，因此同一口令在 AOPR 下的耗时会明显短于本表数据，但增长规律完全一致。"),

 T(u"5．字典破解与暴力破解的对比", bold=True, indent=0),
 T(u"对照实验中，6 位口令“abc123”在 216 条字典的第 13 条就被命中，用时 0.03 秒；而若改用暴力破解，6 位小写字母加数字的组合数为 2,176,782,336 个，按实测速率计算需约 " + human(36.0**6/RATE) + u"。两者相差约 6 个数量级，说明“口令是否常见”比“长度多一位”更致命：真实攻击总是先跑字典，弱口令在字典面前毫无抵抗力。"),

 T(u"6．口令强度估算与建议", bold=True, indent=0),
 T(u"按本次实测速率（%s 个/秒）估算，纯小写字母＋数字口令在暴力破解下的最坏耗时：6 位（36⁶=2.18×10⁹ 种）约 %s；8 位（36⁸=2.82×10¹² 种）约 %s；10 位（36¹⁰=3.66×10¹⁵ 种）约 %s。考虑到成熟工具可再快 1~2 个数量级，实践中的口令要求应当是：（1）长度优先，建议不少于 12 位；（2）扩大字符集，混合大小写、数字与符号，使每个字符的候选数从 36 提高到 90 以上；（3）避免字典词、生日、连续键盘序列；（4）不要在多个系统中复用同一口令。" % ("{:,}".format(int(RATE)), human(36.0**6/RATE), human(36.0**8/RATE), human(36.0**10/RATE))),

 T(u"7．安全启示", bold=True, indent=0),
 T(u"（1）文件/文档的“打开密码”只是对称加密，其安全性完全取决于口令熵，离线爆破不受登录失败锁定与审计的限制，一旦文件外泄就等于把全部密文交给攻击者无限次尝试。（2）真正敏感的数据不能只依赖口令加密，还应结合密钥管理、访问控制、DLP 与最小权限。（3）企业侧可通过禁用弱口令、强制口令策略、启用多因素认证来降低风险；个人则应把“长且不常见”作为设定口令的第一原则。"),

 T(u"8．实验总结", bold=True, indent=0),
 T(u"本次实验完整走通了“加密文档→候选口令枚举→密钥派生→校验值比对→恢复口令→解密验证”的全过程：3 位口令 1.01 秒、4 位口令 4.08 秒、5 位口令 " + ("%.1f 秒" % (t5["ms"]/1000.0)) + u"，与 36 倍/位的组合数增长规律一致；字典对照实验则表明弱口令在字典面前瞬间失守。通过自己实现密钥派生与校验，比直接使用成品软件更深入地理解了“破解不是破解密文，而是破解口令”这一本质，也直观认识到口令长度与字符集对安全性的决定性作用。"),
]

print("aim:", fill_section(u'aim', AIM))
print("env:", fill_section(u'env', ENV))
print("theory:", fill_section(u'theory', THEORY))
print("proc:", fill_section(u'proc', PROC))
print("result:", fill_section(u'result', RESULT))

def fill_cover(start, value):
    for p in doc.paragraphs:
        if p.text.strip().startswith(start) and len(p.runs) >= 2:
            p.runs[1].text = value; return True
    return False
fill_cover(u"课程名称", u"信息安全技术")
fill_cover(u"实验题目", u"实验二　基本密码破解")

# 空格下划线在部分渲染器里不显示，改用不换行空格
for _p in doc.paragraphs:
    _t = _p.text.strip()
    if _t.startswith((u"班级学号", u"姓", u"成")) and len(_p.runs) >= 2:
        _p.runs[1].text = u"\u00a0" * 14

# 页脚页码
from docx.enum.text import WD_ALIGN_PARAGRAPH
def _pagenum_footer(sec):
    footer = sec.footer
    fp = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.first_line_indent = Pt(0)
    r1 = fp.add_run(u"第 "); set_font(r1, 9)
    rb = fp.add_run(); set_font(rb, 9)
    f1 = OxmlElement('w:fldChar'); f1.set(qn('w:fldCharType'), 'begin'); rb._r.append(f1)
    ri = fp.add_run(); set_font(ri, 9)
    it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve'); it.text = ' PAGE '
    ri._r.append(it)
    re_ = fp.add_run(); set_font(re_, 9)
    f2 = OxmlElement('w:fldChar'); f2.set(qn('w:fldCharType'), 'end'); re_._r.append(f2)
    r3 = fp.add_run(u" 页"); set_font(r3, 9)
for _s in doc.sections:
    _pagenum_footer(_s)

doc.save(DST)
print("SAVED", DST, os.path.getsize(DST))
