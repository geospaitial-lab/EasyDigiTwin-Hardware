from pypylon import pylon

names = {"24471741": "Cam 1",
         "24471746": "Cam 2",
         "24471747": "Cam 3",
         "24471750": "Cam 4",
         "24471752": "Cam 5",
         "24471757": "Cam 6",
         "24471763": "Cam 7",
         "24471766": "Cam 8",
         "24471814": "Cam 9",
         "24471815": "Cam 10",
         "24471819": "Cam 11",
         "24471830": "Cam 12",
         "24471835": "Cam 13"}

tlf = pylon.TlFactory.GetInstance()
devs = tlf.EnumerateDevices()

assert len(devs) == 13

for d in devs:
    d.SetFriendlyName(names[d.GetSerialNumber()])
    print(d.GetModelName(), d.GetSerialNumber(), d.GetFriendlyName())
