from serial.tools.list_ports import comports
from serial.serialutil import SerialException
import tkinter as tk
import threading
import serial

class PortException(Exception):
    def __init__(self, message):
        self.message = message

class PortsCore:
    def __init__(self):
        # Current ports
        self.port1_1: serial.Serial | None = None
        self.port1_2: serial.Serial | None = None
        self.port2_1: serial.Serial | None = None
        self.port2_2: serial.Serial | None = None

        # Ports parameters
        self.baudrate: int = 1000
        self.timeout: int = 1

        # Attrs for receiving ports
        self.receiving_thread: threading.Thread | None = None
        self.is_receiving: bool = False

        # Other params
        self.MESSAGE_END_CHAR = b"\0"

    def send_message(self, chosen_device: int, message: bytes) -> int:
        sent_chars_count: int = 0
        chosen_port: serial.Serial | None = None

        if chosen_device == 1 and self.port1_1 and self.port1_1.is_open:
            chosen_port = self.port1_1
        elif chosen_device == 2 and self.port2_2 and self.port2_2.is_open:
            chosen_port = self.port2_2
        else:
            raise "Invalid device number or port is not open"

        chosen_port.write(message + self.MESSAGE_END_CHAR)

        return len(message)


    def start_receiving(self, chosen_device: int) -> None: # , listener: callable
        def receive_tread_body(port: serial.Serial) -> None:
            message: bytes = b""
            received_chars_count: int = 0
            count_of_empty_chars: int = 0

            while self.is_receiving and port and port.is_open:
                try:
                    byte = port.read(1)
                    # if count_of_empty_chars > 5:
                    #     break
                    # elif byte == b"":
                    #     count_of_empty_chars += 1
                    # el
                    if self.is_receiving and byte != b'':
                        message += byte
                        received_chars_count += 1
                        self.emit_received(message, received_chars_count)
                except Exception as e:
                    raise PortException(f"Reading exception")

        chosen_port: serial.Serial | None = None
        if chosen_device == 1:
            chosen_port = self.port1_2
        elif chosen_device == 2:
            chosen_port = self.port2_1
        else:
            raise "Invalid device number"

        self.receiving_thread = threading.Thread(target=receive_tread_body, args=(chosen_port,))
        self.is_receiving = True
        self.receiving_thread.start()

    def end_receiving(self) -> None:
        self.is_receiving = False
        self.receiving_thread.join()
        self.receiving_thread = None

    def emit_received(self, message: bytes, bytes_count: int) -> None:
        pass


    def create_port(self, port_name: str) -> serial.Serial:
        try:
            return serial.Serial(
                port_name,
                baudrate=self.baudrate,
                timeout=self.timeout,
            )
        except SerialException:
            raise PortException("Port is not found or it is unavailable")

    def set_port(self, port: serial.Serial, port_number: int):
        if port_number == 1:
            if self.port1_1: self.close_port(self.port1_1)
            self.port1_1 = port
        elif port_number == 2:
            if self.port1_2: self.close_port(self.port1_2)
            self.port1_2 = port
        elif port_number == 3:
            if self.port2_1: self.close_port(self.port2_1)
            self.port2_1 = port
        elif port_number == 4:
            if self.port2_2: self.close_port(self.port2_2)
            self.port2_2 = port
        else:
            raise PortException("Invalid port number")

    def close_port(self, port: serial.Serial) -> None:
        port.close()


    def get_available_ports(self) -> list[str]:
        ports = [port.name for port in comports()]
        print(ports)
        return ports

    def set_ports_params(self, baudrate: int | None = None, timeout: float | None = None):
        if baudrate:
            self.baud_rate = baudrate

            if self.port1_1 and self.port1_1.is_open: self.port1_1.baudrate = baudrate
            if self.port1_2 and self.port1_2.is_open: self.port1_2.baudrate = baudrate
            if self.port2_1 and self.port2_1.is_open: self.port2_1.baudrate = baudrate
            if self.port2_2 and self.port2_2.is_open: self.port2_2.baudrate = baudrate
        if timeout:
            self.timeout = timeout

            if self.port1_1 and self.port1_1.is_open: self.port1_1.timeout = timeout
            if self.port1_2 and self.port1_2.is_open: self.port1_2.timeout = timeout
            if self.port2_1 and self.port2_1.is_open: self.port2_1.timeout = timeout
            if self.port2_2 and self.port2_2.is_open: self.port2_2.timeout = timeout

    def print_ports_info(self) -> str:
        return f"""
        | port_1_1 | {self.port1_1.name if self.port1_1 else "Not set"}
        | port_1_2 | {self.port1_2.name if self.port1_2 else "Not set"}
        | port_2_1 | {self.port2_1.name if self.port2_1 else "Not set"}
        | port_2_2 | {self.port2_2.name if self.port2_2 else "Not set"}
        | baudrate | {self.baudrate}
        | timeout | {self.timeout}
        """

    def close_active_ports(self) -> None:
        self.port1_1.close()
        self.port1_2.close()
        self.port2_1.close()
        self.port2_2.close()
