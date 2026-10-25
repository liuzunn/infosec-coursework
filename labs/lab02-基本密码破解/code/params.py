
# -*- coding: utf-8 -*-
import os, json, re, base64, hashlib, struct, io, time
import olefile
from Crypto.Cipher import AES
import msoffcrypto

BASE = r"C:\Users\LZ\Desktop\信息安全实验\_lab2"
DOCS = os.path.join(BASE, "docs")
CHARSET = "0123456789abcdefghijklmnopqrstuvwxyz"

def parse(path):
    ole = olefile.OleFileIO(path)
    ei = ole.openstream("EncryptionInfo").read()
    xml = ei[8:].decode("utf-8", "ignore")
    seg = xml[xml.index("encryptedKey"):]          # 只取 <p:encryptedKey .../> 这一段
    def attr(name):
        m = re.search(r'%s="([^"]*)"' % name, seg)
        return m.group(1) if m else None
    return {
        "spinCount": int(attr("spinCount")),
        "keyBits": int(attr("keyBits")),
        "hashAlgorithm": attr("hashAlgorithm"),
        "saltValue": attr("saltValue"),
        "encryptedVerifierHashInput": attr("encryptedVerifierHashInput"),
        "encryptedVerifierHashValue": attr("encryptedVerifierHashValue"),
    }

BLK1 = bytes.fromhex("fea7d2763b4b9e79")
BLK2 = bytes.fromhex("d7aa0f6d3061344e")

def derive_H(pwd, salt, spin):
    h = hashlib.sha512(salt + pwd.encode("utf-16-le")).digest()
    for i in range(spin):
        h = hashlib.sha512(struct.pack("<I", i) + h).digest()
    return h

def verify(pwd, P):
    salt = base64.b64decode(P["saltValue"])
    H = derive_H(pwd, salt, P["spinCount"])
    k1 = hashlib.sha512(H + BLK1).digest()[:P["keyBits"]//8]
    k2 = hashlib.sha512(H + BLK2).digest()[:P["keyBits"]//8]
    v = AES.new(k1, AES.MODE_CBC, salt).decrypt(base64.b64decode(P["encryptedVerifierHashInput"]))
    exp = AES.new(k2, AES.MODE_CBC, salt).decrypt(base64.b64decode(P["encryptedVerifierHashValue"]))
    return hashlib.sha512(v).digest() == exp

# 已知密码（生成时记录）
truth = {3: "ytp", 4: "5ypy", 5: "s6ej2"}
docs = []
for L in (3, 4, 5):
    fn = [n for n in os.listdir(DOCS) if n.startswith("enc_%d_" % L)][0]
    path = os.path.join(DOCS, fn)
    P = parse(path)
    t0 = time.time(); ok = verify(truth[L], P); dt = (time.time()-t0)*1000
    print("L=%d file=%s spin=%d salt=%s 校验=%s 单次派生=%.1fms" % (L, fn, P["spinCount"], P["saltValue"][:12], ok, dt))
    docs.append({"len": L, "password": truth[L], "file": fn, "size": os.path.getsize(path), "params": P})

json.dump({"charset": CHARSET, "documents": docs}, open(os.path.join(BASE, "enc_params.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# 同时生成 Java 易读的参数文件
for d in docs:
    P = d["params"]
    with open(os.path.join(BASE, "doc%d.params" % d["len"]), "w", encoding="utf-8") as f:
        f.write("file=%s\n" % d["file"])
        f.write("spinCount=%d\n" % P["spinCount"])
        f.write("keyBits=%d\n" % P["keyBits"])
        f.write("hashAlgorithm=%s\n" % P["hashAlgorithm"])
        for k in ("saltValue", "encryptedVerifierHashInput", "encryptedVerifierHashValue"):
            f.write("%s=%s\n" % (k, P[k]))
print("参数文件已写出")
