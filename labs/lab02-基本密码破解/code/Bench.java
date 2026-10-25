
import java.security.MessageDigest;

public class Bench {
    // 手写 SHA-1（针对 24 字节定长输入优化，单块）
    static final int[] K = {0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC, 0xCA62C1D6};
    static final int[] H0 = {0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0};

    static void sha1_24(byte[] in, int off, int[] out) {
        int[] w = new int[80];
        for (int i = 0; i < 5; i++) w[i] = ((in[off+i*4]&0xFF)<<24) | ((in[off+i*4+1]&0xFF)<<16) | ((in[off+i*4+2]&0xFF)<<8) | (in[off+i*4+3]&0xFF);
        // in[20..23] 是计数器 + 0x80 填充在同一位置根据长度处理
        w[5] = ((in[off+20]&0xFF)<<24) | ((in[off+21]&0xFF)<<16) | ((in[off+22]&0xFF)<<8) | (in[off+23]&0xFF);
        w[6] = 0x80000000;
        for (int i = 7; i < 15; i++) w[i] = 0;
        w[15] = 24 * 8;
        for (int i = 16; i < 80; i++) {
            int x = w[i-3] ^ w[i-8] ^ w[i-14] ^ w[i-16];
            w[i] = (x << 1) | (x >>> 31);
        }
        int a = H0[0], b = H0[1], c = H0[2], d = H0[3], e = H0[4];
        for (int i = 0; i < 80; i++) {
            int f, k;
            if (i < 20) { f = (b & c) | (~b & d); k = K[0]; }
            else if (i < 40) { f = b ^ c ^ d; k = K[1]; }
            else if (i < 60) { f = (b & c) | (b & d) | (c & d); k = K[2]; }
            else { f = b ^ c ^ d; k = K[3]; }
            int t = ((a << 5) | (a >>> 27)) + f + e + k + w[i];
            e = d; d = c; c = (b << 30) | (b >>> 2); b = a; a = t;
        }
        out[0] = H0[0] + a; out[1] = H0[1] + b; out[2] = H0[2] + c; out[3] = H0[3] + d; out[4] = H0[4] + e;
    }

    public static void main(String[] a) throws Exception {
        byte[] buf = new byte[24];
        int[] outi = new int[5];
        for (int i = 0; i < 20; i++) buf[i] = (byte)(i*7+3);
        // warmup
        for (int i = 0; i < 200000; i++) { buf[20]=(byte)(i>>>24); buf[21]=(byte)(i>>>16); buf[22]=(byte)(i>>>8); buf[23]=(byte)i; sha1_24(buf,0,outi); }
        int N = 2000000;
        long t0 = System.nanoTime();
        for (int i = 0; i < N; i++) {
            buf[20]=(byte)(i>>>24); buf[21]=(byte)(i>>>16); buf[22]=(byte)(i>>>8); buf[23]=(byte)i;
            sha1_24(buf, 0, outi);
        }
        long t1 = System.nanoTime();
        double nsPer = (t1 - t0) / (double) N;
        System.out.println("custom sha1: " + String.format("%.1f ns/hash", nsPer));
        System.out.println("  50000 spins = " + String.format("%.2f ms/candidate", nsPer*50000/1e6));
        System.out.println("  single core = " + String.format("%.0f cand/s", 1e9/(nsPer*50000)));

        // JCE 对照
        MessageDigest md = MessageDigest.getInstance("SHA-1");
        for (int i = 0; i < 100000; i++) { md.reset(); md.update(buf,0,24); md.digest(); }
        int M = 500000;
        t0 = System.nanoTime();
        for (int i = 0; i < M; i++) { md.reset(); md.update(buf,0,24); md.digest(); }
        t1 = System.nanoTime();
        double nsJ = (t1-t0)/(double)M;
        System.out.println("JCE sha1: " + String.format("%.1f ns/hash", nsJ) + "  -> " + String.format("%.0f cand/s", 1e9/(nsJ*50000)));
        System.out.println("cores = " + Runtime.getRuntime().availableProcessors());
    }
}
