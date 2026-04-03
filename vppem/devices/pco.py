from ophyd import Component as Cpt
from ophyd import EpicsSignal, EpicsSignalRO, EpicsSignalWithRBV
from ophyd.areadetector import AreaDetector, ImagePlugin

from ophyd.areadetector.filestore_mixins import resource_factory, FileStoreHDF5, FileStoreTIFF, FileStoreIterativeWrite, FileStorePluginBase
from ophyd.areadetector.plugins import HDF5Plugin_V33, TIFFPlugin_V33, StatsPlugin_V33
import time as ttime
from collections import deque, OrderedDict

class BMMFileStoreHDF5(FileStorePluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filestore_spec = "AD_HDF5"  # spec name stored in resource doc
        self.stage_sigs.update(
            [
                ("file_template", "%s%s_%6.6d.h5"),
                ("file_write_mode", "Capture"),
                ("capture", 1),
                # TODO: Remove once num capture is updated elsewhere
                #("num_capture", 3)

            ]
        )        # 'Single' file_write_mode means one image : one file.
        # It does NOT mean that 'num_images' is ignored.

    def get_frames_per_point(self):
        return self.parent.cam.num_images.get()

    def stage(self):
        super().stage()
        # this over-rides the behavior from the base stage
        self._fn = self.file_template.get() % (
            self.file_path.get(),
            self.file_name.get(),
            # file_number is *next* iteration
            self.file_number.get(),
        )

        resource_kwargs = {
            "frame_per_point": self.get_frames_per_point(),
        }
        self._generate_resource(resource_kwargs)
    
class BMMHDF5Plugin(HDF5Plugin_V33, BMMFileStoreHDF5, FileStoreIterativeWrite):
    def warmup(self):
        """
        A convenience method for 'priming' the plugin.
        The plugin has to 'see' one acquisition before it is ready to capture.
        This sets the array size, etc.
        NOTE : this comes from:
            https://github.com/NSLS-II/ophyd/blob/main/ophyd/areadetector/plugins.py
        We had to replace "cam" with "settings" here.

        This has been slightly modified by Bruce to avoid a situation where the warmup
        hangs.  Also to add some indication on screen for what is happening.
        """
        self.enable.set(1).wait()

        # JOSH: proposed changes for new IOC

        tm = 'Internal'         # trigger mode for Pilatus
        if 'eiger' in self.parent.name:
            tm = 'Internal Series'
        sigs = OrderedDict([(self.parent.cam.array_callbacks, 1),
                            (self.parent.cam.image_mode, "Single"),
                            (self.parent.cam.trigger_mode, tm),
                            # just in case the acquisition time is set very long...
                            (self.parent.cam.acquire_time, 0.2),
                            (self.parent.cam.num_images, 1),
                            #(self.parent.cam.acquire, 1)
                        ]
        )

        original_vals = {sig: sig.get() for sig in sigs}

        # Remove the hdf5.capture item here to avoid an error as it should reset back to 0 itself
        # del original_vals[self.capture]

        for sig, val in sigs.items():
            sig.set(val).wait()
            ttime.sleep(0.1)  # abundance of caution

        self.parent.cam.acquire.set(1).wait()
        
        # JOSH: do we need more than 2 seconds here?
        #       adding more time here helps!
        ttime.sleep(2)  # wait for acquisition

        for sig, val in reversed(list(original_vals.items())):
            ttime.sleep(0.1)
            sig.set(val).wait()

    
