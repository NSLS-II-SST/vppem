from nbs_bl.beamline import GLOBAL_BEAMLINE as bl
from datetime import datetime
import os
from os.path import join

md = bl.md
md['data_session'] = '111111'
md['cycle'] = '2026-2'
md['username'] = 'simuser'
md['start_datetime'] = datetime.now().isoformat()
md['saf'] = '222222'
md['proposal'] = {
    'proposal_id': '111111',
    'title': 'Test Proposal',
    'type': 'GU',
    'pi_name': 'PI, Test'
}

def get_proposal_directory(asset_name):
    write_path_template = "/nsls2/data/sst/proposals"
    date_template = "%Y/%m/%d/"
    proposal_path = f"{md['cycle']}/{md['data_session']}/assets/{asset_name}"
    write_path = join(write_path_template, proposal_path, date_template)
    formatter = datetime.now().strftime
    write_path = formatter(write_path)
    return write_path

def create_proposal_directory(asset_name):
    write_path = get_proposal_directory(asset_name)
    print(f"Creating proposal directory: {write_path}")
    if not os.path.exists(write_path):
        os.makedirs(write_path)
    return write_path

create_proposal_directory('vppem-1')

print("Switching sampling mode to Continuous...")
bl['rbd1'].rbd9103.switch_sampling_mode('Continuous')
bl['rbd2'].rbd9103.switch_sampling_mode('Continuous')
bl['rbd3'].rbd9103.switch_sampling_mode('Continuous')

print("Warming up PCO...")
bl['pco'].hdf5.warmup()

print("VPPEM simulation started.")