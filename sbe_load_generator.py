import configparser
import socket
import struct
import time
from multiprocessing import Process
from sbe_encoder_decoder import UTCTimestampNanos, NewOrderSingle,  ShortTwoSidedQuote,ShortTwoSideBulkQuote, LongTwoSideBulkQuote, ShortOneSideBulkQuote, LongOneSideBulkQuote,MatchTradePreventionType,MtpGroupIDType, LongOneSideQuote,LongTwoSidedQuote,OrderCancelRequest,ExecutionAllocationsGroup,AllocationInstruction,MassCancelRequest
from sbe_encoder_decoder import UINT32,UINT16,UINT8, OrdType, PriceType,TimeInForceType, ExecInstType, TradingCapacityType, SideType, PartyID, PartiesGroup,PartyIDSource, PartyRoleType, ShortPriceType, OptionsSecurityID,ShortOneSideQuote,AllocType,Char,AllocTransType,RequestedAllocationsGroup,NestedPartiesGroup,UnderlyingOrSeriesType
from random import choices, randint
import string
from random import choices, randint, uniform



# Read configuration from config.ini
config = configparser.ConfigParser()
config.read('config.ini')


# Read connection details from connections.cfg
connection_config = configparser.ConfigParser()
connection_config.read(config['Server']['config_file'])

# Read TimeInForce from config.ini
time_in_force_value = config.get('NewOrderSingle', 'TimeInForce')
time_in_force = TimeInForceType(value=time_in_force_value)

# Define the MESSAGE_TYPES dictionary
MESSAGE_TYPES = {
    "NewOrderSingle": 1,
    "ShortTwoSidedBulkQuote": 2,
    "LongTwoSidedBulkQuote": 3,
    "ShortOneSidedBulkQuote": 4,
    "LongOneSidedBulkQuote": 5,
    "ExecutionReport_New": 11,
    "ExecutionReport_BulkQuote_PendingNew": 12,
    "ExecutionReport_BulkQuote_ComponentNew": 13,
    "ExecutionReport_Rejected": 14,
    "ExecutionReport_Trade": 15,
    "ExecutionReport_PendingCancel": 16,
    "ExecutionReport_Canceled": 17,
    "ExecutionReport_PendingReplace": 18,
    "ExecutionReport_Replaced": 19,
    "ExecutionReport_TradeCorrection": 20,
    "ExecutionReport_TradeBreak": 21,
    "ExecutionReport_Restatement": 22,
    "PendingMassCancel": 23,
    "MassCancelReject": 24,
    "MassCancelDone": 25,
    "OrderCancelReject": 26,
    "AllocationInstructionAck": 27,
    "AllocationReport": 28,
    "UserNotification": 29,
    "MassCancelClearLockoutReject": 30,
    "MassCancelClearLockoutDone": 31
}

# Define a list of underliers you want to check
underliers_to_check = ['GLD']  # Add more if needed

# Initialize the dictionary to store options security IDs
options_security_ids_by_underlier = {}

# Read the underliers and their options security IDs from the configuration
for underlier in underliers_to_check:
    # Convert the underlier name to lowercase before retrieving
    underlier_lower = underlier.lower()
    if config.has_option('OptionsSecurityIDs', underlier_lower):
        options_security_ids = config.get('OptionsSecurityIDs', underlier_lower).split(',')
        options_security_ids_by_underlier[underlier] = options_security_ids
    else:
        print(f"Warning: Key '{underlier}' not found in the configuration file.")

# Randomly select an underlier
selected_underlier = choices(underliers_to_check)


# Get the associated options security IDs for the selected underlier
selected_options_security_ids = options_security_ids_by_underlier[selected_underlier[0]]



# Generate random values for price and quantity
random_price = uniform(10, 50)  # Adjust min_price and max_price as needed
random_qty = randint(10, 20)  # Adjust min_qty and max_qty as needed

# Read other configuration parameters
message_rate = config.getint('Load', 'message_rate')
duration = config.getint('Load', 'duration')

weights = {
    'NewOrderSingle': config.getfloat('Weights', 'NewOrderSingle'),
    'ShortTwoSideBulkQuote': config.getfloat('Weights', 'ShortTwoSideBulkQuote'),
    'LongTwoSideBulkQuote': config.getfloat('Weights', 'LongTwoSideBulkQuote'),
    'ShortOneSideBulkQuote': config.getfloat('Weights', 'ShortOneSideBulkQuote'),
    'LongOneSideBulkQuote': config.getfloat('Weights', 'LongOneSideBulkQuote')
}

#security_ids = config.get('OptionsSecurityIDs', 'security_ids').split(',')

