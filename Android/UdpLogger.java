package io.liebrand.udplogger;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.AsyncTask;
import android.preference.PreferenceManager;
import android.util.Log;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.Queue;
import java.util.Random;
import java.util.UUID;

public class UDPDebugLogger {
    private static String TAG = "UDPDEBUGLOGGER";
    private static AsyncTask<Void, Void, Void> async_client;
    private String Message;
    private String app;
    private String key;
    private boolean encrypt;
    private int sequence;
    private Context context;
    private String host;
    private String port;

    /*
        generate a UID and a AES Key
     */
    public String init(Context context) {
        sequence = 0;
        SharedPreferences sharedPref = PreferenceManager.getDefaultSharedPreferences(context);
        if (sharedPref.getBoolean("__udpLoggingInitialized", false)) {
            SharedPreferences.Editor edit = sharedPref.edit();
            edit.putBoolean("__udpLoggingInitialized", true);
            edit.putString( "__udpLoggingUID", UUID.randomUUID().toString();
            key = getRandomString(32);
            edit.putString("__udpLoggingKeyAESKey", key);
            edit.apply();
        }
        else {
            sharedPref.getString("__udpLoggingKeyAESKey", getRandomString(32));
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

    public void configure(String app, boolean encrypt, String host, int port) {
        this.app = app;
        this.encrypt = encrypt;
        this.host = host;
        this.port = port
    }

    public void log(String severity, String message) {

        new SendTask().execute();
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
                    dp = new DatagramPacket(msg, msg.length, host, port);
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

    }
}
