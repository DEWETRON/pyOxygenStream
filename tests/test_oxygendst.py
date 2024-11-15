"""
Copyright DEWETRON GmbH 2024

pyOxygenStream library - Unit Tests
"""
from pyOxygenStream import OxygenStreamReceiver

DT_SYNC_FIXED_SIZE = 28

def test_readSamplesSync():
    stream = OxygenStreamReceiver()
    stream.actual_channel_idx = 0
    stream.scaling_info.append([2, 1])

    data = b'\x00\x00\x00\x01\x00\x00\xff\xff\xff'
    packet = b'\x00' * DT_SYNC_FIXED_SIZE + data
    out = stream.readSamplesSync(packet, 0, len(data)//3, 'int24')
    assert out[0] == 1
    assert out[1] == 1 * 2 + 1
    assert out[2] == -1 * 2 + 1

    out = stream.readSamplesSync(packet, 0, len(data)//3, 'uint24')
    assert out[0] == 1
    assert out[1] == 1 * 2 + 1
    assert out[2] == 0xffffff * 2 + 1
