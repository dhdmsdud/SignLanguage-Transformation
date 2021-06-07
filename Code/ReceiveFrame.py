import json
import errno
import os
import struct
from socket import *
from _thread import *

# 최대 전송 데이터 버퍼 크기
MAX_LEN = 1024
HEADER_INDICATOR_LEN = 4


def mkdir(path):
    try:
        os.makedirs(os.path.join(path), exist_ok=True)
    except OSError as e:
        if e.errno != errno.EEXIST:
            print("Failed to create directory!!!!!")
            raise


def threaded(clientSock, clientAddr):
    buffer = bytearray()
    cur_filename = None
    data_transferred = 0

    while True:
        message = clientSock.recv(MAX_LEN)
        buffer += message

        while True:
            index = buffer.find(b'****', HEADER_INDICATOR_LEN + 1)
            if index != -1:
                data_w_header = buffer[:index]
                buffer = buffer[index:]
            else:
                break

            if data_w_header[:4] == b'****':
                if data_w_header[4:8] == b'exit':
                    f.close()
                    print(str(clientAddr), '연결 해제')
                    return

                headerlen = HEADER_INDICATOR_LEN
                namesize = struct.unpack('H', data_w_header[headerlen:headerlen+2])[0]
                headerlen += 2
                filename = data_w_header[headerlen:headerlen+namesize].decode('utf-8')
                headerlen += namesize
                filesize = struct.unpack('L', data_w_header[headerlen:headerlen+4])[0]
                headerlen += 4
                data = data_w_header[headerlen:]

                # print(headerlen, namesize, filename, filesize)

                if cur_filename == filename:
                    f.write(data)
                    data_transferred += len(data)

                else:
                    if cur_filename is not None:
                        f.close()
                        print('파일 %s 받기 완료. 전송량 %d' % (cur_filename, data_transferred))

                    cur_filename = filename

                    filedir = 'getdata/' + filename
                    folders = filedir.split('/')
                    folders.pop()
                    dst = ''
                    data_transferred = 0
                    for i in range(len(folders)):
                        dst += folders[i] + '/'
                        mkdir(dst)
                    print('받을 파일 크기 : ', filesize, '   받을 데이터 : ', filename)

                    f = open(filedir, 'wb')
                    f.write(data)
                    data_transferred += len(data)

            else:
                print(data_w_header)
                print('잘못된 데이터')
                return


if __name__ == "__main__":
    serverSock = socket(AF_INET, SOCK_STREAM)
    serverSock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    serverSock.bind(('', 8004))
    serverSock.listen()

    while True:
        connectionSock, addr = serverSock.accept()
        print(str(addr), '에서 접속했습니다')

        start_new_thread(threaded, (connectionSock, addr))
