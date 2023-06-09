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
    session_id = None
elif response_type == 2:  # Login Rejected
    response_message = client_socket.recv(response_length)
    print("Login Rejected:", response_message.decode('utf-8'))
    client_socket.close()
    exit()  # Exit the script gracefully after login rejection
else:
    print("Invalid response received.")
    client_socket.close()
    exit()  # Exit the script if an invalid response is received

# Continue with the session
while True:
    response_header = client_socket.recv(2)
    response_type, response_length = struct.unpack('!BB', response_header)
    print(response_header, response_type, response_length)

    if response_type == 3:  # Start of Session
        response_message = client_socket.recv(response_length)
        session_id = struct.unpack('!Q', response_message[3:11])[0]
        print("Start of Session. Session ID:", session_id)
        break
    else:
        print("Invalid response received.")


# Stream Request
stream_request_type = 103
stream_request_length = 16  # 4 bytes for message type and length, 8 bytes for session ID, 8 bytes for next sequence number
NEXT_SEQUENCE_NUMBER = 0
stream_request_header = struct.pack('!BHBQQ', stream_request_type, stream_request_length, session_id, NEXT_SEQUENCE_NUMBER)
stream_request = stream_request_header


# Send the Stream Request
client_socket.sendall(stream_request)


response_header = client_socket.recv(2)
response_type, response_length = struct.unpack('!BB', response_header)

if response_type == 9:  # Stream Rejected
    response_message = client_socket.recv(response_length)
    reject_code = response_message.decode('utf-8')
    print("Stream Rejected. Reject Code:", reject_code)
    client_socket.close()
    exit()
elif response_type == 10:  # End of Stream
    response_message = client_socket.recv(response_length)
    print("End of Stream")
    client_socket.close()
    exit()
else:
    print("Invalid response received.")

# New Order Single
cl_ord_id = 1686883344217
symbol = 'UBER'
side = 2  # Sell
order_qty = 300
ord_type = 2  # Limit
price = 1500000
exponent = -6
time_in_force = 0  # Day
order_capacity = 'A'  # Agency
cust_order_capacity = 1  # MemberTradingOnTheirOwnAccount
exec_inst = 0
reprice_frequency = 0  # SingleReprice
reprice_behavior = 2  # RepriceLockRepriceCross
price_type_bytes = struct.pack('!qB',price, exponent)

#SBE Header
BlockLength = 96
TemplateID = 1
SchemaID = 1
Version =  266
new_order_single_header = struct.pack( '!HBBH',BlockLength,TemplateID,SchemaID,Version)

new_order_single_body = struct.pack('!16s6sBIBqBsBB2sBB',cl_ord_id,
symbol.encode('utf-8'),side,order_qty,ord_type,price,exponent,time_in_force,order_capacity.encode('utf-8')[0],cust_order_capacity,exec_inst,reprice_frequency,reprice_behavior)
new_order_single = new_order_single_header + new_order_single_body

# Unsequenced Message
unsequenced_message_header = struct.pack('!BH', 104, 102) # MessageType=104, MessageLength=6, TCP Header Length=102
unsequenced_message_body = struct.pack('!H', 104)  # TCP Header MessageLength=102, MessageType=104
unsequenced_message = unsequenced_message_header + unsequenced_message_body

# Send the New Order Single with Unsequenced Message
client_socket.sendall(new_order_single + unsequenced_message)

# Receive and handle the response
response_header = client_socket.recv(2)
response_type, response_length = struct.unpack('!BB', response_header)



# Close the socket
client_socket.close()
