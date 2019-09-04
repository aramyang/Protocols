from opentrons import labware, instruments
from otcustomizers import StringSelection
import math

metadata = {
    'protocolName': 'Sample Aliquoting',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request'
}

# create custom labware
plate_name = 'agilent_24_wellplate_10ml'
if plate_name not in labware.list():
    labware.create(
        plate_name,
        grid=(6, 4),
        spacing=(18, 18),
        diameter=17.2,
        depth=40.3,
        volume=10000
    )

# load labware
plate = labware.load(plate_name, '1', 'plate')
tuberack50 = labware.load(
    'opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical', '2')
tuberack15 = labware.load(
    'opentrons_15_tuberack_falcon_15ml_conical', '3')
res12 = labware.load('usascientific_12_reservoir_22ml', '5')
tips1000 = labware.load('opentrons_96_tiprack_1000ul', '7')
tips300 = labware.load('opentrons_96_tiprack_300ul', '8')


def run_custom_protocol(
        p1000_mount: StringSelection('right', 'left') = 'right',
        p300_mount: StringSelection('left', 'right') = 'left'
):
    # check
    if p1000_mount == p300_mount:
        raise Exception('Input different mounts for P1000 and P300 pipettes.')

    # pipettes
    p1000 = instruments.P1000_Single(mount=p1000_mount, tip_racks=[tips1000])
    p1000.start_at_tip(tips1000.wells('B1'))
    p300 = instruments.P300_Single(mount=p300_mount, tip_racks=[tips300])
    p300.start_at_tip(tips300.wells('C1'))

    tubes = {
        'water1': [tuberack50.wells('A3'), -20],
        'water2': [tuberack50.wells('B3'), -20],
        'scale1': [tuberack50.wells('B1'), -20],
        'scale2': [tuberack50.wells('C1'), -20],
        'scale3': [tuberack50.wells('A2'), -20]
    }
    max_depth50 = -113 + 10
    max_depth15 = -117.5 + 10
    r50 = 27.81/2
    r15 = 14.9/2

    def h_trans(vol, source_tube, dest):
        nonlocal tubes
        pip = p1000 if vol > 300 else p300

        if source_tube[0] == 'w':
            dh = vol/((r50**2)*math.pi)
            if tubes[source_tube][1] > max_depth50:
                new_h = tubes[source_tube][1] - dh
            else:
                new_h = max_depth50
        else:
            dh = vol/((r15**2)*math.pi)
            if tubes[source_tube][1] > max_depth15:
                new_h = tubes[source_tube][1] - dh
            else:
                new_h = max_depth50

        tubes[source_tube][1] = new_h
        pip.transfer(
            vol, tubes[source_tube][0].top(new_h), dest, new_tip='never')
        pip.blow_out(dest)

    # transfer water to 15ml tubes
    for row in tuberack15:
        p1000.pick_up_tip()
        for well in row:
            for _ in range(2):
                h_trans(1000, 'water1', well.top())
        p1000.drop_tip()

    # transer water to custom 24-well plate
    p1000.pick_up_tip()
    for i, well in enumerate(plate.wells()):
        water_tube = 'water1' if i < 12 else 'water2'
        for _ in range(2):
            h_trans(1000, water_tube, well.top())
    p1000.drop_tip()

    # transfer corresponding scales and volumes to each 15ml tube
    for row, scale in zip(tuberack15.rows(), ['scale1', 'scale2', 'scale3']):
        p300.pick_up_tip()
        for dest, vol in zip(row, [30*i for i in range(1, 5)]):
            h_trans(vol, scale, dest.top())
        p300.drop_tip()

    # plate dilution
    for source_vol, source_chan, row in zip(
            [100, 50, 50, 50], res12.wells()[:4], plate.rows()):
        p300.pick_up_tip()
        p300.transfer(vol, source_chan, row[0], new_tip='never')
        p300.mix(3, 250, row[0])
        p300.blow_out(row[0].top())
        for source, dest in zip(row[:5], row[1:]):
            p300.transfer(50, source, dest, new_tip='never')
            p300.blow_out()
            p300.mix(3, 250, dest)
            p300.blow_out(dest.top())
        p300.drop_tip()