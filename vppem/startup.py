from nbs_bl.configuration import GLOBAL_BEAMLINE as bl

if 'sampleVoltage' in bl.devices:
    bl.devices['sampleVoltage'].VMeas.kind = "omitted"
    bl.devices['sampleVoltage'].IMeas.kind = "omitted"
    bl.devices['sampleVoltage'].ISource.kind = "config"