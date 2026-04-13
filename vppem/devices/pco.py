from ophyd import EpicsSignalRO
from ophyd.areadetector import AreaDetector, ImagePlugin, CamBase
from ophyd.areadetector.base import ADComponent as ADCpt, EpicsSignalWithRBV as SignalWithRBV

from ophyd.areadetector.plugins import HDF5Plugin_V33
from sst_base.cameras import HDF5PluginWithProposalDirectory
from nslsii.ad33 import SingleTriggerV33
    
class SSTHDF5Plugin(HDF5Plugin_V33, HDF5PluginWithProposalDirectory):
    pass

class PCOEdgeCam(CamBase):
    adc_mode = ADCpt(SignalWithRBV, "AdcMode")
    camera_setup = ADCpt(SignalWithRBV, "CameraSetup")
    readout_mode = ADCpt(SignalWithRBV, "ReadoutMode")
    bit_alignment = ADCpt(SignalWithRBV, "BitAlignment")
    pixel_rate = ADCpt(SignalWithRBV, "PixelRate")

class PCOEdgeDetector(AreaDetector):
    image = ADCpt(ImagePlugin, "image1:")
    cam = ADCpt(PCOEdgeCam, "cam1:")
    hdf5 = ADCpt(SSTHDF5Plugin, "HDF1:")
    stats = ADCpt(EpicsSignalRO, "Stats1:Total_RBV")

class PCOEdgeDetectorSingleTrigger(SingleTriggerV33, PCOEdgeDetector):
    pass