
import java.security.MessageDigest;
import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.util.Base64;

public class Bench2 {
    public static void main(String[] a) throws Exception {
        byte[] salt = new byte[16];
        byte[] in = new byte[68];
        byte[] h1 = new byte[64], h2 = new byte[64];
        for (int i=0;i<16;i++) salt[i]=(byte)i;
        for (int i=0;i<68;i++) in[i]=(byte)(i*3);

        MessageDigest md = MessageDigest.getInstance("SHA-512");
        // 单次 SHA-512 速度
        int N = 300000; long t0=System.nanoTime();
        for (int i=0;i<N;i++){ in[0]=(byte)i; md.reset(); md.update(in,0,68); md.digest(h1,0,64); }
        long t1=System.nanoTime();
        System.out.printf("SHA-512 (68B): %.1f ns/hash%n", (t1-t0)/(double)N);

        // 5000 次自旋（一个候选）
        int M = 200; t0=System.nanoTime();
        for (int c=0;c<M;c++){
            md.reset(); md.update(in,0,68); md.digest(h1,0,64);
            byte[] cur=h1, nxt=h2;
            for (int i=0;i<5000;i++){
                in[0]=(byte)i; in[1]=(byte)(i>>>8);
                System.arraycopy(cur,0,in,4,64);
                md.reset(); md.update(in,0,68); md.digest(nxt,0,64);
                byte[] t=cur; cur=nxt; nxt=t;
            }
        }
        t1=System.nanoTime();
        System.out.printf("5000 次自旋: %.2f ms/candidate%n", (t1-t0)/1e6/M);

        // AES 开销
        Cipher aes = Cipher.getInstance("AES/CBC/NoPadding");
        byte[] k = new byte[32], vi = new byte[16], eh = new byte[64];
        for (int i=0;i<32;i++) k[i]=(byte)i;
        int A = 2000; t0=System.nanoTime();
        for (int i=0;i<A;i++){
            aes.init(Cipher.DECRYPT_MODE, new SecretKeySpec(k,0,32,"AES"), new IvParameterSpec(salt));
            aes.doFinal(vi,0,16);
            aes.init(Cipher.DECRYPT_MODE, new SecretKeySpec(k,0,32,"AES"), new IvParameterSpec(salt));
            aes.doFinal(eh);
        }
        t1=System.nanoTime();
        System.out.printf("2×AES init+decrypt: %.3f ms/candidate%n", (t1-t0)/1e6/A);
        System.out.println("cores=" + Runtime.getRuntime().availableProcessors());
    }
}
