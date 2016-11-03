#!/usr/bin/env python


from obspy.core.inventory import Inventory, Network, Station, Channel, Site
import obspy
import sys
import re
from obspy.core.inventory.response import PolesZerosResponseStage, Response,\
    InstrumentSensitivity
from obspy.core.util.obspy_types import CustomComplex
from lxml.etree import Element

PZnamedict={
        '* NETWORK   (KNETWK)':'net',
        '* STATION    (KSTNM)':'sta',
        '* LOCATION   (KHOLE)':'loc',
        '* CHANNEL   (KCMPNM)':'cha',
        '* CREATED           ':'created',
        '* START             ':'start_time',
        '* END               ':'end_time',
        '* DESCRIPTION       ':'description',
        '* LATITUDE          ':'lat',
        '* LONGITUDE         ':'lon',
        '* ELEVATION         ':'elv',
        '* DEPTH             ':'dep',
        '* DIP               ':'dip',
        '* AZIMUTH           ':'az',
        '* SAMPLE RATE       ':'sample_rate',
        '* INPUT UNIT        ':'in_unit',
        '* OUTPUT UNIT       ':'out_unit',
        '* INSTTYPE          ':'inst_type',
        '* INSTGAIN          ':'inst_gain',
        '* COMMENT           ':'comment',
        '* SENSITIVITY       ':'sensitivity',
        '* A0                ':'A0'
        }

def get_azdip(chadict):
    if not chadict['az'] or not chadict['dip']:
        if chadict['cha'][-1]=='E':
            az=90
            dip=0
        elif chadict['cha'][-1]=='N':
            az=0
            dip=0
        elif chadict['cha'][-1]=='Z':
            az=0
            dip=90
        else: 
            raise(BaseException('Channel name not ending with [E,N,Z]: '+chadict['cha']))
    else:
        try:
            az=float(chadict['az'])
            dip=float(chadict['dip'])
        except:
            raise(BaseException('Can\'t parse az or dip: '+chadict['az']+' '+chadict['dip']))
    return az,dip

def parsePZfile(infile):
    with open(infile,'r') as f:
        fstr=f.read()
        net,chadict=parsePZstr(fstr)
        
    return net,chadict
        
def parsePZstr(fstr):
    chadict={}
    for line in fstr.split('\n'):
        line=line.split(':')
        #print line,line[0]
        try:
            chadict[PZnamedict[line[0]]]=':'.join(line[1:]).strip()
            print PZnamedict[line[0]],':',chadict[PZnamedict[line[0]]]
        except:
            continue
        
    net=parsePZdict(fstr,chadict)
    return net,chadict   

def parsePZstrpaz(fstr):
    poles=[]
    zeros=[]
    lines=fstr.split('\n')
    i=0
    for i in range(len(lines)):
        line=lines[i].split()
        if len(line)>0 and line[0]=='POLES':
            npoles=int(line[1])
            for j in range(npoles):                
                try:
                    line=lines[i+j+1].split()
                    poles.append(float(line[0])+float(line[1])*(1j))
                except:
                    raise(BaseException('failed to read poles in line: '+line))
        
        if len(line)>0 and line[0]=='ZEROS':
            nzeros=int(line[1])
            for j in range(nzeros):
                try:
                    line=lines[i+j+1].split()
                    zeros.append(float(line[0])+float(line[1])*(1j))
                except:
                    raise(BaseException('failed to read zeros in line: '+line))
        
        if len(line)>0 and line[0]=='CONSTANT':
            try:
                constant=float(line[1])
            except:
                raise(BaseException('failed to read constant in line: '+line))
            
    return poles,zeros,constant

def parsePZdict(fstr,chadict):
    #parse PZ string into net
    try:
        lat=float(chadict['lat'])
    except:
        pass
    try:
        lon=float(chadict['lon'])
    except:
        pass
    try:
        elv=float(chadict['elv'])
    except:
        pass
    try:
        dep=float(chadict['dep'])
    except:
        dep=0.   
    
    az,dip=get_azdip(chadict)
    
    net = Network(
    # This is the network code according to the SEED standard.
    code=chadict['net'],
    # A list of stations. We'll add one later.
    stations=[],
    description="Kocaeli Universitesi MARSite istasyonlari",
    # Start-and end dates are optional.
    #start_date=obspy.UTCDateTime(2016, 1, 2))
    )
    
    sta = Station(
    # This is the station code according to the SEED standard.
    code=chadict['sta'],
    latitude=lat,
    longitude=lon,
    elevation=elv,
    creation_date=obspy.UTCDateTime('T'.join(re.sub('\.',':',chadict['created']).split())),
    site=Site(name=chadict['sta'])
    )
    
    cha = Channel(
    # This is the channel code according to the SEED standard.
    code=chadict['cha'],
    # This is the location code according to the SEED standard.
    location_code=chadict['loc'],
    # Note that these coordinates can differ from the station coordinates.
    latitude=lat,
    longitude=lon,
    elevation=elv,
    depth=dep,
    azimuth=az,
    dip=dip
    )
    
    pazstage=get_resp_stage(fstr,chadict)
    
    net.stations.append(sta)
    sta.channels.append(cha)
    cha.response=Response(response_stages=[pazstage])
    
    return net
