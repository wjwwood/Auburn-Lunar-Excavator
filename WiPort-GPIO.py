from socket import *

host = '192.168.1.103'
port = 0x77f0

buf = 1024
addr = (host, port)

udp_socket = socket(AF_INET, SOCK_DGRAM)

# msg = command + 32-bit mask + 32-bit enables (In this case we are masking everything but pin0 and setting it to 1)
msg = '\x1B'+'\x01\x00\x00\x00'+'\x01\x00\x00\x00'

udp_socket.sendto(msg, addr)

udp_socket.close()