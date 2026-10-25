
# -*- coding: utf-8 -*-
import os, json, base64, hashlib, struct, time
from Crypto.Cipher import AES
from msoffcrypto.method.ecma376_agile import ECMA376Agile

BASE = r"C:\Users\LZ\Desktop\信息安全实验\_lab2"
DOCS = os.path.join(BASE, "docs")
BLK1 = bytes.fromhex("fea7d2763b4b9e79")
BLK2 = bytes.fromhex("d7aa0f6d3061344e")

def parse(path):
    import olefile, re
    ei = olefile.OleFileIO(path).openstream("EncryptionInfo").read()
    xml = ei[8:].decode("utf-8", "ignore")
    seg = xml[xml.index("encryptedKey"):]
    g = lambda n: re.search(r'%s="([^"]*)"' % n, seg).group(1)
    return {"spinCount": int(g("spinCount")), "keyBits": int(g("keyBits")),
            "saltValue": g("saltValue"),
            "encryptedVerifierHashInput": g("encryptedVerifierHashInput"),
            "encryptedVerifierHashValue": g("encryptedVerifierHashValue")}

def verify(pwd, P):
    salt = base64.b64decode(P["saltValue"])
    h = hashlib.sha512(salt + pwd.encode("utf-16-le")).digest()
    for i in range(P["spinCount"]):
        h = hashlib.sha512(struct.pack("<I", i) + h).digest()
    k1 = hashlib.sha512(h + BLK1).digest()[:P["keyBits"]//8]
    k2 = hashlib.sha512(h + BLK2).digest()[:P["keyBits"]//8]
    v = AES.new(k1, AES.MODE_CBC, salt).decrypt(base64.b64decode(P["encryptedVerifierHashInput"]))
    exp = AES.new(k2, AES.MODE_CBC, salt).decrypt(base64.b64decode(P["encryptedVerifierHashValue"]))
    return hashlib.sha512(v).digest() == exp

# 1) 生成一个 6 位弱口令文档
plain = os.path.join(BASE, "图书管理系统-实验用文档.docx")
weak = "abc123"
out = os.path.join(DOCS, "enc_6_weak.docx")
with open(plain, "rb") as f:
    buf = ECMA376Agile.encrypt(weak, f, spin_count=1000)
open(out, "wb").write(buf)
P = parse(out)
print("弱口令文档:", os.path.basename(out), " 密码:", weak)

# 2) 常见弱口令字典（模拟 AOPR 自带字典）
dict_words = """123456 password 12345678 qwerty 123456789 12345 1234 111111 1234567 dragon 123123
baseball abc123 football monkey letmein shadow master 666666 qwertyuiop 123321 mustang 1234567890
michael 654321 pussy superman 1qaz2wsx 7777777 fuckyou 121212 000000 qazwsx 123qwe killer trustno1
jordan jennifer zxcvbnm asdfgh hunter buster soccer harley batman andrew tigger sunshine iloveyou
charlie robert thomas hockey ranger daniel starwars klaster 112233 george asshole computer michelle
jessica pepper 1111 zxcvbn 555555 11111111 131313 freedom 777777 pass fuck maggie 159753 aaaaaa
ginger princess joshua cheese amanda summer love ashley 6969 nicole chelsea biteme matthew access
yankees 987654321 dallas austin thunder taylor matrix william corvette hello martin heather secret
merlin diamond 1234qwer gfhjkm hammer silver 222222 88888888 anthony justin test bailey q1w2e3r4
patrick internet scooter orange 11111 golfer cookie richard samantha bigdog guitar jackson whatever
mickey chicken sparky snoopy maverick phoenix camaro sex sexy peanut morgan welcome falcon cowboy
ferrari samsung andrea smokey steelers joseph mercedes dakota arsenal eagles melissa boomer boomerang
spider nascar monster tigers yellow xxxxxx 123123123 gateway marina diablo bulldog qwer1234 compaq
purple hardcore banana junior hannah 123654 porsche lakers iceman money cowboys 987654 london tennis
999999 ncc1701 coffee scooby 0000 miller boston qwerty123 bigdaddy yamaha 1234567891011 redsox
qwertyuiopasdfghjkl angel eleven mommy friends sydney marlboro blonde siemens dolphin computer
happy whatever zzzzzz nintendo passing fuckme bullshit xxx123 viper melanie""".split()

t0 = time.time()
found = None
tried = 0
for w in dict_words:
    tried += 1
    if verify(w, P):
        found = w; break
el = time.time() - t0
print("字典条目数:", len(dict_words), " 尝试次数:", tried)
print("字典破解结果: %s  用时 %.2f 秒" % (found, el))

# 3) 若无字典，暴力破解 6 位需要多少？（按组合数推算）
print("6 位 36 字符集组合数:", 36**6)
