"""
This module implements a reader for .e files produced by the NicoletOne EEG-System.

This reader is based on a MATLAB implementation of a .e file reader (https://github.com/ieeg-portal/Nicolet-Reader).
The original authors of the MATLAB implementation are Joost Wagenaar, Cristian Donos, Jan Brogger and Callum Stewart.

Author: Murezi Capaul <murezi.capaul@kliniklengg.ch>

CHECK IF THIS CHANGE IS ALSO ON THE MAIN BRANCH AND DEV BRANCH
"""

from __future__ import annotations

import numpy as np
import warnings
from datetime import datetime, timedelta
from pathlib import Path

from neo.rawio.baserawio import (
    BaseRawIO,
    _signal_channel_dtype,
    _signal_stream_dtype,
    _spike_channel_dtype,
    _event_channel_dtype,
)


class NicoletRawIO(BaseRawIO):
    '''
    The Class to read in .e files produced by the NicoletOne EEG-System.
    
    Parameters
    ----------
    filepath: str | Path
        The path to the .e file. Will be transformed into a WindowsPath object
        
    Notes
    ----------
        Currently, only channels that have the same sampling rate as the EEG-Channels will be processed. Other channels will be discarded.
    '''

    extensions = ["e"]
    rawmode = "one-file"
    
    LABELSIZE = 32
    TSLABELSIZE = 64
    UNITSIZE = 16
    ITEMNAMESIZE = 64
    UNIX_TIME_CONVERSION = 2209161600 #TODO: Currently, time is always UTC. Find where to read timezones
    SEC_PER_DAY = 86400
    
    TAGS_DICT = {
        'ExtraDataTags' : 'ExtraDataTags',
        'SegmentStream' : 'SegmentStream',
        'DataStream' : 'DataStream',
        'InfoChangeStream' : 'InfoChangeStream',
        'InfoGuids' : 'InfoGuids',
        '{A271CCCB-515D-4590-B6A1-DC170C8D6EE2}' : 'TSGUID',
        '{8A19AA48-BEA0-40D5-B89F-667FC578D635}' : 'DERIVATIONGUID',
        '{F824D60C-995E-4D94-9578-893C755ECB99}' : 'FILTERGUID',
        '{02950361-35BB-4A22-9F0B-C78AAA5DB094}' : 'DISPLAYGUID',
        '{8E94EF21-70F5-11D3-8F72-00105A9AFD56}' : 'FILEINFOGUID',
        '{E4138BC0-7733-11D3-8685-0050044DAAB1}' : 'SRINFOGUID',
        '{C728E565-E5A0-4419-93D2-F6CFC69F3B8F}' : 'EVENTTYPEINFOGUID',
        '{D01B34A0-9DBD-11D3-93D3-00500400C148}' : 'AUDIOINFOGUID',
        '{BF7C95EF-6C3B-4E70-9E11-779BFFF58EA7}' : 'CHANNELGUID',
        '{2DEB82A1-D15F-4770-A4A4-CF03815F52DE}' : 'INPUTGUID',
        '{5B036022-2EDC-465F-86EC-C0A4AB1A7A91}' : 'INPUTSETTINGSGUID',
        '{99A636F2-51F7-4B9D-9569-C7D45058431A}' : 'PHOTICGUID',
        '{55C5E044-5541-4594-9E35-5B3004EF7647}' : 'ERRORGUID',
        '{223A3CA0-B5AC-43FB-B0A8-74CF8752BDBE}' : 'VIDEOGUID',
        '{0623B545-38BE-4939-B9D0-55F5E241278D}' : 'DETECTIONPARAMSGUID',
        '{CE06297D-D9D6-4E4B-8EAC-305EA1243EAB}' : 'PAGEGUID',
        '{782B34E8-8E51-4BB9-9701-3227BB882A23}' : 'ACCINFOGUID',
        '{3A6E8546-D144-4B55-A2C7-40DF579ED11E}' : 'RECCTRLGUID',
        '{D046F2B0-5130-41B1-ABD7-38C12B32FAC3}' : 'GUID TRENDINFOGUID',
        '{CBEBA8E6-1CDA-4509-B6C2-6AC2EA7DB8F8}' : 'HWINFOGUID',
        '{E11C4CBA-0753-4655-A1E9-2B2309D1545B}' : 'VIDEOSYNCGUID',
        '{B9344241-7AC1-42B5-BE9B-B7AFA16CBFA5}' : 'SLEEPSCOREINFOGUID',
        '{15B41C32-0294-440E-ADFF-DD8B61C8B5AE}' : 'FOURIERSETTINGSGUID',
        '{024FA81F-6A83-43C8-8C82-241A5501F0A1}' : 'SPECTRUMGUID',
        '{8032E68A-EA3E-42E8-893E-6E93C59ED515}' : 'SIGNALINFOGUID',
        '{30950D98-C39C-4352-AF3E-CB17D5B93DED}' : 'SENSORINFOGUID',
        '{F5D39CD3-A340-4172-A1A3-78B2CDBCCB9F}' : 'DERIVEDSIGNALINFOGUID',
        '{969FBB89-EE8E-4501-AD40-FB5A448BC4F9}' : 'ARTIFACTINFOGUID',
        '{02948284-17EC-4538-A7FA-8E18BD65E167}' : 'STUDYINFOGUID',
        '{D0B3FD0B-49D9-4BF0-8929-296DE5A55910}' : 'PATIENTINFOGUID',
        '{7842FEF5-A686-459D-8196-769FC0AD99B3}' : 'DOCUMENTINFOGUID',
        '{BCDAEE87-2496-4DF4-B07C-8B4E31E3C495}' : 'USERSINFOGUID',
        '{B799F680-72A4-11D3-93D3-00500400C148}' : 'EVENTGUID',
        '{AF2B3281-7FCE-11D2-B2DE-00104B6FC652}' : 'SHORTSAMPLESGUID',
        '{89A091B3-972E-4DA2-9266-261B186302A9}' : 'DELAYLINESAMPLESGUID',
        '{291E2381-B3B4-44D1-BB77-8CF5C24420D7}' : 'GENERALSAMPLESGUID',
        '{5F11C628-FCCC-4FDD-B429-5EC94CB3AFEB}' : 'FILTERSAMPLESGUID',
        '{728087F8-73E1-44D1-8882-C770976478A2}' : 'DATEXDATAGUID',
        '{35F356D9-0F1C-4DFE-8286-D3DB3346FD75}' : 'TESTINFOGUID'}

    INFO_PROPS = [
        'patientID', 'firstName','middleName','lastName',
        'altID','mothersMaidenName','DOB','DOD','street','sexID','phone',
        'notes','dominance','siteID','suffix','prefix','degree','apartment',
        'city','state','country','language','height','weight','race','religion',
        'maritalStatus']

    #TODO: Find more translations for events guids -> Open file in Nicolet Viewer and here, and compare names of events
    HC_EVENT = {
        '{A5A95612-A7F8-11CF-831A-0800091B5BDA}' : 'Annotation',
        '{A5A95646-A7F8-11CF-831A-0800091B5BDA}' : 'Seizure',
        '{08784382-C765-11D3-90CE-00104B6F4F70}' : 'Format change',
        '{6FF394DA-D1B8-46DA-B78F-866C67CF02AF}' : 'Photic',
        '{481DFC97-013C-4BC5-A203-871B0375A519}' : 'Posthyperventilation',
        '{725798BF-CD1C-4909-B793-6C7864C27AB7}' : 'Review progress',
        '{96315D79-5C24-4A65-B334-E31A95088D55}' : 'Exam start',
        '{A5A95608-A7F8-11CF-831A-0800091B5BDA}' : 'Hyperventilation',                            
        '{A5A95617-A7F8-11CF-831A-0800091B5BDA}' : 'Impedance',
        '{A5A95645-A7F8-11CF-831A-0800091B5BDA}' : 'Event Comment',
        '{C3B68051-EDCF-418C-8D53-27077B92DE22}' : 'Spike',
        '{99FFE0AA-B8F9-49E5-8390-8F072F4E00FC}' : 'EEG Check',
        '{A5A9560A-A7F8-11CF-831A-0800091B5BDA}' : 'Print',
        '{A5A95616-A7F8-11CF-831A-0800091B5BDA}' : 'Patient Event',
        '{0DE05C94-7D03-47B9-864F-D586627EA891}' : 'Eyes closed',
        '{583AA2C6-1F4E-47CF-A8D4-80C69EB8A5F3}' : 'Eyes open',
        '{BAE4550A-8409-4289-9D8A-0D571A206BEC}' : 'Eating',
        '{1F3A45A4-4D0F-4CC4-A43A-CAD2BC2D71F2}' : 'ECG',
        '{B0BECF64-E669-42B1-AE20-97A8B0BBEE26}' : 'Toilet',
        '{A5A95611-A7F8-11CF-831A-0800091B5BDA}' : 'Fix Electrode'}
    
    
    def __init__(self, filepath = ""):
        BaseRawIO.__init__(self)
        self.filepath = Path(filepath)
        
    def _source_name(self):
        return self.filepath

    
    def _parse_header(self):
        self._extract_header_information() 
        self.header = {}
        self.header["nb_block"] = 1 #TODO: Find out if multiple blocks exist
        self.header["nb_segment"] = [len(self.segments_properties)]
        self.header["signal_streams"] = np.array([("Signals", "0")],  #TODO: Consider implementing all recorded channels after finding out if they make sense
                                                 dtype=_signal_stream_dtype)
        self.header["signal_channels"] = self._create_signal_channels(dtype = _signal_channel_dtype) if self.channel_properties else self._create_signal_channels_no_channel_props(_signal_channel_dtype)
        self.header["spike_channels"] = np.array([],  #TODO: Find if there is automatic spike detection
                                                 dtype= _spike_channel_dtype)
        self.header["event_channels"] = np.array([("Events", "0", "event"), #TODO: Find if there are more types of events that can be identified
                                                  ("Epochs", "1", "epoch")], 
                                                 dtype = _event_channel_dtype)
        self._generate_minimal_annotations()
        self._generate_additional_annotations()
            
    def _get_tags(self):
        misc_structure = [
            ('misc1', 'uint32', 5),
            #('unknown', 'uint32'),
            #('index_idx', 'uint32')
            ]
        tags_structure = [
            ('tag', 'S80'),
            ('index', 'uint32')]
        
        with open(self.filepath, "rb") as fid:
            index_idx = read_as_dict(fid, 
                                     misc_structure)
            unknown = read_as_dict(fid,
                                   [('unknown', 'uint32', 1)])
            fid.seek(172)
            n_tags = read_as_list(fid,
                                  [('n_tags', 'uint32')])
            tags = [read_as_dict(fid, 
                                 tags_structure) for _ in range(n_tags)]
            
            for entry in tags:
                try:
                    entry['id_str'] = self.TAGS_DICT[entry['tag']]
                except KeyError:
                    entry['id_str'] = 'UNKNOWN'
                    
        self.n_tags = n_tags
        self.index_idx = index_idx
        self.tags = tags

    def _get_qi(self):
        qi_structure = [
            ('n_entries', 'uint32'),
            ('misc1', 'uint32'),
            ('index_idx', 'uint32'),
            ('misc3', 'uint32'),
            ('l_qi', 'uint64'),
            ('first_idx', 'uint64', self.n_tags),
            ]
        with open(self.filepath, "rb") as fid:
            fid.seek(172208)
            qi = read_as_dict(fid, 
                              qi_structure)
        self.qi = qi
    
    def _get_main_index(self):
        #TODO: Find file with multiple index pointers to test the while loop
        #TODO: Find out what multiple block lengths mean
        main_index = []
        current_index = 0
        next_index_pointer = self.qi['index_idx']
        with open(self.filepath, "rb") as fid:
            while current_index < self.qi['n_entries']:
                fid.seek(next_index_pointer)
                nr_index = read_as_list(fid, 
                                        [('nr_index', 'uint64')]
                                        )
                var = read_as_list(fid,
                                   [('var', 'uint64', int(3*nr_index))])

                for i in range(nr_index):
                    main_index.append({
                        'section_idx' : int(var[3*(i)]),
                        'offset' : int(var[3*(i)+1]),
                        'block_l' : int(var[3*(i)+2] % 2**32),
                        'section_l' : round(var[3*(i)+2]/(2**32))})
                    
                next_index_pointer = read_as_list(fid, 
                                                  [('next_index_pointer', 'uint64')])
                current_index = current_index + (i + 1)
                
        self.main_index = main_index
        self.all_section_ids = [entry['section_idx'] for entry in main_index]
                
    def _read_dynamic_packets(self):
        dynamic_packets = []
        [dynamic_packets_instace] = self._get_index_instances(id_str = 'InfoChangeStream')
        offset = dynamic_packets_instace['offset']
        self.n_dynamic_packets = int(dynamic_packets_instace['section_l']/48)
        with open(self.filepath, "rb") as fid:
            fid.seek(offset)
            for i in range(self.n_dynamic_packets):
                guid_offset = offset + (i+1)*48

                dynamic_packet_structure = [
                    ('guid_list', 'uint8', 16),
                    ('date', 'float64'),
                    ('datefrace', 'float64'),
                    ('internal_offset_start', 'uint64'),
                    ('packet_size', 'uint64')]
                
                dynamic_packet = read_as_dict(fid,
                                              dynamic_packet_structure)
                guid_as_str = _convert_to_guid(dynamic_packet['guid_list'])

                
                if guid_as_str in list(self.TAGS_DICT.keys()):
                    id_str = self.TAGS_DICT[guid_as_str]
                else:
                    id_str = 'UNKNOWN'
                    
                dynamic_packet['offset'] = int(guid_offset)
                dynamic_packet['guid'] = guid_as_str.replace('-', '').replace('{', '').replace('}', '')
                dynamic_packet['guid_as_str'] = guid_as_str
                dynamic_packet['id_str'] = id_str

                dynamic_packets.append(dynamic_packet)
        self.dynamic_packets = dynamic_packets
    
    def _get_dynamic_packets_data(self):
        #TODO: Try to merge into _read_dynamic_packets
        with open(self.filepath, "rb") as fid:
            for i in range(self.n_dynamic_packets):
                data = []
                dynamic_packet_instances = self._get_index_instances(tag = self.dynamic_packets[i]['guid_as_str'])
                internal_offset = 0
                remaining_data_to_read = int(self.dynamic_packets[i]['packet_size'])
                current_target_start = int(self.dynamic_packets[i]['internal_offset_start'])
                for j in range(len(dynamic_packet_instances)):
                    current_instance = dynamic_packet_instances[j]
                    if ((internal_offset <= (current_target_start)) 
                        & ((internal_offset + current_instance['section_l']) >= current_target_start)):
                       
                        start_at = current_target_start
                        stop_at = min(start_at + remaining_data_to_read, 
                                      internal_offset + current_instance['section_l'])
                        read_length = stop_at - start_at
                        
                        file_pos_start = current_instance['offset'] + start_at - internal_offset
                        fid.seek(int(file_pos_start))
                        data_part = read_as_list(fid,
                                                 [('data', 'uint8', read_length)])
                        data  = data + list(data_part)
                        
                        remaining_data_to_read = remaining_data_to_read - read_length
                        current_target_start = current_target_start + read_length
                    
                    internal_offset = internal_offset + current_instance['section_l']
                    
                self.dynamic_packets[i]['data'] =  np.array(data)
    
    def _get_patient_guid(self):
        [idx_instance] = self._get_index_instances(id_str = 'PATIENTINFOGUID')
        patient_info_structure = [
            ('guid', 'uint8', 16),
            ('l_section', 'uint64'),
            ('n_values', 'uint64'),
            ('n_bstr', 'uint64')]
        with open(self.filepath, "rb") as fid:
            fid.seek(idx_instance['offset'])
            patient_info = read_as_dict(fid,
                                        patient_info_structure
                                        )

            for i in range(patient_info['n_values']):
                id_temp = read_as_list(fid,
                                       [('value', 'uint64')])
                
                if id_temp in [7, 8]:
                    value = read_as_list(fid,
                                         [('value', 'float64')])
                    value = _convert_to_date(value)
                elif id_temp in [23, 24]:
                    value = read_as_list(fid,
                                         [('value', 'float64')])
                else:
                    value = 0
                patient_info[self.INFO_PROPS[int(id_temp) - 1]] = value
                

            str_setup = read_as_list(fid,
                                     [('setup', 'uint64', int(patient_info['n_bstr']*2))])

            for i in range(0, int(patient_info['n_bstr']*2), 2):
                id_temp = str_setup[i]
                value = ''.join([read_as_list(fid,
                                    [('value', 'S2')]) for _ in range(int(str_setup[i + 1]) + 1)]).strip()
                patient_info[self.INFO_PROPS[int(id_temp) - 1]] = value
            pass
    
        self.patient_info = patient_info
    
    def _get_signal_properties(self):
        signal_properties = []
        signal_structure_segment = [
            ('guid', 'uint8', 16),
            ('name', 'S1', self.ITEMNAMESIZE)]
        
        idx_instances = self._get_index_instances('SIGNALINFOGUID')
        for instance in idx_instances:
            with open(self.filepath, "rb") as fid:
                fid.seek(instance['offset'])
                signal_structure = read_as_dict(fid,
                                                signal_structure_segment)
                unknown = read_as_list(fid,
                                       [('unknown', 'S1', 152)])
                fid.seek(512,1)
                n_idx = read_as_dict(fid,
                                     [('n_idx', 'uint16'),
                                      ('misc1', 'uint16', 3)])
                
                for i in range(n_idx['n_idx']):
                    
                    signal_properties_segment = [
                        ('name', 'S2', self.LABELSIZE),
                        ('transducer', 'S2', self.UNITSIZE),
                        ('guid', 'uint8', 16),
                        ('bipolar', 'uint32'),
                        ('ac', 'uint32'),
                        ('high_filter', 'uint32'),
                        ('color', 'uint32'),
                        
                        ]
                    
                    properties = read_as_dict(fid,
                                              signal_properties_segment)
                    #TODO: Consider setting On and Biploar to T/F
    
                    signal_properties.append(properties)
                    reserved = read_as_list(fid,
                                            [('reserved', 'S1', 256)])

        self.signal_structure = signal_structure
        self.signal_properties = signal_properties
        pass
    
    def _get_channel_info(self):
        channel_properties = []
        channel_structure_structure= [
            [('guid', 'uint8', 16),
            ('name', 'S1', self.ITEMNAMESIZE)],
            [('reserved', 'uint8', 16),
            ('device_id', 'uint8', 16)]
            ]
        
        [idx_instance] = self._get_index_instances('CHANNELGUID')
        
        with open(self.filepath, "rb") as fid:
            fid.seek(idx_instance['offset'])
            channel_structure = read_as_dict(fid, 
                                             channel_structure_structure[0])
            fid.seek(152, 1)
            channel_structure = channel_structure | read_as_dict(fid,
                                                                 channel_structure_structure[1])
            fid.seek(488,1)
            n_index = read_as_list(fid,
                                   [('n_index', 'int32', 2)])
            
            current_index = 0
            for i in range(n_index[1]):
                
                channel_properties_structure = [
                    ('sensor', 'S2', self.LABELSIZE),
                    ('sampling_rate', 'float64'),
                    ('on', 'uint32'),
                    ('l_input_id', 'uint32'),
                    ('l_input_setting_id', 'uint32')]
                
                info = read_as_dict(fid,
                                    channel_properties_structure)
                fid.seek(128, 1)
                
                if info['on']:
                    index_id = current_index
                    current_index += 1
                else:
                    index_id = -1
                    
                info['index_id'] = index_id
                
                channel_properties.append(info)
                
                reserved = read_as_list(fid,
                                        [('reserved', 'S1', 4)])
            
        self.channel_structure = channel_structure
        self.channel_properties = channel_properties

    def _get_ts_properties(self, ts_packet_index = 0):
        ts_properties = []
        
        ts_packets = [packet for packet in self.dynamic_packets if packet['id_str'] == 'TSGUID']
        l_ts_packets = len(ts_packets)
        self.ts_packets = ts_packets
        if l_ts_packets > 0:
            #TODO: Add support for multiple TS-Info packages
            if l_ts_packets > 1:
                warnings.warn(f'{l_ts_packets} TSinfo packets detected; using first instance for all segments. See documentation for info')
            ts_packet = ts_packets[ts_packet_index]
            elems = _typecast(ts_packet['data'][752:756])[0]
            alloc = _typecast(ts_packet['data'][756:760])[0]
            offset = 760
            
            for i in range(elems):
                internal_offset = 0                
                top_range = (offset + self.TSLABELSIZE)
                
                label = _transform_ts_properties(ts_packet['data'][offset:top_range], np.uint16)
                
                
                internal_offset += 2*self.TSLABELSIZE
                top_range = offset + internal_offset + self.LABELSIZE
                active_sensor = _transform_ts_properties(ts_packet['data'][(offset + internal_offset):top_range], np.uint16)
                internal_offset = internal_offset + self.TSLABELSIZE;
                top_range = offset + internal_offset + 8
                ref_sensor = _transform_ts_properties(ts_packet['data'][(offset + internal_offset):top_range], np.uint16)
                internal_offset += 64;

                low_cut, internal_offset = _read_ts_properties(ts_packet['data'], offset, internal_offset, np.float64)
                high_cut, internal_offset = _read_ts_properties(ts_packet['data'], offset, internal_offset, np.float64)
                sampling_rate, internal_offset = _read_ts_properties(ts_packet['data'], offset, internal_offset, np.float64)
                resolution, internal_offset = _read_ts_properties(ts_packet['data'], offset, internal_offset, np.float64)
                mark, internal_offset = _read_ts_properties(ts_packet['data'], offset, internal_offset, np.uint16)
                notch, internal_offset = _read_ts_properties(ts_packet['data'], offset, internal_offset, np.uint16)
                eeg_offset, internal_offset = _read_ts_properties(ts_packet['data'], offset, internal_offset, np.float64)
                offset += 552
                ts_properties.append({
                    'label' : label,
                    'active_sensor' : active_sensor,
                    'ref_sensor' : ref_sensor,
                    'low_cut' : low_cut,
                    'high_cut' : high_cut,
                    'sampling_rate' : sampling_rate,
                    'resolution' : resolution,
                    'notch' : notch,
                    'mark' : mark,
                    'eeg_offset' : eeg_offset})
        
        self.ts_properties = ts_properties
        pass
        
    
    def _get_segment_start_times(self):
        segments_properties = []
        
        [segment_instance] = self._get_index_instances('SegmentStream')
        n_segments = int(segment_instance['section_l']/152)
        
        with open(self.filepath, "rb") as fid:

            fid.seek(segment_instance['offset'], 0)
            
            for i in range(n_segments):
                segment_info =  {}
                segment_info['date_ole'] = read_as_list(fid,
                                                        [('date', 'float64')])
                fid.seek(8,1)
                segment_info['duration'] = read_as_list(fid,
                                                        [('duration', 'float64')])
                print(segment_info['duration'])
                fid.seek(128, 1)
                segment_info['ch_names'] = [info['label'] for info in self.ts_properties]
                segment_info['ref_names'] = [info['ref_sensor'] for info in self.ts_properties]
                segment_info['sampling_rates'] = [info['sampling_rate'] for info in self.ts_properties]
                segment_info['scale'] = [info['resolution'] for info in self.ts_properties]
                
                date_str = datetime.fromtimestamp(segment_info['date_ole']*self.SEC_PER_DAY - self.UNIX_TIME_CONVERSION)
                start_date = date_str.date()
                start_time = date_str.time()
                segment_info['date'] = date_str
                segment_info['start_date'] = date_str.date()
                segment_info['start_time'] = date_str.time()
                segment_info['duration'] = timedelta(seconds = segment_info['duration'])
                segments_properties.append(segment_info)
        self.segments_properties = segments_properties
        pass
    
    def _get_events(self):
        events = []
        
        event_packet_guid = '{B799F680-72A4-11D3-93D3-00500400C148}'
        
        event_instances = self._get_index_instances(tag = 'Events')
        for instance in event_instances:
            offset = instance['offset']
            with open(self.filepath, "rb") as fid:
                pkt_structure = [
                    ('guid', 'uint8', 16),
                    ('len', 'uint64', 1)]
                fid.seek(offset)
                pkt = read_as_dict(fid,
                                   pkt_structure)
                pkt['guid'] = _convert_to_guid(pkt['guid'])
                n_events = 0
                
                
                while (pkt['guid'] == event_packet_guid):
                    event_structure = [
                        [('date_ole', 'float64'),
                         ('date_fraction', 'float64'),
                         ('duration', 'float64')],
                        [('user', 'S2', 12),
                         ('text_length', 'uint64'),
                         ('guid', 'uint8', 16)],
                        [('label', 'S2', 32)]
                        ]
                    
                    n_events += 1
                    fid.seek(8, 1)
                    event = read_as_dict(fid,
                                         event_structure[0])
                    fid.seek(48, 1)
                    event = event | read_as_dict(fid,
                                                 event_structure[1])
                    fid.seek(16, 1)
                    event = event | read_as_dict(fid,
                                                 event_structure[2])
                    
                    event['date'] = datetime.fromtimestamp(event['date_ole']*self.SEC_PER_DAY + event['date_fraction'] - self.UNIX_TIME_CONVERSION)
                    event['timestamp'] = (event['date'] - self.segments_properties[0]['date']).total_seconds()
                    event['guid'] = _convert_to_guid(event['guid'])
                    
                    try:
                        id_str = self.HC_EVENT[event['guid']]
                    except:
                        id_str = 'UNKNOWN'
                    if id_str == 'Annotation':
                        fid.seek(31, 1)
                        annotation = read_as_list(fid,
                                                  [('annotation', 'S2', event['text_length'])])
                    else:
                        annotation = ''
                    event['id_str'] = id_str
                    event['annotation'] = annotation   
                    
                    event['block_index'] = 0
                    seg_index = 0
                    segment_time_range = [segment['date'] for segment in self.segments_properties]
                    for segment_time in segment_time_range[1:]:
                        if segment_time < event['date']:
                            seg_index += 1
                    event['seg_index'] = seg_index
                    events.append(event)
                    
                    event['type'] = '0' if event['duration'] == 0 else '1'
                    
                    offset += int(pkt['len'])
                    fid.seek(offset)
                    pkt = read_as_dict(fid,
                                       pkt_structure)
                    pkt['guid'] = _convert_to_guid(pkt['guid'])

        self.events = events
        pass
    
    
    
    def _get_montage(self):
        montages = []

        montage_instances = self._get_index_instances(id_str = 'DERIVATIONGUID')
        with open(self.filepath, "rb") as fid:
            
            montage_info_structure = [
                [('name', 'S2', 32)],
                [('n_derivations', 'uint32'),
                 ('n_derivations_2', 'uint32')],
                [('derivation_name', 'S2', 64),
                 ('signal_name_1', 'S2', 32),
                 ('signal_name_2', 'S2', 32)]
                ]
            fid.seek(int(montage_instances[0]['offset']) + 40)
            montage_info = read_as_dict(fid,
                                   montage_info_structure[0])
            fid.seek(640, 1)
            montage_info = montage_info | read_as_dict(fid,
                                             montage_info_structure[1])

            for i in range(montage_info['n_derivations']):
                montage = montage_info | read_as_dict(fid,
                                                 montage_info_structure[2])
                fid.seek(264, 1)

                montages.append(montage)
            display_instances = self._get_index_instances(id_str = 'DISPLAYGUID')
            
            display_structure = [[
                ('name', 'S2', 32)],
                [('n_traces', 'uint32'),
                 ('n_traces_2', 'uint32')],
                [('color', 'uint32')]
                ]
            fid.seek(int(display_instances[0]['offset']) + 40)
            display = read_as_dict(fid,
                                   display_structure[0])
            fid.seek(640, 1)
            display = display | read_as_dict(fid,
                                             display_structure[1])
 
            if display['n_traces'] == montage_info['n_derivations']:
                for i in range(display['n_traces']):
                    fid.seek(32, 1)
                    montages[i]['disp_name'] = display['name']
                    montages[i]['color'] = read_as_list(fid,
                                                        display_structure[2])
            else:
                print('Could not match montage derivations with display color table')
            
        self.montages = montages
        self.display = display
        
    def get_nr_samples(self, block_index = 0, seg_index = 0):
        try:
            duration = self.segments_properties[seg_index]['duration'].total_seconds()
            return([int(sampling_rate * duration) for sampling_rate in self.segments_properties[seg_index]['sampling_rates']])
        except IndexError as error:
            print(str(error) + ': Incorrect segment argument; seg_index must be an integer representing segment index, starting from 0.')
        pass
    
    
    def _get_raw_signal(self):
        earliest_signal_index = [tag['tag'] for tag in self.tags].index('0')
        offset = [index['offset'] for index in self.main_index if index['section_idx'] == earliest_signal_index][0]
        
        raw_signal = np.memmap(self.filepath, dtype="i2", offset = offset, mode="r")
        self.signal_data_offset = offset
        self.raw_signal = raw_signal
    
    def _extract_header_information(self):
        self._get_tags()       
        self._get_qi()       
        self._get_main_index()
        self._read_dynamic_packets()
        self._get_dynamic_packets_data()
        self._get_patient_guid()
        self._get_signal_properties()
        self._get_channel_info()
        self._get_ts_properties()
        self._get_segment_start_times()
        self._get_events()
        self._get_montage()
        self._get_raw_signal()
    
    
    
    def _create_signal_channels(self, dtype):
        '''
        

        _signal_channel_dtype = [
            ("name", "U64"),  # not necessarily unique -> sig, ch, ts
            ("id", "U64"),  # must be unique -> (sig), ch, (ts)
            ("sampling_rate", "float64") -> - , ch, ts
            ("dtype", "U16"), -> given (int16)
            ("units", "U64"), -> sig, -, -
            ("gain", "float64"), -, - , ts
            ("offset", "float64"), -, -, ts
            ("stream_id", "U64"), 
        ]
        
        
        '''
        signal_channels = []   
        for channel in self.channel_properties:
            signal = next((item for item in self.signal_properties if item["name"] == channel['sensor']), None)
            timestream = next((item for item in self.ts_properties if item["label"].split('-')[0] == channel['sensor']), None)
            if signal is None or timestream is None:
                continue
            signal_channels.append((
                channel['sensor'],
                channel['l_input_id'],
                channel['sampling_rate'],
                'int16',
                signal['transducer'],
                timestream['resolution'],
                timestream['eeg_offset'],
                0))
        
        return np.array(signal_channels, dtype = dtype)
    
    def _create_signal_channels_no_channel_props(self, dtype):
        '''
        

        _signal_channel_dtype = [
            ("name", "U64"),  # not necessarily unique -> sig, ts (occasionaly bad names in ts)
            ("id", "U64"),  # must be unique -> Enumerate
            ("sampling_rate", "float64") -> - , ts
            ("dtype", "U16"), -> given (int16)
            ("units", "U64"), -> sig, -
            ("gain", "float64"), -, ts
            ("offset", "float64"), -, ts
            ("stream_id", "U64"), 
        ]
        
        
        '''
        #TODO: Verify that using timestreams make sense by comparing a bunch of them
        
        signal_channels = []
        
            
        for i, timestream in enumerate(self.ts_properties):
            signal = next((item for item in self.signal_properties if item["name"] == timestream['label'].split('-')[0]), None)
            if signal is None:
                continue
            
            signal_channels.append((
                timestream['label'].split('-')[0],
                i,
                int(timestream['sampling_rate']),
                'int16',
                signal['transducer'],
                timestream['resolution'],
                timestream['eeg_offset'],
                0))
                
        return np.array(signal_channels, dtype = dtype)
    
    def _generate_additional_annotations(self):
        for block_index in range(self.header['nb_block']):
            bl_annotations = self.raw_annotations["blocks"][block_index]
            bl_annotations['date'] = self.segments_properties[0]['date']
            try:
                bl_annotations['firstname'] = self.patient_info['firstName']
                bl_annotations['surname'] = self.patient_info['lastName']
            except KeyError:
                bl_annotations['name'] = self.patient_info['altID']
            bl_annotations['duration'] = sum([properties['duration'].total_seconds() for properties in self.segments_properties])
            for i, seg_annotations in enumerate(bl_annotations['segments']):
                try:
                    seg_annotations['firstname'] = self.patient_info['firstName']
                    seg_annotations['surname'] = self.patient_info['lastName']
                except KeyError:
                    seg_annotations['name'] = self.patient_info['altID']
                seg_annotations['date'] = self.segments_properties[i]['date']
                seg_annotations['duration'] = self.segments_properties[i]['duration'].total_seconds()
                for event_types in seg_annotations['events']:
                    event_types['__array_annotations__']['nb_events'] = len([event for event in self.events 
                                                                        if event['seg_index'] == i and event['type'] == event_types['id']])
                
                    
                
                
    

    def _get_analogsignal_chunk(
        self,
        block_index: int = 0,
        seg_index: int = 0,
        i_start: int = None,
        i_stop: int = None,
        stream_index: int = None,
        channel_indexes: np.ndarray | list | slice = None,
    ):
        
        
        
        if block_index >= self.header['nb_block']:
            raise IndexError(f"Block Index out of range. There are {self.header['nb_block']} blocks in the file")
        
        if seg_index >= self.header['nb_segment'][block_index]:
            raise IndexError(f"Segment Index out of range. There are {self.header['nb_segment'][block_index]} segments for block {block_index}")


        
        
        if channel_indexes is None:
            channel_indexes = list(range(0,len(self.ts_properties)))
            nb_chan = len(channel_indexes)
        elif isinstance(channel_indexes, slice):
            channel_indexes = np.arange(len(self.ts_properties), dtype="int")[channel_indexes]
            nb_chan = len(channel_indexes)
        else:
            channel_indexes = np.asarray(channel_indexes)
            if any(channel_indexes < 0):
                raise IndexError("Channel Indices cannot be negative")
            if any(channel_indexes >= len(self.ts_properties)):
                raise IndexError("Channel Indices out of range")
            nb_chan = len(channel_indexes)
            
        if i_start is None:
            i_start = 0
        if i_stop is None:
            i_stop = max(self.get_nr_samples(seg_index))
        if i_start < 0 or i_stop > max(self.get_nr_samples(seg_index)):
            # some checks
            raise IndexError("Start or Stop Index out of bounds")
            
        eeg_sampling_rate = max(self.segments_properties[seg_index]['sampling_rates'])
        

        cum_segment_duration = [0] +  list(np.cumsum([(segment['duration'].total_seconds()) for segment in self.segments_properties]))
        
        data = np.empty([i_stop - i_start, self.segments_properties[0]['sampling_rates'].count(eeg_sampling_rate)])
        
        for i in channel_indexes:
            print('Current Channel: ' + str(i))

            current_samplingrate = self.segments_properties[seg_index]['sampling_rates'][i]
            multiplicator = self.segments_properties[seg_index]['scale'][i]
            
            if current_samplingrate != eeg_sampling_rate:
                continue
            
            [tag_idx] = [tag['index'] for tag in self.tags if tag['tag'] == str(i)]
            all_sections = [j for j, idx_id in enumerate(self.all_section_ids) if idx_id == tag_idx]
            section_lengths = [int(index['section_l']/2) for j, index in enumerate(self.main_index) if j in all_sections]
            cum_section_lengths = [0] +  list(np.cumsum(section_lengths))
            skip_values = cum_segment_duration[seg_index] * current_samplingrate
        
            first_section_for_seg = _get_relevant_section(cum_section_lengths, skip_values) - 1
            last_section_for_seg = _get_relevant_section(cum_section_lengths, 
                                                              current_samplingrate*
                                                              self.segments_properties[seg_index]['duration'].total_seconds()) - 1 + first_section_for_seg
            offset_section_lengths = [length - cum_section_lengths[first_section_for_seg] for length in cum_section_lengths]
            first_section = _get_relevant_section(cum_section_lengths, i_start - 1)
            last_section = _get_relevant_section(cum_section_lengths, i_stop + 1) - 1
            if last_section > last_section_for_seg:
                raise IndexError(f'Index out of range for channel {i}')
                
            use_sections = all_sections[first_section:last_section]
            use_sections_length = section_lengths[first_section:last_section]
            
            
            np_idx = 0
            for section_idx, section_length in zip(use_sections, use_sections_length):
                cur_sec = self.main_index[section_idx]

                start = int((cur_sec['offset'] - self.signal_data_offset)/2) #It appears that the offset was set for a file double the size
                stop = start + section_length
                data[np_idx:(np_idx + section_length), i] = multiplicator*self.raw_signal[slice(start, stop)]
                np_idx += section_length

        return data
        
    def _segment_t_start(self, block_index: int, seg_index: int):
        # this must return a float scaled in seconds
        # this t_start will be shared by all objects in the segment
        # except AnalogSignal
        all_starts = []
        for block_index in range(self.header['nb_block']):
            bl_annotation = self.raw_annotations["blocks"][block_index]
            block_starts = [0]
            startime = 0
            for seg_annotation in (bl_annotation['segments'][1:]):
                startime += seg_annotation['duration']
                block_starts.append(float(startime))
            all_starts.append(block_starts)
        return all_starts[block_index][seg_index]
    

    def _segment_t_stop(self, block_index: int, seg_index: int):
        # this must return a float scaled in seconds
        all_stops = []
        for block_index in range(self.header['nb_block']):
            bl_annotation = self.raw_annotations["blocks"][block_index]
            block_stops = []
            stoptime = 0
            for seg_annotation in (bl_annotation['segments']):
                stoptime += seg_annotation['duration']
                block_stops.append(float(stoptime))
            all_stops.append(block_stops)    
        return all_stops[block_index][seg_index]
    
    def _get_signal_size(self, block_index: int = 0, seg_index: int = 0, stream_index: int = 0):
        # We generate fake data in which the two stream signals have the same shape
        # across all segments (10.0 seconds)
        # This is not the case for real data, instead you should return the signal
        # size depending on the block_index and segment_index
        # this must return an int = the number of samples

        # Note that channel_indexes can be ignored for most cases
        # except for the case of several sampling rates.
        return max(self.get_nr_samples(block_index = block_index,
                                       seg_index = seg_index))
    
    def _get_signal_t_start(self, block_index: int = 0, seg_index: int = 0, stream_index: int = 0):
        #TODO: Find out if this means the start of the signal with respect to the segment, with respect to the block, or with respect to the entire file
        # This give the t_start of a signal.
        # Very often this is equal to _segment_t_start but not
        # always.
        # this must return a float scaled in seconds

        # Note that channel_indexes can be ignored for most cases
        # except for the case of several sampling rates.

        # Here this is the same.
        # this is not always the case
        return self._segment_t_start(block_index, seg_index)
    
    def _spike_count(self, block_index: int, seg_index: int, spike_channel_index: int):
        # Must return the nb of spikes for given (block_index, seg_index, spike_channel_index)
        # we are lucky:  our units have all the same nb of spikes!!
        # it is not always the case
        return 0
    
    def _get_spike_timestamps(
        self, block_index: int, seg_index: int, spike_channel_index: int, t_start: float | None, t_stop: float | None
    ):
        return None
    
    def _rescale_spike_timestamp(self, spike_timestamps: np.ndarray, dtype: np.dtype):
        # must rescale to seconds, a particular spike_timestamps
        # with a fixed dtype so the user can choose the precision they want.
        return None
    
    def _event_count(self, block_index: int = 0, seg_index: int = 0, event_channel_index: int = 0):
        return self.raw_annotations['blocks'][block_index]['segments'][seg_index]['events'][event_channel_index]['__array_annotations__']['nb_events']
    
    
    def _get_event_timestamps(
        self, block_index: int = 0, seg_index: int = 0, event_channel_index: int = 0, t_start: float =  None, t_stop: float = None
    ):
        
        events = [event for event in self.events if event['type'] == str(event_channel_index) and event['seg_index'] == seg_index]
        
        timestamp = np.array([event['timestamp'] for event in events], dtype="float64")
        durations = np.array([event['duration'] for event in events], dtype="float64")
        labels = np.array([event['id_str'] for event in events], dtype="U12")    #TODO: Check if using id_str makes sense
        
        if t_start is not None:
            keep = timestamp >= t_start
            timestamp, durations, labels = timestamp[keep], durations[keep], labels[keep]
        
        if t_stop is not None:
            keep = timestamp <= t_stop
            timestamp, durations, labels = timestamp[keep], durations[keep], labels[keep]
        
        if seg_index == '0':
            durations = None

        return timestamp, durations, labels

    def _rescale_event_timestamp(self, event_timestamps: np.ndarray, dtype: np.dtype, event_channel_index: int):
        event_times = event_timestamps.astype(dtype)
        return event_times    
    
    def _rescale_epoch_duration(self, raw_duration: np.ndarray, dtype: np.dtype, event_channel_index: int):
        durations = raw_duration.astype(dtype)
        return durations
    
    def _get_index_instances(self, id_str = '', tag = ''):
        identifier = 'id_str'
        if tag:
            identifier = 'tag'
            id_str = tag
        info_idx = [entry[identifier] for entry in self.tags].index(id_str)
        matching_idx = [entry['section_idx'] == info_idx for entry in self.main_index]
        idx_instance = [entry for entry, match in zip(self.main_index, matching_idx) if match]
        return(idx_instance)

