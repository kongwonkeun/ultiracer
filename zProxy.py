#
#
#
import errno
import struct
import sys
from base64 import b64encode
from hashlib import sha1
from socket import error as SocketError
from socketserver import ThreadingMixIn, TCPServer, StreamRequestHandler

import zPipe

#===============================
#
#
GUID_WS = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11' # in rfc 6455 - the websocket protocol
HOST = '127.0.0.1'
PORT = 5331

FIN = 0x80
OPCODE_FLD = 0x0f
OPCODE_CONTINUATION = 0x00
OPCODE_TEXT = 0x01
OPCODE_BINARY = 0x02
OPCODE_CLOSE_CONN = 0x08
OPCODE_PING = 0x09
OPCODE_PONG = 0x0a
MASK = 0x80
PAYLOAD_LEN_FLD = 0x7f
PAYLOAD_LEN_EXT16 = 0x7e
PAYLOAD_LEN_EXT64 = 0x7f

#===============================
#
#
class WebSockServer(ThreadingMixIn, TCPServer):

    address_reuse_allow = True
    daemon_threads = True
    clients = []
    id_counter = 0

    def __init__(self, port=PORT, host=HOST):
        TCPServer.__init__(self, (host, port), WebSockHandler)
        self.port = self.socket.getsockname()[1] # (host, port)
    
    #===========================
    #
    #
    def run_server(self):
        try:
            print('start websocket proxy')
            print('--- type ctrl-c to quit ---')
            self.serve_forever()
        except KeyboardInterrupt:
            print('stop proxy')
            self.server_close()
    
    def kill_server(self):
        print('stop proxy')
        self.server_close()

    def send_message(self, client, msg):
        client['handler'].send_message(msg)
    
    def send_message_to_all(self, msg):
        for client in self.clients:
            self.send_message(client, msg)

    def add_client_cb(self, client, server):
        print('browser connected (id=%d)' % client['id'])

    def remove_client_cb(self, client, server):
        print('browser disconnected (id=%d)' % client['id'])

    def recv_message_cb(self, client, server, message):
        print('browser said (id=%d): %s' % (client['id'], message))

    #===========================
    #
    #
    def recv_message(self, handler, msg):
        client = self.get_client(handler)
        self.recv_message_cb(client, self, msg)

    def recv_ping(self, handler, msg):
        print('ping received')
        handler.send_pong(msg)

    def recv_pong(self, handler, msg):
        pass 

    #===========================
    #
    #
    def add_client(self, handler):
        self.id_counter += 1
        client = {
            'id': self.id_counter,
            'handler': handler,
            'address': handler.client_address
        }
        self.clients.append(client)
        self.add_client_cb(client, self)

    def remove_client(self, handler):
        client = self.get_client(handler)
        self.remove_client_cb(client, self)
        if  client in self.clients:
            self.clients.remove(client)

    def get_client(self, handler):
        for client in self.clients:
            if  client['handler'] == handler:
                return client

