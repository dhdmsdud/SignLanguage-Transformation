import datetime
import cv2
import os
import errno
import sys
import RPi.GPIO as GPIO
from PyQt5 import QtCore, QtWidgets, QtGui
from SendFrame import SendFrame
from mqtt_sub import Mqtt_Sub


# settings
savePath = 'saved_data'
fourcc = cv2.VideoWriter_fourcc(*'DIVX')
host = 'ec2-3-35-103-224.ap-northeast-2.compute.amazonaws.com'
port = 5000

Button = 21
GPIO.setmode(GPIO.BCM)
GPIO.setup(Button, GPIO.IN)

def cv2_to_qt(src):
    height, width = src.shape[:2]
    color_swapped_image = cv2.cvtColor(src, cv2.COLOR_BGR2RGB)
    qt_image = QtGui.QImage(color_swapped_image.data, width, height,
                            color_swapped_image.strides[0], QtGui.QImage.Format_RGB888)
    return qt_image


def mkdir(path):
    try:
        os.makedirs(os.path.join(path), exist_ok=True)
    except OSError as e:
        if e.errno != errno.EEXIST:
            print("Failed to create directory!!!!!")
            raise


class ShowVideo(QtCore.QObject):
    # record parameters
    dsize = (112, 112)
    # cap_per_frame = 4
    cap_max_frames = 16

    flag_rec = 0
    flag_name = 0
    button_state = 0
    cnt = 0
    now = None
    vidRec = None
    saveName = ""

    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    camera.set(cv2.CAP_PROP_FPS, 30)

    ret, image = camera.read()
    height, width = image.shape[:2]

    VideoSignal1 = QtCore.pyqtSignal(QtGui.QImage)
    VideoSignal2 = QtCore.pyqtSignal(QtGui.QImage)

    def __init__(self, parent=None):
        super(ShowVideo, self).__init__(parent)

    @QtCore.pyqtSlot()
    def startVideo(self):
        global image

        run_video = True
        push_button1.setEnabled(False)
        push_button1.hide()
        push_button2.show()

        while run_video:
            ret, image = self.camera.read()

            # show roi frame
            cut_width = (self.width - self.height) // 2
            pt1 = (cut_width, 0)
            pt2 = (self.height + cut_width, self.height)

            img_roi = image.copy()
            dst = img_roi[:, cut_width:(self.height + cut_width)]
            dst = cv2.resize(dst, dsize=self.dsize)
            
            #blur
            # gray = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
            dst = cv2.GaussianBlur(dst, (3, 3), 0)

            # show full frame
            cv2.rectangle(img_roi, pt1, pt2, (200, 0, 200), 6)
            qt_image1 = cv2_to_qt(cv2.pyrDown(img_roi))
            self.VideoSignal1.emit(qt_image1)

            # show resized frame
            qt_image2 = cv2_to_qt(dst)
            self.VideoSignal2.emit(qt_image2)
            
            # button check
            if GPIO.input(Button) == 0 and self.button_state == 0:
                self.button_state = 1
                vid.record()

            elif GPIO.input(Button) == 1 and self.button_state == 1:
                self.button_state = 0
            
            # record
            if self.flag_rec:
                self.vidRec.write(dst)
                self.cnt += 1
                # if (self.cnt % self.cap_per_frame) == 1:
                #     cv2.imwrite(savePath + str(self.now) + '/frame' + str(self.cnt) + '.jpg', dst)
                cv2.imwrite(self.saveName + '/frame' + str(self.cnt).zfill(4) + '.jpg', dst)

            loop = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(33, loop.quit)
            loop.exec_()

    @QtCore.pyqtSlot()
    def record(self):
        self.flag_rec = 1 - self.flag_rec
        if self.flag_rec:
            self.cnt = 0
            if self.flag_name:
                self.saveName = savePath + '/' + input_save_name.text()
            else:
                self.now = datetime.datetime.now().strftime("%d_%H%M%S")
                self.saveName = savePath + '/' + str(self.now)

            mkdir(savePath)
            mkdir(self.saveName)
            self.vidRec = cv2.VideoWriter(self.saveName + '.avi',
                                          fourcc, 30.0, (self.dsize[0], self.dsize[1]))
            push_button3.setEnabled(False)
            input_save_name.setEnabled(False)

        else:
            self.vidRec.release()

            # 앞 뒤 자를코드

            # select frames
            per_frame = self.cnt // self.cap_max_frames
            for i in range(1, self.cnt + 1):
                if (i % per_frame) != 0 or i > self.cap_max_frames * per_frame:
                    os.remove(self.saveName + '/frame' + str(i).zfill(4) + '.jpg')

            # transfer frames with socket connection
            clientSock = SendFrame(host, port)
            frameList = os.listdir(self.saveName)
            for frame in frameList:
                clientSock.send(self.saveName + '/' + frame)
            clientSock.close()

            push_button3.setEnabled(True)
            input_save_name.setEnabled(True)
        push_button2.setText({True: "저장", False: "녹화"}[self.flag_rec])

    def setting(self):
        if radio1.isChecked():
            self.flag_name = 0
        else:
            self.flag_name = 1
        disze = int(input_dsize.text())
        cap_per_frame = int(input_cap_frame.text())
        self.dsize = (disze, disze)
        # self.cap_per_frame = cap_per_frame
        self.cap_max_frames = cap_per_frame


