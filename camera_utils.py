import os
import time
from multiprocessing import Process, Event, Queue

import numpy as np
from pypylon import pylon

names = {"24471741": "VRU",
         "24471746": "HRO",
         "24471747": "O__",
         "24471750": "VMO",
         "24471752": "VMU",
         "24471757": "HMO",
         "24471763": "VLO",
         "24471766": "HMU",
         "24471814": "VRO",
         "24471815": "HLU",
         "24471819": "HRU",
         "24471830": "VLU",
         "24471835": "HLO"}


class CameraProcess(Process):
    def __init__(self, camera: pylon.InstantCamera, queue: Queue):
        super(CameraProcess, self).__init__()
        self.cam = camera
        self.queue = queue
        self.exit = Event()
        self.single_image = Event()
        self.mode = "multi"
        self.serial_number = camera.DeviceInfo.GetSerialNumber()
        self.name = camera.DeviceInfo.GetFriendlyName()
        self.times = []
        self.image_nr = 0

    def run(self) -> None:
        self.cam.StartGrabbing()
        _time = time.perf_counter()
        while not self.exit.is_set():
            # try:
            with self.cam.RetrieveResult(pylon.waitForever) as res:
                if res.GrabSucceeded():
                    # print(f"{self.serial_number} took an image")
                    if self.mode == "multi" or self.single_image.is_set():
                        # img_nr = res.ImageNumber
                        array = res.Array
                        # array = res.Buffer

                        # print(f"{self.serial_number} took an image")
                        self.queue.put({"serial_number": self.serial_number,
                                        "name": self.name,
                                        "image_number": self.image_nr,
                                        "timestamp": res.GetTimeStamp(),
                                        "image": array})
                        self.times.append(time.perf_counter() - _time)
                        self.image_nr += 1
                        _time = time.perf_counter()
                        self.single_image.clear()
            # except:
            #     print(f"Problem with {self.serial_number}")

        self.cam.StopGrabbing()
        if len(self.times) > 0:
            print(f"Average FPS for {self.serial_number}: {len(self.times) / sum(self.times)}")
        else:
            print(f"No Images for {self.serial_number}")

    def stop(self):
        print(f"exiting {self.serial_number}")
        self.exit.set()

    def take_single_image(self):
        self.single_image.set()

    def change_mode(self, new_mode):
        self.mode = new_mode


class SaveProcess(Process):
    def __init__(self, queue: Queue, base_save_path, run_id, test_images=False):
        super(SaveProcess, self).__init__()
        self.queue = queue
        self.base_path = base_save_path
        self.run_id = run_id
        self.exit = Event()
        self.times = []
        self.test_images = test_images

    def run(self) -> None:
        _time = time.perf_counter()
        while not self.exit.is_set() or not self.queue.empty():
            if not self.queue.empty():
                data = self.queue.get()
                if self.test_images:
                    filename_numpy = os.path.join(self.base_path, f"test_{data['name']}"
                                                                  f"_img_{data['image_number']}.npy")
                else:
                    filename_numpy = os.path.join(self.base_path, f"run_{self.run_id}_{data['name']}"
                                                                  f"_img_{data['image_number']}"
                                                                  f"_at_{data['timestamp']}.npy")
                np.save(filename_numpy, data["image"])
                self.times.append(time.perf_counter() - _time)
                _time = time.perf_counter()

        if len(self.times) > 0:
            print(f"Average FPS for {self.base_path}: {len(self.times) / sum(self.times)}")
        else:
            print(f"No Images for {self.base_path}")

    def stop(self):
        print(f"exiting SaveProcess")
        self.exit.set()
