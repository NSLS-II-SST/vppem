from ophyd import EpicsSignalRO
from ophyd.areadetector import AreaDetector, ImagePlugin, CamBase
from ophyd.areadetector.base import ADComponent as ADCpt, EpicsSignalWithRBV as SignalWithRBV

from ophyd.areadetector.plugins import HDF5Plugin_V33
from sst_base.cameras import HDF5PluginWithProposalDirectory
from nslsii.ad33 import SingleTriggerV33
from nbs_bl.beamline import GLOBAL_BEAMLINE as bl

import time as ttime
from collections import OrderedDict

class PCOEdgeCam(CamBase):
    adc_mode = ADCpt(SignalWithRBV, "AdcMode")
    camera_setup = ADCpt(SignalWithRBV, "CameraSetup")
    readout_mode = ADCpt(SignalWithRBV, "ReadoutMode")
    bit_alignment = ADCpt(SignalWithRBV, "BitAlignment")
    pixel_rate = ADCpt(SignalWithRBV, "PixelRate")

class PCOHDF5Plugin(HDF5PluginWithProposalDirectory):
    def warmup(self):
        """
        A convenience method for 'priming' the plugin.

        The plugin has to 'see' one acquisition before it is ready to capture.
        This sets the array size, etc.
        """
        self.enable.set(1).wait()
        sigs = OrderedDict(
            [
                (self.parent.cam.array_callbacks, 1),
                (self.parent.cam.image_mode, "Single"),
                (self.parent.cam.trigger_mode, 1),
                # just in case tha acquisition time is set very long...
                (self.parent.cam.acquire_time, 1),
                (self.parent.cam.acquire_period, 1),
                (self.parent.cam.acquire, 1),
            ]
        )

        original_vals = {sig: sig.get() for sig in sigs}

        for sig, val in sigs.items():
            ttime.sleep(0.1)  # abundance of caution
            sig.set(val).wait()

        ttime.sleep(2)  # wait for acquisition

        for sig, val in reversed(list(original_vals.items())):
            ttime.sleep(0.1)
            sig.set(val).wait()


class PCOEdgeDetector(AreaDetector):
    # image = ADCpt(ImagePlugin, "image1:")
    cam = ADCpt(PCOEdgeCam, "cam1:")
    hdf5 = ADCpt(PCOHDF5Plugin, "HDF1:", md=bl.md, camera_name="vppem-1", date_template="%Y/%m/%d/", read_attrs=["time_stamp"])
    stats = ADCpt(EpicsSignalRO, "Stats1:Total_RBV")

    def set_exposure(self, exposure_time, timeout=10):
        max_exposure_time = 2.0
        if exposure_time <= max_exposure_time:
            self.cam.acquire_time.set(exposure_time, timeout=timeout)
            self.cam.num_images.set(1, timeout=timeout)
        else:
            n_images = int(exposure_time / max_exposure_time)
            if n_images*max_exposure_time < exposure_time:
                n_images += 1
            true_exposure_time = exposure_time/n_images
            self.cam.acquire_time.set(true_exposure_time, timeout=timeout)
            self.cam.num_images.set(n_images, timeout=timeout)

class PCOEdgeDetectorSingleTrigger(SingleTriggerV33, PCOEdgeDetector):
    pass