package io.liebrand;


import android.content.Context;
import android.content.SharedPreferences;
import android.os.AsyncTask;
import android.preference.PreferenceManager;
import android.util.Base64;
import android.util.Log;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.LinkedList;
import java.util.Random;
import java.util.UUID;

import javax.crypto.BadPaddingException;
import javax.crypto.Cipher;
import javax.crypto.IllegalBlockSizeException;
import javax.crypto.NoSuchPaddingException;
import javax.crypto.spec.SecretKeySpec;

public class UDPDebugLogger {
    private static String TAG = "UDPDEBUGLOGGER";
    private static AsyncTask<Void, Void, Void> async_client;
    private static String app;
    private static String key;
    private static boolean encrypt;
    private static int sequence=1;
    private static String uid;
    private static String host;
    private static String AESKey;
    private static int port;


    /*
        generate a UID and a AES Key
     */
    public String init(Context context) {
        sequence = 0;
        SharedPreferences sharedPref = PreferenceManager.getDefaultSharedPreferences(context);
        if (!(sharedPref.getBoolean("__udpLoggingInitialized", false))) {
            SharedPreferences.Editor edit = sharedPref.edit();
            edit.putBoolean("__udpLoggingInitialized", true);
            edit.putString( "__udpLoggingUID", UUID.randomUUID().toString());
            key = getRandomString(32);
            edit.putString("__udpLoggingKeyAESKey", key);
            edit.apply();
        }
        else {
            key = sharedPref.getString("__udpLoggingKeyAESKey", "");
            if (key.length()==0) {
                SharedPreferences.Editor edit = sharedPref.edit();
                edit.putBoolean("__udpLoggingInitialized", false);
                edit.apply();
            }

        }
        Log.i(TAG, "AESKey: " + key);
        return key;
    }

    private String getRandomString(int length) {
        final String characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJLMNOPQRSTUVWXYZ1234567890";
        StringBuilder result = new StringBuilder();
        while(length > 0) {
            Random rand = new Random();
            result.append(characters.charAt(rand.nextInt(characters.length())));
            length--;
        }
        return result.toString();
    }

    public String configure(Context ctx, String app, boolean encrypt, String host, int port) {
        UDPDebugLogger.app = app;
        UDPDebugLogger.encrypt = encrypt;
        UDPDebugLogger.host = host;
        UDPDebugLogger.port = port;
        SharedPreferences sharedPref = PreferenceManager.getDefaultSharedPreferences(ctx);
        UDPDebugLogger.uid = sharedPref.getString("__udpLoggingUID", "-");
        UDPDebugLogger.AESKey = sharedPref.getString("__udpLoggingKeyAESKey", "");
        if (UDPDebugLogger.AESKey.length()==0) {
            UDPDebugLogger.encrypt = false;
        }
        return(UDPDebugLogger.uid);
    }

    public void log(String severity, String message) {
        ByteArrayOutputStream oStream = new ByteArrayOutputStream();
        try {
            byte [] data =  null;
            SimpleDateFormat simpleDateFormat =
                    new SimpleDateFormat("yyyy-MM-dd HH:mm:ssZZZZZ");
            Calendar calendar = Calendar.getInstance();
            Date now = calendar.getTime();
            String timestamp = simpleDateFormat.format(now);
            write(oStream, new DataItem("app", app));
            write(oStream, new DataItem("sequence", sequence));
            write(oStream, new DataItem("uid", UDPDebugLogger.uid));
            write(oStream, new DataItem( "when", timestamp));
            write(oStream, new DataItem("severity", severity));
            write(oStream, new DataItem("message", message));
            if(UDPDebugLogger.encrypt) {
                try {
                    SecureRandom sr = SecureRandom.getInstance("SHA1PRNG");
                    byte[] iv = sr.generateSeed(16);
                    write(oStream, new DataItem("random", iv));
                    SecretKeySpec skeySpec = new SecretKeySpec(UDPDebugLogger.AESKey.getBytes("UTF-8"), "AES");
                    Cipher cipher = Cipher.getInstance("AES");
                    cipher.init(Cipher.ENCRYPT_MODE, skeySpec);
                    byte[] encrypted = cipher.doFinal(oStream.toByteArray());
                    String b64ed = Base64.encodeToString(encrypted, Base64.DEFAULT);
                    oStream = new ByteArrayOutputStream();
                    write(oStream, new DataItem("envelope", b64ed));
                    data = oStream.toByteArray();
                }
                catch(NoSuchAlgorithmException e) {
                    Log.e(UDPDebugLogger.TAG, e.getMessage(), e.getCause());
                    write(oStream, new DataItem("warning", "Encryption failed - check log on client app"));
                    data = oStream.toByteArray();
                }
                catch(NoSuchPaddingException e) {
                    Log.e(UDPDebugLogger.TAG, e.getMessage(), e.getCause());
                    write(oStream, new DataItem("warning", "Encryption failed - check log on client app"));
                    data = oStream.toByteArray();
                }
                catch(InvalidKeyException e) {
                    Log.e(UDPDebugLogger.TAG, e.getMessage(), e.getCause());
                    write(oStream, new DataItem("warning", "Encryption failed - check log on client app"));
                    data = oStream.toByteArray();
                }
                catch(IllegalBlockSizeException e) {
                    Log.e(UDPDebugLogger.TAG, e.getMessage(), e.getCause());
                    write(oStream, new DataItem("warning", "Encryption failed - check log on client app"));
                    data = oStream.toByteArray();
                }
                catch(BadPaddingException e) {
                    Log.e(UDPDebugLogger.TAG, e.getMessage(), e.getCause());
                    write(oStream, new DataItem("warning", "Encryption failed - check log on client app"));
                    data = oStream.toByteArray();
                }
            }

            else {
                data = oStream.toByteArray();
            }
            ByteArrayOutputStream oStream2 = new ByteArrayOutputStream();
            writeLongDirect(oStream2, data.length);
            writeBinaryDirect(oStream2, data);
            data = oStream2.toByteArray();
            new SendTask(data).execute();
        }
        catch(IOException e) {
            Log.e(UDPDebugLogger.TAG, e.getMessage(), e.getCause());
        }
        sequence +=1;
    }

