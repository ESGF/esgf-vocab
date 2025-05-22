from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Coordinate(PlainTermDataDescriptor):
    """
    Native vertical grid coordinate type. The coordinate types are all CF standard names (except where indicated) with the same definitions. See section 5.2 Native vertical grid properties.
    Options for the native vertical grid Coordinate property:
        • none
            ◦ (Not a standard name) There is no vertical dimension.
        • height
            ◦ Height is the vertical distance above the earth’s surface.
        • geopotential_height
            ◦ Geopotential height is the geopotential divided by the standard acceleration due to gravity.
        • air_pressure
            ◦ Air pressure is the pressure that exists in the medium of air.
        • air_potential_temperature
            ◦ Air potential temperature is the temperature a parcel of air would have if moved dry adiabatically to a standard pressure.
        • atmosphere_ln_pressure_coordinate
            ◦ Parametric atmosphere natural log pressure coordinate.
        • atmosphere_sigma_coordinate
            ◦ Parametric atmosphere sigma coordinate.
        • atmosphere_hybrid_sigma_pressure_coordinate
            ◦ Parametric atmosphere hybrid sigma pressure coordinate.
        • atmosphere_hybrid_height_coordinate
            ◦ Parametric atmosphere hybrid height coordinate.
        • atmosphere_sleve_coordinate
            ◦ Parametric atmosphere smooth vertical level coordinate.
        • depth
            ◦ Depth is the vertical distance below the earth’s surface.
        • sea_water_pressure
            ◦ Sea water pressure is the pressure that exists in the medium of sea water.
        • sea_water_potential_temperature
            ◦ Sea water potential temperature is the temperature a parcel of sea water would have if moved adiabatically to sea level pressure.
        • ocean_sigma_coordinate
            ◦ Parametric ocean sigma coordinate.
        • ocean_s_coordinate
            ◦ Parametric ocean s-coordinate.
        • ocean_s_coordinate_g1
            ◦ Parametric ocean s-coordinate, generic form 1.
        • ocean_s_coordinate_g2
            ◦ Parametric ocean s-coordinate, generic form 2.
        • ocean_sigma_z_coordinate
            ◦ Parametric ocean sigma over z coordinate.
        • ocean_double_sigma_coordinate
            ◦ Parametric ocean double sigma coordinate.
        • land_ice_sigma_coordinate
            ◦ Land ice (glaciers, ice-caps and ice-sheets resting on bedrock and also includes ice-shelves) sigma coordinate.
        • z*
            ◦ (Not a standard name) The z* coordinate of Adcroft and Campin (2004).
    """

    description: str
