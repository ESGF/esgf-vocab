from esgvoc.cli.drs import drsvalid


_SOME_VALID_CLI_ENTRIES = [['cmip6plus','filename','od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-201212.nc'], 
                     ['cmip6plus','dataset','CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn'],
                     ['cmip6plus','directory','CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923'], 

                    ['cmip6plus','filename','od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-201212.nc', 'od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-201212.nc', 'od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-201212.nc'],
                    ['cmip6plus','dataset','CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn', 'CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn','CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn'],
                    ['cmip6plus','directory','CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923','CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923','CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923' ],

                    ['cmip6plus','filename','od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-201212.nc', 'dataset','CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn', 'directory','CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923'],

                    ['cmip6plus','dataset','CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn', 'cmip6','CMIP6.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn','CMIP6.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn'],


                    ['cmip6plus','dataset','CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn','CMIP6.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn','CMIP6.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn', 'filename',  'od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-201212.nc', 'od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-201212.nc', 'cmip6','od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-201212.nc', 'directory', 'CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923','CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923' ],
                     ]


def test_valid_drs():
    for entry in _SOME_VALID_CLI_ENTRIES:
        reports = drsvalid(entry)
        
        for report in reports:
            print(report)
            assert report.nb_warnings == 0 and report.nb_errors ==0
    

