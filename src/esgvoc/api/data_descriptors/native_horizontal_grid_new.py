from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor, PlainTermDataDescriptor


class NativeHorizontalGrid(PlainTermDataDescriptor):
    """
    The model component’s native horizontal grid is described by a subset of the following properties:

    • Description
        ◦ A free-text description of the grid.
        ◦ A description is only required if there is information that is not covered by any of the other properties.
        ◦ Omit if not needed.
    • Type
        ◦ The horizontal grid type, i.e. the method of distributing grid points over the sphere.
        ◦ Taken from a standardised list: 7.3. Native horizontal grid Type CV.
        ◦ If there is no horizontal grid, then the value “none” must be selected, and no other properties should be set.
        ◦ E.g. regular_latitude_longitude
        ◦ E.g. tripolar
    • Grid mapping
        ◦ The name of the coordinate reference system of the horizontal coordinates.
        ◦ Taken from a standardised list: 7.4. Native horizontal grid Grid Mapping CV.
        ◦ E.g. latitude_longitude
    • Region
        ◦ The geographical region, or regions, over which the component is simulated.
        ◦ A region is a contiguous part of the Earth’s surface, and may include areas for which no calculations are made (such as ocean areas for a land surface component).
        ◦ Taken from a standardised list: 7.5. Native horizontal grid Region CV.
        ◦ E.g. global
        ◦ E.g. antarctica, greenland
    • Temporal refinement
        ◦ The grid temporal refinement, indicating how the distribution of grid cells varies with time.
        ◦ Taken from a standardised list: 7.6. Native horizontal grid Temporal refinement CV.
        ◦ E.g. static
    • Arrangement
        ◦ A characterisation of the relative positions on a grid of mass-, velocity- or flux-related fields.
        ◦ Taken from a standardised list: 7.7. Native horizontal grid Arrangement CV.
        ◦ E.g. arakawa_B
    • Resolution X
        ◦ The size of grid cells in the X direction.
        ◦ The value’s physical units are given by the Units property.
        ◦ Report only when cell sizes are identical or else reasonably uniform (in their given units). When cells sizes are not identical, a representative value should be provided and this fact noted in the Description property, but only if the cell sizes vary by less than 25%.
        ◦ Omit when not applicable.
        ◦ E.g. 3.75
    • Resolution Y
        ◦ The size of grid cells in the Y direction.
        ◦ The value’s physical units are given by the Units property.
        ◦ Report only when cell sizes are identical or else reasonably uniform (in their given units). When cells sizes are not identical, a representative value should be provided and this fact noted in the Description property, but only if the cell sizes vary by less than 25%.
        ◦ Omit when not applicable.
        ◦ E.g. 2.5
    • Units
        ◦ The physical units of the Resolution X and Resolution Y property values.
        ◦ The only acceptable units are  “km” (kilometre, unit for length) or “degree” (unit for angular measure).
        ◦ Omit when not applicable.
        ◦ E.g. km
        ◦ E.g. degree
    • N cells
        ◦ The total number of cells in the horizontal grid.
        ◦ If the horizontal grid is unstructured then when the component utilises primal and dual meshes (i.e. when each vertex of a primal mesh cell is uniquely associated with the “centre” of a dual mesh cell, and vice versa), the number of cells for the primal mesh should be provided.
        ◦ Omit when not applicable or not constant.
        ◦ E.g. 265160
    • N sides
        ◦ For unstructured horizontal grids only, the total number of unique cell sides.
        ◦ When the component utilises primal and dual meshes (i.e. when each vertex of a primal mesh cell is uniquely associated with the “centre” of a dual mesh cell, and vice versa), the number of sides for the primal mesh should be provided.
        ◦ Omit when not applicable or not constant.
        ◦ E.g. 714274
    • N vertices
        ◦ For unstructured horizontal grids only, the number of unique cell vertices.
        ◦ When the component utilises primal and dual meshes (i.e. when each vertex of a primal mesh cell is uniquely associated with the “centre” of a dual mesh cell, and vice versa), the number for the primal mesh should be provided.
        ◦ Omit when not applicable or not constant.
        ◦ E.g. 567145
    • Truncation method
        ◦ The method for truncating the spherical harmonic representation of a spectral model.
        ◦ Taken from a standardised list: 7.8. Native horizontal grid Truncation method CV.
        ◦ Omit when not applicable.
        ◦ E.g. triangular
    • Truncation number
        ◦ The zonal (east-west) wave number at which a spectral model is truncated.
        ◦ Omit when not applicable.
        ◦ E.g. 63
    • Resolution range km
        ◦ The minimum and maximum resolution (in km) of cells of the native horizontal grid.
        ◦ Calculate as described in this documented Python code, which can be used to obtain the maximum, minimum and mean resolution.
        ◦ E.g. 57.0, 290
    • Mean resolution km
        ◦ The mean resolution (in km) of the native horizontal grid on which the mass-related quantities are carried by the model.
        ◦ Calculate as described in this documented Python code, which can be used to obtain the maximum, minimum, and mean resolution.
        ◦ E.g. 234.8
    • Nominal resolution
        ◦ The nominal resolution characterises the approximate resolution of a model’s native horizontal grid.
        ◦ The nominal resolution is obtained (once the Mean resolution km property is calculated) by looking it up in the table at 7.9. Native horizontal grid Nominal resolution CV.
        ◦ E.g. A grid with mean resolution of 82 will have a nominal resolution of 100 km
    """

    description: str
    horizontal_grid_type: str
    grid_mapping: str
    region: str
    temporal_refinement: str
    arrangement: str
    resolutionx: str
    resolutiony: str
    units: str
    ncells: str
    nsides: str
    nvertices: str
    truncation_method: str
    truncation_number: str
    resolution_range: str
    mean_resolution: str
    nominal_resolution: str