def get_resp_stage(fstr,chadict):
    
    poles,zeros,constant=parsePZstrpaz(fstr)
    
    poles=map(CustomComplex,poles)
    zeros=map(CustomComplex,zeros)
    
    a0=float(chadict['A0'])
    
    
    
    #One PAZ stage only:
    
    stage_sequence_number=1
    stage_gain=constant
    
    #info not in PZ file:
    stage_gain_frequency=1.0 #Hz 
    
    #might be messed up, M/S default
    input_units=chadict['in_unit'] #M/S
    
    if input_units not in ['M/S','M/S**2']:
        input_units='M/S' 
    
    output_units=chadict['out_unit']
    
    #assuming
    pz_transfer_function_type='LAPLACE (RADIANS/SECOND)'
    
    #assuming
    normalization_frequency=1.0 #Hz
    
    normalization_factor=float(chadict['A0'])
    
    source=0
    
    pazstage=PolesZerosResponseStage(stage_sequence_number, stage_gain,
    stage_gain_frequency, input_units, output_units, pz_transfer_function_type,
    normalization_frequency, zeros, poles, normalization_factor=normalization_factor,
    resource_id=None, resource_id2=None, name=None, input_units_description=None,
    output_units_description=None, description=None,
    decimation_input_sample_rate=None, decimation_factor=None,
    decimation_offset=None, decimation_delay=None,
    decimation_correction=None)#, instrument_sensitivity=instrument_sensitivity)
    
    #instrument sensitivity:
    value=float(chadict['sensitivity'].split()[0])
    frequency=1.0 #Hz
    input_units=input_units
    
    instrument_sensitivity=InstrumentSensitivity(value, 
                          frequency, 
                          input_units, 
                          output_units, 
                          input_units_description=None, 
                          output_units_description=None, 
                          frequency_range_start=None, 
                          frequency_range_end=None, 
                          frequency_range_db_variation=None)
    
    pazstage.instrument_sensitivity=instrument_sensitivity
    pazstage.instrument_polynomial=None
    return pazstage

def add_to_inv(inv,net):
    #merges net into inv, assuming network and station codes are unique
    if net in inv:
        for sta in net:
            if sta in net:
                for cha in sta:
                    if cha in sta:
                        pass
                        print 'channel already in inventory'
                    else:
                        sta.channels.append(sta)
            else:
                net.stations.append(sta)
    inv.networks.append(net)
    
    return inv
         
def create_sample_inv():
    # We'll first create all the various objects. These strongly follow the
# hierarchy of StationXML files.
    inv = Inventory(
        # We'll add networks later.
        networks=[],
        # The source should be the id whoever create the file.
        source="ObsPy-Tutorial")
    
    net = Network(
        # This is the network code according to the SEED standard.
        code="XX",
        # A list of stations. We'll add one later.
        stations=[],
        description="A test stations.",
        # Start-and end dates are optional.
        start_date=obspy.UTCDateTime(2016, 1, 2))
    
    sta = Station(
        # This is the station code according to the SEED standard.
        code="ABC",
        latitude=1.0,
        longitude=2.0,
        elevation=345.0,
        creation_date=obspy.UTCDateTime(2016, 1, 2),
        site=Site(name="First station"))
    
    cha = Channel(
        # This is the channel code according to the SEED standard.
        code="EHZ",
        # This is the location code according to the SEED standard.
        location_code="",
        # Note that these coordinates can differ from the station coordinates.
        latitude=1.0,
        longitude=2.0,
        elevation=345.0,
        depth=10.0,
        azimuth=0.0,
        dip=-90.0)


    # Now tie it all together.
    inv.networks.append(net)
    net.stations.append(sta)
    sta.channels.append(cha)
    
    return inv,net,sta

def writeStationXml(inv):
    stxml=Element('FDSNStationXML')
    stxml.set('xmlns','http://www.fdsn.org/xml/station/1')
    stxml.set('schemaVersion','1')
    
    #Header
    source=Element('Source')
    source.text='KOERI'
    stxml.append(source)
    
    module=Element('Module')
    module.text='ozakin PZ2stationXML converter 1.0'
    stxml.append(module)
    
    module_uri=Element('ModuleURI')
    module_uri.text='https://github.com/maratumba/pztostationxml'
    stxml.append(module_uri)
    
    created=Element('Created')
    created.text=('2016-09-26T05:20:18.224-07:00')
    stxml.append(created)
    
    
    for net in inv:
        netx=Element('Network')
        netx.set('code',net.code)
        
        description=Element('Description')
        description.text='Kandilli Observatory BB and SM Stations'
        netx.append(description)
        
        for sta in net:
            stax=Element('Station')
            stax.set('code',sta.code)
            stax.set('startDate',)
            
            lat=Element('Latitude')
            lat.text
            
            for cha in sta:
                chax=Element('Channel')
                
                for resp in cha.response_stages:
                    respx=Element('Response')
    

if __name__=='__main__':

    infile='ALTN_BHE_KOU_19900101_OnSite_W.PZ'
    
    
    inv = Inventory(
        # We'll add networks later.
        networks=[],
        # The source should be the id whoever create the file.
        source="Yaman Ozakin - dandik@gmail.com")
    
    

        #if network not in inv, create network
            #if station not in network, create station
                #if channel not in station, create station
    
    net,chadict=parsePZfile(infile)
    inv.networks.append(net)
    
    #ssys.exit()
    
    '''
    resp=PolesZerosResponseStage(stage_sequence_number, stage_gain,
    stage_gain_frequency, input_units, output_units, pz_transfer_function_type,
    normalization_frequency, zeros, poles, normalization_factor=1.0,
    resource_id=None, resource_id2=None, name=None, input_units_description=None,
    output_units_description=None, description=None,
    decimation_input_sample_rate=None, decimation_factor=None,
    decimation_offset=None, decimation_delay=None,
    decimation_correction=None)[source]
    '''
    
    
    #inv.write("station.xml", format="stationxml", validate=True)