#!/usr/bin/env python3
"""
AutoMoto v4.0 - SIM808 GSM/GPRS + GPS Virtual Modem Simulator
Connects to Renode's UART1 socket or a virtual serial port (PTY).
Provides realistic AT command responses, GPS NMEA/GNSS fixes, and network simulation.
"""

import sys
import time
import socket
import threading
import argparse

class MockSIM808:
    def __init__(self, host="127.0.0.1", port=4321, pty_mode=False):
        self.host = host
        self.port = port
        self.pty_mode = pty_mode
        self.running = True
        
        # Simulated State
        self.gps_powered = False
        self.gprs_attached = True
        self.network_registered = True
        self.rssi = 26  # Strong signal
        
        # Telemetry / Location (Default: Izmir Kordon Coordinates)
        self.latitude = 38.4332
        self.longitude = 27.1408
        self.altitude = 12.5
        self.speed_kmh = 0.0
        self.heading = 180.0
        self.satellites = 12

    def generate_cgnsinf(self):
        """Generates SIM808 GNSS Information sentence (+CGNSINF)"""
        if not self.gps_powered:
            return "+CGNSINF: 0,,,,,,,,,,,,,,,,,,,\r\n\r\nOK\r\n"
        
        utc_now = time.strftime("%Y%m%d%H%M%S.000", time.gmtime())
        # Format: <GNSS run status>,<Fix status>,<UTC date & Time>,<Latitude>,<Longitude>,<MSL Altitude>,<Speed Over Ground>,<Course Over Ground>,<Fix Mode>,<Reserved>,<HDOP>,<PDOP>,<VDOP>,<Reserved>,<GNSS Satellites in View>,<GNSS Satellites Used>,<GLONASS Satellites Used>,<Reserved>,<C/N0 max>,<HPA>,<VPA>
        payload = (
            f"+CGNSINF: 1,1,{utc_now},{self.latitude:.6f},{self.longitude:.6f},"
            f"{self.altitude:.1f},{self.speed_kmh:.1f},{self.heading:.1f},1,,1.0,1.5,1.2,,14,{self.satellites},,,"
            f"42,1.2,1.8\r\n\r\nOK\r\n"
        )
        return payload

    def handle_command(self, cmd_line):
        cmd = cmd_line.strip().upper()
        if not cmd:
            return ""

        print(f"[SIM808 RX] << {cmd}")
        response = "\r\nOK\r\n"

        # AT check
        if cmd == "AT":
            response = "\r\nOK\r\n"
        # Echo control
        elif cmd.startswith("ATE"):
            response = "\r\nOK\r\n"
        # SIM Card Status
        elif cmd == "AT+CPIN?":
            response = "\r\n+CPIN: READY\r\n\r\nOK\r\n"
        # Signal Quality
        elif cmd == "AT+CSQ":
            response = f"\r\n+CSQ: {self.rssi},0\r\n\r\nOK\r\n"
        # Network Registration
        elif cmd == "AT+CREG?":
            reg_status = 1 if self.network_registered else 0
            response = f"\r\n+CREG: 0,{reg_status}\r\n\r\nOK\r\n"
        # GPRS Registration
        elif cmd == "AT+CGREG?":
            gprs_status = 1 if self.gprs_attached else 0
            response = f"\r\n+CGREG: 0,{gprs_status}\r\n\r\nOK\r\n"
        # GPS Power Control
        elif cmd == "AT+CGNSPWR=1":
            self.gps_powered = True
            response = "\r\nOK\r\n"
        elif cmd == "AT+CGNSPWR=0":
            self.gps_powered = False
            response = "\r\nOK\r\n"
        elif cmd == "AT+CGNSPWR?":
            pwr = 1 if self.gps_powered else 0
            response = f"\r\n+CGNSPWR: {pwr}\r\n\r\nOK\r\n"
        # Read GPS Navigation Information
        elif cmd == "AT+CGNSINF":
            response = "\r\n" + self.generate_cgnsinf()
        # Battery / Voltage
        elif cmd == "AT+CBC":
            response = "\r\n+CBC: 0,95,3860\r\n\r\nOK\r\n"
        # TCP/IP & GPRS Bearer
        elif cmd.startswith("AT+SAPBR"):
            response = "\r\nOK\r\n"
        elif cmd.startswith("AT+CIPSHUT"):
            response = "\r\nSHUT OK\r\n"
        elif cmd.startswith("AT+CIPSTATUS"):
            response = "\r\nOK\r\n\r\nSTATE: IP INITIAL\r\n"
        else:
            # Default fallback for unhandled AT commands
            response = "\r\nOK\r\n"

        print(f"[SIM808 TX] >> {response.strip()}")
        return response

    def run_tcp_client(self):
        """Connects to Renode's CreateServerSocketTerminal port"""
        print(f"[*] Connecting to Renode UART1 at {self.host}:{self.port}...")
        while self.running:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((self.host, self.port))
                print(f"[+] Connected to Renode UART1 ({self.host}:{self.port})!")
                
                buffer = ""
                while self.running:
                    data = s.recv(1024)
                    if not data:
                        break
                    buffer += data.decode("utf-8", errors="ignore")
                    if "\r" in buffer or "\n" in buffer:
                        lines = buffer.splitlines(True)
                        for line in lines:
                            if "\r" in line or "\n" in line:
                                resp = self.handle_command(line)
                                if resp:
                                    s.sendall(resp.encode("utf-8"))
                        buffer = lines[-1] if not (buffer.endswith("\r") or buffer.endswith("\n")) else ""
            except ConnectionRefusedError:
                print(f"[-] Renode UART1 port not ready yet. Retrying in 2 seconds...")
                time.sleep(2)
            except Exception as e:
                print(f"[!] Socket error: {e}. Reconnecting in 2 seconds...")
                time.sleep(2)

def main():
    parser = argparse.ArgumentParser(description="AutoMoto SIM808 Virtual Modem Simulator")
    parser.add_argument("--host", default="127.0.0.1", help="Renode UART1 TCP host")
    parser.add_argument("--port", type=int, default=4321, help="Renode UART1 TCP port")
    args = parser.parse_args()

    modem = MockSIM808(host=args.host, port=args.port)
    try:
        modem.run_tcp_client()
    except KeyboardInterrupt:
        print("\n[*] Exiting Mock SIM808.")

if __name__ == "__main__":
    main()
