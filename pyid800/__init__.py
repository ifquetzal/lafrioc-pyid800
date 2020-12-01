# -*- coding: utf-8 -*-
"""
Created on Tue Mar 20 15:08:31 2018

@author: Luis Villegas
"""

from ctypes import byref,c_int,c_int8,c_int32,c_int64,c_double
try:
    from ctypes import WinDLL
except ImportError:
    raise(ImportError("This package only works on Windows 32-bit due to \
    driver incompatibilities."))
from os import path
import pyid800.config as config
import warnings

class TDC:
    def __init__(self, libpath = None):
        if libpath is not None:
            self._libpath = libpath
        else:
            self._libpath = path.join(path.dirname(__file__),
                                        'tdcbase.dll')
        self.dll_lib = WinDLL(self._libpath)

        # Timebase
        self.getTimebase = self.dll_lib.TDC_getTimebase
        self.getTimebase.restype = c_double
        self.timebase = self.getTimebase()
        self.timestamp_count = config.timestamp_count

        # Variable declarations
        c_array8 = c_int8*self.timestamp_count
        c_array64 = c_int64*self.timestamp_count
        self.getVersion = self.dll_lib.TDC_getVersion
        self.getVersion.restype = c_double
        self.channelMask = c_int8()
        self.coincWin = c_int(config.coincidence_window)
        self.expTime = c_int(config.exposure_time)
        self.timestamps = c_array64()
        self.channels = c_array8()
        self.valid = c_int32()

        # Activate
        rs = self.dll_lib.TDC_init(-1) # Accept every device
        print(">>> Init module : ", end="")
        self.switch(rs)
        if rs != 0:
            self.connection = False
        else:
            self.connection = True

        # Select channelmask [byte = channel] to use (id800 userguide)
        # 0 = none         8 = 4
        # 1 = 1            9 = 1,4
        # 2 = 2           10 = 2,4
        # 3 = 1,2         11 = 1,2,4
        # 4 = 3           12 = 3,4
        # 5 = 1,3         13 = 1,3,4
        # 6 = 2,3         14 = 2,3,4
        # 7 = 1,2,3       15 = 1,2,3,4
        self.channels_enabled = config.channels_enabled # All
        print(">>> Enabling channelmask {} : ".format(c_int8(self.channels_enabled).value),end="")
        rs = self.dll_lib.TDC_enableChannels(self.channels_enabled)
        self.switch(rs)
        # Coincidence window and exposure time
        print(">>> Setting Coincidence Counter parameters : ", end="")
        rs = self.dll_lib.TDC_setCoincidenceWindow(self.coincWin)
        self.switch(rs)
        self.dll_lib.TDC_setExposureTime(self.expTime)
        # Set the buffer size
        self.dll_lib.TDC_setTimestampBufferSize(self.timestamp_count)
        # Histogram
        self.setHistogramParams()
        self.toobig = c_int32()
        self.toosmall = c_int32()
        self.datacount = c_int32()
        self.hexpTime = c_int32()


    def close(self):
        rs = self.dll_lib.TDC_deInit()
        return self.switch(rs)

    def switch(self,rs):
        """ For debugging, refer to tdcbase.h
        """
        if rs == 0 and rs is not False: #TDC_Ok
            msg = "Success"
        elif rs == -1: #TDC_Error
            msg = "Unspecified error"
        elif rs == 1: #TDC_Timeout
            msg = "Receive timed out"
        elif rs == 2: #TDC_NotConnected
            msg = "No connection was established"
        elif rs == 3: #TDC_DriverError
            msg = "Error accessing the USB driver"
        elif rs == 7: #TDC_DeviceLocked
            msg = "Can't connect device beause already in use"
        elif rs == 8: #TDC_Unknown
            msg = "Unknown error"
        elif rs == 9: #TDC_NoDevice
            msg = "Invalid device number used in call"
        elif rs == 10: #TDC_OutOfRange
            msg = "Parameter in func. call is out of range"
        elif rs == 11: #TDC_CantOpen
            msg = "Failed to open specified file"
        else:
            msg = "????"
        print(msg)
        return msg

    def switchTermination(self,on=True):
        rs = self.dll_lib.TDC_switchTermination(on)
        return self.switch(rs)

    def getChannel(self,chan=0):
        dictionary = {0:None,1:(0,),2:(1,),3:(0,1),4:(2,),5:(0,2),6:(1,2),7:(0,1,2),
                      8:(3,),9:(0,3),10:(1,3),11:(0,1,3),12:(2,3),13:(0,2,3),
                      14:(1,2,3),15:(0,1,2,3)}
        return dictionary[chan]

    def getDeviceParams(self):
        self.dll_lib.TDC_getDeviceParams(byref(self.channelMask),
                                                byref(self.coincWin),
                                                byref(self.expTime))
        print("Channels: {}".format(self.channelMask.value))
        print("Coincidence Window: {} bins".format(self.coincWin.value))
        print("Exposure Time: {} ms".format(self.expTime.value))

    def configureSelfTest(self,test_channel,sg_period,sg_burst,burst_dist):
        rs = self.dll_lib.TDC_configureSelftest(test_channel,
                                                sg_period,
                                                sg_burst,
                                                burst_dist)
        return self.switch(rs)

    def getLastTimestamps(self,reset=False,output=False,*args):
        freeze = True
        if freeze:
            self.dll_lib.TDC_freezeBuffers(1)
        self.dll_lib.TDC_getLastTimestamps(reset,byref(self.timestamps),
                                                byref(self.channels),
                                                byref(self.valid))
        if output:
            self.saveTimestamps(*args)
            print("Saving to file...")
        if freeze:
            self.dll_lib.TDC_freezeBuffers(0)

    def saveTimestamps(self,filenamet="timestamps",filenamec="channels",
                       filesuffix=".bin"):
        timefile = open(filenamet+filesuffix,"w")
        for item in self.timestamps:
            timefile.write("%s\n" % item)
        timefile.close()

        channelfile = open(filenamec+filesuffix,"w")
        for item in self.channels:
            channelfile.write("%s\n" % item)
        channelfile.close()

    def writeTimestamps(self,filename=None,binary=False):
        if not filename:
            # Stop writing to file
            print(">>> Closing data file.")
            self.dll_lib.TDC_writeTimestamps(None,binary)
        else:
            # Start writing to file
            print(">>> Opening data file \""+filename+"\"")
            self.dll_lib.TDC_writeTimestamps(str.encode(filename),binary)

    def setHistogramParams(self,bincount=0,binwidth=0):
        self.dll_lib.TDC_clearAllHistograms()

        if binwidth == 0 or bincount == 0:
            self.bincount = config.bincount
            self.binwidth = config.binwidth
        else:
            self.bincount = bincount
            self.binwidth = binwidth
        c_array32 = c_int32*self.bincount
        self.hist = c_array32()
        self.bins2ns = c_double(self.binwidth*(81*1e-6))

        print(">>> Setting Histogram parameters : ", end="")
        rs = self.dll_lib.TDC_setHistogramParams(self.binwidth,
                                                 self.bincount)
        self.switch(rs)

    def getHistogramParams(self):
        binWidth = c_int32()
        binCount = c_int32()
        self.dll_lib.TDC_getHistogramParams(byref(binWidth),
                                                byref(binCount))
        print("Bin width: {} ns".format(binWidth.value*self.timebase*1e6))
        print("Bin count: {} bins".format(binCount.value))

    def getHistogram(self,channel1=-1,channel2=-1,clear=1):
        self.dll_lib.TDC_freezeBuffers(1)
        self.dll_lib.TDC_getHistogram(channel1,channel2,clear,
                                      byref(self.hist),byref(self.datacount),
                                      byref(self.toosmall),byref(self.toobig),
                                      None,None,byref(self.expTime))
        self.dll_lib.TDC_freezeBuffers(0)

    def getCoincCounters(self):
        self.coincidence_array = (c_int32*19)()
        rs = self.dll_lib.TDC_getCoincCounters(self.coincidence_array)
        if not rs:
            print("Coincidences calculated for {}ms".format(str(self.expTime.value)))
        else:
            print(">>> Getting Coincidence Counters : ")
            self.switch(rs)

    def getDataLost(self):
        """ LED signalling
        """
        self.data_loss = c_int8()
        print(">>> Checking for data loss : ", end="")
        rs = self.dll_lib.TDC_getDataLost(self.data_loss)
        self.switch(rs)
        if rs:
            warnings.warn("Possible data loss! Make sure PC is able to receive data.")
