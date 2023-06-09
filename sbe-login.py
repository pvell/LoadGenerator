import socket
import struct

# TCP/IP connection details
host = '10.2.128.10'
port = 30076

# Token and header details
user = 'exactpro6'
password = 'expro6pwd'
token = f'{user}:{password}'

# Login request
message_type = 100
token_type = 'P'  # Assuming token type is always 'P'
token_length = len(token)
header = struct.pack('!BHB', message_type, token_length + 1, token_type.encode('utf-8')[0])
message = header + token.encode('utf-8')

# Create a socket and establish the connection
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((host, port))

# Set socket to binary mode
client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

# Send the login request
client_socket.sendall(message)

# Receive and handle the response
response_header = client_socket.recv(2)
response_type, response_length = struct.unpack('!BB', response_header)

if response_type == 1:  # Login Accepted
    response_message = client_socket.recv(response_length)
    print("Login Accepted:", response_message.decode('utf-8'))
elif response_type == 2:  # Login Rejected
    response_message = client_socket.recv(response_length)
    print("Login Rejected:", response_message.decode('utf-8'))
    client_socket.close()
    exit()  # Exit the script gracefully after login rejection
elif response_type == 3:  # Start of Session
    response_message = client_socket.recv(response_length)
    session_id = struct.unpack('!Q', response_message[:8])[0]
    print("Start of Session. Session ID:", session_id)
else:
    print("Invalid response received.")
    client_socket.close()
    exit()  # Exit the script if an invalid response is received

# Continue with the session
while True:
    response_header = client_socket.recv(2)
    response_type, response_length = struct.unpack('!BB', response_header)

    if response_type == 3:  # Start of Session
        response_message = client_socket.recv(response_length)
        print("Start of Session:", response_message.decode('utf-8'))
        break
    else:
        print("Invalid response received.")
        client_socket.close()
        exit()  # Exit the script if an invalid response is received

# Close the socket
client_socket.close()