class ImageViewer(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ImageViewer, self).__init__(parent)
        self.image = QtGui.QImage()
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawImage(0, 0, self.image)
        self.image = QtGui.QImage()

    def initUI(self):
        self.setWindowTitle('Test')

    @QtCore.pyqtSlot(QtGui.QImage)
    def setImage(self, image):
        if image.isNull():
            print("Viewer Dropped frame!")

        self.image = image
        if image.size() != self.size():
            self.setFixedSize(image.size())
        self.update()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    thread = QtCore.QThread()
    thread.start()
    vid = ShowVideo()
    vid.moveToThread(thread)

    image_viewer1 = ImageViewer()
    image_viewer2 = ImageViewer()

    vid.VideoSignal1.connect(image_viewer1.setImage)
    vid.VideoSignal2.connect(image_viewer2.setImage)

    push_button1 = QtWidgets.QPushButton('카메라 연결')
    push_button2 = QtWidgets.QPushButton('녹화')
    push_button2.hide()
    push_button2.setCheckable(True)
    push_button1.clicked.connect(vid.startVideo)
    push_button2.toggled.connect(vid.record)

    groupBox = QtWidgets.QGroupBox('저장할 파일 이름')
    groupBox.minimumHeight()
    radio1 = QtWidgets.QRadioButton('현재 시간')
    radio2 = QtWidgets.QRadioButton('입력한 이름')
    radio1.setChecked(True)
    input_save_name = QtWidgets.QLineEdit()
    text_dsize = QtWidgets.QLabel('변환 할 이미지 크기')
    input_dsize = QtWidgets.QLineEdit('112')
    input_dsize.setValidator(QtGui.QIntValidator(32, 720))
    # text_cap_frame = QtWidgets.QLabel('프레임 마다 이미지 저장')
    text_cap_frame = QtWidgets.QLabel('저장할 프레임 수')
    input_cap_frame = QtWidgets.QLineEdit('16')
    input_cap_frame.setValidator(QtGui.QIntValidator(1, 30))
    push_button3 = QtWidgets.QPushButton('입력')
    push_button3.clicked.connect(vid.setting)

    vertical_layout = QtWidgets.QVBoxLayout()
    horizontal_layout = QtWidgets.QHBoxLayout()
    horizontal_layout.addWidget(image_viewer1)
    horizontal_layout.addWidget(image_viewer2)

    vertical_layout.addLayout(horizontal_layout)
    vertical_layout.addWidget(push_button1)
    vertical_layout.addWidget(push_button2)

    vertical_layout.addWidget(text_dsize)
    vertical_layout.addWidget(input_dsize)
    vertical_layout.addWidget(text_cap_frame)
    vertical_layout.addWidget(input_cap_frame)
    vertical_layout.addWidget(groupBox)

    groupBox_layout = QtWidgets.QHBoxLayout()
    groupBox.setMinimumHeight(50)
    groupBox_layout.addWidget(radio1)
    groupBox_layout.addWidget(radio2)
    groupBox_layout.addStretch()
    groupBox_layout.addWidget(input_save_name)
    groupBox.setLayout(groupBox_layout)
    vertical_layout.addWidget(push_button3)

    layout_widget = QtWidgets.QWidget()
    layout_widget.setLayout(vertical_layout)

    main_window = QtWidgets.QMainWindow()
    main_window.setCentralWidget(layout_widget)
    main_window.show()
    main_window.move(0, 0)
    
    # mqtt = Mqtt_Sub()
    sys.exit(app.exec_())
