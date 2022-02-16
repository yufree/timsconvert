from timsconvert.constants import *
from timsconvert.timestamp import *
import numpy as np
import sys
import logging


def parse_lcms_tdf(tdf_data, frame_start, frame_stop, ms1_groupby, mode, ms2_only, encoding):
    if encoding == 32:
        encoding_dtype = np.float32
    elif encoding == 64:
        encoding_dtype = np.float64

    list_of_frames_dict = tdf_data.frames.to_dict(orient='records')
    if tdf_data.pasefframemsmsinfo is not None:
        list_of_pasefframemsmsinfo_dict = tdf_data.pasefframemsmsinfo.to_dict(orient='records')
    if tdf_data.precursors is not None:
        list_of_precursors_dict = tdf_data.precursors.to_dict(orient='records')
    list_of_parent_scans = []
    list_of_product_scans = []

    if mode == 'profile':
        centroided = False
    elif mode == 'centroid' or mode == 'raw':
        centroided = True

    for index in range(frame_start, frame_stop):
        frame = int(tdf_data.ms1_frames[index])
        frames_dict = [i for i in list_of_frames_dict if int(i['Id']) == frame][0]

        if frames_dict['MsMsType'] in MSMS_TYPE_CATEGORY['ms1']:
            if ms2_only == False:
                if ms1_groupby == 'frame':
                    frame_mz_arrays = []
                    frame_intensity_arrays = []
                    frame_mobility_arrays = []
                for scan_num in range(0, int(frames_dict['NumScans'])):
                    mz_array, intensity_array = extract_spectrum_arrays(tdf_data,
                                                                        mode,
                                                                        True,
                                                                        frame,
                                                                        scan_num,
                                                                        scan_num + 1,
                                                                        encoding)
                    if mz_array.size != 0 and intensity_array.size != 0 and mz_array.size == intensity_array.size:
                        mobility = tdf_data.scan_num_to_oneoverk0(frame, np.array([scan_num]))[0]
                        mobility_array = np.repeat(mobility, mz_array.size)

                        if ms1_groupby == 'frame':
                            frame_mz_arrays.append(mz_array)
                            frame_intensity_arrays.append(intensity_array)
                            frame_mobility_arrays.append(mobility_array)
                        elif ms1_groupby == 'scan':
                            base_peak_index = np.where(intensity_array == np.max(intensity_array))

                            scan_dict = {'scan_number': int(scan_num),
                                         'scan_type': 'MS1 spectrum',
                                         'ms_level': 1,
                                         'mz_array': mz_array,
                                         'intensity_array': intensity_array,
                                         'mobility': mobility,
                                         'mobility_array': mobility_array,
                                         'polarity': frames_dict['Polarity'],
                                         'centroided': centroided,
                                         'retention_time': float(frames_dict['Time']),
                                         'total_ion_current': sum(intensity_array),
                                         'base_peak_mz': mz_array[base_peak_index][0].astype(float),
                                         'base_peak_intensity': intensity_array[base_peak_index][0].astype(float),
                                         'high_mz': float(max(mz_array)),
                                         'low_mz': float(min(mz_array)),
                                         'frame': frame}
                            list_of_parent_scans.append(scan_dict)

                if frame_mz_arrays and frame_intensity_arrays and frame_mobility_arrays:
                    frames_array = np.stack((np.concatenate(frame_mz_arrays, axis=None),
                                             np.concatenate(frame_intensity_arrays, axis=None),
                                             np.concatenate(frame_mobility_arrays, axis=None)),
                                            axis=-1)
                    frames_array = np.unique(frames_array[np.argsort(frames_array[:, 0])], axis=0)

                    base_peak_index = np.where(frames_array[:, 1] == np.max(frames_array[:, 1]))

                    scan_dict = {'scan_number': None,
                                 'scan_type': 'MS1 spectrum',
                                 'ms_level': 1,
                                 'mz_array': frames_array[:, 0],
                                 'intensity_array': frames_array[:, 1],
                                 'mobility': None,
                                 'mobility_array': frames_array[:, 2],
                                 'polarity': frames_dict['Polarity'],
                                 'centroided': centroided,
                                 'retention_time': float(frames_dict['Time']),
                                 'total_ion_current': sum(frames_array[:, 1]),
                                 'base_peak_mz': frames_array[:, 0][base_peak_index][0].astype(float),
                                 'base_peak_intensity': frames_array[:, 1][base_peak_index][0].astype(float),
                                 'high_mz': float(max(frames_array[:, 0])),
                                 'low_mz': float(min(frames_array[:, 0])),
                                 'frame': frame}
                    list_of_parent_scans.append(scan_dict)
            if int(tdf_data.ms1_frames[index + 1]) - int(tdf_data.ms1_frames[index]) > 1:
                precursor_dicts = [i for i in list_of_precursors_dict if int(i['Parent']) == frame]
                for precursor_dict in precursor_dicts:
                    pasefframemsmsinfo_dicts = [i for i in list_of_pasefframemsmsinfo_dict
                                                if int(i['Precursor']) == int(precursor_dict['Id'])]
                    pasef_mz_arrays = []
                    pasef_intensity_arrays = []
                    #pasef_mobility_arrays = []
                    for pasef_dict in pasefframemsmsinfo_dicts:
                        scan_begin = int(pasef_dict['ScanNumBegin'])
                        scan_end = int(pasef_dict['ScanNumEnd'])
                        frame_mz_arrays = []
                        frame_intensity_arrays = []
                        #frame_mobility_arrays = []
                        for scan_num in range(scan_begin, scan_end):
                            mz_array, intensity_array = extract_spectrum_arrays(tdf_data,
                                                                                mode,
                                                                                True,
                                                                                int(pasef_dict['Frame']),
                                                                                scan_begin,
                                                                                scan_end,
                                                                                encoding)
                            if mz_array.size != 0 and intensity_array.size != 0 and mz_array.size == intensity_array.size:
                                #mobility = tdf_data.scan_num_to_oneoverk0(int(pasef_dict['Frame']),
                                #                                          np.array([scan_num]))[0]
                                #mobility_array = np.repeat(mobility, mz_array.size)

                                frame_mz_arrays.append(mz_array)
                                frame_intensity_arrays.append(intensity_array)
                                #frame_mobility_arrays.append(mobility_array)
                        if frame_mz_arrays and frame_intensity_arrays:
                            frames_array = np.stack((np.concatenate(frame_mz_arrays, axis=None),
                                                     np.concatenate(frame_intensity_arrays, axis=None)),
                                                     #np.concatenate(frame_mobility_arrays, axis=None)),
                                                    axis=-1)
                            frames_array = np.unique(frames_array[np.argsort(frames_array[:, 0])], axis=0)
                            pasef_mz_arrays.append(frames_array[:, 0])
                            pasef_intensity_arrays.append(frames_array[:, 1])
                            #pasef_mobility_arrays.append(frames_array[:, 2])
                    if pasef_mz_arrays and pasef_intensity_arrays:
                        pasef_array = np.stack((np.concatenate(pasef_mz_arrays, axis=None),
                                                np.concatenate(pasef_intensity_arrays, axis=None)),
                                                #np.concatenate(pasef_mobility_arrays, axis=None)),
                                               axis=-1)
                        pasef_array = np.unique(pasef_array[np.argsort(pasef_array[:, 0])], axis=0)

                        base_peak_index = np.where(pasef_array[:, 1] == np.max(pasef_array[:, 1]))

                        scan_dict = {'scan_number': None,
                                     'scan_type': 'MSn spectrum',
                                     'ms_level': 2,
                                     'mz_array': pasef_array[:, 0],
                                     'intensity_array': pasef_array[:, 1],
                                     'mobility': None,
                                     'mobility_array': None,
                                     'polarity': frames_dict['Polarity'],
                                     'centroided': centroided,
                                     'retention_time': float(frames_dict['Time']),
                                     'total_ion_current': sum(pasef_array[:, 1]),
                                     'base_peak_mz': pasef_array[:, 0][base_peak_index][0].astype(float),
                                     'base_peak_intensity': pasef_array[:, 1][base_peak_index][0].astype(float),
                                     'high_mz': float(max(pasef_array[:, 0])),
                                     'low_mz': float(min(pasef_array[:, 0])),
                                     'target_mz': float(precursor_dict['AverageMz']),
                                     'isolation_lower_offset': float(pasefframemsmsinfo_dicts[0]['IsolationWidth']) / 2,
                                     'isolation_upper_offset': float(pasefframemsmsinfo_dicts[0]['IsolationWidth']) / 2,
                                     'selected_ion_mz': float(precursor_dict['LargestPeakMz']),
                                     'selected_ion_intensity': float(precursor_dict['Intensity']),
                                     'selected_ion_mobility': tdf_data.scan_num_to_oneoverk0(int(precursor_dict['Parent']),
                                                              np.array([int(precursor_dict['ScanNumber'])]))[0],
                                     'charge_state': precursor_dict['Charge'],
                                     'collision_energy': pasefframemsmsinfo_dicts[0]['CollisionEnergy'],
                                     'parent_frame': int(precursor_dict['Parent']),
                                     'parent_scan': int(precursor_dict['ScanNumber'])}
                        list_of_product_scans.append(scan_dict)
    return list_of_parent_scans, list_of_product_scans


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
