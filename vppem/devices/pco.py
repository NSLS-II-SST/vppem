from ophyd import EpicsSignalRO
from ophyd.areadetector import AreaDetector, ImagePlugin, CamBase
from ophyd.areadetector.base import ADComponent as ADCpt, EpicsSignalWithRBV as SignalWithRBV

from ophyd.areadetector.plugins import HDF5Plugin_V33
from sst_base.cameras import HDF5ProposalPlugin
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
    delay_time = ADCpt(SignalWithRBV, "DelayTime")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.stage_sigs[self.trigger_mode] = 0 # Auto
        self.stage_sigs[self.delay_time] = 0
        self.stage_sigs[self.size.size_x] = 2560
        self.stage_sigs[self.size.size_y] = 2160
        self.stage_sigs[self.array_callbacks] = 1 # Array callbacks enabled
        self.acquire_time.tolerance = 1e-4

class PCOHDF5Plugin(HDF5ProposalPlugin):
    """
    HDF5 writer for PCO Edge with Tiled-friendly chunking.

    Chunk layout is passed to the tiled writer via ``chunk_shape`` on the
    stream resource. Image axes are tiled at ``IMAGE_TILE_CHUNK``; leading
    dimensions chunk one scan point (and one exposure when stacking frames).
    """

    def tiled_chunk_shape(self, resource_kwargs):
        """
        Chunk shape for Tiled storage of PCO image arrays.

        Parameters
        ----------
        resource_kwargs : dict
            Resource options; ``frame_per_point`` controls whether exposures
            are stacked as an extra dimension.

        Returns
        -------
        tuple of int
            ``chunk_shape`` for the stream resource. Single exposure per point
            uses ``(1, 512, 512)``; multiple exposures use ``(1, 1, 512, 512)``
            so each Tiled chunk is at most one 512x512 tile (~0.5 MB as uint16).
        """
        frame_per_point = resource_kwargs.get("frame_per_point", 1)
        if frame_per_point > 1:
            return (1, 1, 2160, 2560)
        return (1, 2160, 2560)

    def warmup(self, timeout=10):
        """
        A convenience method for 'priming' the plugin.

        The plugin has to 'see' one acquisition before it is ready to capture.
        This sets the array size, etc.
        """
        self.enable.set(1).wait()
        sigs = OrderedDict(
            [
                (self.parent.cam.array_callbacks, 1),
                (self.parent.cam.image_mode, 0),
                (self.parent.cam.trigger_mode, 0),
                (self.parent.cam.num_images, 1),
                # just in case tha acquisition time is set very long...
                (self.parent.cam.acquire_time, 1),
                (self.parent.cam.acquire_period, 1),
                (self.parent.cam.acquire, 1),
            ]
        )

        original_vals = {sig: sig.get() for sig in sigs}

        for sig, val in sigs.items():
            ttime.sleep(0.1)  # abundance of caution
            sig.set(val, timeout=timeout).wait()

        ttime.sleep(2)  # wait for acquisition

        for sig, val in reversed(list(original_vals.items())):
            ttime.sleep(0.1)
            sig.set(val, timeout=timeout).wait()


    def _generate_resource(self, resource_kwargs):
        """
        Configure stream resource for stacked exposures and Tiled chunking.

        Parameters
        ----------
        resource_kwargs : dict
            Passed through to ``HDF5ProposalPlugin``; may include
            ``frame_per_point``.
        """
        if resource_kwargs.get("frame_per_point", 1) > 1:
            resource_kwargs["join_method"] = "stack"
        if "chunk_shape" not in resource_kwargs:
            resource_kwargs["chunk_shape"] = self.tiled_chunk_shape(resource_kwargs)
        super()._generate_resource(resource_kwargs)

class PCOEdgeDetector(AreaDetector):
    # image = ADCpt(ImagePlugin, "image1:")
    cam = ADCpt(PCOEdgeCam, "cam1:")
    hdf5 = ADCpt(PCOHDF5Plugin, "HDF1:", md=bl.md, camera_name="vppem-1", write_path_template="/nsls2/data/sst/proposals", date_template="%Y/%m/%d/", read_attrs=["time_stamp"])
    stats = ADCpt(EpicsSignalRO, "Stats1:Total_RBV")

    def set_exposure(self, exposure_time, timeout=10):
        max_exposure_time = 2.0
        if exposure_time <= max_exposure_time:
            st_list = []
            st_list.append(self.cam.acquire_time.set(exposure_time, timeout=timeout))
            st_list.append(self.cam.num_images.set(1, timeout=timeout))
            st_list.append(self.cam.image_mode.set(0, timeout=timeout)) # Single image mode

        else:
            n_images = int(exposure_time / max_exposure_time)
            if n_images*max_exposure_time < exposure_time:
                n_images += 1
            true_exposure_time = exposure_time/n_images
            st_list = []
            st_list.append(self.cam.acquire_time.set(true_exposure_time, timeout=timeout))
            st_list.append(self.cam.num_images.set(n_images, timeout=timeout))
            st_list.append(self.cam.image_mode.set(1, timeout=timeout)) # Multi-image mode

        for st in st_list:
            st.wait()
'''            
    def unstage(self):
        res = super().unstage()
        print(f"PCOEdgeDetector.unstage")
        from time import sleep
        print(f"PCOEdgeDetector.unstage: sleeping for 10 seconds")
        sleep(10)
        print(f"PCOEdgeDetector.unstage: done sleeping")
        return res
'''

class PCOEdgeDetectorSingleTrigger(SingleTriggerV33, PCOEdgeDetector):
    pass