import os
import subprocess
import numpy as np
from scipy.spatial.transform import Rotation as R

mypath = "" # add your data path


def se3(x, y, z, a, b, c, d):
    r = R.from_quat([a, b, c, d])
    R_mat = r.as_matrix()

    # 将旋转矩阵和平移向量组合成SE(3)变换矩阵
    T = np.eye(4)
    T[:3, :3] = R_mat
    T[:3, 3] = [x, y, z]

    return T


def se3toPos(T):
    t = T[:3, 3]
    R_mat = T[:3, :3]
    r = R.from_matrix(R_mat)
    quat = r.as_quat()
    return t, quat


def translate(item, transform, scale):
    list = item.split()
    newList = list[0]
    T = se3(float(list[1]), float(list[2]), float(list[3]), float(
        list[4]), float(list[5]), float(list[6]), float(list[7]))
    newSE3 = scale * np.dot(transform, T)
    newPos, newQuat = se3toPos(newSE3)
    # print(newPos)
    # print(newQuat)

    newList = newList + " " + str(newPos[0]) + " " + str(newPos[1]) + " " + str(newPos[2]) + \
        " " + str(newQuat[0]) + " " + str(newQuat[1]) + \
        " " + str(newQuat[2]) + " " + str(newQuat[3]) + "\n"

    return newList


def run_evo_ape(path):
    # 要执行的命令及其参数
    command = ['evo_ape', 'tum', path +
               '/device.tum', path+'/newDevice.tum', '-vas']

    # 执行命令，并获取输出结果
    result = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 打印输出结果
    # print(result.stdout.decode('utf-8'))

    # 如果命令返回非零退出码，则打印错误信息
    if result.returncode != 0:
        print(result.stderr.decode('utf-8'))
    return result.stdout.decode('utf-8')


if __name__ == '__main__':
    RMSEfile = open(mypath + "rmse.txt", "w")
    for dirpath, dirnames, filenames in os.walk(mypath):
        # print(dirpath)
        if (dirpath != '/Users/wangyuesong/Downloads/实验数据/轨迹标定一'):
            print("calculating the data in " + dirpath + " ...")
            file = open(dirpath+"/camera.tum", "r")
            newFile = open(dirpath+"/newDevice.tum", "w")
            data = open(dirpath + "/data.txt", "r")

            temp = data.readlines()
            line1 = temp[1][2:-2].split()
            line2 = temp[2][2:-2].split()
            line3 = temp[3][2:-3].split()
            line4 = temp[5][1:-2].split()

            transform = np.array(
                [[float(line1[0]), float(line1[1]), float(line1[2]), float(line4[0])],
                 [float(line2[0]), float(line2[1]),
                 float(line2[2]), float(line4[1])],
                 [float(line3[0]), float(line3[1]),
                 float(line3[2]), float(line4[2])],
                 [0, 0, 0, 1]]
            )

            scale = float(temp[6][18:])
            # print(scale)
            for line in file:
                newFile.writelines(translate(line, transform, scale))

            file.close()
            newFile.close()
            data.close()

            msg = run_evo_ape(dirpath)
            index = msg.find('rmse')
            rmse = msg[index: index+14]
            # print(rmse)
            RMSEfile.writelines(dirpath + " " + rmse)
    RMSEfile.close()
    with open(mypath + "rmse.txt", 'r') as f:
        # 读取所有行并进行排序
        sorted_lines = sorted(f.readlines())

    # 打开同一文件以写入排序后的行
    with open(mypath + "rmse.txt", 'w') as f:
        # 将排序后的行写回到文件中
        f.writelines(sorted_lines)