#===============================
#
#
class WebSockHandler(StreamRequestHandler):

    def __init__(self, socket, addr, server):
        self.server = server
        StreamRequestHandler.__init__(self, socket, addr, server)
    
    # override
    def setup(self):
        StreamRequestHandler.setup(self)
        self.keep_alive = True
        self.handshake_done = False
        self.client_valid = False

    # override
    def handle(self):
        while self.keep_alive:
            if  not self.handshake_done:
                self.handshake()
            elif self.client_valid:
                self.recv_message()
    
    # override
    def finish(self):
        StreamRequestHandler.finish(self) # ----kong----
        self.server.remove_client(self)

    #===========================
    #
    #
    def recv_message(self):
        try:
            b1, b2 = self.read_bytes(2)
        except SocketError as e:
            if  e.errno == errno.ECONNRESET:
                self.keep_alive = False
                return
            b1, b2 = 0, 0
        except ValueError:
            b1, b2 = 0, 0
        
        fin = b1 & FIN
        opcode = b1 & OPCODE_FLD
        mask = b2 & MASK
        payload_len = b2 & PAYLOAD_LEN_FLD

        if  opcode == OPCODE_CLOSE_CONN:
            self.keep_alive = False
            return
        if  not mask: # client must always be masked
            self.keep_alive = False
            return
        if  opcode == OPCODE_CONTINUATION: # not support
            return
        elif opcode == OPCODE_BINARY: # not support
            return
        elif opcode == OPCODE_TEXT:
            opcode_handler = self.server.recv_message
        elif opcode == OPCODE_PING:
            opcode_handler = self.server.recv_ping
        elif opcode == OPCODE_PONG:
            opcode_handler = self.server.recv_pong
        else:
            self.keep_alive = False
            return

        if  payload_len == 126:
            payload_len = struct.unpack('>H', self.rfile.read(2))[0]
        elif payload_len == 127:
            payload_len = struct.unpack('>Q', self.rfile.read(8))[0]

        masks = self.read_bytes(4)
        message_bytes = bytearray()
        for msg_byte in self.read_bytes(payload_len):
            msg_byte ^= masks[len(message_bytes) % 4]
            message_bytes.append(msg_byte)
        opcode_handler(self, message_bytes.decode('utf-8'))

    def read_bytes(self, num):
        bytes = self.rfile.read(num)
        return bytes

    #===========================
    #
    #
    def handshake(self):
        try:
            headers = self.read_http_headers()
            assert headers['upgrade'].lower() == 'websocket' # if no websocket then AssertionError
        except AssertionError:
            self.keep_alive = False
            return
        try:
            key = headers['sec-websocket-key'] # if no key then KeyError
        except KeyError:
            self.keep_alive = False
            return
        response = self.make_handshake_response(key)
        self.handshake_done = self.request.send(response.encode())
        self.client_valid = True
        self.server.add_client(self)
    
    def read_http_headers(self):
        headers = {}
        http_request = self.rfile.readline().decode().strip()
        assert http_request.upper().startswith('GET') # if not GET then AssertionError
        while True:
            header = self.rfile.readline().decode().strip()
            if  not header:
                break
            head, value = header.split(':', 1)
            headers[head.lower().strip()] = value.strip()
        return headers

    @classmethod
    def make_handshake_response(cls, key):
        return \
            'HTTP/1.1 101 Switching Protocols\r\n' \
            'Upgrade: websocket\r\n' \
            'Connection: Upgrade\r\n' \
            'Sec-WebSocket-Accept: %s\r\n' \
            '\r\n' % cls.make_handshake_response_key(key)
    
    @classmethod
    def make_handshake_response_key(cls, key):
        hash = sha1(key.encode() + GUID_WS.encode())
        response_key = b64encode(hash.digest()).strip()
        return response_key.decode('ASCII')

    #===========================
    #
    #
    def send_message(self, message):
        self.send_text(message)
    
    def send_pong(self, message):
        self.send_text(message, OPCODE_PONG)
    
    def send_text(self, message, opcode=OPCODE_TEXT):
        if  isinstance(message, bytes):
            message = self.decode_utf8(message)
            if  not message:
                return False
        elif isinstance(message, str):
            pass
        else:
            return False

        header = bytearray()
        payload = self.encode_utf8(message)
        payload_len = len(payload)

        if  payload_len <= 125:
            header.append(FIN | opcode)
            header.append(payload_len)
        elif payload_len >= 126 and payload_len <= 65535:
            header.append(FIN | opcode)
            header.append(PAYLOAD_LEN_EXT16)
            header.append(struct.pack('>H', payload_len)) # big-endian unsigned short (16 bits)
        elif payload_len < 18446744073709551616:
            header.append(FIN | opcode)
            header.append(PAYLOAD_LEN_EXT64)
            header.append('>Q', payload_len) # big-endian unsigned long long (64 bits)
        else:
            raise Exception('message is too big')

        self.request.send(header + payload)

    #===========================
    #
    #
    def encode_utf8(self, data):
        try:
            return data.encode('utf-8')
        except UnicodeEncodeError:
            return False
        except Exception:
            raise

    def decode_utf8(self, data):
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            return False
        except Exception:
            raise


#===============================
#
#
if  __name__ == '__main__':

    print('--- type ctrl-c to quit ---')
    server = WebSockServer()
    client = zPipe.PipeClient(callback=server.send_message_to_all)
    server.run_server()
    client.quit()

    sys.exit()

#
#
#