template_file = config.get('Template', 'template_file')

# Load template.txt
with open(template_file) as template_file:
    template = template_file.read()

# Establish SBE TCP session
def establish_session(session_name):


    # Get connection details for the specified session name
    host = connection_config[session_name]['host']
    port = int(connection_config[session_name]['port'])
    user = connection_config[session_name]['user']
    password = connection_config[session_name]['password']
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
    response_header = client_socket.recv(3)
    response_type, response_length = struct.unpack('!B H', response_header)
    print(response_type, response_length)

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
        response_header = client_socket.recv(11)
        response_type, response_length, session_id = struct.unpack('!B H Q', response_header)
        print(response_header, response_type, response_length)

        if response_type == 3:  # Start of Session
            print("Start of Session. Session ID:", session_id)
            break
        else:
            print("Invalid response received.")


    # Stream Request
    stream_request_type = 103
    stream_request_length = 16  # 4 bytes for message type and length, 8 bytes for session ID, 8 bytes for next sequence number
    NEXT_SEQUENCE_NUMBER = 0
    stream_request_header = struct.pack('!BHQQ', stream_request_type, stream_request_length, session_id, NEXT_SEQUENCE_NUMBER)
    stream_request = stream_request_header

    # Send the Stream Request
    client_socket.sendall(stream_request)

    response_header = client_socket.recv(3)
    response_type, response_length = struct.unpack('!B H', response_header)
    print(response_type, response_length)

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
    elif response_type == 8:  # Stream Begin
        response_message = client_socket.recv(response_length - 2)
        print(response_message)
        NEXT_SEQUENCE_NUMBER  = struct.unpack('!Q', response_message[3:11])
        print("Stream Begin received")
    else:
        print("Invalid Message received")
    

    return client_socket, session_id

# Generate a random message type based on the weights
def generate_message_type():
    message_types = list(weights.keys())
    return choices(message_types, weights=list(weights.values()), k=1)[0]

