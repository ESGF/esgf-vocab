import json
from string import Template

from jsonschema import validate

from esgvoc.api import projects
from esgvoc.apps.jsg import json_schema_generator as jsg
from tests.api_inputs import project_id  # noqa: F401

_COMPLIANCE_PROJECT_TESTED = 'cmip6'

project_specs_being_tested = projects.get_project(_COMPLIANCE_PROJECT_TESTED)

if project_specs_being_tested is not None and \
   project_specs_being_tested.catalog_specs is not None:
  project_version = project_specs_being_tested.catalog_specs.version
  project_extensions = project_specs_being_tested.catalog_specs.catalog_properties.extensions
  extension_url_template = project_specs_being_tested.catalog_specs.catalog_properties.url_template
  extension_urls = list()
  for project_extension in project_extensions:
     extension_url = extension_url_template.format(extension_name=project_extension.name,
                                                   extension_version=project_extension.version)
     extension_urls.append(extension_url)
  extension_url = extension_url_template.format(extension_name=_COMPLIANCE_PROJECT_TESTED,
                                                extension_version=project_version)
  extension_urls.append(extension_url)
else:
   raise RuntimeError('unable to compute extension URL')


json_template = Template(
"""
{
  "type": "Feature",
  "stac_version": "1.1.0",
  "stac_extensions": $extension_urls,
  "id": "CMIP6.ScenarioMIP.THU.CIESM.ssp585.r1i1p1f1.Amon.rsus.gr.v20200806",
  "collection": "CMIP6",
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [
          -180,
          -90
        ],
        [
          178.75,
          -90
        ],
        [
          178.75,
          90
        ],
        [
          -180,
          90
        ],
        [
          -180,
          -90
        ]
      ]
    ]
  },
  "bbox": [
    -180,
    -90,
    178.75,
    90
  ],
  "properties": {
    "created": "2025-01-24T14:29:23.741213Z",
    "end_datetime": "4114-12-16T12:00:00Z",
    "latest": true,
    "retracted": false,
    "size": 138734,
    "start_datetime": "4029-01-16T12:00:00Z",
    "title": "This is my dataset",
    "updated": "2025-01-24T14:29:23.741213Z",
    "cmip6:version": "20250724",
    "cmip6:activity_id": [
      "CMIP",
      "PAMIP"
    ],
    "cmip6:citation_url": "http://cera-www.dkrz.de/WDCC/meta/CMIP6/CMIP6.ScenarioMIP.THU.CIESM.ssp585.r1i1p1f1.Amon.rsus.gr.v20200806.json",
    "cmip6:conventions": [
      "CF-1.7",
      "CMIP-6.2"
    ],
    "cmip6:data_specs_version": "01.00.29",
    "cmip6:experiment": "CMIP6 historical (CO2 emission-driven)",
    "cmip6:experiment_id": "ssp585",
    "cmip6:forcing_index": "1",
    "cmip6:frequency": "mon",
    "cmip6:further_info_url": "https://furtherinfo.es-doc.org/CMIP6.THU.CIESM.ssp585.none.r1i1p1f1",
    "cmip6:grid": "zonal mean data reported on a model's native latitude grid",
    "cmip6:grid_label": "gr",
    "cmip6:initialization_index": "1",
    "cmip6:institution": "National Taiwan University, Taipei 10650, Taiwan",
    "cmip6:institution_id": "THU",
    "cmip6:license": "CC-BY-4.0",
    "cmip6:member_id": "s1989-r1i1p1f1",
    "cmip6:nominal_resolution": "100 km",
    "cmip6:physics_index": "1",
    "cmip6:pid": "hdl:21.14100/7a8097a5-3ebb-4491-8640-01843dbdecd2",
    "cmip6:product": "model-output",
    "cmip6:realization_index": "1",
    "cmip6:realm": [
      "atmos"
    ],
    "cmip6:source": "NUIST ESM v3",
    "cmip6:source_id": "CIESM",
    "cmip6:source_type": [
      "AOGCM"
    ],
    "cmip6:sub_experiment": "initialized near end of year 1950",
    "cmip6:sub_experiment_id": "s1989",
    "cmip6:table_id": "Amon",
    "cmip6:variable_cf_standard_name": "surface_upwelling_shortwave_flux_in_air",
    "cmip6:variable_id": "rsus",
    "cmip6:variable_long_name": "Surface Upwelling Shortwave Radiation",
    "cmip6:variable_units": "W m-2",
    "cmip6:variant_label": "r1i1p1f1"
  },
  "links": [
    {
      "rel": "self",
      "type": "application/geo+json",
      "href": "https://api.stac.ceda.ac.uk/collections/cmip6/items/CMIP6.ScenarioMIP.THU.CIESM.ssp585.r1i1p1f1.Amon.rsus.gr.v20200806"
    },
    {
      "rel": "parent",
      "type": "application/json",
      "href": "https://api.stac.ceda.ac.uk/collections/cmip6"
    },
    {
      "rel": "collection",
      "type": "application/json",
      "href": "https://api.stac.ceda.ac.uk/collections/cmip6"
    },
    {
      "rel": "root",
      "type": "application/json",
      "href": "https://api.stac.ceda.ac.uk/"
    }
  ],
  "assets": {
    "reference_file": {
      "href": "https://dap.ceda.ac.uk/badc/cmip6/metadata/kerchunk/pipeline1/ScenarioMIP/THU/CIESM/kr1.0/CMIP6_ScenarioMIP_THU_CIESM_ssp585_r1i1p1f1_Amon_rsus_gr_v20200806_kr1.0.json",
      "type": "application/zstd",
      "created": "2025-01-24T14:29:23.741213Z",
      "file:checksum": "90e402107a7f2588a85362b9beea2a12d4514d45",
      "file:size": 12345,
      "protocol": "https",
      "updated": "2025-01-24T14:29:23.741213Z",
      "cmip6:tracking_id": "hdl:21.14100/7a8097a5-3ebb-4491-8640-01843dbdecd2",
      "roles": [
        "replica",
        "data"
      ],
      "open_zarr_kwargs": {
        "decode_times": true
      }
    },
    "data0001": {
      "href": "https://dap.ceda.ac.uk/badc/cmip6/data/CMIP6/ScenarioMIP/THU/CIESM/ssp585/r1i1p1f1/Amon/rsus/gr/v20200806/rsus_Amon_CIESM_ssp585_r1i1p1f1_gr_402901-411412.nc",
      "type": "application/netcdf",
      "created": "2025-01-24T14:29:23.741213Z",
      "file:checksum": "90e402107a7f2588a85362b9beea2a12d4514d45",
      "file:size": 23553,
      "protocol": "s3",
      "updated": "2025-01-24T14:29:23.741213Z",
      "cmip6:tracking_id": "hdl:21.14100/7a8097a5-3ebb-4491-8640-01843dbdecd2",
      "roles": [
        "data"
      ]
    }
  }
}
""")
str_extension_urls = "[" + ", ".join(f'"{url}"' for url in extension_urls) + "]"
json_example = json.loads(json_template.substitute(extension_urls=str_extension_urls))


def test_cmip6_compliance() -> None:
    json_schema = jsg.generate_json_schema(_COMPLIANCE_PROJECT_TESTED)
    validate(instance=json_example, schema=json_schema)



def test_js_generation(project_id) -> None:
    js = jsg.generate_json_schema(project_id)
    assert js
