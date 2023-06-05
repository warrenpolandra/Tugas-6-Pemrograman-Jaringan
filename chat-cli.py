import socket
import os
import sys
import json

TARGET_IP = "127.0.0.1"


class ChatClient:
    def __init__(self, server):
        self.server = server
        self.portnumber = 8889
        if server == 'A':
            self.portnumber = 8889
        elif server == 'B':
            self.portnumber = 9000
        elif server == 'C':
            self.portnumber = 9001
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = (TARGET_IP, self.portnumber)
        self.sock.connect(self.server_address)
        self.tokenid = ""

    def proses(self, cmdline):
        j = cmdline.split(" ")
        try:
            command = j[0].strip()
            if command == 'auth':
                username = j[1].strip()
                password = j[2].strip()
                return self.login(username, password)
            elif command == 'connect':
                server_id = j[1].strip()
                return self.connect(server_id)
            elif command == 'send':
                address = j[1].strip().split('@')
                usernameto = address[0].strip()
                serverto = address[1].strip()
                message = ""
                for w in j[2:]:
                    message = "{} {}".format(message, w)
                if serverto == self.server:
                    return self.send_message(usernameto, message)
                else:
                    return self.send_message_to_server(serverto, usernameto, message)
            elif command == 'sendgroup':
                group_usernames = j[1].strip()
                message = ""
                for w in j[2:]:
                    message = "{} {}" . format(message, w)
                return self.sendgroupmessage(group_usernames, message)
            elif command == 'inbox':
                return self.inbox()
            elif command == 'addrealm':
                realm_id = j[1].strip()
                target_realm_address = j[2].strip()
                target_realm_port = j[3].strip()
                return self.add_realm(realm_id, target_realm_address, target_realm_port)
            elif command == 'sendgrouprealm':
                realm_id = j[1].strip()
                group_usernames = j[2].strip()
                message = ""
                for w in j[3:]:
                    message = "{} {}" . format(message, w)
                return self.send_group_realm_message(realm_id, group_usernames, message)
            elif command == 'getrealminbox':
                realm_id = j[1].strip()
                return self.get_realm_inbox(realm_id)
            else:
                return "*Maaf, command tidak benar"
        except IndexError:
            return "-Maaf, command tidak benar"

    def sendstring(self, string):
        try:
            self.sock.sendall(string.encode())
            receivemsg = ""
            while True:
                data = self.sock.recv(64)
                print("diterima dari server", data)
                if (data):
                    # data harus didecode agar dapat di operasikan dalam bentuk string
                    receivemsg = "{}{}" . format(receivemsg, data.decode())
                    if receivemsg[-4:] == '\r\n\r\n':
                        print("end of string")
                        return json.loads(receivemsg)
        except:
            self.sock.close()
            return {'status': 'ERROR', 'message': 'Gagal'}

    def login(self, username, password):
        string = "auth {} {} \r\n" . format(username, password)
        result = self.sendstring(string)
        if result['status'] == 'OK':
            self.tokenid = result['tokenid']
            return "username {} logged in, token {} " .format(username, self.tokenid)
        else:
            return "Error, {}" . format(result['message'])

    def connect(self, server_id):
        if self.tokenid == "":
            return "Error, not authorized"
        message = "connect {} \r\n".format(server_id)
        result = self.sendstring(message)
        if result['status'] == 'OK':
            return 'Server {} succesfully connected'.format(server_id)
        else:
            return "Error: {}".format(result['message'])

    def send_message(self, usernameto="xxx", message="xxx"):
        if self.tokenid == "":
            return "Error, not authorized"
        string = "send {} {} {}\r\n" . format(
            self.tokenid, usernameto, message)
        print(string)
        result = self.sendstring(string)
        if result['status'] == 'OK':
            return "message sent to {}" . format(usernameto)
        else:
            return "Error, {}" . format(result['message'])

    def send_message_to_server(self, serverid, usernameto, message):
        if self.tokenid == "":
            return "Error, not authorized"
        string = "sendrealm {} {} {} {}".format(self.tokenid, serverid, usernameto, message)
        result = self.sendstring(string)
        if result['status'] == 'OK':
            return "Message sent to server {}".format(serverid)
        else:
            return "Error: {}".format(result['message'])

    def inbox(self):
        if self.tokenid == "":
            return "Error, not authorized"
        string = "inbox {} \r\n" . format(self.tokenid)
        result = self.sendstring(string)
        if result['status'] == 'OK':
            return "{}" . format(json.dumps(result['messages']))
        else:
            return "Error, {}" . format(result['message'])

    def sendgroupmessage(self, group_usernames="xxx,yyy", message="xxx"):
        if self.tokenid == "":
            return "Error, not authorized"
        string = "sendgroup {} {} {} \r\n" . format(
            self.tokenid, group_usernames, message)
        print(string)
        result = self.sendstring(string)
        if result['status'] == 'OK':
            return "message sent to {}" . format(group_usernames)
        else:
            return "Error, {}" . format(result['message'])

    def add_realm(self, realm_id, target_realm_address, target_realm_port):
        if self.tokenid == "":
            return "Error, not authorized"
        string = "addrealm {} {} {} \r\n" . format(
            realm_id, target_realm_address, target_realm_port)
        result = self.sendstring(string)
        if result['status'] == 'OK':
            return "Realm {} added" . format(realm_id)
        else:
            return "Error, {}" . format(result['message'])

    def send_group_realm_message(self, realm_id, group_usernames, message):
        if self.tokenid == "":
            return "Error, not authorized"
        string = "sendgrouprealm {} {} {} {} \r\n" . format(
            self.tokenid, realm_id, ','.join(group_usernames), message)
        print(string)
        result = self.sendstring(string)
        if result['status'] == 'OK':
            return "message sent to group {} in realm {}" .format(group_usernames, realm_id)
        else:
            return "Error {}".format(result['message'])

    def get_realm_inbox(self, realm_id):
        if self.tokenid == "":
            return "Error, not authorized"
        string = "getrealminbox {} {} \r\n" . format(self.tokenid, realm_id)
        print("Sending: " + string)
        result = self.sendstring(string)
        print("Received: " + str(result))
        if result['status'] == 'OK':
            return "Message received from realm {}: {}".format(realm_id, result['messages'])
        else:
            return "Error, {}".format(result['message'])


if __name__ == "__main__":
    server = 'A'
    try:
        server = sys.argv[1]
    except:
        pass

    if server != 'A' and server != 'B' and server != 'C':
        print("Server tidak ada!")
        sys.exit()

    cc = ChatClient(server)
    while True:
        cmdline = input("Command {}:" . format(cc.tokenid))
        print(cc.proses(cmdline))
