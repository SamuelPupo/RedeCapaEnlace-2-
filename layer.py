from hub import Hub
from host import Host
from switch import Switch
from converter import hexadecimal_to_binary


class Layer:
    def __init__(self):
        self.devices = set()

    def create(self, error_detection: str, device: str, name: str, ports_number: int = 1):
        if device == "hub":
            self.devices.add(Hub(name, ports_number))
        elif device == "host":
            self.devices.add(Host(error_detection, name))
        elif device == "switch":
            self.devices.add(Switch(name, ports_number))

    def connect(self, time: int, device1: str, port1: int, device2: str, port2: int):
        if device1 == device2:
            print("\nCAN'T CONNECT A DEVICE WITH ITSELF.")
            raise Exception
        d1 = None
        d2 = None
        for d in self.devices:
            if d.name == device1:
                d1 = d
            elif d.name == device2:
                d2 = d
        if d1 is None or d2 is None:
            print("\nUNRECOGNIZED DEVICE.")
            raise Exception
        if port1 > d1.ports_number or port2 > d2.ports_number:
            print("\nUNRECOGNIZED PORT.")
            raise Exception
        d1.connect(time, port1, d2, port2)
        d2.connect(time, port2, d1, port1)

    def send(self, signal_time: int, time: int, host: str, data: list):
        for d in self.devices:
            if d.name == host:
                if type(d) != Host:
                    print("\nWRONG SEND INSTRUCTION DEVICE TYPE.")
                    raise Exception
                d.start_send(signal_time, time, data)
                return
        print("\nUNRECOGNIZED DEVICE.")
        raise Exception

    def disconnect(self, time: int, device: str, port: int):
        for d in self.devices:
            if d.name == device:
                if port > d.ports_number:
                    print("\nUNRECOGNIZED PORT.")
                    raise Exception
                d.disconnect(time, port)
                return
        print("\nUNRECOGNIZED DEVICE.")
        raise Exception

    def mac(self, host: str, address: str):
        for d in self.devices:
            if d.name == host:
                if type(d) != Host:
                    print("\nWRONG MAC INSTRUCTION DEVICE TYPE.")
                    raise Exception
                try:
                    int(address, 16)
                except Exception:
                    print("\nMAC ISN'T HEXADECIMAL.")
                    raise Exception
                d.rename(address)
                return
        print("\nUNRECOGNIZED DEVICE.")
        raise Exception

    def send_frame(self, signal_time: int, time: int, host: str, destiny_mac: str, data: list):
        for d in self.devices:
            if d.name == host:
                if type(d) != Host:
                    print("\nWRONG SEND INSTRUCTION DEVICE TYPE.")
                    raise Exception
                try:
                    destiny_mac = hexadecimal_to_binary(destiny_mac)
                except Exception:
                    print("\nMAC ISN'T HEXADECIMAL.")
                    raise Exception
                d.start_send(signal_time, time, data, destiny_mac)
                return
        print("\nUNRECOGNIZED DEVICE.")
        raise Exception
