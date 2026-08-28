"""
Model of the known branded variable data descriptor.
"""

from pydantic import field_validator, model_validator

from esgvoc.api.data_descriptors._validators import NonEmptyString
from esgvoc.api.data_descriptors.area_label import AreaLabel
from esgvoc.api.data_descriptors.coordinate import DataCoordinate
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor
from esgvoc.api.data_descriptors.frequency import Frequency
from esgvoc.api.data_descriptors.horizontal_label import HorizontalLabel
from esgvoc.api.data_descriptors.realm import Realm
from esgvoc.api.data_descriptors.table import Table
from esgvoc.api.data_descriptors.temporal_label import TemporalLabel
from esgvoc.api.data_descriptors.variable import Variable
from esgvoc.api.data_descriptors.vertical_label import VerticalLabel
from esgvoc.api.pydantic_handler import create_union


class KnownBrandedVariable(PlainTermDataDescriptor):
    """
    A climate variable with full sampling and branding metadata.

    A known branded variable combines a root variable with a branding suffix
    and the coordinate, sampling, and CF metadata needed by consumers. Its
    dimensions reference data-coordinate terms by ID or as resolved objects.
    """

    variable_root_name: Variable | NonEmptyString
    """
    Root variable name before branding.

    References a :class:`Variable` term by ID when it has not been resolved.
    """

    branding_suffix_name: NonEmptyString
    """
    Branding suffix encoding temporal, vertical, horizontal, and area sampling.
    """

    long_name: NonEmptyString | None = None
    """
    Descriptive name of the branded variable.
    """

    cf_standard_name: NonEmptyString
    """
    CF standard name used by this branded variable.

    This may differ from the root variable's canonical standard name when a
    project retains a more specific or historical definition.
    """

    out_name: NonEmptyString
    """
    Variable name written to the data file.

    This commonly equals the DRS name of ``variable_root_name``, but projects
    may retain a different historical output name.
    """

    units: NonEmptyString | None = None
    """
    CF-compliant units string used by this branded variable.

    This may differ from the root variable's canonical units.
    """

    dimensions: list[DataCoordinate | NonEmptyString]
    """
    Ordered data coordinates that define the variable's axes.

    String entries reference :class:`DataCoordinate` terms by ID. Their order
    matches the dimension order in the data file.
    """

    temporal_label: TemporalLabel | NonEmptyString
    """
    Temporal sampling label.

    References a :class:`TemporalLabel` term by ID when it has not been
    resolved.
    """

    vertical_label: VerticalLabel | NonEmptyString
    """
    Vertical sampling label.

    References a :class:`VerticalLabel` term by ID when it has not been
    resolved.
    """

    horizontal_label: HorizontalLabel | NonEmptyString
    """
    Horizontal sampling label.

    References a :class:`HorizontalLabel` term by ID when it has not been
    resolved.
    """

    area_label: AreaLabel | NonEmptyString
    """
    Area-type label.

    References an :class:`AreaLabel` term by ID when it has not been resolved.
    """

    realm: Realm | NonEmptyString | None = None
    """
    Earth-system realm.

    References a :class:`Realm` term by ID when it has not been resolved.
    """

    cell_methods: NonEmptyString | None = None
    """
    CF cell-methods string describing statistical processing along each axis.
    """

    cell_measures: NonEmptyString | None = None
    """
    CF cell-measures string identifying measure variables such as cell areas.
    """

    flag_values: list[int] | None = None
    """
    Integer flag values for categorical variables.
    """

    flag_meanings: list[NonEmptyString] | None = None
    """
    Human-readable meaning corresponding to each value in ``flag_values``.
    """

    var_def_qualifier: NonEmptyString | None = None
    """
    Qualifier distinguishing variants of the root variable definition.
    """

    bn_status: NonEmptyString | None = None
    """
    Status of the branded name.
    """

    cf_sn_status: NonEmptyString | None = None
    """
    Status of the CF standard name.
    """

    history: NonEmptyString | None = None
    """
    History of changes to the branded-variable definition.
    """

    compound_name: list[NonEmptyString] | None = None
    """
    Project-specific legacy compound names.

    These names vary by project, region, and frequency and therefore have no
    canonical value in the universe vocabulary.
    """

    table_id: list[Table | NonEmptyString] | None = None
    """
    Project-specific legacy table identifiers.

    String entries reference :class:`Table` terms by ID when they have not
    been resolved.
    """

    frequency: list[Frequency | NonEmptyString] | None = None
    """
    Project-specific legacy frequency values.

    String entries reference :class:`Frequency` terms by ID when they have
    not been resolved.
    """

    @field_validator("dimensions")
    @classmethod
    def validate_dimensions(cls, value: list[DataCoordinate | NonEmptyString]):
        """
        Require at least one dimension reference.
        """
        if not value:
            raise ValueError("dimensions cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_root_relationship(self):
        """
        Validate the universal branded-name rule for a resolved root variable.
        """
        if isinstance(self.variable_root_name, Variable):
            root = self.variable_root_name
            if self.drs_name != f"{root.drs_name}_{self.branding_suffix_name}":
                raise ValueError("drs_name must equal variable_root_name.drs_name + '_' + branding_suffix_name")
        return self

    @model_validator(mode="after")
    def validate_branding_suffix(self):
        """
        Validate the suffix against fully resolved sampling labels.
        """
        resolved_labels = (
            isinstance(self.temporal_label, TemporalLabel),
            isinstance(self.vertical_label, VerticalLabel),
            isinstance(self.horizontal_label, HorizontalLabel),
            isinstance(self.area_label, AreaLabel),
        )
        if all(resolved_labels):
            expected_suffix = (
                f"{self.temporal_label.drs_name}-{self.vertical_label.drs_name}-"
                f"{self.horizontal_label.drs_name}-{self.area_label.drs_name}"
            )
            if self.branding_suffix_name != expected_suffix:
                raise ValueError(
                    "branding_suffix_name must equal the temporal, vertical, "
                    "horizontal, and area label DRS names joined by '-'"
                )
        return self

    @model_validator(mode="after")
    def validate_flag_metadata(self):
        """
        Require flag values and meanings to be present in equal numbers.
        """
        if self.flag_values is None and self.flag_meanings is None:
            return self
        if self.flag_values is None or self.flag_meanings is None:
            raise ValueError("flag_values and flag_meanings must be provided together")
        if len(self.flag_values) != len(self.flag_meanings):
            raise ValueError("flag_values and flag_meanings must have equal lengths")
        return self


class KnownBrandedVariableLegacy(PlainTermDataDescriptor):
    """
    Legacy known branded variable used by published ESGVoc databases.

    This model preserves the schema that predates the coordinate-model update.
    In particular, it uses ``cf_units``, permits empty legacy directive fields,
    and has no required ``out_name``. New vocabulary records use
    :class:`KnownBrandedVariable` and its stricter validation instead.
    """

    cf_standard_name: str
    """
    CF standard name.
    """

    cf_units: str
    """
    CF standard units under the legacy field name.
    """

    cf_sn_status: str
    """
    Status of the CF standard name.
    """

    variable_root_name: str
    """
    Variable root name.
    """

    var_def_qualifier: str = ""
    """
    Legacy variable-definition qualifier.
    """

    branding_suffix_name: str
    """
    Branding suffix.
    """

    dimensions: list[str]
    """
    Ordered dimension identifiers.
    """

    cell_methods: str = ""
    """
    CF cell-methods string.
    """

    cell_measures: str = ""
    """
    CF cell-measures string.
    """

    history: str = ""
    """
    Legacy registration history.
    """

    realm: str
    """
    Earth-system realm identifier.
    """

    temporal_label: str
    """
    Temporal branding label.
    """

    vertical_label: str
    """
    Vertical branding label.
    """

    horizontal_label: str
    """
    Horizontal branding label.
    """

    area_label: str
    """
    Area branding label.
    """

    bn_status: str
    """
    Status of the branded name.
    """

    positive_direction: str = ""
    """
    Legacy positive-direction metadata.
    """


KnownBrandedVariableModel = create_union(KnownBrandedVariable, KnownBrandedVariableLegacy)
