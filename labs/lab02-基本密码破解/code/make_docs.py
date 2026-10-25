
# -*- coding: utf-8 -*-
import os, io, json, base64, re, secrets, hashlib, time
import olefile
from docx import Document
from msoffcrypto.method.ecma376_agile import ECMA376Agile
import msoffcrypto

BASE = r"C:\Users\LZ\Desktop\信息安全实验\_lab2"
DOCS = os.path.join(BASE, "docs")
os.makedirs(DOCS, exist_ok=True)

CHARSET = "0123456789abcdefghijklmnopqrstuvwxyz"
SPIN = 1000

# 1) 明文 Word 文档（真实的实验用文档）
plain = os.path.join(BASE, "图书管理系统-实验用文档.docx")
d = Document()
d.add_heading(u"图书管理系统 —— 信息安全实验二 加密文档", level=1)
d.add_paragraph(u"本文档由实验者在本地生成，用于“基本密码破解”实验：先加密码保护，再由同组同学使用破解工具恢复密码。")
for i in range(1, 8):
    d.add_paragraph(u"第 %d 段：图书信息测试数据。书号 B%04d，书名《信息安全原理与实践》第 %d 版，作者 XYP，价格 %d.00 元，出版社：机械工业出版社。Mixed ASCII content line %d." % (i, 1000+i, i, 30+i*5, i*13))
d.add_paragraph(u"机密等级：内部资料，未经授权不得复制、传播。")
d.save(plain)
print("明文文档:", os.path.getsize(plain), "bytes")

def make(pwd, tag):
    out = os.path.join(DOCS, "enc_%d_%s.docx" % (len(pwd), tag))
    with open(plain, "rb") as f:
        buf = ECMA376Agile.encrypt(pwd, f, spin_count=SPIN)
    with open(out, "wb") as f:
        f.write(buf)
    return out

def dump_params(path):
    ole = olefile.OleFileIO(path)
    ei = ole.openstream("EncryptionInfo").read()
    xml = ei[8:].decode("utf-8", "ignore")
    def attr(name):
        m = re.search(r'%s="([^"]*)"' % name, xml)
        return m.group(1) if m else None
    return {
        "spinCount": int(attr("spinCount")),
        "keyBits": int(attr("keyBits")),
        "hashAlgorithm": attr("hashAlgorithm"),
        "saltValue": attr("saltValue"),
        "encryptedVerifierHashInput": attr("encryptedVerifierHashInput"),
        "encryptedVerifierHashValue": attr("encryptedVerifierHashValue"),
        "cipherAlgorithm": attr("cipherAlgorithm"),
    }

# 2) 生成 3/4/5 位随机密码并加密
info = []
for L in (3, 4, 5):
    pwd = {3:"ytp",4:"5ypy",5:"s6ej2"}[L]
    tag = "".join(str(CHARSET.index(c) % 10) for c in pwd)  # 仅用于文件名去重
    path = make(pwd, "x" + tag)
    p = dump_params(path)
    # 3) 回环校验：用 msoffcrypto 解回明文，确认文档可用
    with open(path, "rb") as f:
        of = msoffcrypto.OfficeFile(f)
        of.load_key(password=pwd)
        buf = io.BytesIO(); of.decrypt(buf)
    ok = buf.getvalue()[:4] == b"PK\x03\x04"
    info.append({"len": L, "password": pwd, "file": os.path.basename(path),
                 "size": os.path.getsize(path), "roundtrip_ok": ok, "params": p})
    print("L=%d pwd=%r file=%s size=%d 解密回环=%s  spincount=%d" % (L, pwd, os.path.basename(path), os.path.getsize(path), ok, p["spinCount"]))

with io.open(os.path.join(BASE, "enc_params.json"), "w", encoding="utf-8") as f:
    json.dump({"charset": CHARSET, "documents": info}, f, ensure_ascii=False, indent=2)
print("参数已导出 enc_params.json")
