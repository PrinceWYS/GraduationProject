import base64
import cv2
import gzip
import hashlib
import hmac
import json
import numpy as np
import os
import pyrealsense2 as rs
import requests
import time
import uuid
import select
import shutil
import socket
import sys
from scipy.spatial.transform import Rotation as Ro

from io import BytesIO
from PIL import Image

class Location:
    def __init__(self):
        self.m_bLocating = False
        self.m_ImageBuffer = None
        self.m_ImageWidth = 0
        self.m_ImageHeight = 0
        self.m_ImageBufferAfterRotate = None
        self.m_ResizeWidth = 0
        self.m_ResizeHeight = 0
        self.m_NeedResize = False
        self.m_SendImgBuffer = None
        self.m_ImageBufferAfterRotate = None
        self.m_FocallenX = 0.0
        self.m_FocallenY = 0.0
        self.m_GlassConfig = self.GlassConfig()
        self.rotation = np.identity(3)
        self.tum = ""
        self.picTime = ""

        self.m_Config = self.Config()
        self.m_TimeOut = False
        self.m_ImageInit = False

        if self.m_GlassConfig is None:
            print("m_GlassConfig is None")
            self.m_GlassConfig = self.GlassConfig()
            self.readGlassConfig(
                "sdcard/stconfig/stglass_config.txt", self.m_GlassConfig)

    def RequestOnceLocation(self, image_path):
        """ 线程
        """
        self.m_bLocating = True
        self.CheckImageAndLocate(image_path)

    def CheckImageAndLocate(self, image_path):
        if image_path is None:
            print("sx: CheckImageAndLocate 1", not self.m_ImageInit)
            if not self.m_ImageInit:
                print("sx: CheckImageAndLocate 2")
                # use rgb cam instead
                self.m_ImageWidth = self.m_RGBCam.width
                self.m_ImageHeight = self.m_RGBCam.height

                print("sx: CheckImageAndLocate 3",
                      self.m_ImageWidth, self.m_ImageHeight)
                if self.m_ImageBuffer is None or len(self.m_ImageBuffer) < self.m_ImageWidth * self.m_ImageHeight:
                    self.m_ImageBuffer = np.zeros(
                        self.m_ImageWidth * self.m_ImageHeight, dtype=np.uint8)
                    self.m_ImageBufferOrig = np.zeros(
                        self.m_ImageWidth * self.m_ImageHeight * 2, dtype=np.uint8)  # original stereo image
                    self.m_ImageBufferAfterRotate = np.zeros(
                        self.m_ImageWidth * self.m_ImageHeight, dtype=np.uint8)
                    self.m_ResizeWidth = self.m_ImageWidth
                    self.m_ResizeHeight = self.m_ImageHeight
                    self.m_NeedResize = self.CheckResize(
                        self.m_ResizeWidth, self.m_ResizeHeight)
                    self.m_SendImgBuffer = np.zeros(
                        self.m_ResizeWidth * self.m_ResizeHeight, dtype=np.uint8)

                print("sx: CheckImageAndLocate 4")
                self.m_FocallenX = (self.m_ImageWidth +
                                    self.m_ImageHeight) / 2.0
                self.m_FocallenY = self.m_FocallenX
                # if not self.m_ARFoundation.TryGetFocalLength(ref m_FocallenX, ref m_FocallenY):
                #    InvokeResultCallback(ARLocationStatus.CHECK_IMAGE_GET_FAIL)
                #    return

                print("sx: CheckImageAndLocate 5 focal",
                      self.m_FocallenX, self.m_FocallenY)
                self.m_ImageInit = True

            image = np.array(self.m_RGBCam.GetPixels())
            image = np.reshape(
                image, (self.m_ImageHeight, self.m_ImageWidth, 4))
            image = image[:, :, :3]  # remove alpha channel
            image = image[::-1, :, :]  # reverse top-bottom
            # convert to grayscale
            image = np.dot(image[..., :3], [0.299, 0.587, 0.114])
            self.m_ImageBuffer = (image * 255).astype(np.uint8)

        else:
            fileList = image_path.split('/')
            picName = fileList[len(fileList)-1]
            self.picTime = picName.split('.')[0]
            # print(self.picTime)
            self.GetLocalImage(image_path)

        self.Locate()

    def GetLocalImage(self, image_path):
        if image_path is not None:
            original_image = Image.open(image_path)
            original_image = original_image.convert(
                'L')  # convert to grayscale
            self.m_ImageBuffer = np.array(original_image)
            self.m_ImageWidth, self.m_ImageHeight = original_image.size
            self.m_ImageBufferAfterRotate = np.zeros(
                self.m_ImageWidth * self.m_ImageHeight, dtype=np.uint8)
            self.m_ResizeWidth = self.m_ImageWidth
            self.m_ResizeHeight = self.m_ImageHeight
            self.m_NeedResize = False
            self.m_SendImgBuffer = np.zeros(
                self.m_ResizeWidth * self.m_ResizeHeight, dtype=np.uint8)
            self.m_FocallenX = (self.m_ImageWidth + self.m_ImageHeight) / 2.0
            self.m_FocallenY = self.m_FocallenX

    def Locate(self):
        np.copyto(self.m_SendImgBuffer, self.m_ImageBufferAfterRotate)
        _ = self.SendLocateData(self.m_ImageBuffer)

    def async_compress_bytes(self, buffer):
        with BytesIO() as compressed_stream:
            with gzip.GzipFile(fileobj=compressed_stream, mode='wb') as gzip_file:
                gzip_file.write(buffer)
            return compressed_stream.getvalue()[:]

    def SendLocateData(self, buffer):
        # 压缩图像数据
        self.imgBuffer = None
        self.imgBuffer = self.async_compress_bytes(buffer)
        # 创建 LocateData 对象
        data = {
            "image": base64.b64encode(self.imgBuffer).decode("utf-8"),
            "cameraConfig": {
                "width": self.m_ResizeWidth,
                "height": self.m_ResizeHeight,
                "fx": self.m_GlassConfig.m_rgbFx,
                "fy": self.m_GlassConfig.m_rgbFy,
                "cx": self.m_GlassConfig.m_rgbCx,
                "cy": self.m_GlassConfig.m_rgbCy,
                "p1": self.m_GlassConfig.m_rgbP1,
                "p2": self.m_GlassConfig.m_rgbP2,
                "p3": self.m_GlassConfig.m_rgbP3,
                "p4": self.m_GlassConfig.m_rgbP4
            },
            "zipType": "gzip"
        }
        # 发送定位请求
        self.RequestLocateNewApi(data, self.OnLocationResultReturn)

    def GetTimeStamp1970(self):
        epoch_time = time.mktime(time.gmtime(0))
        current_time = time.mktime(time.gmtime())
        return str(round(time.time()*1000))

    def OnLocationResultReturn(self, result, isResponse):
        if not isResponse:
            print("Network error...")
            return
        if result['status'] != "SUCCESS":
            print("Locate Fail")
            return
        output_json_str = json.dumps(result)
        
        pose = result['pose']
        self.rotation[0][0] = pose[0]
        self.rotation[0][1] = pose[1]
        self.rotation[0][2] = pose[2]
        self.rotation[1][0] = pose[4]
        self.rotation[1][1] = pose[5]
        self.rotation[1][2] = pose[6]
        self.rotation[2][0] = pose[8]
        self.rotation[2][1] = pose[9]
        self.rotation[2][2] = pose[10]
        
        qx, qy, qz, qw = self.rotation_matrix_to_quaternion(self.rotation)
        
        self.tum = self.picTime + " " + str(result['x']) + " " + str(result['y']) + " " + str(
            result['z']) + " " + str(qx) + " " + str(qy) + " " + str(qz) + " " + str(qw)
        print(self.tum)

        global f
        f.write(self.tum+'\n')

    def LocateDebug(self, str):
        print("[LOCATE]:" + str)

    RequestTimeout = 10

    def RequestLocate(self, requestData, callback):
        print("Start Request")
        url = self.m_Config.Location_Base_URL
        print(self.m_Config.appKey)
        headers = {
            "Content-Type": "application/json",
            "packageName": "testPackageName",
            "Debug-Mode": "true",
            "App-Key": self.m_Config.appKey,
            "App-Secret": self.m_Config.appSecret
        }
        data = json.dumps(requestData)
        response = requests.post(
            url, data=data, headers=headers, timeout=self.RequestTimeout)

        if response.status_code != 200:
            print("WebRequest Error:", response.status_code, response.reason)
            callback(None, False)
            print("ErrorText:", response.text)
            return

        print(">>>Receive Text:", response.text)
        output = json.loads(response.text)
        callback(output, True)

    def RequestLocateNewApi(self, requestData, callback):
        requestUrl = self.m_Config.Location_Base_URL
        # requestUrl = self.m_Config.Location_Base_URL
        uid = str(uuid.uuid4())
        # print('uid: ', uid)

        headers = {
            "Content-Type": "application/json",
            "Request-Origin": "HTTP",  # or "iOS" or "HTTP"
            "App-Key": self.m_Config.appKey,
            # "Request-Timestamp": self.GetTimeStamp1970(),
            "Request-Timestamp": self.GetTimeStamp1970(),
            "Request-Uuid": uid,
            "Accept": "application/json",
            "Signature-Headers": "",
            "Content-MD5": self.CreateMD5Hash(json.dumps(requestData).encode('utf-8')),
            "packageName": "testPackageName",
            "Debug-Mode": "true",
            "camera-width": str(640),
            "camera-height": str(480),
            "image_type": str(1)
        }

        headers["Request-Signature"] = self.generateSignature(
            "POST", headers["Content-MD5"], requestUrl, self.m_Config.appSecret)

        response = requests.post(
            requestUrl, json=requestData, headers=headers, timeout=self.RequestTimeout)

        if response.status_code != 200:
            print("WebRequest Error: " + response.text, response.status_code)
            callback(None, False)
            return

        output = json.loads(response.text)
        callback(output, True)

    def rotation_matrix_to_quaternion(self, R):
        # 计算四元数
        q = Ro.from_matrix(R).as_quat()
        return q[0], q[1], q[2], q[3]

    def CreateMD5Hash(self, input_bytes):
        md5_hash = hashlib.md5(input_bytes)
        # md5_hash.update()
        hex_digest = md5_hash.hexdigest()
        # print('MD5: ', base64.b64encode(
            # hex_digest.encode("utf-8")).decode("utf-8"))
        return base64.b64encode(hex_digest.encode("utf-8")).decode("utf-8")

    def generateSignature(self, method, md5, url, secret):
        str_builder = ""

        if method == "POST":
            str_builder += "POST\n"
        elif method == "GET":
            str_builder += "GET\n"
        elif method == "PUT":
            str_builder += "PUT\n"
        elif method == "DELETE":
            str_builder += "DELETE\n"
        if md5:
            str_builder += md5
            str_builder += "\n"
        else:
            str_builder += "\n"

        paths = url.split('?')
        str_builder += paths[0]
        sortParams = []
        if len(paths) > 1:
            param = paths[1]
            requestParams = param.split('&')
            requestParams.sort()
            for request_param in requestParams:
                sortParams.append(request_param)
            str_builder += '?' + '&'.join(sortParams)
        message = ''.join(str_builder).encode('utf-8')
        secret_bytes = secret.encode('utf-8')
        signature = hmac.new(secret_bytes, message, hashlib.sha256)
        return base64.b64encode(signature.digest()).decode('utf-8')

    class GlassConfig:
        def __init__(self):
            self.m_eyeWidth = 0
            self.m_eyeHeight = 0
            self.m_refreshRate = 0

            self.m_leftFx = 0.0
            self.m_leftFy = 0.0
            self.m_leftCx = 0.0
            self.m_leftCy = 0.0
            self.m_leftRotX = 0.0
            self.m_leftRotY = 0.0
            self.m_leftRotZ = 0.0
            self.m_leftPosX = 0.0
            self.m_leftPosY = 0.0
            self.m_leftPosZ = 0.0

            self.m_rightFx = 0.0
            self.m_rightFy = 0.0
            self.m_rightCx = 0.0
            self.m_rightCy = 0.0
            self.m_rightRotX = 0.0
            self.m_rightRotY = 0.0
            self.m_rightRotZ = 0.0
            self.m_rightPosX = 0.0
            self.m_rightPosY = 0.0
            self.m_rightPosZ = 0.0

            self.m_leftCamFx = 0.0
            self.m_leftCamFy = 0.0
            self.m_leftCamCx = 0.0
            self.m_leftCamCy = 0.0
            self.m_leftCamK1 = 0.0
            self.m_leftCamK2 = 0.0
            self.m_leftCamK3 = 0.0
            self.m_leftCamK4 = 0.0

            # self.m_rgbFx = 912.878
            # self.m_rgbFy = 911.218
            # self.m_rgbCx = 635.101
            # self.m_rgbCy = 360.478
            self.m_rgbCx = 316.734
            self.m_rgbCy = 240.319
            self.m_rgbFx = 608.586
            self.m_rgbFy = 607.479
            self.m_rgbP1 = 0.0
            self.m_rgbP2 = 0.0
            self.m_rgbP3 = 0.0
            self.m_rgbP4 = 0.0

    class Config:
        def __init__(self):
            self.appKey = '29da1c7918fb4f698789cf846cbef615'
            self.appSecret = '6c8a1815714341cc9440'
            self.Location_Base_URL = 'https://mr-stage.sensetime.com/api/app/positioning/scheduler/v1/regions/gAj84noD?'\
                                     'algoVersion=v4&buildingCode=Xr3GMF8Y&blockCode=wtb2IUh3&floorNum=4&tenantId=a93afefb-62e7-4c5a-90ab-f3768a23434a'
            self.TenantId = 'a93afefb-62e7-4c5a-90ab-f3768a23434a'
            self.RegionCode = 'gAj84noD'
            self.BuildingCode = 'Xr3GMF8Y'
            self.BlockCode = 'wtb2IUh3'
            self.PoiURL = 'https://mr-stage.sensetime.com/api/poi-discovery/v1/sites'
            self.AlgoVersion = 'v4'

if __name__ == '__main__':
    f = open("./camera.tum",'w')

    files =os.listdir("./images") #采用listdir来读取所有文件
    files.sort() #排序
    s= []                   #创建一个空列表
    for file_ in files:     #循环读取每个文件名
        f_name = str(file_)
        Location().RequestOnceLocation('/home/cvg/Downloads/location/images/'+f_name)
