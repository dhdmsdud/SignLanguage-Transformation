import struct
from socket import *
from os.path import exists, getsize
import sys
import threading
from time import sleep

# 최대 전송 데이터 버퍼 크기
MAX_LEN = 1024


# 15.164.148.156
class SendFrame(threading.Thread):
    def __init__(self, host, port):
        super().__init__()
        self.clientSock = socket(AF_INET, SOCK_STREAM)
        self.clientSock.connect((host, port))
        print('연결에 성공했습니다.')

    def send(self, filename):
        # 파일 크기, 이름을 보내는 헤더
        headerstart = '****'  # 메시지 시작 문자
        sendname = ''
        for path in (filename.split('/'))[1:]:
            sendname += path + '/'
        sendname = sendname[:-1]
        namesize = len(sendname)
        filesize = getsize(filename)

        header = headerstart.encode('utf-8') + struct.pack('H', namesize) \
                 + sendname.encode('utf-8') + struct.pack('L', filesize)
        headerlen = len(header)

        data_transferred = 0

        if not exists(filename):
            print("no file")
            sys.exit()

        print("파일 %s 전송 시작" % filename)
        with open(filename, 'rb') as f:
            try:
                data = f.read(MAX_LEN - headerlen - 60)  # 바이트 읽음
                while data:  # 데이터가 없을 때까지
                    data_transferred += len(data)  # 크기 저장
                    self.clientSock.send(header + data)
                    data = f.read(MAX_LEN - headerlen - 60)  # 바이트 읽음
            except Exception as ex:
                print(ex)
        print("전송완료 %s, 전송량 %d" % (filename, data_transferred))
        
        #sleep(0.1)
        #r_message = self.clientSock.recv(MAX_LEN)
        #print(r_message)

    def close(self):
        self.clientSock.sendall(b'****exit****')
        self.clientSock.close()