#%%


def read_as_dict(fid, dtype):
    info = dict()  
    dt = np.dtype(dtype)
    h = np.frombuffer(fid.read(dt.itemsize), dt)[0]
    for k in dt.names:
        v = h[k]
        v = _process_bytes(v, dt[k])
        info[k] = v     
    return info

def read_as_list(fid, dtype):
    #if offset is not None:
    #    fid.seek(offset) 
    dt = np.dtype(dtype)
    h = np.frombuffer(fid.read(dt.itemsize), dt)[0][0]
    h = _process_bytes(h, dt[0])
    return h
    
def _process_bytes(byte_data, data_type):
    is_list_of_binaries = (type(byte_data) == np.ndarray and type(byte_data[0]) == np.bytes_)
    byte_obj = b''.join(byte_data) if is_list_of_binaries else byte_data
    bytes_decoded = _decode_string(byte_obj) if data_type.kind == "S" or is_list_of_binaries else byte_obj
    return bytes_decoded

def _decode_string(string):
    try:
        string = string.decode("utf8")
    except:
        string = string.decode('latin_1')
    string = string.replace("\x03", "")
    string = string.replace("\x00", "")
    return string

def _convert_to_guid(hex_list, 
                       guid_format = '{3}{2}{1}{0}-{5}{4}-{7}{6}-{8}{9}-{10}{11}{12}{13}{14}{15}'):
    dec_list = [f'{nr:x}'.upper().rjust(2, '0') for nr in hex_list]
    return('{' + guid_format.format(*dec_list) + '}') 

