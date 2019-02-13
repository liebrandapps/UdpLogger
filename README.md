# UdpLogger
The idea for the UdpLogger came up during development of an Android App. During recent versions of Android, the execution
of background tasks has been limited in order to save battery. This means that developers have to carefully check whether
theirs services and broadcastreceivers really do their intended work while in the background.

As this is not so easy to debug and probably requires a little bit of a long term monitoring, the idea for the project came up.

The implementation for Android queues the log messages and snds them off as async task. This should take load off the phone 
and prevents an overrun of UDP messages.

