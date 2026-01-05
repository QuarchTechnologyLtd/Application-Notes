#!/usr/bin/env python
import logging
import subprocess
import threading
import time
from datetime import datetime
from timeit import default_timer as timer
import struct

class HdStreamer:
    def __init__(self, quarch_device):
        self.__my_device = quarch_device
        self.__socket_recv_size = 512
        self.__header_valid = False
        self.__stream_average_rate = None
        self.__stream_header_version = None
        self.__stream_header_channels = None
        self.__header_size = 4
        self.__sync_packet_active = False
        self.__stream_end_status = -1  # -1 = not status set
        self.__old_socket_timeout = None
        self.__request_stop = False
        self.__mega_buffer = None
        self.__data_store_pos = 0
        self.__next_data_pos = 0
        self.__stream_decode_state = None
        self.__stream_decode_prev_state = None
        self.__stream_stop_ordered = False
        self.calculate_power = False
        self.__real_time_thread_running = False
        self.dump_complete = False
        self.__save_mode = "post_process"
        self.__csv_file_path = None
        # Members used to buffer and then write to file during the CSV creating process
        self.__write_buffer = ""
        self.__file_stream = None        
        # Decode flags to persist across buffers to track cases where words are split
        self.__flag_word_low = False
        self.__val_word_high = 0
        # Tracks the time of the next stripe to be written
        self.stream_time_pos = 0
        # Socket is buried in a rather ugly way...
        self.__stream_socket = self.__my_device.connectionObj.connection.Connection
        # Data storage for processed output data
        self.processed_data = None
        # Temp holding for data processing the final stripes
        self.__value_time = 0
        self.__value_12v = 0
        self.__value_12i = 0
        self.__value_5v = 0
        self.__value_5i = 0
        self.__value_12p = 0
        self.__value_5p = 0
        self.__value_totp = 0
        self.__isHdPlus = False
        self.__LastValid = False
        self.__Last5V_V = 0
        self.__Last5V_I = 0
        self.__Last12V_V = 0
        self.__Last12V_I = 0
        self.__logger = None
        # Members used for debug logging to .dat file during implementation testing
        self.__debug_file_stream = None
        self.__debug_time_structure = bytearray(8)
        self.__debug_bad_packets = 0

        # State machine setup for the streaming decode.  Provides the state transitions needed for any given channel selection
        # Channel selection is commented in the right. -1 means disabled channel.
        self.__stream_decode = [(-1, -1, -1, -1),  # 0 0 0 0
                                (-1, -1, -1, 3),  # 0 0 0 1
                                (-1, -1, 2, -1),  # 0 0 1 0
                                (-1, -1, 3, 2),  # 0 0 1 1
                                (-1, 1, -1, -1),  # 0 1 0 0
                                (-1, 3, -1, 1),  # 0 1 0 1
                                (-1, 2, 1, -1),  # 0 1 1 0
                                (-1, 2, 3, 1),  # 0 1 1 1
                                (0, -1, -1, -1),  # 1 0 0 0
                                (3, -1, -1, 0),  # 1 0 0 1
                                (2, -1, 0, -1),  # 1 0 1 0
                                (2, -1, 3, 0),  # 1 0 1 1
                                (1, 0, -1, -1),  # 1 1 0 0
                                (1, 3, -1, 0),  # 1 1 0 1
                                (1, 2, 0, -1),  # 1 1 1 0
                                (1, 2, 3, 0)]  # 1 1 1 1

        # Check this is a QTL1944 (HD) module code hardware
        if ("1944" not in self.__my_device.sendCommand("*serial?")):
            raise ValueError(
                "Attached device not supported.  This code only supports HD power modules (QTL1999 / QTL1995)")
                
        # Check if this is an HD plus module, which means PAM style block/packet based encoding
        if ("HD PLUS" in self.__my_device.sendCommand("hello?").upper()):
            self.__isHdPlus = True
            # Mark header size as undefined at setup time (size is dynamic)
            self.__header_size = -1

    # Gets the next state for the decode state machine
    def __get_next_decode_state(self, current_state):
        return self.__stream_decode[self.__stream_header_channels][current_state]

    @property
    def _average_rate(self):
        average_rates = {
            "0": 250000,
            "2": 125000,
            "4": 62500,
            "8": 31250,
            "16": 15625,
            "32": 7812.5,
            "64": 3906.25,
            "128": 1953.125,
            "256": 976.5625,
            "1k": 488.28125,
            "2k": 244.14062,
            "4k": 122.07031,
            "8k": 61.03515,
            "16k": 30.51758,
            "32k": 15.25879
        }
        return average_rates

    def start_stream(self, seconds, csv_file_path, logger, fio_command=None, save_mode="post_process", debug_data_dump=False):

        self.__save_mode = save_mode
        self.__csv_file_path = csv_file_path
        self.__logger = logger
        self.__debug_data_dump = debug_data_dump

        # Open debug raw dump file if requested
        if (self.__debug_data_dump == True):
            self.__debug_file_stream = open(csv_file_path + ".dat", 'wb')
            # Write the fixed header bytes required            
            self.__debug_file_stream.write(bytearray(b'\x00\x02'))
            
        # Work out how many bytes will be in a stripe, based on channel enables
        bytes_per_stripe = self._get_bytes_per_stripe()

        # Get the averaging rate
        stripes_per_second = self._get_average_rate()

        # Allocate the full buffer now, with 5% additional
        mega_buffer_len = int(seconds * stripes_per_second * bytes_per_stripe * 1.05)

        # Create initial receive buffers, avoiding repeat allocation                
        data, data_buffer_len, len_data = self._create_initial_receive_buffers(logger, mega_buffer_len)

        myproc = self._start_stream_and_start_processing_thread(fio_command, logger, save_mode)

        self._process_stream_data(data, data_buffer_len, len_data, seconds)

        if fio_command is not None:
            # If this while loop is entered, the stream time is too short for the FIO job.
            while myproc.poll() is None:
                print("Waiting for FIO to finish..")
                logger.info(datetime.now().isoformat() + "\t: Waiting for FIO to finish...")
                time.sleep(1)

        if save_mode == "post_process":
            self._post_processing(csv_file_path, logger)

        elif save_mode == "real_time":
            self._real_time_monitoring(logger)
        else:
            raise ValueError("Invalid save mode: " + save_mode)

    def _start_stream_and_start_processing_thread(self, fio_command, logger, save_mode):
        myproc = None
        # Tell the PPM we are stream capable, to unlock the stream function
        self.__my_device.sendCommand("conf stream enable on")
        # Start stream
        self.__my_device.sendCommand("rec stream")
        logger.info(datetime.now().isoformat() + "\t: Stream Started")
        if fio_command:
            print("Starting FIO workload")
            fio_formatted_cmd = fio_command.split(" ")
            myproc = subprocess.Popen(fio_formatted_cmd)
            logger.info(datetime.now().isoformat() + "\t: FIO workload Started")
        # Start threaded real-time save process if requested
        if save_mode == "real_time":
            proc_thread = threading.Thread(name='save_worker', target=self.__decode_stream_section_worker)
            proc_thread.start()
        return myproc

    def _real_time_monitoring(self, logger):
        # Wait here until the thread based save is complete
        real_time_start_time = time.time()
        while self.__real_time_thread_running:
            self.dump_complete = True
            logger.info(datetime.now().isoformat() + "\t: Waiting for save to complete")
            time.sleep(1)
        real_time_end_time = time.time()
        wait_time = real_time_end_time - real_time_start_time
        logger.info("Process complete! Waited {} seconds for thread based save to complete".format(wait_time))

    def _post_processing(self, csv_file_path, logger):
        csv_start_time = time.time()
        print("Post-processing data to CSV")
        logger.info(datetime.now().isoformat() + "\t: Started CSV post-processing")
        # Stream has now fully completed, write the data to csv, as required
        self.__prepare_csv_file(csv_file_path)
        # Process the buffered data
        self.__decode_stream_data_buffer(memoryview(self.__mega_buffer))
        logger.info(datetime.now().isoformat() + "\t: Closing file stream")
        self.__file_stream.close()
        if (self.__debug_file_stream is not None):
            self.__debug_file_stream.close()
        logger.info(datetime.now().isoformat() + "\t: Completed CSV post-processing, exiting")
        csv_done_time = time.time()
        processing_time = csv_done_time - csv_start_time
        logger.info("CSV created, process complete! Processing took {} seconds".format(processing_time))

    def _process_stream_data(self, data, data_buffer_len, len_data, seconds):
        # Loop to get all data in the stream, not returning until done
        stream_start = timer()
        while self.__stream_end_status == -1:
            # Read packet size first
            got_bytes = self.__stream_socket.recv_into(memoryview(len_data), 2)
            if (got_bytes != 2):
                raise Exception ("Unable to read data block length")

            if not len_data:
                break
            data, len_bytes = self._send_and_receive_data(data, data_buffer_len, len_data)

            # If packet capture debug is enabled, process it here
            if (self.__debug_file_stream is not None):
                # Write the 8 byte time in nS since the last packet.  Unused for now, so set to 0
                self.__debug_file_stream.write(self.__debug_time_structure)
                # Write the 4 byte Int32 form packet length
                byte_string = struct.pack(">I", len_bytes)
                self.__debug_file_stream.write(byte_string)
                # Finally the data block is written
                self.__debug_file_stream.write(data[:len_bytes])

            # If header is not valid, assume this is the stream header and process it (one time operation at start)
            if not self.__header_valid:
                # Ensure we pass only the valid data to the processing function as the buffer can be sized larger
                self.__process_stream_header(data, len_bytes)
                self.__header_valid = True
                # HD has a 4 byte header, HD Plus is dynamic and fills the first block returned
                if (self.__header_size > 0):
                    len_bytes -= self.__header_size
                else:
                    len_bytes -= len_bytes

                # If we're done after the header bytes, continue and skip processing
                if len_bytes == 0:
                    continue

            self._process_data_and_send_ack(data, len_bytes)

            # calculate end time
            if timer() - stream_start > seconds:
                if not self.__request_stop:
                    logging.debug(datetime.now().isoformat() + "\t: Stream time complete, halting")
                    self.__request_stop = True

    def _process_data_and_send_ack(self, data, len_bytes):
        # Odd byte count means a status byte at the end which must be processed
        if (len_bytes & 1) != 0:
            self.__handle_status_byte(data[len_bytes - 1])
            len_bytes -= 1
        if len_bytes > 0:
            # Store data into the stream mega buffer, at the end of current data (no processing during the stream,
            # to avoid any performance hit)
            self.__mega_buffer[self.__data_store_pos:self.__data_store_pos + len_bytes] = data[0:len_bytes]
            self.__data_store_pos += len_bytes
        # Perform ACK sequence as required by the current status
        if self.__sync_packet_active:
            self.__send_sync()
            self.__sync_packet_active = False

            # End after set time

    # Handles the receipt of a single 'block' of data.   2 bytes are passed in from the previous read, to
    # tell us how big the block is.  Outside of a timeout, we cannot leave here until the full block is read
    # as otherwise we would be out of step for the next block
    def _send_and_receive_data(self, data, data_buffer_len, len_data):
        read_bytes = 0
        len_bytes = int(len_data[0] + (len_data[1] << 8))

        # If the current buffer is not large enough, re-allocate with a bit of headroom
        if len_bytes > data_buffer_len:
            data = bytearray(len_bytes + 10)

        # Loop until the entire stream block is read
        while (read_bytes < len_bytes):
            # Receive from the socket into the end of the current data
            received = self.__stream_socket.recv_into(memoryview(data)[read_bytes:], (len_bytes - read_bytes))
            read_bytes += received               
        
        # Force an TCP ACK by sending a stub packet, used to speed up the data flow on devices with low TCP RAM
        self.__stream_socket.send(bytearray(b'\x02\x00\xff\xff'))
        return data, len_bytes

    def _create_initial_receive_buffers(self, logger, mega_buffer_len):
        self.__mega_buffer = bytearray(0)  # mega_buffer_len)
        logger.info(datetime.now().isoformat() + "\t: Init megabuffer as length: " + str(mega_buffer_len))
        self.__data_store_pos = 0
        data_buffer_len = 1024
        data = bytearray(data_buffer_len)
        len_data = bytearray(2)
        return data, data_buffer_len, len_data

    def _get_average_rate(self):
        ave_rate_str = self.__my_device.sendCommand("rec:ave?")
        ave_rate = ave_rate_str.split(':')[0].strip()
        if ave_rate in self._average_rate:
            stripes_per_second = self._average_rate[ave_rate]
        else:
            raise ValueError("Unknown averaging rate response: " + ave_rate_str)
        return stripes_per_second

    def _get_bytes_per_stripe(self):
        bytes_per_stripe = 0
        if ("ON" in self.__my_device.sendCommand("rec:5v:volt:enable?")):
            bytes_per_stripe += 2
        if ("ON" in self.__my_device.sendCommand("rec:12v:volt:enable?")):
            bytes_per_stripe += 2
        if ("ON" in self.__my_device.sendCommand("rec:5v:current:enable?")):
            bytes_per_stripe += 4
        if ("ON" in self.__my_device.sendCommand("rec:12v:current:enable?")):
            bytes_per_stripe += 4
        return bytes_per_stripe

    def __prepare_csv_file(self, path):
        self.__file_stream = open(path, 'w')
        self.__logger.info(datetime.now().isoformat() + "\t: Preparing CSV file headers")

        # Write header (based on active channels)
        self.__file_stream.write("Time us,")
        if (self.__stream_header_channels & 0x0008) != 0:  # 5V V
            self.__file_stream.write("5V voltage mV,")
        if (self.__stream_header_channels & 0x0004) != 0:  # 5V I
            self.__file_stream.write("5V current uA,")
        if (self.__stream_header_channels & 0x0002) != 0:  # 12V V
            self.__file_stream.write("12V voltage mV,")
        if (self.__stream_header_channels & 0x0001) != 0:  # 12V I
            self.__file_stream.write("12V current uA,")
        if (self.__stream_header_channels & 0x0008 != 0 and self.__stream_header_channels & 0x0004 != 0):
            self.__file_stream.write("5V power uW,")
        if (self.__stream_header_channels & 0x0002 != 0 and self.__stream_header_channels & 0x0001 != 0):
            self.__file_stream.write("12V power uW,")
        if (
                self.__stream_header_channels & 0x0008 != 0 and self.__stream_header_channels & 0x0004 != 0 and self.__stream_header_channels & 0x0002 != 0 and self.__stream_header_channels & 0x0001 != 0):
            self.__file_stream.write("Total power uW")
        self.__file_stream.write("\r")

    # Processes each packet coming in
    def __process_packet(self, data, data_len):
        # If header is not valid, assume this is the stream header and process it
        if (self.__header_valid == False):
            self.__process_stream_header(data, data_len)
            self.__header_valid = True

            # process remainder as regular stream data
            if (len(data) > self.__header_size):
                data = data[self.__header_size:]
                self.__process_stream_data(data)
                # Else process as a regular stream data packet
        else:
            self.__process_stream_data(data)

    # Handles the status byte and sets actions based on it
    def __handle_status_byte(self, status_byte):

        # Termination request on 0-2
        if (status_byte >= 0 and status_byte < 3):
            self.__stream_end_status = status_byte
            logging.debug(datetime.now().isoformat() + "\t: Stream download from PPM complete: " + str(status_byte))
        # No data yet on 3
        elif (status_byte == 3):
            logging.debug(datetime.now().isoformat() + "\t: Status byte - no data: " + str(status_byte))
            pass
        # Sync packet, must be replied to on 7
        elif (status_byte == 7):
            logging.debug(datetime.now().isoformat() + "\t: Status byte - sync: " + str(status_byte))
            self.__sync_packet_active = True
        # Else bad status byte
        else:
            logging.debug(datetime.now().isoformat() + "\t: Status byte - unexpected: " + str(status_byte))
            print ("BAD STATUS: " + str(status_byte))

    # Processing for stream data
    def __process_stream_data(self, data):
        data_len = len(data)

        # Odd byte count means a status byte at the end
        if ((data_len & 1) != 0):
            self.__handle_status_byte(data[data_len - 1])
            data_len -= 1

        if (data_len > 0):
            # Store data into the stream mega buffer, at the end of current data (no processing during the stream, to avoid any performance hit)
            # mem_view = memoryview(self.__mega_buffer)[self.__data_store_pos:]
            self.__mega_buffer[self.__data_store_pos:self.__data_store_pos + data_len] = data[0:data_len]
            # mem_view[:] = bytes(b'hello')#data[0:data_len]
            self.__data_store_pos += data_len

        # Perform ACK sequence as required by the current status
        if (self.__sync_packet_active):
            self.__send_sync()
            self.__sync_packet_active = False

    # Send an ACK packet to the SYNC request, allowing streaming to continue
    def __send_sync(self):
        if (self.__request_stop == True):
            self.__my_device.sendCommand("rec stop")
            if (self.__stream_stop_ordered == False):
                self.__stream_stop_ordered = True
                print ("Stopping stream, recording time is complete")
        self.__stream_socket.send(bytearray(b'\x02\x00\xff\x01'))

    # Processing for stream header
    def __process_stream_header(self, data, len_bytes):
        buffer_index = 0
        string_size = 0
        group_count = 0
        # HD plus header is a more complex format
        if (self.__isHdPlus):
            self.__logger.info(datetime.now().isoformat() + "\t: HD PPM Plus header found")
            self.__logger.info(datetime.now().isoformat() + "\t: header length: " + str(len_bytes))
            self.__stream_header_version = data[buffer_index]
            buffer_index += 2
            if (self.__stream_header_version == 1):
                raise Exception ("HD plus decode requires a later header version")
            elif (self.__stream_header_version == 2):
                # Jump to string table size
                buffer_index += 6
                string_size = data[buffer_index]
                buffer_index += 1
                string_size += data[buffer_index] * 256
                buffer_index += 1
                # Jump to group count
                group_count = data[buffer_index]
                buffer_index += 2
                if (group_count > 1):
                    raise Exception ("More than one hardware stream group is not supported!")
                # Get the channel count word
                channel_count = data[buffer_index]
                buffer_index += 1
                channel_count += data[buffer_index] * 256
                buffer_index += 1
                if (channel_count != 4):
                    raise Exception ("PPM Plus Decode only currently supported with all channels enabled!")
                buffer_index += 4
                # Store the averaging rate
                self.__stream_average_rate = data[buffer_index]
                # Mark all channels enabled
                self.__stream_header_channels = 0x0F
            else:
                raise Exception("HD plus decode does not support header version above 2")


        # Original HD header is a small number of bytes indicating the channels and averaging rate
        else:
            self.__stream_header_version = data[0]
            # Future code may need header size to change based on version here
            # data[1] is a reserved padding byte
            self.__stream_header_channels = data[2]
            self.__stream_average_rate = data[3]

        # Calculate the initial stream state given the available channels
        self.__init_stream_state(self.__stream_header_channels & 0x0F)

        # Prepare the output file for real time write if required
        if (self.__file_stream is None and self.__save_mode == "real_time"):
            logging.debug(datetime.now().isoformat() + "\t: Opened CSV for real-time processing")
            self.__prepare_csv_file(self.__csv_file_path)

    # Set the initial decode state, given the channels that will be returned.  This comes from the stream header
    def __init_stream_state(self, channel_enable):
        if (channel_enable & 0x0008) != 0:  # 5V V
            self.__stream_decode_state = 0

        elif (channel_enable & 0x0004) != 0:  # 5V I
            self.__stream_decode_state = 1

        elif (channel_enable & 0x0002) != 0:  # 12V V
            self.__stream_decode_state = 2

        elif (channel_enable & 0x0001) != 0:  # 12V I
            self.__stream_decode_state = 3

        if self.__stream_decode_state == -1:
            raise ValueError('Device header indicates that no channels are enabled for streaming')

    # Makes sure this looks like a header (basic check only)
    def __is_header_valid(self, data):
        ret_val = False

        if (len(data) > 1):
            if (data[0] == 5):
                ret_val = True

        return ret_val

    # Converts a buffer element to word
    def __stream_buffer_to_word(self, buffer):
        wordVal = int.from_bytes(buffer, byteorder='little', signed=False)
        # wordVal = (_struct.unpack( '<h', buffer)[0])
        wordVal = wordVal & 0x3fff

        return wordVal

    # Thread worker function, used to process stream data while recording
    def __decode_stream_section_worker(self):
        self.__real_time_thread_running = True

        buffer_needed = 1500
        process_size = 512      # HD plus requirement, decide in stream blocks

        logging.debug(datetime.now().isoformat() + "\t: Real-time save worker: Started")

        # While there is data to process
        while (self.__data_store_pos >= self.__next_data_pos and self.dump_complete == False):

            # If there are more than x bytes to process, process a block
            next_data = self.__next_data_pos
            store_pos = self.__data_store_pos
            if (store_pos - next_data > buffer_needed):
                # logging.debug(datetime.now().isoformat() + "\t: Real-time save worker: Decode " + str(next_data) + "-" + str(next_data+process_size))
                self.__decode_stream_data_buffer(self.__mega_buffer[next_data:next_data + process_size])
                self.__next_data_pos = (next_data + process_size)
            # Else wait a little for more to come along
            else:
                time.sleep(0.25)

        logging.debug(datetime.now().isoformat() + "\t: Real-time save worker: Final processing")

        # Process all remaining bytes
        next_data = self.__next_data_pos
        self.__decode_stream_data_buffer(self.__mega_buffer[next_data:])

        logging.debug(datetime.now().isoformat() + "\t: Real-time save worker: Closing")

        self.__real_time_thread_running = False

    # Decodes a buffer of streaming data measurements.  The header and and additional transport bytes must have been
    # removed by this point, leaving only pure measurement data.  The decode uses a state machine (PPM), initialised by the
    # header bytes at the start of streaming.  Multiple calls can be made provided sequential buffers of valid data
    # are given.  HD PPM Plus decode path splits here
    def __decode_stream_data_buffer(self, buffer):
        i = 0
        buffer_len = len(buffer)

        # Note: Fixed HD 4uS per stripe base measurement rate
        ave_multiplier = (pow(self.__stream_average_rate, 2) * 4)
        if (ave_multiplier == 0):
            ave_multiplier = 4        
        
        # HD Plus format requires alternate processing, as the format is different
        if (self.__isHdPlus == True):            
            self.__decode_hdplus_stream_data_buffer(buffer, ave_multiplier)
        else:
            while i < buffer_len:
                to_buffer = False
                i, to_buffer = self._process_stream_decode_state(buffer, i, to_buffer)

                if not self.__flag_word_low:
                    self.__stream_decode_prev_state = self.__stream_decode_state
                    self.__stream_decode_state = self.__get_next_decode_state(self.__stream_decode_state)

                # If meas ready to be output
                if to_buffer:
                    if self.__stream_decode_state <= self.__stream_decode_prev_state:
                        self._calculate_time_and_power_values(ave_multiplier)
                    
    # HD Plus decode section, intended to take 1 512 byte block at a time but other sizes should work provided
    # the data is packed with no additional bytes
    def __decode_hdplus_stream_data_buffer(self, buffer, ave_multiplier):
        buffer_len = len(buffer)
        access_byte = 0
        repeat_count = 0
        packet_id = 0
        self.__value_5v = 0
        self.__value_5i = 0
        self.__value_12v = 0
        self.__value_12i = 0
        temp_decode = 0
        file_string = ""        
        
        # Iterate and process out stripes, we have to decode the packet types
        # in full to do this here!
        while (access_byte < buffer_len):
            
            # Switch on the packet ID
            packet_id = buffer[access_byte^1]
            
            # Absolute packet
            if (packet_id == 4):
                access_byte += 2
                
                # 15 bit signed voltage
                self.__value_5v = buffer[access_byte ^ 1]
                self.__value_5v = self.__value_5v << 8
                access_byte += 1
                self.__value_5v += buffer[access_byte ^ 1]
                self.__value_5v = self.__value_5v >> 1
                # Handle negative numbers (hard-coded to PPM for speed)
                if (self.__value_5v & 0x4000) != 0:
                    self.__value_5v = self.__value_5v - 0x8000

                # 25 bit signed current (starting bottom bit of last byte)
                self.__value_5i = buffer[access_byte ^ 1]
                self.__value_5i = self.__value_5i & 0x01
                self.__value_5i = self.__value_5i << 8
                access_byte += 1
                self.__value_5i += buffer[access_byte ^ 1]
                self.__value_5i = self.__value_5i << 8
                access_byte += 1
                self.__value_5i += buffer[access_byte ^ 1]
                self.__value_5i = self.__value_5i << 8
                access_byte += 1
                self.__value_5i += buffer[access_byte ^ 1]
                # Handle negative numbers (hard-coded to PPM for speed)
                if (self.__value_5i & 0x1000000) != 0:
                    self.__value_5i = self.__value_5i - 0x2000000

                # 15 bit signed voltage
                access_byte += 1
                self.__value_12v = buffer[access_byte ^ 1]
                self.__value_12v = self.__value_12v << 8
                access_byte += 1
                self.__value_12v += buffer[access_byte ^ 1]
                self.__value_12v = self.__value_12v >> 1
                # Handle negative numbers (hard-coded to PPM for speed)
                if (self.__value_12v & 0x4000) != 0:
                    self.__value_12v = self.__value_12v - 0x8000

                # 25 bit signed current (starting bottom bit of last byte)
                self.__value_12i = buffer[access_byte ^ 1]
                self.__value_12i = self.__value_12i & 0x01
                self.__value_12i = self.__value_12i << 8
                access_byte += 1
                self.__value_12i += buffer[access_byte ^ 1]
                self.__value_12i = self.__value_12i << 8
                access_byte += 1
                self.__value_12i += buffer[access_byte ^ 1]
                self.__value_12i = self.__value_12i << 8
                access_byte += 1
                self.__value_12i += buffer[access_byte ^ 1]
                # Handle negative numbers (hard-coded to PPM for speed)
                if (self.__value_12i & 0x1000000) != 0:
                    self.__value_12i = self.__value_12i - 0x2000000

                # Copy current values to last and flag we have a value set of last values
                # This is needed for repeats and deltas later
                self.__Last5V_V = self.__value_5v
                self.__Last5V_I = self.__value_5i
                self.__Last12V_V = self.__value_12v
                self.__Last12V_I = self.__value_12i
                self.__LastValid = True
                # Flag one value to process
                repeat_count = 1

                # Advance to next byte at end
                access_byte+=1
            
            # Blank packet - skip over
            elif (packet_id == 8):
                # Skip the number of bytes specified in the packet
                access_byte+=1
                access_byte += buffer[access_byte^1] + 1
                repeat_count = 0
            
            # Trigger packet - skip over
            elif (packet_id == 10):
                # Skip the fixed size packet
                access_byte += 2
                repeat_count = 0

            # Delta data packet
            elif (packet_id == 12):

                # Get length byte
                access_byte += 2
                temp_decode = buffer[access_byte ^ 1]
                temp_decode &= 0xF0
                temp_decode = temp_decode >> 4
                if temp_decode != 10:
                    # Halt/error on unexpected data length
                    raise Exception ("Invalid length for delta paket!")

                # Decode 5v volt, 10 bits long starting lower nibble of first byte
                self.__value_5v = buffer[access_byte ^ 1]
                self.__value_5v = self.__value_5v & 0x0F
                self.__value_5v = self.__value_5v << 6
                access_byte += 1
                temp_decode = buffer[access_byte ^ 1]
                temp_decode = temp_decode >> 2
                self.__value_5v += temp_decode

                # Handle negative numbers (hard-coded to PPM for speed)
                if (self.__value_5v & 0x0200) != 0:
                    self.__value_5v = self.__value_5v - 0x0400

                # Decode 5v current, 10 bits long starting lower 2 bits of current byte
                self.__value_5i = buffer[access_byte ^ 1]
                self.__value_5i = self.__value_5i & 0x03
                self.__value_5i = self.__value_5i << 8
                access_byte += 1
                self.__value_5i += buffer[access_byte ^ 1]

                if (self.__value_5i & 0x0200) != 0:
                    self.__value_5i = self.__value_5i - 0x0400

                # Decode 12v volt, 10 bits long starting on a full byte
                access_byte += 1
                self.__value_12v = buffer[access_byte ^ 1]
                self.__value_12v = self.__value_12v << 2
                access_byte += 1
                temp_decode = buffer[access_byte ^ 1]
                temp_decode = temp_decode >> 6
                temp_decode &= 0x03
                self.__value_12v += temp_decode

                # Handle negative numbers (hard-coded to PPM for speed)
                if (self.__value_12v & 0x0200) != 0:
                    self.__value_12v = self.__value_12v - 0x0400

                # Decode 12v current, 10 bits long starting lower 6 bits of current byte
                self.__value_12i = buffer[access_byte ^ 1]
                self.__value_12i &= 0x3F
                self.__value_12i = self.__value_12i << 2
                access_byte += 1
                temp_decode = buffer[access_byte ^ 1]
                temp_decode = temp_decode >> 4
                temp_decode &= 0x0F
                self.__value_12i += temp_decode

                # Handle negative numbers (hard-coded to PPM for speed)
                if (self.__value_12i & 0x0200) != 0:
                    self.__value_12i = self.__value_12i - 0x0400

                # Skip if to absolute data yet
                if self.__LastValid:
                    # New value is current plus last, then store the updated last value
                    self.__value_5v += self.__Last5V_V
                    self.__Last5V_V = self.__value_5v
                    self.__value_5i += self.__Last5V_I
                    self.__Last5V_I = self.__value_5i
                    self.__value_12v += self.__Last12V_V
                    self.__Last12V_V = self.__value_12v
                    self.__value_12i += self.__Last12V_I
                    self.__Last12V_I = self.__value_12i
                    repeat_count = 1
                else:
                    repeat_count = 0

                # Advance to next byte at end
                access_byte+=1

            # Repeat data packet
            elif (packet_id == 14):
                # Skip over group count
                access_byte += 2
                # Store the repeat count as the number of last values to repeat
                repeat_count = buffer[access_byte^1]
                access_byte+=1

                # Can't process if no absolute data yet
                if (self.__LastValid == False):
                    repeat_count = 0
            # Case for bad packet ID
            else:
                # Log error to the file
                logging.info(datetime.now().isoformat() + "\t: Corrupt stream: ID=" + str(packet_id))
                logging.info(datetime.now().isoformat() + "\t: Corrupt stream: Access Pos=" + str(access_byte))
                logging.info(datetime.now().isoformat() + "\t: Corrupt stream: Length=" + str(buffer_len))
                # Log the bad block to the console
                for i in range(0, len(buffer), 16):
                    row = buffer[i:i+16]
                    swapped_row = bytes(reversed(row))
                    hex_row = ' '.join([f"{byte:02x}" for byte in swapped_row])
                    print(hex_row)

                # Fail after 3 bad packets to simplify debug
                if (self.__debug_bad_packets > 3):
                    # CLose the debug file to make sure we do not lose final data before raising an exception
                    if (self.__debug_file_stream is not None):
                        self.__debug_file_stream.close()
                    raise Exception ("Invalid packet ID in stream, data is corrupt: " + str(packet_id))
                else:
                    self.__debug_bad_packets += 1
            # Process if data is ready
            if (repeat_count > 0):
                # Calculate time and power values
                value_5p = (self.__value_5v * self.__value_5i) / 1000
                value_12p = (self.__value_12v * self.__value_12i) / 1000
                value_totp = value_5p + value_12p

                # Write the line(s) to file
                for x in range (repeat_count):
                    file_string = str(self.stream_time_pos) + "," + str(self.__value_5v) + "," + str(self.__value_5i) + "," + str(self.__value_12v) + "," + str(self.__value_12i) + "," + str(value_5p) + "," + str(value_12p) + "," + str(value_totp) + "\r"
                    self.__file_stream.write(file_string)
                    self.stream_time_pos = self.stream_time_pos + ave_multiplier

    def _process_stream_decode_state(self, buffer, i, to_buffer):
        if self.__stream_decode_state == 0:
            # scale 5V V and write to file
            self.__value_5v = (int.from_bytes(buffer[i:i + 2], byteorder='little', signed=False) & 0x3FFF)
            to_buffer = True
            i = i + 2
        elif self.__stream_decode_state == 1:
            # scale 5V I and write to file
            to_buffer = self._scale_5v_and_write_to_file(buffer, i, to_buffer)
            i = i + 2
        elif self.__stream_decode_state == 2:
            # scale 12V V and write to file
            self.__value_12v = (int.from_bytes(buffer[i:i + 2], byteorder='little', signed=False) & 0x3FFF)
            to_buffer = True
            i = i + 2
        elif self.__stream_decode_state == 3:
            # scale 12V I and write to file
            to_buffer = self._scale_12v_and_write_to_file(buffer, i, to_buffer)
            i = i + 2
        return i, to_buffer

    def _scale_12v_and_write_to_file(self, buffer, i, to_buffer):
        if self.__flag_word_low:
            self.__flag_word_low = False
            self.__value_12i = (self.__val_word_high * 4096)
            self.__value_12i = self.__value_12i + (
                    int.from_bytes(buffer[i:i + 2], byteorder='little', signed=False) & 0x3FFF)
            to_buffer = True
        else:
            self.__flag_word_low = True
            self.__val_word_high = (int.from_bytes(buffer[i:i + 2], byteorder='little', signed=False) & 0x3FFF)
        return to_buffer

    def _scale_5v_and_write_to_file(self, buffer, i, to_buffer):
        if self.__flag_word_low:
            self.__flag_word_low = False
            self.__value_5i = (self.__val_word_high * 4096)
            self.__value_5i = self.__value_5i + (
                    int.from_bytes(buffer[i:i + 2], byteorder='little', signed=False) & 0x3FFF)
            to_buffer = True
        else:
            self.__flag_word_low = True
            self.__val_word_high = (int.from_bytes(buffer[i:i + 2], byteorder='little', signed=False) & 0x3FFF)
        return to_buffer

    def _calculate_time_and_power_values(self, ave_multiplier):
        # Calculate time and power values
        value_time = self.stream_time_pos
        value_5p = (self.__value_5v * self.__value_5i) / 1000
        value_12p = (self.__value_12v * self.__value_12i) / 1000
        value_totp = value_5p + value_12p
        self.__file_stream.write(
            str(value_time) + "," + str(self.__value_5v) + "," + str(self.__value_5i) + "," + str(
                self.__value_12v) + "," + str(self.__value_12i) + "," + str(value_5p) + "," + str(
                value_12p) + "," + str(value_totp) + "\r")
        # Next stripe
        self.stream_time_pos = self.stream_time_pos + ave_multiplier
