"""
Model (i.e. schema/definition) of the model component data descriptor
"""
#
# from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor
#
#
# class ModelComponent(PlainTermDataDescriptor):
#     """
#     Model component
#
#     Examples: "AOGCM", "AER", "BGC"
#
#     These terms are intended to help with identifying required components for experiments
#     or filtering models based on having common components.
#     For example, an aerosol scheme or a circulation model or a biogeochemistry component.
#     However, model component is only an approximate term, there is no precise definition
#     of whether any given model has or does not have a given component.
#     """
#
#     # These should probably come back in.
#     # However, this level of detail is only relevant for EMD.
#     # For CMOR tables, the convention seems to just be to use the drs_name,
#     # which is awkward because there is more than one possible AOGCM (for example).
#     # Hence, I think we actually need two classes.
#     # `ModelComponent` and `EMDModelcomponent`
#     # (or we just get rid of this model component idea completely/
#     # leve it entirely up to EMD)
#     # name: str
#     # realm: dict
#     # nominal_resolution: dict
#     # version: int
