import json
import os
import time
from datetime import datetime
from multiprocessing import Manager

import pytz
from pypylon import pylon

from camera_utils import CameraProcess, SaveProcess, names

with open("/home/ross/run_counter.json", "r") as file:
    run_counter = json.load(file)["counter"]

base_path_1 = "/disk1"
base_path_2 = "/disk2"

run_config = {"start time": datetime.now(pytz.timezone("Europe/Berlin")).isoformat(),
              "run id": run_counter + 1,
              "format": "BayerRG8",
              "gamma": True,
              "color transformation": False,
              "color adjustment": True,
              "white balance": True,
              "exposure": 666.0}


def main():
    os.makedirs(base_path_1, exist_ok=True)
    os.makedirs(base_path_2, exist_ok=True)

    tlf = pylon.TlFactory.GetInstance()
    devs = tlf.EnumerateDevices()

    print(f"Detected {len(devs)} cameras")

    for d in devs:
        print(d.GetModelName(), d.GetSerialNumber(), d.GetIpAddress())  # , d.GetFriendlyName()

    assert len(devs) == 13

    with open(os.path.join(base_path_1, f"run_{run_config['run id']}_config.json"), "w") as file:
        json.dump(run_config, file)

    with open("/home/ross/run_counter.json", "w") as file:
        json.dump({"counter": run_counter + 1}, file)

    cameras = []

    for dev in devs:
        cam = pylon.InstantCamera(tlf.CreateDevice(dev))
        cam.Open()
        cameras.append(cam)
        cam.DeviceInfo.SetFriendlyName(names[cam.DeviceInfo.GetSerialNumber()])

    processes = []

    queues = []

    save_processes = []

    for i in range(4):
        queue = Manager().Queue()
        queues.append(queue)
        base_path = base_path_1 if i % 2 else base_path_2
        save_processes.append(SaveProcess(queue, base_path, run_config["run id"]))

    for idx, cam in enumerate(cameras):
        camera_serial = cam.DeviceInfo.GetSerialNumber()
        print(f"Setting up {cam.DeviceInfo.GetFriendlyName()} ({camera_serial}) with context {idx}")
        cam.UserSetSelector = "Default"
        cam.UserSetLoad.Execute()
        cam.SetCameraContext(idx)
        cam.GevIEEE1588 = True
        cam.ExposureTimeAbs = run_config["exposure"]
        cam.PixelFormat.SetValue(run_config["format"])

        cam.LineSelector = "Line3"
        cam.LineMode = "Input"
        cam.TriggerSelector = "FrameStart"
        cam.TriggerSource = "Line3"
        cam.TriggerMode = "On"

        cam.GammaEnable.SetValue(run_config["gamma"])
        if not run_config["color transformation"]:
            cam.ColorTransformationMatrixFactor.SetValue(0.0)
        cam.ColorAdjustmentEnable.SetValue(run_config["color adjustment"])
        if not run_config["white balance"]:
            cam.BalanceRatioSelector.SetValue("Red")
            cam.BalanceRatioAbs.SetValue(1.0)
            cam.BalanceRatioSelector.SetValue("Green")
            cam.BalanceRatioAbs.SetValue(1.0)
            cam.BalanceRatioSelector.SetValue("Blue")
            cam.BalanceRatioAbs.SetValue(1.0)

        queue = queues[idx % len(queues)]

        process = CameraProcess(cam, queue)
        processes.append(process)

    print("Start recording")

    for process in save_processes:
        process.start()

    for process in processes:
        process.start()

    input("Press Enter to stop recording...")

    print("Stopping")
    for process in processes:
        process.stop()

    for process in save_processes:
        process.stop()

    finish = False
    while not finish:
        time.sleep(0.1)
        finish = True
        for process in save_processes:
            if process.is_alive():
                finish = False


if __name__ == "__main__":
    main()
