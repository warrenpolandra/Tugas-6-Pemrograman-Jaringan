import sys
import os
import json
import uuid
import logging
import threading
import socket
from queue import Queue


class ServerToServerThread(threading.Thread):
    def __init__(self, chat, server_address, server_port):
        self.chat = chat
        self.server_address = server_address
        self.server_port = server_port
        self.queue = Queue()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        threading.Thread.__init__(self)

    def run(self):
        self.sock.connect((self.server_address, self.server_port))
        while True:
            data = self.sock.recv(1024)
            if data:
                command = data.decode()
                response = self.chat.proses(command)
                self.sock.sendall(json.dumps(response).encode())
            while not self.queue.empty():
                message = self.queue.get()
                self.sock.sendall(json.dumps(message).encode())

    def put(self, message):
        self.queue.put(message)


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
            elif command == 'connect':
                server_id = j[1].strip()
                return self.connect(server_id)
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

    def get_inbox(self, username):
        s_fr = self.get_user(username)
        incoming = s_fr['incoming']
        msgs = {}
        for users in incoming:
            msgs[users] = []
            while not incoming[users].empty():
                msgs[users].append(s_fr['incoming'][users].get_nowait())

        return {'status': 'OK', 'messages': msgs}

    def connect(self, server_id):
        if server_id in self.running_servers:
            return {'status': 'ERROR', 'message': 'Server {} is already connected'.format(server_id)}
        else:
            self.servers[server_id].start()
            self.running_servers.append(server_id)
            return {'status: OK'}


if __name__ == "__main__":
    j = Chat()