    private static class SendTask extends AsyncTask<Void, Void, String> {

        private LinkedList<byte[]> mq = new LinkedList<byte[]>();

        public SendTask(byte [] messageData){
            mq.add(messageData);
        }

        @Override
        protected String doInBackground(Void... params) {

            DatagramSocket ds = null;
            try
            {
                ds = new DatagramSocket();
                DatagramPacket dp;
                while (!(mq.isEmpty())) {
                    byte [] msg = mq.pop();
                    dp = new DatagramPacket(msg, msg.length, InetAddress.getByName(host), port);
                    ds.send(dp);
                    Thread.sleep(50);
                }
            }
            catch (Exception e)
            {
                e.printStackTrace();
            }
            finally
            {
                if (ds != null)
                {
                    ds.close();
                }
            }
            return null;
        }

    }

    public static void write(OutputStream stream, DataItem item) throws IOException {
        stream.write(item.getType());
        switch (item.getType()) {
            case DataItem.TYPE_STRING:
                writeRawString(stream, item.getKey());
                writeRawString(stream, item.getString());
                break;
            case DataItem.TYPE_BINARY:
                writeRawString(stream, item.getKey());
                writeRawBinary(stream, item.getBinary());
                break;
            case DataItem.TYPE_NUMBER:
                writeRawString(stream, item.getKey());
                writeRawLong(stream, item.getLong());
                break;

        }

    }

    public static void writeBinaryDirect(OutputStream stream, byte [] data) throws IOException {
        stream.write(data);
    }

    private static void writeRawString(OutputStream stream, String strg) throws IOException {
        int ln=strg.length();
        byte hiByte=(byte)(ln / 256);
        byte loByte=(byte)(ln % 256);
        stream.write((char)hiByte);
        stream.write((char)loByte);
        stream.write(strg.getBytes());
    }

    private static void writeRawBinary(OutputStream stream, byte [] binary) throws IOException {
        int ln=binary.length;
        int hiInt=(int)(ln / 65536);
        int loInt=(int)(ln % 65536);
        byte hiByte=(byte)(hiInt / 256);
        byte loByte=(byte)(hiInt % 256);
        stream.write((char)hiByte);
        stream.write((char)loByte);
        hiByte=(byte)(loInt / 256);
        loByte=(byte)(loInt % 256);
        stream.write((char)hiByte);
        stream.write((char)loByte);
        stream.write(binary);
    }

    private static void writeLongDirect(OutputStream stream, long lng) throws IOException {
        stream.write(DataItem.TYPE_LONGDIRECT);
        writeRawLong(stream, lng);
    }

    private static void writeRawLong(OutputStream stream, long lng) throws IOException {
        int hiInt=(int)(lng / 65536);
        int loInt=(int)(lng % 65536);
        byte hiByte=(byte)(hiInt / 256);
        byte loByte=(byte)(hiInt % 256);
        stream.write((char)hiByte);
        stream.write((char)loByte);
        hiByte=(byte)(loInt / 256);
        loByte=(byte)(loInt % 256);
        stream.write((char)hiByte);
        stream.write((char)loByte);
    }


    public class DataItem {

        public static final byte TYPE_STRING=1;
        public static final byte TYPE_NUMBER=2;
        public static final byte TYPE_COMMAND=3;
        public static final byte TYPE_BINARY=4;
        public static final byte TYPE_LONGDIRECT=64;

        private int length;
        private byte type;
        private String key;
        private String valueString;
        private long valueLong;
        private byte [] valueBinary;

        public DataItem(String key, String valueString) {
            type=TYPE_STRING;
            this.key=key;
            this.valueString=valueString;
        }

        public DataItem(String key, long valueLong) {
            type=TYPE_NUMBER;
            this.key=key;
            this.valueLong=valueLong;
        }

        public DataItem(String key, byte [] binary) {
            type=TYPE_BINARY;
            this.key=key;
            this.valueBinary=binary;
        }

        public byte getType() {
            return(type);
        }

        public String getKey() {
            return(key);
        }

        public String getString() {
            return(valueString);
        }

        public byte [] getBinary() {
            return(valueBinary);
        }

        public long getLong() {
            return(valueLong);
        }

        public void setLenInStream(int len) {
            length=len;
        }

        public int getLenInStream() {
            return(length);
        }


    }



}