def generate_message(message_type,session_name, send_cancels=False):
    new_order_single_message = None
    order_cancel_message = None
    if message_type == 'NewOrderSingle':
  
        # Generate values for the fields
        sending_time = UTCTimestampNanos(int(time.time() * 10**9))
        orig_cl_ord_id = ''.join(choices(string.ascii_letters + string.digits, k=20))
        options_security_id = choices(selected_options_security_ids)[0]
        value=choices([SideType.BUY, SideType.SELL])
        side = value[0]
        order_qty = UINT32(value=randint(1, 10))
        ord_type = OrdType(value=OrdType.LIMIT)
        price_value = UINT32(value=randint(1, 10))
        realprice = price_value.value * 10**14
        #price = PriceType(50000000000000000)  # Set the price with 10^8 multiplier
        price = PriceType(realprice) 
        time_in_force = TimeInForceType(value=TimeInForceType.DAY)
        #time_in_force = TimeInForceType(value=TimeInForceType.IMMEDIATE_OR_CANCEL)
        exec_inst = ExecInstType(value=ExecInstType.ParticipateDoNotInitiate)  # Set the execution instructions
        trading_capacity = TradingCapacityType(value=TradingCapacityType.CUSTOMER)  # Set the trading capacity
        efid = connection_config[session_name]['EFID']
        party_id = PartyID(efid)
        party_id_source = PartyIDSource('D')
        party_role = PartyRoleType(1)
        party_id1 = PartyID(efid)
        party_id_source1 = PartyIDSource('D')
        party_role1 = PartyRoleType(66)
        parties = [PartiesGroup(party_ids=[[party_id, party_id_source, party_role],[party_id1, party_id_source1, party_role1]])]
        no_parties_groups = 2

        # Create an instance of NewOrderSingle and set the field values
        new_order_single = NewOrderSingle(
            sending_time=sending_time,
            cl_ord_id=orig_cl_ord_id,
            options_security_id=options_security_id,
            side=side,
            order_qty=order_qty,
            ord_type=ord_type,
            price=price,
            time_in_force=time_in_force,
            exec_inst=exec_inst,
            trading_capacity=trading_capacity,
            parties_group=parties,
            party_entries=no_parties_groups
        )

        
        messageLength = 73 + (18 * (no_parties_groups))
        unsequenced_message = struct.pack('!BH', 104, messageLength)  # MessageType=104, MessageLength=91, TCP Header Length=102
        # Encode the NewOrderSingle instance
        encoded_message = new_order_single.encode()
        message = unsequenced_message + encoded_message

        new_order_single_message = message

        if send_cancels:
                print('\n\nsending order cancel:')
                sending_time = UTCTimestampNanos(int(time.time() * 10**9))
                cl_ord_id = ''.join(choices(string.ascii_uppercase + string.digits, k=20))
                list_seq_no = UINT8(0)
                orig_cl_ord_id = orig_cl_ord_id
                options_security_id = options_security_id
                side = side
    

                order_cancel_request = OrderCancelRequest(
                sending_time=sending_time,
                cl_ord_id=cl_ord_id,
                list_seq_no = list_seq_no,
                orig_cl_ord_id = orig_cl_ord_id,
                options_security_id = options_security_id,
                side = side
                )


                encoded_message = order_cancel_request.encode()
                unsequenced_message = struct.pack('!BH', 104, 73)  # MessageType=104,112 MessageLength=6, TCP Header Length=102
                message = unsequenced_message + encoded_message
                # Print the encoded message
                print('order_cancel_request:')
                print(message)
                order_cancel_message = message

        # Print the encoded message
        print('NewOrderSingle:')
        print(encoded_message)

        return new_order_single_message,order_cancel_message

    elif message_type == 'NewOrderSingle_mkt':
  
        # Generate values for the fields
        sending_time = UTCTimestampNanos(int(time.time() * 10**9))
        cl_ord_id = ''.join(choices(string.ascii_letters + string.digits, k=20))
        options_security_id = choices(selected_options_security_ids)[0]
        side = SideType(value=SideType.BUY)  # Set the side to "Buy"
        order_qty = UINT32(value=randint(1, 10))
        ord_type = OrdType(value=OrdType.MARKET)
        price = PriceType(None)  # Set the price with 10^8 multiplier
        time_in_force = TimeInForceType(value=TimeInForceType.DAY)  # Set the time in force to "Day"
        exec_inst = ExecInstType(value=ExecInstType.ParticipateDoNotInitiate)  # Set the execution instructions
        trading_capacity = TradingCapacityType(value=TradingCapacityType.MARKET_MAKER)  # Set the trading capacity
        efid = connection_config[session_name]['EFID']
        party_id = PartyID(efid)
        party_id_source = PartyIDSource('D')
        party_role = PartyRoleType(1)
        parties = [PartiesGroup(party_ids=[[party_id, party_id_source, party_role]])]

        # Create an instance of NewOrderSingle and set the field values
        new_order_single = NewOrderSingle(
            sending_time=sending_time,
            cl_ord_id=cl_ord_id,
            options_security_id=options_security_id,
            side=side,
            order_qty=order_qty,
            ord_type=ord_type,
            price=price,
            time_in_force=time_in_force,
            exec_inst=exec_inst,
            trading_capacity=trading_capacity,
            parties_group=parties
        )
        
        no_parties_groups = 1
        messageLength = 73 + (18 * (no_parties_groups))
        unsequenced_message = struct.pack('!BH', 104, messageLength)  # MessageType=104, MessageLength=6, TCP Header Length=102
        # Encode the NewOrderSingle instance

        encoded_message = new_order_single.encode()
        message = unsequenced_message + encoded_message

        # Print the encoded message
        print('NewOrderSingle:')
        print(encoded_message)

        return message


    elif message_type == 'ShortTwoSideBulkQuote':
        # Generate ShortTwoSideBulkQuote message
        sending_time = UTCTimestampNanos(int(time.time() * 10**9))
        cl_ord_id = ''.join(choices(string.ascii_uppercase + string.digits, k=20))
        time_in_force = TimeInForceType(value=TimeInForceType.DAY)
        exec_inst = UINT16(1)
        trading_capacity = TradingCapacityType(value=TradingCapacityType.MARKET_MAKER)
        mtp_group_id = MtpGroupIDType(1)
        match_trade_prevention = MatchTradePreventionType(1)
        cancel_group_id = UINT16(1)
        risk_group_id = UINT16(1)
        efid = connection_config[session_name]['EFID']
        party_id = PartyID(efid)
        party_id_source = PartyIDSource('D')
        party_role = PartyRoleType(1)
        party_id1 = PartyID(efid)
        party_id_source1 = PartyIDSource('D')
        party_role1 = PartyRoleType(66)
        parties = [PartiesGroup(party_ids=[[party_id, party_id_source, party_role],[party_id1, party_id_source1, party_role1]])]
        options_security_id=choices(selected_options_security_ids)[0]
        quote1 = ShortTwoSidedQuote(list_seq_no=1, options_security_id=options_security_id, bid_size=10, bid_mantissa=50000,offer_size=20,offer_mantissa=75000)
        quote2 = ShortTwoSidedQuote(list_seq_no=2, options_security_id=options_security_id, bid_size=15,bid_mantissa=80000, offer_size=25, offer_mantissa=85000)

        quotes = [quote1, quote2]
        

        short_two_side_bulk_quote = ShortTwoSideBulkQuote(
            sending_time=sending_time,
            cl_ord_id=cl_ord_id,
            time_in_force=time_in_force,
            exec_inst=exec_inst,
            trading_capacity=trading_capacity,
            mtp_group_id=mtp_group_id,
            match_trade_prevention=match_trade_prevention,
            cancel_group_id=cancel_group_id,
            risk_group_id=risk_group_id,
            parties=parties,
            quotes=quotes
        )

        # Encode the ShortTwoSideBulkQuote instance
        encoded_message = short_two_side_bulk_quote.encode()

        no_parties_groups = 2
        no_of_quotes = 2
        messageLength = 73 + (18 * (no_parties_groups)) + (17 * (no_of_quotes))
        unsequenced_message = struct.pack('!BH', 104, messageLength)  # MessageType=104, MessageLength=6, TCP Header Length=102
        message = unsequenced_message + encoded_message

        # Print the encoded message
        print('short_two_side_bulk_quote:')

        new_order_single_message = message


        print(new_order_single_message)

        if send_cancels:
                print('\n\nsending order cancel:')
                sending_time = UTCTimestampNanos(int(time.time() * 10**9))
                cl_ord_id = ''.join(choices(string.ascii_uppercase + string.digits, k=20))
                efid = efid
                #mass_cancel_inst = MassCancelInstType(value=MassCancelInstType.CancelOrdersFromThisPortOnly)
                underlying_or_series = 	UnderlyingOrSeriesType(value = UnderlyingOrSeriesType.CancelAllOnSeries)
                #underlying_or_series = 	UnderlyingOrSeriesType(value = UnderlyingOrSeriesType.CancelAllOnUnderlying)

            
                mass_cancel_inst = UINT8(2)
                print('\nmass cancel request fields are:')
                print('client order id:',cl_ord_id)
                print('efid:',efid)
                print('mass_cancel_inst:',mass_cancel_inst.value)
                print('\n\n')
                mass_cancel_request = MassCancelRequest(
                sending_time=sending_time,
                cl_ord_id=cl_ord_id,
                efid = efid,
                underlying_or_series =underlying_or_series,
                options_security_id = options_security_id,
                mass_cancel_inst = mass_cancel_inst
                )

            
                encoded_message = mass_cancel_request.encode()
                unsequenced_message = struct.pack('!BH', 104, 57)  # MessageType=104,112 MessageLength=6, TCP Header Length=102
                message = unsequenced_message + encoded_message
                # Print the encoded message
                print('mass_cancel_request:')
                print(message)
                order_cancel_message = message
                # Print the encoded message



        return new_order_single_message,order_cancel_message



    elif message_type == 'LongTwoSideBulkQuote':
        # Generate LongTwoSideBulkQuote message
        sending_time = UTCTimestampNanos(int(time.time() * 10**9))
        cl_ord_id = ''.join(choices(string.ascii_uppercase + string.digits, k=20))
        time_in_force = TimeInForceType(value=TimeInForceType.DAY)
        #exec_inst = ExecInstType(value=ExecInstType.ParticipateDoNotInitiate)
        exec_inst = UINT16(1)
        trading_capacity = TradingCapacityType(value=TradingCapacityType.MARKET_MAKER)
        mtp_group_id = MtpGroupIDType(0)
        match_trade_prevention = MatchTradePreventionType(0)
        cancel_group_id = UINT16(0)
        risk_group_id = UINT16(0)
        efid = connection_config[session_name]['EFID']
        party_id = PartyID(efid)
        party_id_source = PartyIDSource('D')
        party_role = PartyRoleType(1)
        party_id1 = PartyID(efid)
        party_id_source1 = PartyIDSource('D')
        party_role1 = PartyRoleType(66)
        parties = [PartiesGroup(party_ids=[[party_id, party_id_source, party_role],[party_id1, party_id_source1, party_role1]])]
        options_security_id=choices(selected_options_security_ids)[0]
        quote1 = LongTwoSidedQuote(list_seq_no=1, options_security_id=options_security_id, bid_size=10, bid_px=1000000000000000,offer_size=20,offer_px=15000000000000000)
        quote2 = LongTwoSidedQuote(list_seq_no=2, options_security_id=options_security_id,bid_size=15,bid_px=20000000000000000, offer_size=25, offer_px=250000000000000000)

        quotes = [quote1, quote2]
        

        long_two_side_bulk_quote = LongTwoSideBulkQuote(
            sending_time=sending_time,
            cl_ord_id=cl_ord_id,
            time_in_force=time_in_force,
            exec_inst=exec_inst,
            trading_capacity=trading_capacity,
            mtp_group_id=mtp_group_id,
            match_trade_prevention=match_trade_prevention,
            cancel_group_id=cancel_group_id,
            risk_group_id=risk_group_id,
            parties=parties,
            quotes=quotes
        )

        # Encode the LongTwoSideBulkQuote instance
        encoded_message = long_two_side_bulk_quote.encode()
        no_parties_groups = 2
        no_of_quotes = 2
        messageLength = 50 + (18 * (no_parties_groups)) + (33 * (no_of_quotes))
        unsequenced_message = struct.pack('!BH', 104, messageLength)  # MessageType=104, MessageLength=6, TCP Header Length=102
        message = unsequenced_message + encoded_message
        new_order_single_message = message

        # Print the encoded messag´
        print('long_two_side_bulk_quote:')
        print(message)

        if send_cancels:
                print('\n\nsending order cancel:')
                sending_time = UTCTimestampNanos(int(time.time() * 10**9))
                cl_ord_id = ''.join(choices(string.ascii_uppercase + string.digits, k=20))
                efid = efid
                #mass_cancel_inst = MassCancelInstType(value=MassCancelInstType.CancelOrdersFromThisPortOnly)
                underlying_or_series = 	UnderlyingOrSeriesType(value = UnderlyingOrSeriesType.CancelAllOnSeries)
                #underlying_or_series = 	UnderlyingOrSeriesType(value = UnderlyingOrSeriesType.CancelAllOnUnderlying)

            
                mass_cancel_inst = UINT8(2)
                print('\nmass cancel request fields are:')
                print('client order id:',cl_ord_id)
                print('efid:',efid)
                print('mass_cancel_inst:',mass_cancel_inst.value)
                print('\n\n')
                mass_cancel_request = MassCancelRequest(
                sending_time=sending_time,
                cl_ord_id=cl_ord_id,
                efid = efid,
                underlying_or_series =underlying_or_series,
                options_security_id = options_security_id,
                mass_cancel_inst = mass_cancel_inst
                )

            
                encoded_message = mass_cancel_request.encode()
                unsequenced_message = struct.pack('!BH', 104, 57)  # MessageType=104,112 MessageLength=6, TCP Header Length=102
                message = unsequenced_message + encoded_message
                # Print the encoded message
                print('mass_cancel_request:')
                print(message)
                order_cancel_message = message
                # Print the encoded message



        return new_order_single_message,order_cancel_message

     

    elif message_type == 'ShortOneSideBulkQuote':
        sending_time = UTCTimestampNanos(int(time.time() * 10**9))
        cl_ord_id = ''.join(choices(string.ascii_uppercase + string.digits, k=20))
        time_in_force = TimeInForceType(value=TimeInForceType.DAY)
        exec_inst = UINT16(1)
        trading_capacity = TradingCapacityType(value=TradingCapacityType.MARKET_MAKER)
        mtp_group_id = MtpGroupIDType(0)
        match_trade_prevention = MatchTradePreventionType(0)
        cancel_group_id = UINT16(0)
        risk_group_id = UINT16(0)
        efid = connection_config[session_name]['EFID']
        party_id = PartyID(efid)
        party_id_source = PartyIDSource('D')
        party_role = PartyRoleType(1)
        party_id1 = PartyID(efid)
        party_id_source1 = PartyIDSource('D')
        party_role1 = PartyRoleType(66)
        parties = [PartiesGroup(party_ids=[[party_id, party_id_source, party_role],[party_id1, party_id_source1, party_role1]])]
        options_security_id=choices(selected_options_security_ids)[0]
        quote1 = ShortOneSideQuote(list_seq_no=1, options_security_id=options_security_id, side = SideType(value=SideType.BUY),quantity=11, price=10000)
        quote2 = ShortOneSideQuote(list_seq_no=2, options_security_id=options_security_id,side=SideType(value=SideType.SELL), quantity=12, price=20000)

        quotes = [quote1, quote2]
        

        short_one_side_bulk_quote = ShortOneSideBulkQuote(
            sending_time=sending_time,
            cl_ord_id=cl_ord_id,
            time_in_force=time_in_force,
            exec_inst=exec_inst,
            trading_capacity=trading_capacity,
            mtp_group_id=mtp_group_id,
            match_trade_prevention=match_trade_prevention,
            cancel_group_id=cancel_group_id,
            risk_group_id=risk_group_id,
            parties=parties,
            quotes=quotes
        )

        # Encode the ShortTwoSideBulkQuote instance
        encoded_message = short_one_side_bulk_quote.encode()
        no_parties_groups = 2
        no_of_quotes = 2
        messageLength = 73 + (18 * (no_parties_groups)) + (14 * (no_of_quotes))
        print(messageLength)
        unsequenced_message = struct.pack('!BH', 104, messageLength)  # MessageType=104, MessageLength=6, TCP Header Length=102
        message = unsequenced_message + encoded_message
        new_order_single_message = message

        # Print the encoded message
        print('short_one_side_bulk_quote:')

    
        if send_cancels:
                print('\n\nsending order cancel:')
                sending_time = UTCTimestampNanos(int(time.time() * 10**9))
                cl_ord_id = ''.join(choices(string.ascii_uppercase + string.digits, k=20))
                efid = efid
                #mass_cancel_inst = MassCancelInstType(value=MassCancelInstType.CancelOrdersFromThisPortOnly)
                underlying_or_series = 	UnderlyingOrSeriesType(value = UnderlyingOrSeriesType.CancelAllOnSeries)
                #underlying_or_series = 	UnderlyingOrSeriesType(value = UnderlyingOrSeriesType.CancelAllOnUnderlying)

            
                mass_cancel_inst = UINT8(2)
                print('\nmass cancel request fields are:')
                print('client order id:',cl_ord_id)
                print('efid:',efid)
                print('mass_cancel_inst:',mass_cancel_inst.value)
                print('\n\n')
                mass_cancel_request = MassCancelRequest(
                sending_time=sending_time,
                cl_ord_id=cl_ord_id,
                efid = efid,
                underlying_or_series =underlying_or_series,
                options_security_id = options_security_id,
                mass_cancel_inst = mass_cancel_inst
                )

            
                encoded_message = mass_cancel_request.encode()
                unsequenced_message = struct.pack('!BH', 104, 57)  # MessageType=104,112 MessageLength=6, TCP Header Length=102
                message = unsequenced_message + encoded_message
                # Print the encoded message
                print('mass_cancel_request:')
                print(message)
                order_cancel_message = message
                # Print the encoded message
        return new_order_single_message,order_cancel_message 

    elif message_type == 'LongOneSideBulkQuote':
        # Generate LongOneSideBulkQuote message
        sending_time = UTCTimestampNanos(int(time.time() * 10**9))
        cl_ord_id = ''.join(choices(string.ascii_uppercase + string.digits, k=20))
        time_in_force = TimeInForceType(value=TimeInForceType.DAY)
        exec_inst = UINT16(1)
        trading_capacity = TradingCapacityType(value=TradingCapacityType.MARKET_MAKER)
        mtp_group_id = MtpGroupIDType(0)
        match_trade_prevention = MatchTradePreventionType(0)
        cancel_group_id = UINT16(0)
        risk_group_id = UINT16(0)
        efid = connection_config[session_name]['EFID']
        party_id = PartyID(efid)
        party_id_source = PartyIDSource('D')
        party_role = PartyRoleType(1)
        party_id1 = PartyID(efid)
        party_id_source1 = PartyIDSource('D')
        party_role1 = PartyRoleType(66)
        parties = [PartiesGroup(party_ids=[[party_id, party_id_source, party_role],[party_id1, party_id_source1, party_role1]])]
        options_security_id=choices(selected_options_security_ids)[0]
        quote1 = LongOneSideQuote(list_seq_no=1, options_security_id=options_security_id, side=SideType(value=SideType.BUY),quantity=12, price=100000000000000000)
        quote2 = LongOneSideQuote(list_seq_no=2, options_security_id=options_security_id, side=SideType(value=SideType.BUY),quantity=13, price=200000000000000000)
        quote3 = LongOneSideQuote(list_seq_no=3, options_security_id=options_security_id, side=SideType(value=SideType.SELL),quantity=13, price=300000000000000000)
        quote4 = LongOneSideQuote(list_seq_no=4, options_security_id=options_security_id, side=SideType(value=SideType.SELL),quantity=13, price=400000000000000000)
        quote5 = LongOneSideQuote(list_seq_no=5, options_security_id=options_security_id, side=SideType(value=SideType.SELL),quantity=13, price=500000000000000000)
        quote6 = LongOneSideQuote(list_seq_no=6, options_security_id=options_security_id, side=SideType(value=SideType.BUY),quantity=12, price=100000000000000000)
        quote7 = LongOneSideQuote(list_seq_no=7, options_security_id=options_security_id, side=SideType(value=SideType.BUY),quantity=13, price=200000000000000000)
        quote8 = LongOneSideQuote(list_seq_no=8, options_security_id=options_security_id, side=SideType(value=SideType.SELL),quantity=13, price=300000000000000000)
        quote9 = LongOneSideQuote(list_seq_no=9, options_security_id=options_security_id, side=SideType(value=SideType.SELL),quantity=13, price=400000000000000000)
        quote10 = LongOneSideQuote(list_seq_no=10, options_security_id=options_security_id, side=SideType(value=SideType.SELL),quantity=13, price=500000000000000000)
        quote11 = LongOneSideQuote(list_seq_no=11, options_security_id=options_security_id, side=SideType(value=SideType.BUY),quantity=12, price=100000000000000000)
        quote12 = LongOneSideQuote(list_seq_no=12, options_security_id=options_security_id, side=SideType(value=SideType.BUY),quantity=13, price=200000000000000000)
        quote13 = LongOneSideQuote(list_seq_no=13, options_security_id=options_security_id, side=SideType(value=SideType.SELL),quantity=13, price=300000000000000000)
        quote14 = LongOneSideQuote(list_seq_no=14, options_security_id=options_security_id, side=SideType(value=SideType.SELL),quantity=13, price=400000000000000000)
        quote15 = LongOneSideQuote(list_seq_no=15, options_security_id=options_security_id, side=SideType(value=SideType.SELL),quantity=13, price=500000000000000000)
        quote16 = LongOneSideQuote(list_seq_no=16, options_security_id=options_security_id, side=SideType(value=SideType.BUY),quantity=12, price=100000000000000000)
        quote17= LongOneSideQuote(list_seq_no=17, options_security_id=options_security_id, side=SideType(value=SideType.BUY),quantity=13, price=200000000000000000)
        quote18= LongOneSideQuote(list_seq_no=18, options_security_id=options_security_id, side=SideType(value=SideType.SELL),quantity=13, price=300000000000000000)
        quote19= LongOneSideQuote(list_seq_no=19, options_security_id=options_security_id, side=SideType(value=SideType.SELL),quantity=13, price=400000000000000000)
        quote20= LongOneSideQuote(list_seq_no=20, options_security_id=options_security_id, side=SideType(value=SideType.SELL),quantity=13, price=500000000000000000)
       

        quotes = [quote1, quote2, quote3, quote4, quote5,quote6, quote7, quote8, quote9, quote10,quote11, quote12, quote13, quote14, quote15,quote16, quote17, quote18, quote19, quote20]
        

        long_one_side_bulk_quote = LongOneSideBulkQuote(
            sending_time=sending_time,
            cl_ord_id=cl_ord_id,
            time_in_force=time_in_force,
            exec_inst=exec_inst,
            trading_capacity=trading_capacity,
            mtp_group_id=mtp_group_id,
            match_trade_prevention=match_trade_prevention,
            cancel_group_id=cancel_group_id,
            risk_group_id=risk_group_id,
            parties=parties,
            quotes=quotes
        )

       
        encoded_message = long_one_side_bulk_quote.encode()
        no_parties_groups = 2
        no_of_quotes = 20
        messageLength = 73 + (18 * (no_parties_groups)) + (22 * (no_of_quotes))
        unsequenced_message = struct.pack('!BH', 104, messageLength)  # MessageType=104, MessageLength=6, TCP Header Length=102
        message = unsequenced_message + encoded_message
        new_order_single_message = message



    


        if send_cancels:
                print('\n\nsending order cancel:')
                sending_time = UTCTimestampNanos(int(time.time() * 10**9))
                cl_ord_id = ''.join(choices(string.ascii_uppercase + string.digits, k=20))
                efid = efid
                #mass_cancel_inst = MassCancelInstType(value=MassCancelInstType.CancelOrdersFromThisPortOnly)
                underlying_or_series = 	UnderlyingOrSeriesType(value = UnderlyingOrSeriesType.CancelAllOnSeries)
                #underlying_or_series = 	UnderlyingOrSeriesType(value = UnderlyingOrSeriesType.CancelAllOnUnderlying)

            
                mass_cancel_inst = UINT8(2)
                print('\nmass cancel request fields are:')
                print('client order id:',cl_ord_id)
                print('efid:',efid)
                print('mass_cancel_inst:',mass_cancel_inst.value)
                print('\n\n')
                mass_cancel_request = MassCancelRequest(
                sending_time=sending_time,
                cl_ord_id=cl_ord_id,
                efid = efid,
                underlying_or_series =underlying_or_series,
                options_security_id = options_security_id,
                mass_cancel_inst = mass_cancel_inst
                )

            
                encoded_message = mass_cancel_request.encode()
                unsequenced_message = struct.pack('!BH', 104, 57)  # MessageType=104,112 MessageLength=6, TCP Header Length=102
                message = unsequenced_message + encoded_message
                # Print the encoded message
                print('mass_cancel_request:')
                print(message)
                order_cancel_message = message
                # Print the encoded message



        return new_order_single_message,order_cancel_message   
    
    elif message_type == 'AllocationInstruction':
        # Generate AllowInstruction message
       sending_time = UTCTimestampNanos(1234567890)
       alloc_id = ''.join(choices(string.ascii_uppercase + string.digits, k=20))
       alloc_type = AllocType(value=AllocType.I)
       alloc_trans_type = AllocTransType(value=AllocType.N)
       ref_alloc_id = Char("")
       options_security_id = Char("98765432")
       side = SideType(value=SideType.BUY) 

       # Construct ExecutionAllocationsGroup instances
       execution_allocations = [
            ExecutionAllocationsGroup(12345, 100, PriceType(1234567890)),
            ExecutionAllocationsGroup(67890, 50, PriceType(9876543210))
        ]

       # Construct NestedPartiesGroup instances
       nested_parties = [
            NestedPartiesGroup("Nested1", "S", PartyRoleType(1)),
            NestedPartiesGroup("Nested2", "T", PartyRoleType(2))
        ]

        # Construct RequestedAllocationsGroup instances
       requested_allocations = [
            RequestedAllocationsGroup(10, Char("O"), nested_parties),
            RequestedAllocationsGroup(20, Char("C"), [])
        ]
       
       allocation_instruction = AllocationInstruction(
            sending_time = sending_time,
            alloc_id = alloc_id,
            alloc_type = alloc_type,
            alloc_trans_type = alloc_trans_type,
            ref_alloc_id = ref_alloc_id,
            options_security_id = options_security_id,
            side = side,
            execution_allocations = execution_allocations,
            requested_allocations = requested_allocations
         )
        
        
       encoded_message = allocation_instruction.encode()
       execution_allocations = 2
       execution_allocations = 2
       messageLength = 73 + (18 * (execution_allocations)) + (22 * (execution_allocations))
       unsequenced_message = struct.pack('!BH', 104, messageLength)  # MessageType=104, MessageLength=6, TCP Header Length=102
       message = unsequenced_message + encoded_message
       return message



    else:
        raise ValueError(f"Invalid message type: {message_type}")