def _convert_to_date(data_float, origin = '31-12-1899'):
    return(datetime.strptime(origin, '%d-%m-%Y') 
            + timedelta(days = int(data_float)))

def _typecast(data, dtype_in = np.uint8, dtype_out = np.uint32):
    data = np.array(data, dtype = dtype_in)
    return(data.view(dtype_out))

def _transform_ts_properties(data, dtype):
    cast_list = list(_typecast(data, dtype_out = dtype))
    if dtype == np.float64:
        [cast_list] = cast_list
        return(cast_list)
    else:
        return(_transform_char(cast_list))
    
def _transform_char(line):
    if type(line) != list: line = [line] #TODO: Find a better way to do this
    line = ''.join([chr(item) for item in line if chr(item) != '\x00'])
    return line

def _read_ts_properties(data, offset, internal_offset, dtype):
    offset_modifier = 8 if (dtype == np.float64) else 2
    
    top_range = offset + internal_offset + offset_modifier
    value = _transform_ts_properties(data[(offset + internal_offset):top_range], dtype)
    internal_offset += offset_modifier
    return(value, internal_offset)

def _get_relevant_section(lengths_list, to_compare):
    try:
        segment = min([j for j, length in enumerate(lengths_list) if length > to_compare])
    except ValueError:
        segment = len(lengths_list)
    return(segment)

    

    
