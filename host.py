from hub import Device, Data
from algorithms import define, detect, create
from converter import binary_to_hexadecimal, binary_to_decimal, hexadecimal_to_binary, decimal_to_binary


class Host(Device):
    def __init__(self, signal_time: int, error_detection: str, name: str, mac: str = "FFFF"):
        super().__init__(name, 1)
        self.signal_time = signal_time
        self.error_detection = define(str.upper(error_detection))
        self.mac = mac
        self.transmitting_started = -1
        self.data = []
        self.data_pointer = 0
        self.resend_attempts = 0
        self.receiving_data = [[] for _ in range(6)]
        self.receiving_data_pointer = [0, 0]
        file = open("output/{}_data.txt".format(name), 'w')
        file.close()

    def connect(self, time: int, port: int, other_device: Device, other_port: int):
        super().connect(time, port, other_device, other_port)
        if self.ports[0].data != Data.NULL:
            self.data_pointer += 1

    def disconnect(self, time: int, port: int):
        cable = self.ports[port]
        device = cable.device
        if device is None:
            return
        if len(self.data) > 0:
            device.receive_bit(time, cable.port, Data.NULL, True)
        if type(device) != Host and len(self.receiving_data[0]) > 0:
            self.receive_bit(time, cable.port, Data.NULL, True)
        super().disconnect(time, port)
        self.data_pointer = 0  # Comment if the the host must not restart sending data in case of disconnection

    def collision(self, string: str):
        super().collision(string)
        if self.data_pointer > 0:
            self.data_pointer -= 1  # Comment if the the host must not wait to resend data in case of collision
        self.resend_attempts += 1
        if self.resend_attempts == 50:
            self.reset()
        self.ports[0].data = Data.NULL

    def reset(self):
        self.data.pop(0)
        if len(self.data) < 1:
            self.transmitting_started = -1
        self.data_pointer = 0
        self.resend_attempts = 0
        self.ports[0].data = Data.NULL

    def receive_bit(self, time: int, port: int, data: Data, disconnected: bool = False):
        super().receive_bit(time, port, data, disconnected)
        self.write("\n")
        section = self.receiving_data_pointer[0]
        pointer = self.receiving_data_pointer[1]
        if data != Data.NULL:
            self.receiving_data[section].append(1 if data == Data.ONE else 0)
            self.receiving_data_pointer[1] += 1
            pointer += 1
            if ((section == 0 or section == 1) and pointer == 16) or \
                    (section == 4 and pointer == self.receiving_data[2]) or \
                    (section == 5 and pointer == self.receiving_data[3]):
                if section != 5:
                    if section != 4:
                        self.receiving_data[section] = binary_to_hexadecimal(self.receiving_data[section])
                    self.receiving_data_pointer[0] += 1
                    self.receiving_data_pointer[1] = 0
                else:
                    self.reset_receiving(time)
            elif (section == 2 or section == 3) and pointer == 8:
                self.receiving_data[section] = binary_to_decimal(self.receiving_data[section]) * 8
                self.receiving_data_pointer[0] += 1
                self.receiving_data_pointer[1] = 0
        else:
            if pointer > 0:
                if section == 0 or section == 1:
                    self.receiving_data[section] = binary_to_hexadecimal(self.receiving_data[section])
                elif section == 2 or section == 3:
                    self.receiving_data[section] = binary_to_decimal(self.receiving_data[section]) * 8
            self.reset_receiving(time)

    def reset_receiving(self, time: int):
        receiving_data = self.receiving_data
        destination = receiving_data[0]
        if destination == self.mac or destination == "FFFF":
            sender = receiving_data[1]
            data = binary_to_hexadecimal(receiving_data[4])
            state = "ERROR" if receiving_data[2] != len(receiving_data[4]) or \
                    receiving_data[3] != len(receiving_data[5]) or \
                    not detect(self.error_detection, receiving_data[4], receiving_data[5]) else "OK"
            file = open("output/{}_data.txt".format(self.name), 'a')
            file.write("time={}, host_mac={}, data={}, state={}\n".format(time, sender if len(sender) > 0 else "FFFF",
                                                                          data if len(data) > 0 else "NULL", state))
            file.close()
        self.receiving_data = [[] for _ in range(6)]
        self.receiving_data_pointer = [0, 0]

    def start_send(self, time: int, data: list, destination_mac: list = None):
        if destination_mac is None:
            destination_mac = [1 for _ in range(16)]
        origen_mac = hexadecimal_to_binary(self.mac)
        data_length = decimal_to_binary(int(len(data) / 8))
        code = create(self.error_detection, data)
        code_length = decimal_to_binary(int(len(code) / 8))
        self.data.append(destination_mac + origen_mac + data_length + code_length + data + code)
        if len(self.data) == 1:
            self.transmitting_started = time
            self.send(time)

    def send(self, time: int, disconnected: bool = False):
        if self.transmitting_started == -1:
            return Data.NULL
        if (time - self.transmitting_started) % self.signal_time != 0:
            return Data.ZERO
        if disconnected:
            data = Data.NULL
        else:
            pointer = self.data_pointer
            if len(self.data) > 0 and pointer < len(self.data[0]):
                data = Data.ONE if self.data[0][pointer] == 1 else Data.ZERO
                self.data_pointer += 1
            else:
                data = Data.NULL
                self.data.pop(0)
                self.data_pointer = 0
                if len(self.data) < 1:
                    self.transmitting_started = -1
                    self.data = []
                    self.data_pointer = 0
                    self.resend_attempts = 0
                    self.ports[0].data = Data.NULL
        self.send_bit(time, data, disconnected)
        if self.ports[0].device is None:
            self.data_pointer -= 1  # Comment if the the host must not wait to resend data in case of disconnection
            self.resend_attempts += 1
            if self.resend_attempts == 25:
                self.reset()
        elif self.data_pointer > 0:
            self.resend_attempts = 0
        return data if not disconnected and len(self.data) < 1 else data.ZERO

    def set_mac(self, mac: str):
        if mac == "FFFF":
            print("\nWRONG MAC ADDRESS.")
            raise Exception
        self.mac = mac
