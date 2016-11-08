#!/usr/bin/env python


from obspy.core.inventory import Inventory, Network, Station, Channel, Site
import obspy
import sys
import re
from obspy.core.inventory.response import PolesZerosResponseStage, Response,\
    InstrumentSensitivity
from obspy.core.util.obspy_types import CustomComplex, ComplexWithUncertainties

from lxml.etree import Element
from obspy.core.inventory.util import Frequency, Equipment
import glob
from obspy.core.utcdatetime import UTCDateTime


#Response Stage
#https://docs.obspy.org/master/packages/autogen/obspy.core.inventory.response.ResponseStage.__init__.html


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
                    pole=float(line[0])+float(line[1])*(1j)
                    pole=ComplexWithUncertainties(CustomComplex(pole),lower_uncertainty=0.0,upper_uncertainty=0.0)
                    poles.append(pole)
                except:
                    raise(BaseException('failed to read poles in line: '+line))
        
        if len(line)>0 and line[0]=='ZEROS':
            nzeros=int(line[1])
            for j in range(nzeros):
                try:
                    line=lines[i+j+1].split()
                    zero=float(line[0])+float(line[1])*(1j)
                    zero=ComplexWithUncertainties(CustomComplex(zero),lower_uncertainty=0.0,upper_uncertainty=0.0)
                    zeros.append(zero)
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
    try:
        sample_rate=float(chadict['sample_rate'])
    except:
        None
    
    az,dip=get_azdip(chadict)
    
    net = Network(
                  # This is the network code according to the SEED standard.
                  code=chadict['net'],
                  # A list of stations. We'll add one later.
                  stations=[],
                  description="Kocaeli Marsite",
                  # Start-and end dates are optional.
                  start_date=obspy.UTCDateTime(chadict['start_time']),
                  )
    
    
    
    sta = Station(
                  # This is the station code according to the SEED standard.
                  code=chadict['sta'],
                  latitude=lat,
                  longitude=lon,
                  elevation=elv,
                  creation_date=obspy.UTCDateTime('T'.join(re.sub('\.',':',chadict['created']).split())),
                  start_date=obspy.UTCDateTime(chadict['start_time']),
                  site=Site(name=chadict['sta'])
                  )
    
    # necessary minimum sensor info for channel:
    #<Sensor>
    #   <Model>30s,</Model>
    #</Sensor>
    equipment=Equipment(chadict['inst_type'])
    
    
    #Channel ref: http://docs.obspy.org/archive/0.10.2/packages/autogen/obspy.station.channel.Channel.__init__.html
    cha = Channel(
                  sensor=equipment,
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
                  start_date=obspy.UTCDateTime(chadict['start_time']),
                  dip=dip,
                  sample_rate=sample_rate
                  )
    
    pazstage=get_resp_stage(fstr,chadict)
    
    net.stations.append(sta)
    sta.channels.append(cha)
    cha.response=Response(
                          response_stages=[pazstage],
                          instrument_sensitivity=pazstage.instrument_sensitivity
                          )
    
    
    return net

def get_resp_stage(fstr,chadict):
    
    norm_freq_def=1.0 #Hz
    stage_gain_frequency=1.0 #Hz
    frequency_def=1.0 #Hz
    
    poles,zeros,constant=parsePZstrpaz(fstr)
    
    #for pole in poles:
    #    pole=ComplexWithUncertainties(CustomComplex(pole),lower_uncertainty=0.0,upper_uncertainty=0.0)
        
    #for zero in zeros:
    #    zero=ComplexWithUncertainties(CustomComplex(zero),lower_uncertainty=0.0,upper_uncertainty=0.0)
    
    #poles=map(ComplexWithUncertainties,poles)
    #zeros=map(ComplexWithUncertainties,zeros)
    
    a0=float(chadict['A0'])
    
    
    
    #One PAZ stage only:
    
    stage_sequence_number=1
    stage_gain=constant
    
    #info not in PZ file:
     
    
    #might be messed up, M/S default
    input_units=chadict['in_unit'] #M/S
    
    if input_units not in ['M/S','M/S**2']:
        input_units='M/S' 
    
    output_units=chadict['out_unit']
    
    #assuming
    pz_transfer_function_type='LAPLACE (RADIANS/SECOND)'
    
    #assuming
    normalization_frequency=Frequency(norm_freq_def,lower_uncertainty=0, upper_uncertainty=0) #Hz
    
    normalization_factor=float(chadict['A0'])
    
    source=0
    
    #print poles,type(poles[0])
    
    pazstage=PolesZerosResponseStage(stage_sequence_number, 
                                     stage_gain,
                                     stage_gain_frequency, 
                                     input_units, output_units, 
                                     pz_transfer_function_type,
                                     normalization_frequency, 
                                     zeros, 
                                     poles, 
                                     normalization_factor=normalization_factor,
                                     resource_id=None, 
                                     resource_id2=None, 
                                     name=None, 
                                     input_units_description=None,
                                     output_units_description=None, 
                                     description=None,
                                     decimation_input_sample_rate=None, 
                                     decimation_factor=None,
                                     decimation_offset=None, 
                                     decimation_delay=None,
                                     decimation_correction=None)#, instrument_sensitivity=instrument_sensitivity)
    
    #instrument sensitivity:
    value=float(chadict['sensitivity'].split()[0])
    frequency=frequency_def #Hz
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

