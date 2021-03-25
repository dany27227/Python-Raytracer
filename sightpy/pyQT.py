import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QObject, QThread, pyqtSignal

class App(QWidget):

    def __init__(self, Sc):
        super().__init__()
        self.title = 'render window'
        self.left = 200
        self.top = 200
        self.width = Sc.camera.screen_width
        self.height = Sc.camera.screen_height

        self.initUI(Sc)

    def initUI(self, Sc):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # Create widget
        self.label = QLabel(self)
        pixmap = QPixmap(Sc.camera.screen_width, Sc.camera.screen_height)
        self.label.setPixmap(pixmap)
        self.label.adjustSize()

        self.show()

    def runLongTask(self, Sc, progResStep, threads):
        if progResStep == 0:
            # Step 2: Create a QThread object
            self.thread = QThread()
            # Step 3: Create a worker object
            self.worker = Worker(Sc, progResStep, threads)
            # Step 4: Move worker to the thread
            self.worker.moveToThread(self.thread)
            # Step 5: Connect signals and slots
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.samplePass.connect(self.refresh)
            # Step 6: Start the thread
            self.thread.start()

        elif progResStep == 1:
            # Step 2: Create a QThread object
            self.thread2 = QThread()
            # Step 3: Create a worker object
            self.worker2 = Worker(Sc, progResStep, threads)
            # Step 4: Move worker to the thread
            self.worker2.moveToThread(self.thread2)
            # Step 5: Connect signals and slots
            self.thread2.started.connect(self.worker2.run)
            self.worker2.finished.connect(self.thread2.quit)
            self.worker2.finished.connect(self.worker2.deleteLater)
            self.thread2.finished.connect(self.thread2.deleteLater)
            self.worker2.samplePass.connect(self.refresh)
            # Step 6: Start the thread
            self.thread2.start()

        elif progResStep == 2:
            # Step 2: Create a QThread object
            self.thread3 = QThread()
            # Step 3: Create a worker object
            self.worker3 = Worker(Sc, progResStep, threads)
            # Step 4: Move worker to the thread
            self.worker3.moveToThread(self.thread3)
            # Step 5: Connect signals and slots
            self.thread3.started.connect(self.worker3.run)
            self.worker3.finished.connect(self.thread3.quit)
            self.worker3.finished.connect(self.worker3.deleteLater)
            self.thread3.finished.connect(self.thread3.deleteLater)
            self.worker3.samplePass.connect(self.refresh)
            # Step 6: Start the thread
            self.thread3.start()


    def refresh(self, sample):
        if sample == 0 or sample == 1:
            newpixmap = QPixmap(f"G:/Projects/Python/Python-Raytracer/images/progThread{sample + 1}.png")
            newpixmap = newpixmap.scaled(self.width, self.height)
        else:
            newpixmap = QPixmap(f"G:/Projects/Python/Python-Raytracer/images/progThread{sample + 1}.png")
        self.label.setPixmap(newpixmap)
        self.label.update()
        self.label.adjustSize()



class Worker(QObject):
    finished = pyqtSignal()
    samplePass = pyqtSignal(int)

    def __init__(self, Sc, progResStep, threads, parent=None):
        QObject.__init__(self, parent)
        self.Sc = Sc
        self.progResStep = progResStep
        self.threads = threads

    def run(self):
        self.Sc.render(worker=self, progResStep=self.progResStep, threads=self.threads, samples_per_pixel=6)

        self.finished.emit()

        # you are going to need more than 10 samples to remove the noise. At least 1000 for a nice image.
        #img.save("cornell_box.png")