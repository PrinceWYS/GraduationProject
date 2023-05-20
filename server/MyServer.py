from re import U
import socket
from threading import Thread
import time
import json

ADDRESS = ('', 8848)  # 绑定地址
g_socket_server = None  # 负责监听的socket
g_conn_pool = {}  # 连接池
conn_num = 0 # 当前连接数
count = 0 # User编号计数，按进入顺序依次编号，全部断开后重新计数
device_connect = False
camera_connect = False
isLocate = False
device_id = ''
camera_id = ''

def accept_client():
    global g_socket_server
    g_socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
    g_socket_server.bind(ADDRESS)
    g_socket_server.listen(5)  # 最大等待数
    print("server start, wait for client connecting...")
    '''
    接收新连接
    '''
    while True:
        client, info = g_socket_server.accept()  # 阻塞，等待客户端连接
        # 给每个客户端创建一个独立的线程进行管理
        thread = Thread(target=message_handle, args=(client, info))
        thread.setDaemon(True)
        thread.start()
 
 
def message_handle(client, info):
    '''
    消息处理
    '''
    global isLocate
    handle_id = info[1]
    print("new client:" + str(handle_id))
    # 缓存客户端socket对象
    g_conn_pool[handle_id] = client
    global conn_num, count, device_connect, camera_connect, device_id, camera_id
    current = str(handle_id)
    while True:
        try:
            data = client.recv(1024)
            print("receive time: " + (str)((int)(time.time()*1000)))
            jsonstr = data.decode(encoding='utf8')
            print(jsonstr)
            jd = json.loads(jsonstr)
            protocol = jd['protocol']
            role = jd['role']
            position = jd['msg'].split(',')
            print(role+": "+ jd['protocol'] +":")
            print(position)
            if 'login' == protocol:
                # 新用户加入
                conn_num += 1
                count += 1
                uname = 'User' + str(count) # 自动编号作为用户 œ名
                print('on client login, ' + uname)
                # jd['protocol'] = 'conn_num'
                # jd['msg'] = str(conn_num)
                print("当前总人数：" + str(conn_num))
                # 发送当前人数给所有客户端
                # for u in g_conn_pool:
                #     g_conn_pool[u].sendall(json.dumps(jd).encode(encoding='utf8'))
                if 'device' == role:
                    device_connect = True
                    device_id = current
                    print('device connected')
                elif 'camera' == role:
                    camera_connect = True
                    camera_id = current
                    print('camera connected')
            else:
                # 收到客户端操作信息
                # print(jd['protocol'] +":"+ jd['msg'])
                # 直接转发给所有客户端
                for u in g_conn_pool:
                    g_conn_pool[u].sendall(data)

            if device_connect and camera_connect:
                if jd['protocol'] != 'pause':       
                    if jd['protocol'] == 'stop':
                        jd['role'] = 'server'
                        isLocate = True
                    elif isLocate == False:
                        jd['protocol'] = 'location'
                        jd['role'] = 'server'
                    for u in g_conn_pool:
                        print("send time: " + (str)((int)(time.time()*1000)))
                        g_conn_pool[u].sendall(json.dumps(jd).encode(encoding='utf8'))
                else:
                    jd['role'] = 'server'
        except Exception as e:
            print("%s"%e)
            remove_client(handle_id)
            break

def remove_client(handle_id):
    client = g_conn_pool[handle_id]
    global conn_num, count, device_id, camera_id, device_connect, camera_connect
    if handle_id == device_id:
        device_connect = False
        print("device offline")

    if handle_id == camera_id:
        camera_connect = False
        print("camera offline")

    if None != client:
        client.close()
        g_conn_pool.pop(handle_id)
        print("client offline: " + str(handle_id))
        conn_num -= 1
        if(conn_num < 0):
            conn_num = 0
        if(conn_num == 0):
            count = 0
            print("重置房间")
        dic = {'protocol': 'conn_num','msg':str(conn_num)}
        # 转发给所有客户端
        for u in g_conn_pool:
            g_conn_pool[u].sendall(json.dumps(dic).encode(encoding='utf8')) #返回当前人数
        print("当前总人数：" + str(conn_num))

if __name__ == '__main__':
    # 新开一个线程，用于接收新连接
    thread = Thread(target=accept_client)
    thread.setDaemon(True)
    thread.start()
    # 主线程逻辑
    while True:
        time.sleep(0.1) 