# Send the generated message over the TCP connection        
def send_message(client_socket, message):


    # Send the message
    client_socket.sendall(message)

    # Sleep for a short period to control the message rate
    time.sleep(1 / message_rate)

def session_worker(session_name):
    #try:
        # Establish SBE TCP session for the current session name
        client_socket, session_id = establish_session(session_name)

        # Start time for calculating duration
        start_time = time.time()

        # Generate and send messages for the specified duration
        while time.time() - start_time < duration:
            # Generate a random message type
            message_type = generate_message_type()

            # Generate one or two messages
            new_order_single_message, order_cancel_message = generate_message(message_type, session_name, send_cancels=config.getboolean('Load', 'SendCancels'))

            # Send the NewOrderSingle message
            if new_order_single_message:
                send_message(client_socket, new_order_single_message)

            # Send the OrderCancelRequest message if it's generated
            if order_cancel_message:
                send_message(client_socket, order_cancel_message)

            
            '''
            # Receive 10 bytes of the response
            response_data = client_socket.recv(11)
            print(response_data)

            # Extract SBE header fields
            template_id = struct.unpack_from('!B', response_data, 7)[0]
            #sbe_header_data = response_data[3:]
            #block_length, template_id, schema_id, version, num_groups = struct.unpack('!H B B H B', sbe_header_data)

            # Print extracted header fields
            print("Template ID:", template_id)

                
            message_type_name = None
            for message_name, template_id_value in MESSAGE_TYPES.items():
                if template_id == template_id_value:
                   message_type_name = message_name
                   break

            if message_type_name:
                print("Message Type Name:", message_type_name)
            else:
                print("Unknown Message Type")
            
            '''

            # Sleep for a short period to control the message rate
            time.sleep(1 / message_rate)

        # Close the TCP connection for the current session
        client_socket.close()

    #except Exception as e:
    #   print(f"Failed to establish session for {session_name}: {str(e)}")

def main():
    # Read session names from connections.cfg
    session_names = connection_config.sections()

    # List to hold the worker processes
    processes = []

    # Iterate over session names and create worker processes
    for session_name in session_names:
        process = Process(target=session_worker, args=(session_name,))
        processes.append(process)

    # Start all the worker processes
    for process in processes:
        process.start()

    # Wait for all worker processes to complete
    for process in processes:
        process.join()

    # Print the number of active sessions
    print(f"Total active sessions: {len(processes)}")

# Start the main execution
if __name__ == '__main__':
    main()
