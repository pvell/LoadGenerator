import configparser
import random
import time
import datetime
import os
import quickfix as fix
import quickfix44 as fix44



# Global variables
sessions = {}

# Class representing the FIX application
class MyApplication(fix.Application):
    def __init__(self, message_weights, message_rate):
        super().__init__()
        self.message_weights = message_weights
        self.message_rate = message_rate
        self.sessions = {}
        self.log_directory = "log"
        self.captured_clordids = []  # Initialize an empty list to store the captured ClOrdIDs
        self.efid_map = {}
        self.captured_clordid_side_mapping = {}

        efid_mapping = dict(config.items("EFID"))
        for comp_id, efid in efid_mapping.items():
            efid, trading_capacity = efid.split(",")
            self.efid_map[comp_id] = {"efid": efid, "trading_capacity": int(trading_capacity)}
            #print(efid,trading_capacity)


    def onCreate(self, sessionID):
        print("Session created -", sessionID.toString())
        self.sessions[sessionID] = fix.Session.lookupSession(sessionID)

    def toAdmin(self, message, sessionID):
        if message.getHeader().getField(fix.MsgType()).getString() == fix.MsgType_Logon:
            message.getHeader().setField(1408, "1.3")
            message.getHeader().setField(43, "Y")
            print("sent admin message", message.toString())
        return True

    def toApp(self, message, sessionID):
        session_id = sessionID.toString()
        msg_type_field = fix.MsgType()
        if message.getHeader().getFieldIfSet(msg_type_field):
            msg_type = msg_type_field.getValue()
        else:
            print("Message does not have a MsgType tag (35), skipping sending.")
            return
        with open(self.get_log_file(), "a") as file:
            file.write(f"Session: {session_id}\n")
            file.write(message.toString() + '\n')
        print("sent application message", message.toString())

    def fromApp(self, message, sessionID):
        session_id = sessionID.toString()
        with open(self.get_log_file(), "a") as file:
            file.write(f"Session: {session_id}\n")
            file.write(message.toString() + '\n')
        print("received application message", message.toString())
        msg_type = fix.MsgType()
        message.getHeader().getField(msg_type)

        if msg_type.getValue() == fix.MsgType_ExecutionReport:
            cl_ord_id = fix.ClOrdID()
            exec_type = fix.ExecType()
            order_id = fix.OrderID()
            side = fix.Side()
            tag_21035 = fix.StringField(21035)
            message.getField(cl_ord_id)
            message.getField(exec_type)
            message.getField(side)
            message.getField(tag_21035)
           

            # Check if the execution report matches the conditions
            if exec_type.getValue() == fix.ExecType_NEW or exec_type.getValue() == fix.ExecType_TRADE:
                #self.handle_execution_report(message)
                
                # Extract ClOrdID and OrdID from the execution report
                clordid = cl_ord_id.getString()
                side_value = side.getString()
                tag_21035_value = tag_21035.getValue()
                


                # Store the captured ClOrdID in the list
                self.captured_clordids.append(clordid)

                # Store the ClOrdID and its corresponding side in the dictionary
                self.captured_clordid_side_mapping[clordid] = {"side": side_value, "tag_21035": tag_21035_value, "session": sessionID}
                #print(self.captured_clordid_side_mapping)

    

    def fromAdmin(self, message, sessionID):
        global sessions
        session_id = sessionID.toString()
        incoming_msg_seq_num = int(message.getHeader().getField(34))
        msg_type = message.getHeader().getField(35)
        #print(message)

        if msg_type == 'A':  # Logon message
            if incoming_msg_seq_num == 1:
                print(f"Session established for {session_id}")
                sessions[session_id] = True
        elif msg_type == '5':  # Logout message
            print(f"Session disconnected for {session_id}")
            sessions[session_id] = False
        with open(self.get_log_file(), 'a') as file:
            file.write(f"Received fromAdmin message:{message.toString()}\n")


    def onLogout(self, sessionID):
        print("Logout initiated -", sessionID.toString())

    def onLogon(self, sessionID):
        print("Logon Successful -", sessionID.toString())

    def generate_clordid(self):
        return str(random.randint(100000, 999999))

    def calculate_checksum(self, message):
        checksum = sum(ord(c) for c in message) % 256
        return f"{checksum:03}"  # Ensure the CheckSum is three digits

    def get_outgoing_seq_num(self, session_id):
        session = fix.Session.lookupSession(session_id)
        if session is not None:
            return session.getExpectedSenderNum()
        return 0

    def generate_message(self, message_type, session_id):

            if message_type.lower() == "logon":
                message = fix.Message()
                message.getHeader().setField(fix.BeginString(fix.BeginString_FIXT11))
                message.getHeader().setField(fix.MsgType(fix.MsgType_Logon))

                # Set other required fields for Logon message
                message.setField(fix.EncryptMethod(0))
                message.setField(fix.HeartBtInt(30))
                message.setField(fix.ResetSeqNumFlag(False))
                message.setField(fix.DefaultApplVerID("FIX.5.0SP2"))
                message.setField(fix.DefaultCstmApplVerID("1.3"))

            elif message_type.lower() == "newordersingle":

                selected_symbol = random.choice(symbols)
                random_quantity = random.randint(1, 100)
                random_price = round(random.uniform(1, 100), 0)
              

                sender_comp_id = session_id.getSenderCompID().getString()


                efid_info = self.efid_map.get(sender_comp_id.lower())
                if efid_info is None:
                    print(f"EFID mapping not found for SenderCOmpID: {sender_comp_id}")

                efid =efid_info["efid"]
                trading_capacity = efid_info["trading_capacity"]
                print(efid,trading_capacity)

                
                message = fix.Message()
                message.getHeader().setField(fix.BeginString(session_id.getBeginString().getString()))
                message.getHeader().setField(fix.MsgType(fix.MsgType_NewOrderSingle))
                message.getHeader().setField(fix.SenderCompID(session_id.getSenderCompID().getString()))
                message.getHeader().setField(fix.TargetCompID(session_id.getTargetCompID().getString()))
                message.getHeader().setField(fix.MsgSeqNum(self.get_outgoing_seq_num(session_id)))


                # Set other required fields for NewOrderSingle message
                #message.setField(fix.Symbol(selected_symbol))
                message.setField(fix.Side(fix.Side_BUY))
                message.setField(fix.OrderQty(random_quantity))
                message.setField(fix.Price(random_price))
                message.setField(fix.OrdType(fix.OrdType_LIMIT))
                message.setField(fix.TimeInForce(fix.TimeInForce_DAY))
                message.setField(fix.ClOrdID(self.generate_clordid()))
                message.setField(fix.ExecInst("h"))
                #message.setField(1815,"6")
                message.setField(1815,str(trading_capacity))
                message.setField(21035,selected_symbol)
                sending_time = datetime.datetime.utcnow().strftime('%Y%m%d-%H:%M:%S.%f')[:-3]
                message.setField(60,sending_time)
                message.setField(77,"O")
                #message.setField(201,"1")
                #message.setField(202,"100")
                # Create the repeating group for PartyIDs
                party_group = fix44.NewOrderSingle.NoPartyIDs()
                party_group.setField(448, efid)
                party_group.setField(447, "D")
                party_group.setField(452, "1")
                message.addGroup(party_group)
                



            elif message_type.lower() == "orderreplace":
                pass
                # ...
                # Code for other message types
                # ...

            elif message_type.lower() == "ordercancel":
                # Generate OrderCancelRequest message using captured ClOrdIDs
                if self.captured_clordids:
                    org_clordid = random.choice(self.captured_clordids)
                    clordid_info = self.captured_clordid_side_mapping.get(org_clordid)
                    if clordid_info is not None:
                        session_obj = clordid_info.get("session")
                   

                        if session_obj is not None:
                            side = clordid_info["side"]
                            tag_21035 = clordid_info["tag_21035"]
                            #side = self.captured_clordid_side_mapping.get(clordid, "UNKNOWN")
                            message = fix.Message()
                            sending_time = datetime.datetime.utcnow().strftime('%Y%m%d-%H:%M:%S.%f')[:-3]
                            message.setField(60,sending_time)
                            message.getHeader().setField(fix.BeginString(session_id.getBeginString().getString()))
                            message.getHeader().setField(fix.MsgType(fix.MsgType_OrderCancelRequest))
                            message.getHeader().setField(fix.SenderCompID(session_id.getSenderCompID().getString()))
                            message.getHeader().setField(fix.TargetCompID(session_id.getTargetCompID().getString()))
                            message.getHeader().setField(fix.MsgSeqNum(self.get_outgoing_seq_num(session_id)))
                            message.setField(fix.ClOrdID(self.generate_clordid()))

                            message.setField(fix.OrigClOrdID(org_clordid))
                            message.setField(fix.Side(side))
                            message.setField(21035, tag_21035)
                            print(message)
                            
                            # Send the Order Cancel Request on the same session as the corresponding ClOrdID
                            fix.Session.sendToTarget(message, session_obj)
                        else:
                            print(f"Error: ClOrdID Session info not found for ClOrdID={org_clordid}")
                            return fix.Message()

                    else:
                        print(f"Error: ClOrdID info not found for ClOrdID={org_clordid}")
                        return fix.Message()
                                

                else:
                    # Handle the case when no captured ClOrdIDs are available
                    print("No captured ClOrdIDs available for order cancel")
                    return fix.Message()

                return message

            else:
                # Unknown message type
                return None

            return message if message is not None else fix.Message()



    def increment_outgoing_seq_num(self, session_id):
        session = fix.Session.lookupSession(fix.SessionID(session_id))
        if session is not None:
            session.incrementNextSenderMsgSeqNum()



    def send_heartbeats(self, session_id, interval):
        while sessions[session_id]:
            session = fix.Session.lookupSession(fix.SessionID(session_id))
            if session is not None:
                heartbeat_message = fix.Message()
                heartbeat_message.getHeader().setField(34, str(self.get_outgoing_seq_num(session_id)))
                fix.Session.sendToTarget(heartbeat_message, session_id)
                self.increment_outgoing_seq_num(session_id)
            time.sleep(interval)

    def generate_load(self):
        load = []
        for message_type, weight in self.message_weights.items():
            weight = int(weight)
            print(weight)
            template = self.generate_template_for_message_type(message_type)
            if template:
                load.extend([message_type.lower()] * weight)

        print(f"Generated load: {load}")
        random.shuffle(load)
        load_length = len(load)
        iterations = int(self.message_rate * self.send_duration)

        if iterations > load_length:
            quotient, remainder = divmod(iterations, load_length)
            print(f"Repeating load: {quotient} times, with remainder: {remainder}")
            load = load * quotient + load[:remainder]
        else:
            load = load[:iterations]

        return load

    def generate_template_for_message_type(self, message_type):
        if message_type.lower() == "logon":
            return "logon"
        elif message_type.lower() == "newordersingle":
            return "new_order_template"
        elif message_type.lower() == "orderreplace":
            return "order_replace_template"
        elif message_type.lower() == "ordercancel":
            return "order_cancel_template"
        else:
            return None
        
    def get_log_file(self):
        os.makedirs(self.log_directory, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H")
        log_file_name = f"log_file_{timestamp}.log"
        print(os.path.join(self.log_directory, log_file_name))
        return os.path.join(self.log_directory, log_file_name)

    def run(self):
        settings = fix.SessionSettings(self.connection_config_file)
        application = fix.SocketInitiator(self, fix.FileStoreFactory(settings), settings)
        application.start()

        while not all(session.isLoggedOn() for session in self.sessions.values()):
            time.sleep(1)

        load = self.generate_load()

        start_time = time.time()
        message_count = 0

        while True:
            elapsed_time = time.time() - start_time

            if elapsed_time >= self.send_duration:
                break

            if message_count >= len(load):
                message_count = 0
            print(self.sessions)

            for session_id in self.sessions:
                session = self.sessions[session_id]
                print(session)

                if session is not None and session.isLoggedOn():
                    message = self.generate_message(load[message_count], session_id)
                    fix.Session.sendToTarget(message, session_id)
                message_count += 1

            time.sleep(1)

        application.stop()


# Read configuration from config.ini
config = configparser.ConfigParser()
config.read("config.ini")

# Load configuration values
connection_config_file = config.get("LoadGenerator", "connection_config_file")
log_file = config.get("LoadGenerator", "log_file")
message_rate = float(config.get("LoadGenerator", "message_rate"))
send_duration = int(config.get("LoadGenerator", "send_duration"))
symbols = config.get("LoadGenerator", "symbols").split(",")


message_weights = dict(config.items("MessageTypes"))

# Initialize the FIX application
app = MyApplication(message_weights, message_rate)
app.connection_config_file = connection_config_file
app.send_duration = send_duration


# Run the FIX application
app.run()

