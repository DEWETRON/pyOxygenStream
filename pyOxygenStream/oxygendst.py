#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright DEWETRON GmbH 2018
"""

import socket
import struct
import sys
import getopt
import numpy as np
import xml.etree.ElementTree as ET
import logging

# General data stream definitions
DT_PROTOCOL_VERSION = 0x01050000
DT_WELCOME_MSG_SIZE = 64
DT_START_TOKEN = "OXYGEN<<".encode()
DT_END_TOKEN = ">>OXYGEN".encode()
DT_TOKEN_SIZE = 8
DT_PACKET_HEADER_FMT = "=8sI"
DT_PACKET_HEADER_SIZE = 12
DT_SUBPACKET_HEADER_FMT = "=2I"
DT_SUBPACKET_HEADER_SIZE = 8
DT_PACKET_INFO_FMT = "=6I"
DT_SYNC_FIXED_FMT = "=3IQd"
DT_SYNC_FIXED_SIZE = 28
DT_ASYNC_FIXED_FMT = "=3Id"
DT_ASYNC_FIXED_SIZE = 20

# Sub packet types
SBT_PACKET_INFO = 0x00000001
SBT_XML_CONFIG = 0x00000002
SBT_SYNC_FIXED = 0x00000003
SBT_SYNC_VARIABLE = 0x00000004
SBT_ASYNC_FIXED = 0x00000005
SBT_ASYNC_VARIABLE = 0x00000006
SBT_PACKET_FOOTER = 0x00000007

# Stream Status IDs
ST_FIRST_PACKET = 0x00000001
ST_LAST_PACKET = 0x00000002
ST_NORMAL_PACKET = 0x00000000
ST_ERROR_PACKET = 0x10000000

DT_DATA_TYPE = {
    0:  "int8",
    1:  "uint8",
    2:  "int16",
    3:  "uint16",
    4:  "int24",
    5:  "uint24",
    6:  "int32",
    7:  "uint32",
    8:  "int64",
    9:  "uint64",
    10: "float32",
    11: "float64",
    12: "complex64",
    13: "complex128",
    14: False,
    15: False
}

def recvFixedSize(s, size):
    data = bytearray(size)
    view = memoryview(data)
    data_to_read = size
    while data_to_read:
        num_bytes = s.recv_into(view, data_to_read)
        view = view[num_bytes:]
        data_to_read -= num_bytes
    return data

def parseargs(argv):
    """
    Parse Input Arguments if run itself

    Parameters
    ----------
    argv : str
        -a <address> -p <port>

    Returns
    -------
    address : str
        IP Host.
    port : int
        IP Port.

    """
    address = '127.0.0.1'
    port = 10003
    try:
        opts, args = getopt.getopt(argv, "ha:p:", ["address=", "port="])
    except getopt.GetoptError:
        print('dt_client.py -a <address> -p <port>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('dt_client.py -a <address> -p <port>')
            sys.exit()
        elif opt in ("-a", "--address"):
            address = arg
        elif opt in ("-p", "--port"):
            port = int(arg)
    return address, port


class DtPacketInfo:
    """ Packet Info Object
    """
    protocol_version = 0
    stream_id = 0
    sequence_number = 0
    stream_status = 0
    seed = 0
    number_of_subpackets = 0


class DtXmlSubPacket:
    """ XML Object
    """
    xml_content = ''
    xml_content_size = 0


class DtChannelSyncFixed:
    """ Sync Channel's Information Object
    """
    channel_data_type = 0
    channel_dimension = 0
    number_samples = 0
    timestamp = 0
    timebase_frequency = 0
    sample_data = 0
    sample_data_size = 0


class DtChannelAsyncFixed:
    """ Async Channel's Information Object
    """
    channel_data_type = 0
    channel_dimension = 0
    number_samples = 0
    timebase_frequency = 0
    sample_data = 0
    sample_data_size = 0


class OxygenStreamReceiver:
    """ Oxygen Stream Receiver Object to receive one stream
    """
    def __init__(self, timeout = 5.0):
        self.timeout = timeout
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.struct_header = struct.Struct(DT_PACKET_HEADER_FMT)
        self.struct_subpackage_header = struct.Struct(DT_SUBPACKET_HEADER_FMT)
        self.struct_packet_info = struct.Struct(DT_PACKET_INFO_FMT)
        self.packet_info = DtPacketInfo()
        self.packet_xml = []
        self.scaling_info = []
        self.struct_sync_fixed = struct.Struct(DT_SYNC_FIXED_FMT)
        self.struct_async_fixed = struct.Struct(DT_ASYNC_FIXED_FMT)
        self.actual_channel_idx = 0

    def connectTo(self, dt_server, port):
        """ Connect to Oxygen on dt_server:port and read welcome message
        """
        try:
            if self.sock.fileno() == -1:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(self.timeout)
            self.sock.connect((dt_server, port))
        except socket.gaierror as err:
            logging.error("Invalid address: {}".format(err))
            return False
        except OSError as err:
            logging.error("Connection to {:s}:{:d} failed: {}".format(dt_server, port, err))
            return False
        # Read Welcome Message
        welcome_buffer = bytearray(DT_WELCOME_MSG_SIZE)
        bc = self.sock.recv_into(welcome_buffer, DT_WELCOME_MSG_SIZE)
        if bc == 0:
            logging.error("Could not read welcome message")
            return None
        logging.debug("Data stream product name: %s", welcome_buffer.decode())
        return True

    def readPacket(self):
        """ Read one packet and process it afterwards
        """
        # Read packet header
        packet_header_buffer = bytearray(self.sock.recv(DT_TOKEN_SIZE))
        packet_size_buffer = bytearray(DT_PACKET_HEADER_SIZE - DT_TOKEN_SIZE)
        # Search for Packet Start Token
        while packet_header_buffer != DT_START_TOKEN:
            logging.error("Invalid start packet token: " + str(packet_header_buffer))
            try:
                packet_header_buffer += self.sock.recv(1)
            except socket.timeout:
                logging.warning("No data available yet")
                return False
            packet_header_buffer.pop(0)
        # Read Packet Size
        try:
            bc = self.sock.recv_into(packet_size_buffer, DT_PACKET_HEADER_SIZE - DT_TOKEN_SIZE)
        except socket.timeout:
            logging.warning("No data available yet")
            return False
        if (DT_PACKET_HEADER_SIZE - DT_TOKEN_SIZE) != bc:
            logging.error("Could not read packet size")
            return False
        packet_size = int.from_bytes(packet_size_buffer, byteorder='little', signed=False)
        # Read rest of packet
        packet_size -= DT_PACKET_HEADER_SIZE
        #packet_data = bytearray(packet_size)
        packet_data = recvFixedSize(self.sock, packet_size)
        if len(packet_data) != packet_size:
            logging.error("Could not read all packet data")
            return False
        self.channelValue = []
        self.processPacket(packet_data)
        return self.channelValue

    def processPacket(self, packet):
        """ Read and unpack packet content according to subpacket types
        """
        pos = 0
        self.actual_channel_idx = 0
        hit_footer = False
        while pos < len(packet) and not hit_footer:
            sub_packet_size, sub_packet_type = (
                self.struct_subpackage_header.unpack_from(packet, pos))
            if SBT_PACKET_INFO == sub_packet_type:
                self.processPacketInfo(packet,
                                       pos+DT_SUBPACKET_HEADER_SIZE)
            if SBT_XML_CONFIG == sub_packet_type:
                self.processXmlConfig(packet,
                                      pos+DT_SUBPACKET_HEADER_SIZE,
                                      sub_packet_size-DT_SUBPACKET_HEADER_SIZE)
            if SBT_SYNC_FIXED == sub_packet_type:
                self.processSyncFixed(packet,
                                      pos+DT_SUBPACKET_HEADER_SIZE)
            if SBT_ASYNC_FIXED == sub_packet_type:
                self.processAsyncFixed(packet, pos+DT_SUBPACKET_HEADER_SIZE)
            pos += sub_packet_size

    def processPacketInfo(self, packet, pos: int):
        """ Read packet information
        """
        (self.packet_info.protocol_version,
         self.packet_info.stream_id,
         self.packet_info.sequence_number,
         self.packet_info.stream_status,
         self.packet_info.seed,
         self.packet_info.number_of_subpackets) = self.struct_packet_info.unpack_from(packet, pos)
        logging.debug("PacketInfo:")
        logging.debug("  Version:           %0x", self.packet_info.protocol_version)
        logging.debug("  Stream ID:         %d", self.packet_info.stream_id)
        logging.debug("  Seq Number:        %d", self.packet_info.sequence_number)
        logging.debug("  Stream status:     %0x", self.packet_info.stream_status)
        logging.debug("  Stream seed:       %x", self.packet_info.seed)
        logging.debug("  Num sub packets:   %d", self.packet_info.number_of_subpackets)

    def processXmlConfig(self, packet, pos, size):
        """ Read one xml subpackage and add it to the xml list
        """
        sub_packet = DtXmlSubPacket()
        sub_packet.xml_content = packet[pos:pos+size].decode()
        sub_packet.xml_content_size = size
        self.packet_xml.append(sub_packet)
        self.parseScalingXML(sub_packet.xml_content)
        logging.debug("XMLPacket:")
        logging.debug("  xml_content:     %s", sub_packet.xml_content)

    def parseScalingXML(self, xml_content):
        root = ET.fromstring(xml_content)
        if root.tag == "ChannelInfo":
            for child in root:
                factor = child[0].get('factor')
                offset = child[0].get('offset')

                if factor == None:
                    factor = 1

                if offset == None:
                    offset = 0

                self.scaling_info.append((factor, offset))

    def processSyncFixed(self, packet, pos):
        """ Read synchronous samples from packet
        """
        sub_packet = DtChannelSyncFixed()
        (sub_packet.channel_data_type,
         sub_packet.channel_dimension,
         sub_packet.number_samples,
         sub_packet.timestamp,
         sub_packet.timebase_frequency) = self.struct_sync_fixed.unpack_from(packet, pos)
        data = self.readSamples(packet, sub_packet, pos, SBT_SYNC_FIXED)
        timeStamps = np.arange(sub_packet.timestamp, sub_packet.timestamp+sub_packet.number_samples)/sub_packet.timebase_frequency
        data = np.c_[timeStamps, data]
        self.channelValue.append(data)
        logging.debug("DtChannelSyncFixed:")
        logging.debug("  channel idx:         %d", self.actual_channel_idx)
        logging.debug("  channel_data_type:   %d", sub_packet.channel_data_type)
        logging.debug("  channel_dimension:   %d", sub_packet.channel_dimension)
        logging.debug("  number_samples:      %d", sub_packet.number_samples)
        logging.debug("  timestamp:           %d", sub_packet.timestamp)
        logging.debug("  timebase_frequency:  %f", sub_packet.timebase_frequency)
        logging.debug("  first 10 samples:    %s", np.array2string(data[:10]))
        self.actual_channel_idx += 1

    def processAsyncFixed(self, packet, pos):
        """ Read asynchronous samples from packet
        """
        sub_packet = DtChannelAsyncFixed()
        (sub_packet.channel_data_type,
         sub_packet.channel_dimension,
         sub_packet.number_samples,
         sub_packet.timebase_frequency) = self.struct_async_fixed.unpack_from(packet, pos)
        data = self.readSamples(packet, sub_packet, pos, SBT_ASYNC_FIXED)
        if data.size > 0:
            timeStamps = data['f0']/sub_packet.timebase_frequency
            data = np.c_[timeStamps, data['f1']]
        self.channelValue.append(data)
        logging.debug("DtChannelAsyncFixed:")
        logging.debug("  channel idx:         %d", self.actual_channel_idx)
        logging.debug("  channel_data_type:   %d", sub_packet.channel_data_type)
        logging.debug("  channel_dimension:   %d", sub_packet.channel_dimension)
        logging.debug("  number_samples:      %d", sub_packet.number_samples)
        logging.debug("  timebase_frequency:  %f", sub_packet.timebase_frequency)
        logging.debug("  first 10 samples:    %s", np.array2string(data[:10]))
        self.actual_channel_idx += 1

    def readSamples(self, packet, sub_packet, pos, sample_type):
        """ Read data from packet
        """
        dtype = DT_DATA_TYPE[sub_packet.channel_data_type]
        dim = sub_packet.channel_dimension
        num_samples = sub_packet.number_samples
        if dtype:
            if sample_type == SBT_SYNC_FIXED and num_samples > 0:
                if dim == 1:
                    data = self.readSamplesSync(packet, pos, num_samples, dtype)
                else:
                    data = self.readArraySync(packet, pos, dim, num_samples, dtype)

            elif sample_type == SBT_ASYNC_FIXED and sub_packet.number_samples > 0:
                if dim == 1:
                    data = self.readSamplesAsync(packet, pos, num_samples, dtype)
                else:
                    data = self.readArrayAsync(packet, pos, dim, num_samples, dtype)
            else:
                logging.warning("No or invalid data received.")
                data = np.empty(0)

        elif not dtype:
            logging.warning("Data type not supported yet by python")
            data = np.empty(0)
        else:
            data = np.empty(0)

        return data

    def readSamplesSync(self, packet, pos: int, num_samples: int, sample_type: str):

        f = float(self.scaling_info[self.actual_channel_idx][0])
        o = float(self.scaling_info[self.actual_channel_idx][1])

        if sample_type == 'int24':
            data = np.frombuffer(packet, dtype="uint8",  offset=pos+DT_SYNC_FIXED_SIZE, count=num_samples*3)
            data = data[2::3].astype('int8').astype('int32')*2**16+data[1::3].astype('int32')*2**8+data[::3]

        elif sample_type == 'uint24':
            data = np.frombuffer(packet, dtype="uint8",  offset=pos+DT_SYNC_FIXED_SIZE, count=num_samples*3)
            data = data[2::3].astype('int32')*2**16+data[1::3].astype('int32')*2**8+data[::3]

        else:
            data = np.frombuffer(packet, dtype=sample_type, offset=pos+DT_SYNC_FIXED_SIZE, count=num_samples)

        return data.astype('float64') * f + o

    def readArraySync(self, packet, pos: int, dim: int, num_samples: int, sample_type: str):

        data = []
        cur = pos + DT_SYNC_FIXED_SIZE

        for i in range(0, num_samples):
            data.append(np.frombuffer(packet, dtype=sample_type, offset=cur, count=dim))
            cur += dim * np.dtype(sample_type).itemsize

        return data


    def readSamplesAsync(self, packet, pos, num_samples, sample_type):
        data = np.frombuffer(packet, dtype="uint64,"+sample_type,
                             offset=pos+DT_ASYNC_FIXED_SIZE, count=num_samples)

        return data

    def readArrayAsync(self, packet, pos, dim, num_samples, sample_type):

        data = []
        cur = pos + DT_ASYNC_FIXED_SIZE

        for i in range(0, num_samples):
            ts = np.frombuffer(packet, dtype="uint64", offset=cur, count=1)[0]
            cur += np.dtype('uint64').itemsize
            samples = list(np.frombuffer(packet, dtype=sample_type, offset=cur, count=dim))
            samples.insert(0, ts)
            data.append(samples)
            cur += dim * np.dtype(sample_type).itemsize

        return data

    def disconnect(self):
        """ Disconnect from Oxygen stream socket
        """
        self.sock.close()


if __name__ == "__main__":
    a, p = parseargs(sys.argv[1:])

    # Example usage of OxygenStreamReceiver Class
    dt_stream = OxygenStreamReceiver()
    if dt_stream.connectTo(a, p):
        # Read 10 packets
        try:
            while True:
                data = dt_stream.readPacket()
                print("Data: ", data)
        except KeyboardInterrupt:
            dt_stream.disconnect()