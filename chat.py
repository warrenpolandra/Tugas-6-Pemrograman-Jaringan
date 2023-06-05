import sys
import os
import json
import uuid
import logging
from queue import Queue
import threading
import socket


class ServerToServerThread(threading.Thread):
    def __init__(self, chat, target_realm_address, target_realm_port):
        self.chat = chat
        self.target_realm_address = target_realm_address
        self.target_realm_port = target_realm_port
        self.queue = Queue()  # Queue for outgoing messages to the other realm
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        threading.Thread.__init__(self)

    def run(self):
        self.sock.connect((self.target_realm_address, self.target_realm_port))
        while True:
            # Check if there are messages to be sent
            while not self.queue.empty():
                msg = self.queue.get()
                self.sock.sendall(msg.encode())

            # # Menerima data dari realm lain
            # data = self.sock.recv(1024)
            # if data:
            #     command = data.decode()
            #     response = self.chat.proses(command)
            #     # Mengirim balasan ke realm lain
            #     self.sock.sendall(json.dumps(response).encode())

    def put(self, msg):
        self.queue.put(msg)


class Chat:
    def __init__(self):
        self.sessions = {}
        self.users = {'messi': {'nama': 'Lionel Messi', 'negara': 'Argentina', 'password': 'surabaya', 'incoming': {},
                                'outgoing': {}},
                      'henderson': {'nama': 'Jordan Henderson', 'negara': 'Inggris', 'password': 'surabaya',
                                    'incoming': {}, 'outgoing': {}},
                      'lineker': {'nama': 'Gary Lineker', 'negara': 'Inggris', 'password': 'surabaya', 'incoming': {},
                                  'outgoing': {}},
                      'maguire': {'nama': 'Harry Maguire', 'negara': 'Inggris', 'password': 'surabaya', 'incoming': {},
                                  'outgoing': {}}}
        self.servers = {'A': ServerToServerThread(self, '127.0.0.1', 8889),
                        'B': ServerToServerThread(self, '127.0.0.1', 9000),
                        'C': ServerToServerThread(self, '127.0.0.1', 9001)}
        self.running_servers = []

    def proses(self, data):
        j = data.split(" ")
        try:
            command = j[0].strip()
            if command == 'auth':
                username = j[1].strip()
                password = j[2].strip()
                logging.warning("AUTH: auth {} {}".format(username, password))
                return self.autentikasi_user(username, password)
            elif command == 'send':
                sessionid = j[1].strip()
                usernameto = j[2].strip()
                message = ""
                for w in j[3:]:
                    message = "{} {}".format(message, w)
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning(
                    "SEND: session {} send message from {} to {}".format(sessionid, usernamefrom, usernameto))
                return self.send_message(sessionid, usernamefrom, usernameto, message)
            elif command == 'inbox':
                sessionid = j[1].strip()
                username = self.sessions[sessionid]['username']
                logging.warning("INBOX: {}".format(sessionid))
                return self.get_inbox(username)
            elif command == 'sendgroup':
                sessionid = j[1].strip()
                group_usernames = j[2].strip().split(',')
                message = ""
                for w in j[3:]:
                    message = "{} {}".format(message, w)
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning(
                    "SEND: session {} send message from {} to {}".format(sessionid, usernamefrom, group_usernames))
                return self.send_group_message(sessionid, usernamefrom, group_usernames, message)
            elif command == 'connect':
                server_id = j[1].strip()
                return self.connect(server_id)
            elif command == 'addrealm':
                realm_id = j[1].strip()
                target_realm_address = j[2].strip()
                target_realm_port = int(j[3].strip())
                self.add_realm(realm_id, target_realm_address, target_realm_port)
                return {'status': 'OK'}
            elif command == 'sendrealm':
                sessionid = j[1].strip()
                server_id = j[2].strip()
                usernameto = j[3].strip()
                message = ""
                for w in j[4:]:
                    message = "{} {}".format(message, w)
                logging.warning("SENDREALM: session {} send message from {} to {} in realm {}".format(sessionid,
                                                                                                      self.sessions[
                                                                                                          sessionid][
                                                                                                          'username'],
                                                                                                      usernameto,
                                                                                                      server_id))
                return self.send_realm_message(sessionid, server_id, usernameto, message)
            elif command == 'sendgrouprealm':
                sessionid = j[1].strip()
                realm_id = j[2].strip()
                group_usernames = j[3].strip().split(',')
                message = ""
                for w in j[4:]:
                    message = "{} {}".format(message, w)
                logging.warning("SENDGROUPREALM: session {} send message from {} to {} in realm {}".format(sessionid,
                                                                                                           self.sessions[
                                                                                                               sessionid][
                                                                                                               'username'],
                                                                                                           group_usernames,
                                                                                                           realm_id))
                return self.send_group_realm_message(sessionid, realm_id, group_usernames, message)
            elif command == 'server_inbox':
                username_from = j[1].strip()
                username_to = j[2].strip()
                message = ""
                for w in j[3:]:
                    message = "{} {}".format(message, w)
                self.server_inbox(username_from, username_to, message)
            else:
                return {'status': 'ERROR', 'message': '**Protocol Tidak Benar'}
        except KeyError:
            return {'status': 'ERROR', 'message': 'Informasi tidak ditemukan'}
        except IndexError:
            return {'status': 'ERROR', 'message': '--Protocol Tidak Benar'}

    def autentikasi_user(self, username, password):
        if username not in self.users:
            return {'status': 'ERROR', 'message': 'User Tidak Ada'}
        if self.users[username]['password'] != password:
            return {'status': 'ERROR', 'message': 'Password Salah'}
        tokenid = str(uuid.uuid4())
        self.sessions[tokenid] = {'username': username, 'userdetail': self.users[username]}
        return {'status': 'OK', 'tokenid': tokenid}

    def get_user(self, username):
        if username not in self.users:
            return False
        return self.users[username]

    def connect(self, server_id):
        if server_id in self.running_servers:
            return {'status': 'ERROR', 'message': 'Server {} is already connected'.format(server_id)}
        else:
            self.servers[server_id].start()
            self.running_servers.append(server_id)
            return {'status': 'OK'}

    def send_message(self, sessionid, username_from, username_dest, message):
        if sessionid not in self.sessions:
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        s_fr = self.get_user(username_from)
        s_to = self.get_user(username_dest)

        if s_fr == False or s_to == False:
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}

        message = {'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message}
        outqueue_sender = s_fr['outgoing']
        inqueue_receiver = s_to['incoming']
        try:
            outqueue_sender[username_from].put(message)
        except KeyError:
            outqueue_sender[username_from] = Queue()
            outqueue_sender[username_from].put(message)
        try:
            inqueue_receiver[username_from].put(message)
        except KeyError:
            inqueue_receiver[username_from] = Queue()
            inqueue_receiver[username_from].put(message)
        return {'status': 'OK', 'message': 'Message Sent'}

    def send_group_message(self, sessionid, username_from, group_usernames, message):
        if sessionid not in self.sessions:
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        s_fr = self.get_user(username_from)
        if s_fr is False:
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        for username_dest in group_usernames:
            s_to = self.get_user(username_dest)
            if s_to is False:
                continue
            message = {'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message}
            outqueue_sender = s_fr['outgoing']
            inqueue_receiver = s_to['incoming']
            try:
                outqueue_sender[username_from].put(message)
            except KeyError:
                outqueue_sender[username_from] = Queue()
                outqueue_sender[username_from].put(message)
            try:
                inqueue_receiver[username_from].put(message)
            except KeyError:
                inqueue_receiver[username_from] = Queue()
                inqueue_receiver[username_from].put(message)
        return {'status': 'OK', 'message': 'Message Sent'}

    def get_inbox(self, username):
        s_fr = self.get_user(username)
        incoming = s_fr['incoming']
        msgs = {}
        for users in incoming:
            msgs[users] = []
            while not incoming[users].empty():
                msgs[users].append(s_fr['incoming'][users].get_nowait())
        return {'status': 'OK', 'messages': msgs}

    def server_inbox(self, username_from, username_to, message):
        s_fr = self.get_user(username_from)
        s_to = self.get_user(username_to)
        message = {'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message}
        outqueue_sender = s_fr['outgoing']
        inqueue_receiver = s_to['incoming']
        try:
            outqueue_sender[username_from].put(message)
        except KeyError:
            outqueue_sender[username_from] = Queue()
            outqueue_sender[username_from].put(message)
        try:
            inqueue_receiver[username_from].put(message)
        except KeyError:
            inqueue_receiver[username_from] = Queue()
            inqueue_receiver[username_from].put(message)

    def add_realm(self, realm_id, target_realm_address, target_realm_port):
        self.servers[realm_id] = ServerToServerThread(self, target_realm_address, target_realm_port)
        self.servers[realm_id].start()

    def send_realm_message(self, sessionid, realm_id, username_to, message):
        if sessionid not in self.sessions:
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if realm_id not in self.servers:
            return {'status': 'ERROR', 'message': 'Realm Tidak Ada'}
        username_from = self.sessions[sessionid]['username']
        self.servers[realm_id].put('server_inbox {} {} {} \r\n'.format(username_from, username_to, message))
        return {'status': 'OK', 'message': 'Message Sent to Realm'}

    def send_group_realm_message(self, sessionid, realm_id, group_usernames, message):
        if sessionid not in self.sessions:
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if realm_id not in self.servers:
            return {'status': 'ERROR', 'message': 'Realm Tidak Ada'}
        username_from = self.sessions[sessionid]['username']
        for username_to in group_usernames:
            message = {'msg_from': username_from, 'msg_to': username_to, 'msg': message}
            self.servers[realm_id].put(message)
            self.servers[realm_id].queue.put(message)
        return {'status': 'OK', 'message': 'Message Sent to Group in Realm'}


if __name__ == "__main__":
    j = Chat()
