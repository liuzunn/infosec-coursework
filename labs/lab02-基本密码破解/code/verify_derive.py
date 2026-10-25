
# -*- coding: utf-8 -*-
import json, base64, hashlib, struct, time
from Crypto.Cipher import AES

BASE = r"C:\Users\LZ\Desktop\信息安全实验\_lab2"
meta = json.load(open(BASE + r"\enc_params.json", encoding="utf-8"))
doc = meta["documents"][0]
P = doc["params"]
print("doc:", doc["file"], "pwd:", doc["password"], "spin:", P["spinCount"])

salt = base64.b64decode(P["saltValue"])
encIn = base64.b64decode(P["encryptedVerifierHashInput"])
encHash = base64.b64decode(P["encryptedVerifierHashValue"])
print("salt:", salt.hex(), "encIn len:", len(encIn), "encHash len:", len(encHash))

BLK1 = bytes([0xFE,0xA7,0xD2,0x76,0x3B,0x4B,0x9E,0x79])
BLK2 = bytes([0xD7,0xAA,0x0F,0x6D,0x30,0x61,0x34,0x4E])

def derive(pwd):
    h = hashlib.sha512(salt + pwd.encode("utf-16-le")).digest()
    for i in range(P["spinCount"]):
        h = hashlib.sha512(struct.pack("<I", i) + h).digest()
    return h

t0 = time.time()
H = derive(doc["password"])
t1 = time.time()
print("单次密钥派生(5000次SHA512)耗时: %.1f ms" % ((t1-t0)*1000))

def key_for(H, blk):
    k = hashlib.sha512(H + blk).digest()[:32]
    return k

k1 = key_for(H, BLK1)
k2 = key_for(H, BLK2)

def try_iv(iv):
    try:
        v = AES.new(k1, AES.MODE_CBC, iv).decrypt(encIn)
        hv = AES.new(k2, AES.MODE_CBC, iv).decrypt(encHash)
        return hashlib.sha512(v).digest() == hv, v.hex()[:32]
    except Exception as e:
        return False, str(e)

for name, iv in (("iv=salt", salt), ("iv=sha512(salt+blk1)[:16]", hashlib.sha512(salt+BLK1).digest()[:16])):
    ok, extra = try_iv(iv)
    print("  尝试 %s -> %s  (%s)" % (name, ok, extra))
