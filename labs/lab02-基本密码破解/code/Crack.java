
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;
import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.util.Base64;

public class Crack {
    static byte[] salt, encIn, encHash;
    static int spin, keyBits, keyLen;
    static String charset;
    static final byte[] BLK1 = hex("fea7d2763b4b9e79");
    static final byte[] BLK2 = hex("d7aa0f6d3061344e");
    static volatile String found = null;
    static volatile long foundIdx = -1;
    static final AtomicLong scanned = new AtomicLong(0);

    static byte[] hex(String s) {
        byte[] b = new byte[s.length()/2];
        for (int i=0;i<b.length;i++) b[i] = (byte)Integer.parseInt(s.substring(i*2,i*2+2),16);
        return b;
    }

    static Map<String,String> readParams(String f) throws IOException {
        Map<String,String> m = new HashMap<>();
        for (String line : Files.readAllLines(Paths.get(f), StandardCharsets.UTF_8)) {
            int i = line.indexOf('=');
            if (i > 0) m.put(line.substring(0,i).trim(), line.substring(i+1).trim());
        }
        return m;
    }

    // 单候选校验
    static boolean check(byte[] pwd, MessageDigest md, Cipher aes,
                         byte[] saltPwd, byte[] in, byte[] h1, byte[] h2, byte[] tmp) throws Exception {
        // H0 = SHA512(salt || pwd_utf16le)
        int n = salt.length + pwd.length*2;
        System.arraycopy(salt, 0, saltPwd, 0, salt.length);
        int p = salt.length;
        for (byte b : pwd) { saltPwd[p++] = b; saltPwd[p++] = 0; }
        md.reset(); md.update(saltPwd, 0, n);
        byte[] cur = h1, nxt = h2;
        md.digest(cur, 0, 64);
        // 迭代
        for (int i = 0; i < spin; i++) {
            in[0]=(byte)i; in[1]=(byte)(i>>>8); in[2]=(byte)(i>>>16); in[3]=(byte)(i>>>24);
            System.arraycopy(cur, 0, in, 4, 64);
            md.reset(); md.update(in, 0, 68);
            md.digest(nxt, 0, 64);
            byte[] t = cur; cur = nxt; nxt = t;
        }
        // key1 = SHA512(H || blk1)[:keyLen]
        System.arraycopy(cur, 0, tmp, 0, 64); System.arraycopy(BLK1, 0, tmp, 64, 8);
        md.reset(); md.update(tmp, 0, 72); md.digest(nxt, 0, 64);
        byte[] k1 = nxt;
        // key2
        System.arraycopy(cur, 0, tmp, 0, 64); System.arraycopy(BLK2, 0, tmp, 64, 8);
        md.reset(); md.update(tmp, 0, 72); md.digest(h1, 0, 64);
        byte[] k2 = h1;
        // AES-CBC 解密 verifierHashInput
        aes.init(Cipher.DECRYPT_MODE, new SecretKeySpec(k1, 0, keyLen, "AES"), new IvParameterSpec(salt));
        byte[] v = aes.doFinal(encIn, 0, 16);
        aes.init(Cipher.DECRYPT_MODE, new SecretKeySpec(k2, 0, keyLen, "AES"), new IvParameterSpec(salt));
        byte[] exp = aes.doFinal(encHash);
        md.reset(); md.update(v); md.digest(nxt, 0, 64);
        for (int i = 0; i < 64; i++) if (nxt[i] != exp[i]) return false;
        return true;
    }

    static void idxToPwd(long idx, int len, byte[] out, int base) {
        for (int i = len-1; i >= 0; i--) { out[i] = (byte) charset.charAt((int)(idx % base)); idx /= base; }
    }

    public static void main(String[] args) throws Exception {
        Map<String,String> P = readParams(args[0]);
        int L = Integer.parseInt(args[1]);
        charset = args.length > 2 ? args[2] : "0123456789abcdefghijklmnopqrstuvwxyz";
        int threads = args.length > 3 ? Integer.parseInt(args[3]) : Runtime.getRuntime().availableProcessors();
        spin = Integer.parseInt(P.get("spinCount"));
        keyBits = Integer.parseInt(P.get("keyBits"));
        keyLen = keyBits/8;
        salt = Base64.getDecoder().decode(P.get("saltValue"));
        encIn = Base64.getDecoder().decode(P.get("encryptedVerifierHashInput"));
        encHash = Base64.getDecoder().decode(P.get("encryptedVerifierHashValue"));

        int base = charset.length();
        long space = 1; for (int i=0;i<L;i++) space *= base;
        final long SPACE = space;
        System.out.println("目标文档: " + P.get("file"));
        System.out.println("密码长度=" + L + "  字符集大小=" + base + " (" + charset + ")  候选总数=" + space);
        System.out.println("迭代次数(spinCount)=" + spin + "  线程数=" + threads);

        long t0 = System.nanoTime();
        Thread[] ts = new Thread[threads];
        for (int t = 0; t < threads; t++) {
            final int tid = t;
            ts[t] = new Thread(() -> {
                try {
                    MessageDigest md = MessageDigest.getInstance("SHA-512");
                    Cipher aes = Cipher.getInstance("AES/CBC/NoPadding");
                    byte[] pwd = new byte[L];
                    byte[] saltPwd = new byte[salt.length + L*2];
                    byte[] in = new byte[68], h1 = new byte[64], h2 = new byte[64], tmp = new byte[72];
                    long local = 0;
                    for (long idx = tid; idx < SPACE; idx += threads) {
                        if (found != null) break;
                        idxToPwd(idx, L, pwd, base);
                        if (check(pwd, md, aes, saltPwd, in, h1, h2, tmp)) {
                            found = new String(pwd, StandardCharsets.US_ASCII);
                            foundIdx = idx;
                            break;
                        }
                        if ((++local & 0xFFF) == 0) scanned.addAndGet(0x1000);
                    }
                    scanned.addAndGet(local & 0xFFF);
                } catch (Exception e) { e.printStackTrace(); }
            });
            ts[t].start();
        }
        final long total = space;
        Thread mon = new Thread(() -> {
            while (found == null) {
                try { Thread.sleep(1000); } catch (InterruptedException e) { return; }
                long el = (System.nanoTime()-t0)/1_000_000;
                if (el > 3000)
                    System.out.printf("  已扫描 %,d / %,d (%.1f%%)  速率 %,d 个/秒  已用 %.1f 秒%n",
                        scanned.get(), total, scanned.get()*100.0/total, scanned.get()*1000/Math.max(el,1), el/1000.0);
                if (el > 3600_000L * 3) { System.out.println("超时退出"); System.exit(2); }
            }
        });
        mon.setDaemon(true); mon.start();
        for (Thread t : ts) t.join();
        long ms = (System.nanoTime()-t0)/1_000_000;
        if (found != null) {
            System.out.println(">>> 破解成功！密码 = \"" + found + "\"");
            System.out.println(">>> 命中序号 = " + foundIdx + " / " + space);
            System.out.println(">>> 用时 = " + ms + " ms (" + String.format("%.2f", ms/1000.0) + " 秒)");
            System.out.println(">>> 平均速率 = " + (ms>0 ? (foundIdx+1)*1000L/Math.max(ms,1) : 0) + " 个/秒");
        } else {
            System.out.println("未找到，用时 " + ms + " ms，已扫描 " + scanned.get());
        }
    }
}
