from hub import Device, Data
from algorithms import define, create, detect
from converter import binary_to_hexadecimal, binary_to_decimal, hexadecimal_to_binary, decimal_to_binary


class Host(Device):
    def __init__(self, error_detection: str, name: str, mac: int = "FFFF"):
        super().__init__(name, 1)
        self.mac = mac
        self.transmitting_started = -1
        self.data = []
        self.data_pointer = [0, 0]
        self.resend_attempts = 0
        self.receiving_data = [[] for _ in range(6)]
        self.receiving_data_pointer = [0, 0]
        self.error_detection = define(str.upper(error_detection))
        file = open("output/{}_data.txt".format(name), 'w')
        file.close()

    def disconnect(self, time: int, port: int):
        cable = self.ports[port]
        device = cable.device
        if device is None:
            return
        if len(self.data) > 0:
            device.receive_bit(time, cable.port, Data.NULL, True)
        if type(device) != Host and device.ports[cable.port].data != Data.NULL:
            self.receive_bit(time, cable.port, Data.NULL, True)
        super().disconnect(time, port)
        self.data_pointer[1] = 0  # Comment if the the host must not restart sending data in case of disconnection
        self.reset_receiving(time)

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

    def reset_receiving(self, time):
        destination = self.receiving_data[0]
        if destination == self.mac or destination == "FFFF":
            file = open("output/{}_data.txt".format(self.name), 'a')
            sender = self.receiving_data[1]
            data = binary_to_hexadecimal(self.receiving_data[4])
            file.write("time={}, host_mac={}, data={}".format(time, sender if len(sender) > 0 else "FFFF",
                                                              data if len(data) > 0 else "null"))
            file.write(", state={}\n".format("ERROR" if self.receiving_data[2] / 4 != len(self.receiving_data[4]) or
                                             self.receiving_data[3] != len(self.receiving_data[5]) or
                                             not detect(self.error_detection, self.receiving_data[4],
                                                        self.receiving_data[5]) else "OK"))
            file.close()
        self.receiving_data = [[] for _ in range(6)]
        self.receiving_data_pointer = [0, 0]

    def start_send(self, signal_time: int, time: int, data: list, destiny_mac: list = None):
        if destiny_mac is None:
            destiny_mac = [1 for _ in range(8)]
        code = create(self.error_detection, data)
        self.data.append(destiny_mac + hexadecimal_to_binary(str(self.mac)) + decimal_to_binary(int(len(data) / 8)) +
                         decimal_to_binary(int(len(code) / 8)) + data + code)
        if len(self.data) == 1:
            self.transmitting_started = time
            self.send(signal_time, time)

    def send(self, signal_time: int, time: int, disconnected: bool = False):
        if self.transmitting_started == -1:
            return Data.NULL
        if (time - self.transmitting_started) % signal_time != 0:
            return Data.ZERO
        if disconnected:
            data = Data.NULL
        else:
            frame = self.data_pointer[0]
            pointer = self.data_pointer[1]
            if pointer < len(self.data[frame]):
                data = Data.ONE if self.data[frame][pointer] == 1 else Data.ZERO
                self.data_pointer[1] += 1
            else:
                data = Data.NULL
                self.data_pointer[0] += 1
                self.data_pointer[1] = 0
                frame += 1
                if frame >= len(self.data):
                    self.reset()
        self.send_bit(time, data, disconnected)
        if self.ports[0].device is None:
            self.data_pointer[1] -= 1  # Comment if the the host must not wait to resend data in case of disconnection
            self.resend_attempts += 1
            if self.resend_attempts == 20:
                self.reset()
        else:
            self.resend_attempts = 0
        return data if not disconnected and len(self.data) < 1 else data.ZERO

    def reset(self):
        self.transmitting_started = -1
        self.data = []
        self.data_pointer = [0, 0]
        self.ports[0].data = Data.NULL

    def rename(self, mac: str):
        if mac == "FFFF":
            raise Exception
        self.mac = mac