if __name__ == '__main__':
    
    #file = NicoletRawIO(r'\\fsnph01\NPH_Research\xxx_PythonShare\nicolet_parser\data\janbrogger.e')
    #file = NicoletRawIO(r'\\fsnph01\NPH_Research\xxx_PythonShare\nicolet_parser\data\Routine6t1.e')
    #file = NicoletRawIO(r'\\fsnph01\NPH_Archiv\LTM\Band0299\58795\9140.e')
    #file = NicoletRawIO(r'C:\temp\3407_2.e')
    file = NicoletRawIO(r'C:\temp\3407_2.e')
    #file = NicoletRawIO(r'C:\temp\Patient20_ABLEIT53_t1.e')
    file._parse_header()
    tags = file.tags
    qi = file.qi
    main_index = file.main_index
    dynamic_packets = file.dynamic_packets
    
    pat_info = file.patient_info
    signal_structure = file.signal_structure
    signal_properties = file.signal_properties
    
    channel_structure = file.channel_structure
    channel_properties = file.channel_properties
    
    ts_properties = file.ts_properties
    ts_packets = file.ts_packets
    
    segments_properties = file.segments_properties
    
    events = file.events
    
    montages = file.montages
    
    raw_signal = file.raw_signal
    print('reading data')
    data = file._get_analogsignal_chunk()
    
    header = file.header
    
    raw_annotations = file.raw_annotations
    

    #Construct an mne object
    
#%%

