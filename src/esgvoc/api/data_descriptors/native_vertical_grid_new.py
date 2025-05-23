from pydantic import Field

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class NativeVertivalGrid(PlainTermDataDescriptor):
    """
            5.2. Native vertical grid properties
    The model component’s native vertical grid is described by a subset of the following properties:
        • Description
            ◦ A free-text description of the vertical grid.
            ◦ A description is only required if there is information that is not covered by any of the other properties.
            ◦ Omit if not needed.
        • Coordinate
            ◦ The coordinate type of the vertical grid.
            ◦ Taken from a standardised list: 7.10. Native vertical grid Coordinate CV.
            ◦ If there is no vertical grid, then the value “none” must be selected, and no other properties should be set.
            ◦ E.g. height
            ◦ E.g. none
        • N z
            ◦ The number of layers (i.e. grid cells) in the Z direction.
            ◦ Omit when not applicable or not constant.
            ◦ If the number of layers varies in time or across the horizontal grid, then the N z range property may be used instead.
            ◦ E.g. 70
        • N z range
            ◦ The minimum and maximum number of layers for vertical grids with a time- or space-varying number of layers.
            ◦ Omit if the N z property has been set.
            ◦ E.g. 5, 15
        • Bottom layer thickness
            ◦ The thickness of the bottom model layer (i.e. the layer closest to the centre of the Earth).
            ◦ The value should be reported as a dimensional (as opposed to parametric) quantity.
            ◦ If the value varies in time or across the horizontal grid, then provide a nominal or typical value.
            ◦ The value’s physical units are given by the Units property.
            ◦ Omit when not applicable.
            ◦ E.g. 10
        • Top layer thickness
            ◦ The thickness of the top model layer (i.e. the layer furthest away from the centre of the Earth).
            ◦ The value should be reported as a dimensional (as opposed to parametric) quantity.
            ◦ If the value varies in time or across the horizontal grid, then provide a nominal or typical value.
            ◦ The value’s physical units are given by the Units property.
            ◦ Omit when not applicable.
            ◦ E.g. 10
        • Top of model
            ◦ The upper boundary of the top model layer (i.e. the upper boundary of the layer that is furthest away from the centre of the Earth).
            ◦ The value should be relative to the lower boundary of the bottom layer of the model, or an appropriate datum (such as mean sea level).
            ◦ The value should be reported as a dimensional (as opposed to parametric) quantity.
            ◦ The value’s physical units are given by the Units property.
            ◦ Omit when not applicable or not constant.
            ◦ E.g. 85003.5
        • Units
            ◦ The physical units of the Bottom layer thickness, Top layer thickness, and Top of Model property values.
            ◦ Taken from a standardised list: 7.11. Native vertical grid Units CV.
            ◦ Omit when not applicable.
            ◦ E.g. m
    """

    description: str = Field(
        description="A free-text description of the vertical grid. A description is only required if there is information that is not covered by any of the other properties. Omit if not needed."
    )
    coordinate: str = Field(
        description="The coordinate type of the vertical grid. Taken from a standardised list: 7.10. Native vertical grid Coordinate CV. If there is no vertical grid, then the value 'none' must be selected, and no other properties should be set. E.g. height, none"
    )
    nz: str = Field(
        description="The number of layers (i.e. grid cells) in the Z direction. Omit when not applicable or not constant. If the number of layers varies in time or across the horizontal grid, then the N z range property may be used instead. E.g. 70"
    )
    nzrange: str = Field(
        description="The minimum and maximum number of layers for vertical grids with a time- or space-varying number of layers. Omit if the N z property has been set. E.g. 5, 15"
    )
    bottom_layer_thickness: str = Field(
        description="The thickness of the bottom model layer (i.e. the layer closest to the centre of the Earth). The value should be reported as a dimensional (as opposed to parametric) quantity. If the value varies in time or across the horizontal grid, then provide a nominal or typical value. The value's physical units are given by the Units property. Omit when not applicable. E.g. 10"
    )
    top_layer_thickness: str = Field(
        description="The thickness of the top model layer (i.e. the layer furthest away from the centre of the Earth). The value should be reported as a dimensional (as opposed to parametric) quantity. If the value varies in time or across the horizontal grid, then provide a nominal or typical value. The value's physical units are given by the Units property. Omit when not applicable. E.g. 10"
    )
    top_of_model: str = Field(
        description="The upper boundary of the top model layer (i.e. the upper boundary of the layer that is furthest away from the centre of the Earth). The value should be relative to the lower boundary of the bottom layer of the model, or an appropriate datum (such as mean sea level). The value should be reported as a dimensional (as opposed to parametric) quantity. The value's physical units are given by the Units property. Omit when not applicable or not constant. E.g. 85003.5"
    )
    units: str = Field(
        description="The physical units of the Bottom layer thickness, Top layer thickness, and Top of Model property values. Taken from a standardised list: 7.11. Native vertical grid Units CV. Omit when not applicable. E.g. m"
    )