def add_to_inv(inv2,net):
    #merges net into inv, assuming network and station codes are unique
    
    inv=inv2.copy()
    
    if net.code in set((net2.code) for net2 in inv.networks):
        net_inv=[net2 for net2 in inv if net2.code == net.code][0]
        for sta in net:
            if sta.code in set((sta2.code) for sta2 in net_inv):
                sta_inv=[sta2 for sta2 in net_inv if sta2.code == sta.code][0]
                for cha in sta:
                    if cha.code in set((cha2.code) for cha2 in sta_inv):
                        print 'channel already in inventory'
                    else:
                        sta_inv.channels.append(cha)
            else:
                net_inv.stations.append(sta)
    else:
        inv.networks.append(net)
    
    return inv     
         
def create_empty_inv(source='None'):
    inv=Inventory(
                  networks=[],
                  source=source)
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
    #not working, not necessary now that it can read into inventory 
    
    #defaults missing in PZ
    sample_rate_def=100. #Hz
    depth_def=0. #m
    clock_drift_def=0. #s
    sensor_type_def=30. #s
    
    
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
            stax.set('startDate',str(sta.creation_date))
            
            lat=Element('Latitude')
            lat.text=str(chadict['lat'])
            stax.append(lat)
            
            
            lon=Element('Longitude')
            lon.text=str(chadict['lon'])
            stax.append(lon)
            
            elv=Element('Elevation')
            elv.text=str(chadict['elv'])
            stax.append(elv)
            
            
            creation_date=Element('Created')
            creation_date.text=str(sta.creation_date)
            stax.append(creation_date)
            
            for cha in sta:
                chax=Element('Channel')
                lat=Element('Latitude')
                lat.text=str(chadict['lat'])
                chax.append(lat)
                
                
                lon=Element('Longitude')
                lon.text=str(chadict['lon'])
                chax.append(lon)
                
                elv=Element('Elevation')
                elv.text=str(chadict['elv'])
                chax.append(elv)
                
                dep=Element('Depth')
                dep.text=str(depth)
                chax.append(dep_def)
                
                az=Element('Azimuth')
                az.text=str(cha.az)
                chax.append(az)
                
                dip=Element('Dip')
                dip.text=str(cha.dip)
                chax.append(dip)
                
                type=Element('Type')
                type.text='GEOPHYSICS'
                chax.append(type)
                
                type=Element('Type')
                type.text='CONTINUOUS'
                chax.append(type)
                
                sample_rate=Element('SampleRate')
                sample_rate.text=sample_rate_def
                chax.append(sample_rate)
                
                clock_drift=Element('ClockDrift')
                clock_drift.text=clock_drift_def
                chax.append(clock_drift)
                
                sensor=Element('Sensor')
                sensor_desc=Element('Description')
                sensor_desc.text=sensor_type_def
                sensor.append(sensor_desc)
                chax.append(sensor)
                
                for resp in cha.response.response_stages:
                    respx=Element('Response')
                    
                    resp_elems={
                                'InstrumentSensitivity':'hebe'
                                }
                    
                    
                    
                    
                    
                    
            netx.append(stax)
        stxml.append(netx)
    
    return stxml
    

if __name__=='__main__':

    #infile='ALTN_BHE_KOU_19900101_OnSite_W.PZ'
    
    inv = create_empty_inv('Yaman Ozakin - dandik@gmail.com')
    
    for f in glob.glob('*PZ'):
        net,chadict=parsePZfile(f)
        inv=add_to_inv(inv, net)
        
    #change the network name to TL
    inv[0].code='TL'
    inv.write('kocaeli_radian.xml',format='stationxml',validate=True)
    
        # We'll add networks later.
        #networks=[],
        # The source should be the id whoever create the file.
        #source="Yaman Ozakin - dandik@gmail.com")
    
    

        #if network not in inv, create network
            #if station not in network, create station
                #if channel not in station, create station
    
    #net,chadict=parsePZfile(infile)
    #inv.networks.append(net)
    
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