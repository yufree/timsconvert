from timsconvert.parse_lcms import *
import os
import logging
import numpy as np
from lxml import etree as et
from psims.mzml import MzMLWriter


def write_mzml_metadata(data, writer, infile, mode, ms2_only):
    # Basic file descriptions.
    file_description = []
    # Add spectra level and centroid/profile status.
    if ms2_only == False:
        file_description.append('MS1 spectrum')
        file_description.append('MSn spectrum')
    elif ms2_only == True:
        file_description.append('MSn spectrum')
    if mode == 'raw' or mode == 'centroid':
        file_description.append('centroid spectrum')
    elif mode == 'profile':
        file_description.append('profile spectrum')
    writer.file_description(file_description)

    # Source file
    sf = writer.SourceFile(os.path.split(infile)[0],
                           os.path.split(infile)[1],
                           id=os.path.splitext(os.path.split(infile)[1])[0])

    # Add list of software.
    acquisition_software_id = data.meta_data['AcquisitionSoftware']
    acquisition_software_version = data.meta_data['AcquisitionSoftwareVersion']
    if acquisition_software_id == 'Bruker otofControl':
        acquisition_software_params = ['micrOTOFcontrol', ]
    else:
        acquisition_software_params = []
    psims_software = {'id': 'psims-writer',
                      'version': '0.1.2',
                      'params': ['python-psims', ]}
    writer.software_list([{'id': acquisition_software_id,
                           'version': acquisition_software_version,
                           'params': acquisition_software_params},
                          psims_software])

    # Instrument configuration.
    inst_count = 0
    if data.meta_data['InstrumentSourceType'] in INSTRUMENT_SOURCE_TYPE.keys():
        inst_count += 1
        source = writer.Source(inst_count, [INSTRUMENT_SOURCE_TYPE[data.meta_data['InstrumentSourceType']]])
    # If source isn't found in the GlobalMetadata SQL table, hard code source to ESI
    else:
        inst_count += 1
        source = writer.Source(inst_count, [INSTRUMENT_SOURCE_TYPE['1']])

    # Analyzer and detector hard coded for timsTOF fleX
    inst_count += 1
    analyzer = writer.Analyzer(inst_count, ['quadrupole', 'time-of-flight'])
    inst_count += 1
    detector = writer.Detector(inst_count, ['electron multiplier'])
    inst_config = writer.InstrumentConfiguration(id='instrument', component_list=[source, analyzer, detector],
                                                 params=[INSTRUMENT_FAMILY[data.meta_data['InstrumentFamily']]])
    writer.instrument_configuration_list([inst_config])

    # Data processing element.
    proc_methods = []
    proc_methods.append(writer.ProcessingMethod(order=1, software_reference='psims-writer',
                                                params=['Conversion to mzML']))
    processing = writer.DataProcessing(proc_methods, id='exportation')
    writer.data_processing_list([processing])


# Calculate the number of spectra to be written.
# Basically an abridged version of parse_lcms_tdf to account for empty spectra that don't end up getting written.
def get_spectra_count(tdf_data):
    ms1_count = tdf_data.frames['MsMsType'].values.size
    ms2_count = len(list(filter(None, tdf_data.precursors['MonoisotopicMz'].values)))
    return ms1_count + ms2_count


def update_spectra_count(outdir, outfile, scan_count):
    mzml_tree = et.parse(os.path.join(outdir, outfile))
    mzml = mzml_tree.getroot()
    ns = mzml.tag[:mzml.tag.find('}') + 1]
    mzml.find('.//' + ns + 'spectrumList').set('count', str(scan_count).encode('utf-8'))
    mzml_tree.write(os.path.join(outdir, outfile), encoding='utf-8', xml_declaration=True)
