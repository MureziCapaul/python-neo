"""
Tests of neo.io.exampleio
"""

import pathlib
import unittest

from neo.io.nicoletio import NicoletIO
from neo.test.iotest.common_io_test import BaseTestIO
from neo.test.iotest.tools import get_test_file_full_path
from neo.io.proxyobjects import AnalogSignalProxy, SpikeTrainProxy, EventProxy, EpochProxy
from neo import AnalogSignal, SpikeTrain

import quantities as pq
import numpy as np


class TestExampleIO(
    BaseTestIO,
    unittest.TestCase,
):
    ioclass = NicoletIO
    entities_to_download = ["nicolet"]
    entities_to_test = [
        "nicolet/e_files/test.e",
    ]

    def setUp(self):
        super().setUp()
        for entity in self.entities_to_test:
            full_path = get_test_file_full_path(self.ioclass, filename=entity, directory=self.local_test_dir)
            pathlib.Path(full_path).touch()

    def tearDown(self) -> None:
        super().tearDown()
        for entity in self.entities_to_test:
            full_path = get_test_file_full_path(self.ioclass, filename=entity, directory=self.local_test_dir)
            pathlib.Path(full_path).unlink(missing_ok=True)

class TestNicoletIO(unittest.TestCase):
    def test_read_segment_lazy(self):
        r = NicoletIO(filename=None)
        seg = r.read_segment(lazy=True)
        for ana in seg.analogsignals:
            assert isinstance(ana, AnalogSignalProxy)
            ana = ana.load()
            assert isinstance(ana, AnalogSignal)
        for st in seg.spiketrains:
            assert isinstance(st, SpikeTrainProxy)
            st = st.load()
            assert isinstance(st, SpikeTrain)

        seg = r.read_segment(lazy=False)
        for anasig in seg.analogsignals:
            assert isinstance(ana, AnalogSignal)
            self.assertNotEqual(anasig.size, 0)
        for st in seg.spiketrains:
            assert isinstance(st, SpikeTrain)
            self.assertNotEqual(st.size, 0)

        # annotations
        assert "seg_extra_info" in seg.annotations
        assert seg.name == "Seg #0 Block #0"
        for anasig in seg.analogsignals:
            assert anasig.name is not None
        for st in seg.spiketrains:
            assert st.name is not None
        for ev in seg.events:
            assert ev.name is not None
        for ep in seg.epochs:
            assert ep.name is not None

    def test_read_block(self):
        r = NicoletIO(filename=None)
        bl = r.read_block(lazy=True)
        # assert len(bl.list_units) == 3
        # assert len(bl.channel_indexes) == 1 + 1  # signals grouped + units grouped

    def test_read_segment_with_time_slice(self):
        r = NicoletIO(filename=None)
        seg = r.read_segment(time_slice=None)
        shape_full = seg.analogsignals[0].shape
        spikes_full = seg.spiketrains[0]
        event_full = seg.events[0]

        t_start, t_stop = 260 * pq.ms, 1.854 * pq.s
        seg = r.read_segment(time_slice=(t_start, t_stop))
        shape_slice = seg.analogsignals[0].shape
        spikes_slice = seg.spiketrains[0]
        event_slice = seg.events[0]

        assert shape_full[0] > shape_slice[0]

        assert spikes_full.size > spikes_slice.size
        assert np.all(spikes_slice >= t_start)
        assert np.all(spikes_slice <= t_stop)
        assert spikes_slice.t_start == t_start
        assert spikes_slice.t_stop == t_stop

        assert event_full.size > event_slice.size
        assert np.all(event_slice.times >= t_start)
        assert np.all(event_slice.times <= t_stop)


if __name__ == "__main__":
    unittest.main()
