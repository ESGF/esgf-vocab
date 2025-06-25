from dataclasses import dataclass
from typing import Any, Generator, Iterable, Mapping

import pytest

from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor
from esgvoc.api.project_specs import DrsType, ProjectSpecs
from esgvoc.api.search import Item, ItemKind, MatchingTerm
from esgvoc.apps.drs.report import (
    AssignedTerm,
    BlankTerm,
    ConflictingCollections,
    DrsGenerationReport,
    DrsIssue,
    DrsValidationReport,
    ExtraChar,
    ExtraSeparator,
    ExtraTerm,
    FileNameExtensionIssue,
    GenerationError,
    GenerationIssue,
    GenerationWarning,
    InvalidTerm,
    MissingTerm,
    ParsingIssue,
    Space,
    TermIssue,
    TooManyTermCollection,
    Unparsable,
    ValidationError,
    ValidationWarning,
)


@dataclass
class Parameter:
    project_id: str
    data_descriptor_id: str
    collection_id: str
    term_id: str


@dataclass
class FindExpression:
    expression: str
    item: Parameter | None
    item_kind: ItemKind | None


@dataclass
class ValidationExpression:
    value: str
    item: Parameter
    nb_matching_terms_in_collection: int
    nb_matching_terms_in_project: int
    nb_matching_terms_in_all_projects: int
    nb_errors: int


@dataclass
class DrsValidatorIssue:
    type: type[ValidationError | ValidationWarning]
    index: int | None = None
    part: str | None = None
    collection_id: str | None = None


@dataclass
class DrsValidatorExpression:
    expression: str
    drs_type: DrsType
    project_id: str
    errors: list[DrsValidatorIssue]
    warnings: list[DrsValidatorIssue]


@dataclass
class DrsGenerationIssue:
    type: type[GenerationError | GenerationWarning]
    index: int | None = None
    parts: str | list[str] | None = None
    collection_ids: str | list[str] | None = None


@dataclass
class DrsGeneratorExpression:
    project_id: str
    drs_type: DrsType
    generated_expression: str
    errors: list[DrsGenerationIssue]
    warnings: list[DrsGenerationIssue]


@dataclass
class DrsMappingGeneratorExpression(DrsGeneratorExpression):
    mapping: Mapping[str, str]


@dataclass
class DrsTermsGeneratorExpression(DrsGeneratorExpression):
    terms: Iterable[str]


class GenerationIssueChecker:
    def __init__(self, expected_result: DrsGenerationIssue) -> None:
        self.expected_result = expected_result

    def _check_type(self, issue: GenerationIssue) -> None:
        assert isinstance(issue, self.expected_result.type)

    def visit_invalid_term_issue(self, issue: InvalidTerm) -> Any:
        self._check_type(issue)
        assert self.expected_result.parts == issue.term
        assert self.expected_result.collection_ids == issue.collection_id_or_constant_value
        assert self.expected_result.index == issue.term_position

    def visit_missing_term_issue(self, issue: MissingTerm) -> Any:
        self._check_type(issue)
        assert self.expected_result.collection_ids == issue.collection_id
        assert self.expected_result.index == issue.collection_position

    def visit_too_many_terms_collection_issue(self, issue: TooManyTermCollection) -> Any:
        self._check_type(issue)
        assert self.expected_result.collection_ids == issue.collection_id
        assert self.expected_result.parts == issue.terms

    def visit_conflicting_collections_issue(self, issue: ConflictingCollections) -> Any:
        self._check_type(issue)
        assert self.expected_result.collection_ids == issue.collection_ids
        assert self.expected_result.parts == issue.terms

    def visit_assign_term_issue(self, issue: AssignedTerm) -> Any:
        self._check_type(issue)
        assert self.expected_result.parts == issue.term
        assert self.expected_result.collection_ids == issue.collection_id


DEFAULT_DD = "variable"
DEFAULT_PROJECT = "cmip6plus"
DEFAULT_COLLECTION = "variable_id"
PROJECT_IDS = ["cmip6plus", "cmip6"]
LEN_PROJECTS = len(PROJECT_IDS)
LEN_COLLECTIONS: dict[str, dict[str, int]] = {
    "cmip6plus": {
        "institution_id": 90,
        "time_range": 3,
        "source_id": 6,
        "variable_id": 990,
        "table_id": 70,
        "variant_label": 1,
        "experiment_id": 300,
    },
    "cmip6": {
        "institution_id": 30,
        "time_range": 3,
        "source_id": 130,
        "variable_id": 990,
        "table_id": 40,
        "variant_label": 1,
        "experiment_id": 300,
        "member_id": 1,
    },
}
LEN_DATA_DESCRIPTORS: dict[str, int] = {
    "institution": 70,
    "time_range": 3,
    "source": 130,
    "variable": 1300,
    "table": 110,
    "variant_label": 3,
    "experiment": 300,
    "member_id": 1,
}


# Parameter('', '', '', ''),
GET_PARAMETERS: list[Parameter] = [
    Parameter("cmip6plus", "institution", "institution_id", "ipsl"),
    Parameter("cmip6plus", "time_range", "time_range", "daily"),
    Parameter("cmip6plus", "source", "source_id", "miroc6"),
    Parameter("cmip6plus", "variable", "variable_id", "airmass"),
    Parameter("cmip6plus", "institution", "institution_id", "cnes"),
    Parameter("cmip6plus", "table", "table_id", "ACmon"),
    Parameter("cmip6plus", "variant_label", "variant_label", "ripf"),
    Parameter("cmip6", "institution", "institution_id", "ipsl"),
    Parameter("cmip6", "time_range", "time_range", "daily"),
    Parameter("cmip6", "source", "source_id", "miroc6"),
    Parameter("cmip6", "variable", "variable_id", "airmass"),
    Parameter("cmip6", "table", "table_id", "Eyr"),
    Parameter("cmip6", "experiment", "experiment_id", "ssp245-aer"),
    Parameter("cmip6", "variable", "variable_id", "prw2h"),
    Parameter("cmip6", "member_id", "member_id", "subexp_variant"),
]

PARAMETERS: dict[str, Parameter] = {f"{param.project_id}_{param.term_id}": param for param in GET_PARAMETERS}

# FindExpression('', PARAMETERS[''], ItemKind.TERM),
FIND_TERM_PARAMETERS: list[FindExpression] = [
    FindExpression("ipsl", PARAMETERS["cmip6plus_ipsl"], ItemKind.TERM),
    FindExpression("airmass", PARAMETERS["cmip6_airmass"], ItemKind.TERM),
    FindExpression("cnes", PARAMETERS["cmip6plus_cnes"], ItemKind.TERM),
    FindExpression("mir*", PARAMETERS["cmip6plus_miroc6"], ItemKind.TERM),
    FindExpression("pArIs NOT CNES", PARAMETERS["cmip6plus_ipsl"], ItemKind.TERM),
    FindExpression("ssp245-aer", PARAMETERS["cmip6_ssp245-aer"], ItemKind.TERM),
    FindExpression("'ssp245-aer'", PARAMETERS["cmip6_ssp245-aer"], ItemKind.TERM),
    FindExpression("- column : paris", None, None),
    FindExpression("- column : ^ paris", None, None),
    FindExpression("NEAR(e d, 10)", None, None),
    FindExpression('NEAR("e d", 10)', None, None),
    FindExpression("NEAR(e d)", None, None),
    FindExpression('NEAR("e d")', None, None),
    FindExpression("ipsl +paris", PARAMETERS["cmip6plus_ipsl"], ItemKind.TERM),
    FindExpression("pari", PARAMETERS["cmip6plus_ipsl"], ItemKind.TERM),
    FindExpression("pari*", PARAMETERS["cmip6plus_ipsl"], ItemKind.TERM),
    FindExpression("ipsl paris", PARAMETERS["cmip6plus_ipsl"], ItemKind.TERM),
    FindExpression("ipsl* paris*", PARAMETERS["cmip6plus_ipsl"], ItemKind.TERM),
    FindExpression("ipsl* AND paris*", PARAMETERS["cmip6plus_ipsl"], ItemKind.TERM),
    FindExpression("prw* NOT prw", PARAMETERS["cmip6_prw2h"], ItemKind.TERM),
]

# FindExpression('', PARAMETERS[''], ItemKind.DATA_DESCRIPTOR),
FIND_DATA_DESCRIPTOR_PARAMETERS: list[FindExpression] = [
    FindExpression("institution", PARAMETERS["cmip6plus_ipsl"], ItemKind.DATA_DESCRIPTOR),
    FindExpression("_label", PARAMETERS["cmip6plus_ripf"], ItemKind.DATA_DESCRIPTOR),
    FindExpression("var* NOT ver*", PARAMETERS["cmip6plus_airmass"], ItemKind.DATA_DESCRIPTOR),
]

# FindExpression('', PARAMETERS[''], ItemKind.COLLECTION),
FIND_COLLECTION_PARAMETERS: list[FindExpression] = [
    FindExpression("institution_id", PARAMETERS["cmip6plus_ipsl"], ItemKind.COLLECTION),
    FindExpression("tab*_id", PARAMETERS["cmip6_Eyr"], ItemKind.COLLECTION),
    FindExpression("var* NOT ver*", PARAMETERS["cmip6plus_airmass"], ItemKind.COLLECTION),
]

FIND_UNIVERSE_ITEM_PARAMETERS = FIND_TERM_PARAMETERS + FIND_DATA_DESCRIPTOR_PARAMETERS

FIND_PROJECT_ITEM_PARAMETERS = FIND_TERM_PARAMETERS + FIND_COLLECTION_PARAMETERS

# ValidationExpression('', PARAMETERS[''], , , ),
VALIDATION_QUERIES: list[ValidationExpression] = [
    ValidationExpression("IPSL", PARAMETERS["cmip6plus_ipsl"], 1, 1, 2, 0),
    ValidationExpression("ssp245-aer", PARAMETERS["cmip6_ssp245-aer"], 1, 1, 1, 0),
    ValidationExpression("r1i1p1f1", PARAMETERS["cmip6plus_ripf"], 2, 1, 4, 0),
    ValidationExpression("IPL", PARAMETERS["cmip6plus_ipsl"], 0, 0, 0, 1),
    ValidationExpression("r1i1p1f111", PARAMETERS["cmip6plus_ripf"], 2, 1, 4, 0),
    ValidationExpression("20241206-20241207", PARAMETERS["cmip6plus_daily"], 1, 1, 2, 0),
    ValidationExpression("0241206-0241207", PARAMETERS["cmip6plus_daily"], 0, 0, 0, 1),
    ValidationExpression("s1990-r1i1p1f1", PARAMETERS["cmip6_subexp_variant"], 1, 1, 2, 0),
    ValidationExpression("r1i1p1f1", PARAMETERS["cmip6_subexp_variant"], 2, 1, 4, 0),
]

# DrsValidatorExpression("",
#                        DrsType.,
#                        "", [], []),
DRS_VALIDATION_ERROR_LESS_QUERIES: list[DrsValidatorExpression] = [
    DrsValidatorExpression(
        "CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923", DrsType.DIRECTORY, "cmip6plus", [], []
    ),
    DrsValidatorExpression(
        "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-201212.nc", DrsType.FILE_NAME, "cmip6plus", [], []
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn", DrsType.DATASET_ID, "cmip6plus", [], []
    ),
]

DRS_VALIDATION_DIRECTORY_TYPO_WARNINGS: list[DrsValidatorExpression] = [
    DrsValidatorExpression(
        "CMIP6Plus/CMIP/NCC/MIROC6/amip//r2i2p1f2/ACmon/od550aer/gn/v20190923",
        DrsType.DIRECTORY,
        "cmip6plus",
        [],
        [DrsValidatorIssue(ExtraSeparator, index=32)],
    ),
    DrsValidatorExpression(
        "CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923/",
        DrsType.DIRECTORY,
        "cmip6plus",
        [],
        [DrsValidatorIssue(ExtraSeparator, index=68)],
    ),
    DrsValidatorExpression(
        "CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923//",
        DrsType.DIRECTORY,
        "cmip6plus",
        [],
        [DrsValidatorIssue(ExtraSeparator, index=68)],
    ),
    DrsValidatorExpression(
        " CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923//",
        DrsType.DIRECTORY,
        "cmip6plus",
        [],
        [DrsValidatorIssue(Space), DrsValidatorIssue(ExtraSeparator, index=69)],
    ),
]

DRS_VALIDATION_DIRECTORY_TYPO_ERRORS: list[DrsValidatorExpression] = [
    DrsValidatorExpression(
        "CMIP6Plus/CMIP/NCC/MIROC6/amip/ /r2i2p1f2/ACmon/od550aer/gn/v20190923",
        DrsType.DIRECTORY,
        "cmip6plus",
        [DrsValidatorIssue(BlankTerm, index=32)],
        [],
    ),
    DrsValidatorExpression(
        "CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923/ /",
        DrsType.DIRECTORY,
        "cmip6plus",
        [DrsValidatorIssue(ExtraChar, index=68)],
        [],
    ),
    DrsValidatorExpression(
        "  CMIP6Plus/CMIP/NCC/MIROC6/amip/  /r2i2p1f2/ACmon/od550aer/gn/v20190923/ // ",
        DrsType.DIRECTORY,
        "cmip6plus",
        [DrsValidatorIssue(BlankTerm, index=34), DrsValidatorIssue(ExtraChar, index=73)],
        [DrsValidatorIssue(Space)],
    ),
]

DRS_VALIDATION_FILE_NAME_WARNINGS: list[DrsValidatorExpression] = [
    DrsValidatorExpression(
        "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn.nc",
        DrsType.FILE_NAME,
        "cmip6plus",
        [],
        [DrsValidatorIssue(MissingTerm, collection_id="time_range", index=7)],
    ),
]

DRS_VALIDATION_FILE_NAME_EXTENSION_ERRORS: list[DrsValidatorExpression] = [
    DrsValidatorExpression(
        "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn",
        DrsType.FILE_NAME,
        "cmip6plus",
        [DrsValidatorIssue(FileNameExtensionIssue)],
        [],
    ),
    DrsValidatorExpression(
        "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn.md",
        DrsType.FILE_NAME,
        "cmip6plus",
        [DrsValidatorIssue(FileNameExtensionIssue)],
        [],
    ),
    DrsValidatorExpression(
        "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn.n",
        DrsType.FILE_NAME,
        "cmip6plus",
        [DrsValidatorIssue(FileNameExtensionIssue)],
        [],
    ),
    DrsValidatorExpression(
        "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn.n c",
        DrsType.FILE_NAME,
        "cmip6plus",
        [DrsValidatorIssue(FileNameExtensionIssue)],
        [],
    ),
]

DRS_VALIDATION_FILE_NAME_EXTRA_TOKEN_ERRORS: list[DrsValidatorExpression] = [
    DrsValidatorExpression(
        "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-20121.nc",
        DrsType.FILE_NAME,
        "cmip6plus",
        [DrsValidatorIssue(ExtraTerm, part="201211-20121", index=6, collection_id="time_range")],
        [],
    ),
    DrsValidatorExpression(
        "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211- 20121.nc",
        DrsType.FILE_NAME,
        "cmip6plus",
        [DrsValidatorIssue(ExtraTerm, part="201211- 20121", index=6, collection_id="time_range")],
        [],
    ),
    DrsValidatorExpression(
        "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-201212_hello.nc",
        DrsType.FILE_NAME,
        "cmip6plus",
        [DrsValidatorIssue(ExtraTerm, part="hello", index=7)],
        [],
    ),
]

DRS_VALIDATION_DATASET_ID_TYPO_WARNINGS: list[DrsValidatorExpression] = [
    DrsValidatorExpression(
        " CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
        DrsType.DATASET_ID,
        "cmip6plus",
        [],
        [DrsValidatorIssue(Space)],
    ),
    DrsValidatorExpression(
        "  CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
        DrsType.DATASET_ID,
        "cmip6plus",
        [],
        [DrsValidatorIssue(Space)],
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn ",
        DrsType.DATASET_ID,
        "cmip6plus",
        [],
        [DrsValidatorIssue(Space)],
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn  ",
        DrsType.DATASET_ID,
        "cmip6plus",
        [],
        [DrsValidatorIssue(Space)],
    ),
]


DRS_VALIDATION_DATASET_ID_TYPO_ERRORS: list[DrsValidatorExpression] = [
    DrsValidatorExpression(
        "CMIP6Plus_CMIP_IPSL_MIROC6_amip_r2i2p1f2_ACmon_od550aer_gn",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(Unparsable)],
        [],
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn.",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(ExtraChar, index=59)],
        [],
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn..",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(ExtraChar, index=59)],
        [],
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn.. ",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(ExtraChar, index=59)],
        [DrsValidatorIssue(Space)],
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL..MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn. ..",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(ExtraSeparator, index=21), DrsValidatorIssue(ExtraChar, index=60)],
        [],
    ),
    DrsValidatorExpression(
        ".CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(ExtraSeparator, index=1)],
        [],
    ),
    DrsValidatorExpression(
        "..CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(ExtraSeparator, index=1), DrsValidatorIssue(ExtraSeparator, index=2)],
        [],
    ),
    DrsValidatorExpression(
        " ..CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(ExtraSeparator, index=2), DrsValidatorIssue(ExtraSeparator, index=3)],
        [DrsValidatorIssue(Space)],
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL..MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(ExtraSeparator, index=21)],
        [],
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL. MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(InvalidTerm, part=" MIROC6", index=4, collection_id="source_id")],
        [],
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL.  MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(InvalidTerm, part="  MIROC6", index=4, collection_id="source_id")],
        [],
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL. .MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(BlankTerm, index=21)],
        [],
    ),
    DrsValidatorExpression(
        ".CMIP6Plus.CMIP.IPSL.  .MIROC6.amip..r2i2p1f2.ACmon.od550aer.gn. ..",
        DrsType.DATASET_ID,
        "cmip6plus",
        [
            DrsValidatorIssue(ExtraSeparator, index=1),
            DrsValidatorIssue(BlankTerm, index=22),
            DrsValidatorIssue(ExtraSeparator, index=37),
            DrsValidatorIssue(ExtraChar, index=64),
        ],
        [],
    ),
    DrsValidatorExpression(
        ".CMIP6Plus.CMIP.IPSL.  .MIROC6.amip..r2i2p1f2.ACmon.od550aer. ..gn",
        DrsType.DATASET_ID,
        "cmip6plus",
        [
            DrsValidatorIssue(ExtraSeparator, index=1),
            DrsValidatorIssue(BlankTerm, index=22),
            DrsValidatorIssue(ExtraSeparator, index=37),
            DrsValidatorIssue(BlankTerm, index=62),
            DrsValidatorIssue(ExtraSeparator, index=64),
        ],
        [],
    ),
    DrsValidatorExpression(
        " .CMIP6Plus.CMIP.IPSL.  .MIROC6.amip..r2i2p1f2.ACmon.od550aer. ..gn",
        DrsType.DATASET_ID,
        "cmip6plus",
        [
            DrsValidatorIssue(ExtraSeparator, index=2),
            DrsValidatorIssue(BlankTerm, index=23),
            DrsValidatorIssue(ExtraSeparator, index=38),
            DrsValidatorIssue(BlankTerm, index=63),
            DrsValidatorIssue(ExtraSeparator, index=65),
        ],
        [DrsValidatorIssue(Space)],
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer-gn",
        DrsType.DATASET_ID,
        "cmip6plus",
        [
            DrsValidatorIssue(InvalidTerm, part="od550aer-gn", index=8, collection_id="variable_id"),
            DrsValidatorIssue(MissingTerm, index=9, collection_id="grid_label"),
        ],
        [],
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer/gn",
        DrsType.DATASET_ID,
        "cmip6plus",
        [
            DrsValidatorIssue(InvalidTerm, part="od550aer/gn", index=8, collection_id="variable_id"),
            DrsValidatorIssue(MissingTerm, index=9, collection_id="grid_label"),
        ],
        [],
    ),
]


DRS_VALIDATION_DATASET_ID_TOKEN_ERRORS: list[DrsValidatorExpression] = [
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(MissingTerm, index=9, collection_id="grid_label")],
        [],
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon",
        DrsType.DATASET_ID,
        "cmip6plus",
        [
            DrsValidatorIssue(MissingTerm, index=8, collection_id="variable_id"),
            DrsValidatorIssue(MissingTerm, index=9, collection_id="grid_label"),
        ],
        [],
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn.hello",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(ExtraTerm, index=9, part="hello")],
        [],
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn.hello.world",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(ExtraTerm, index=9, part="hello"), DrsValidatorIssue(ExtraTerm, index=10, part="world")],
        [],
    ),
]


DRS_VALIDATION_DATASET_ID_ERRORS: list[DrsValidatorExpression] = [
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.world",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(InvalidTerm, part="world", index=9, collection_id="grid_label")],
        [],
    ),
    DrsValidatorExpression(
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.hello.world",
        DrsType.DATASET_ID,
        "cmip6plus",
        [
            DrsValidatorIssue(InvalidTerm, part="hello", index=8, collection_id="variable_id"),
            DrsValidatorIssue(InvalidTerm, part="world", index=9, collection_id="grid_label"),
        ],
        [],
    ),
    DrsValidatorExpression(
        "Hello.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
        DrsType.DATASET_ID,
        "cmip6plus",
        [DrsValidatorIssue(InvalidTerm, part="Hello", index=1, collection_id="mip_era")],
        [],
    ),
]

DRS_VALIDATION_ALL_QUERIES = (
    DRS_VALIDATION_DATASET_ID_ERRORS
    + DRS_VALIDATION_DATASET_ID_TOKEN_ERRORS
    + DRS_VALIDATION_DATASET_ID_TYPO_ERRORS
    + DRS_VALIDATION_DATASET_ID_TYPO_WARNINGS
    + DRS_VALIDATION_FILE_NAME_EXTRA_TOKEN_ERRORS
    + DRS_VALIDATION_FILE_NAME_EXTENSION_ERRORS
    + DRS_VALIDATION_FILE_NAME_WARNINGS
    + DRS_VALIDATION_DIRECTORY_TYPO_ERRORS
    + DRS_VALIDATION_DIRECTORY_TYPO_WARNINGS
    + DRS_VALIDATION_ERROR_LESS_QUERIES
)

DRS_GENERATION_EXPRESSIONS: list[DrsTermsGeneratorExpression | DrsMappingGeneratorExpression] = [
    DrsMappingGeneratorExpression(
        "cmip6plus",
        DrsType.DATASET_ID,
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
        [],
        [],
        {
            "member_id": "r2i2p1f2",
            "activity_id": "CMIP",
            "source_id": "MIROC6",
            "mip_era": "CMIP6Plus",
            "experiment_id": "amip",
            "variable_id": "od550aer",
            "table_id": "ACmon",
            "grid_label": "gn",
            "institution_id": "IPSL",
        },
    ),
    DrsMappingGeneratorExpression(
        "cmip6plus",
        DrsType.DATASET_ID,
        "CMIP6Plus.CMIP.IPSL.[INVALID].[MISSING].r2i2p1f2.ACmon.od550aer.gn",
        [
            DrsGenerationIssue(InvalidTerm, parts="MIROC", index=4, collection_ids="source_id"),
            DrsGenerationIssue(MissingTerm, index=5, collection_ids="experiment_id"),
        ],
        [],
        {
            "member_id": "r2i2p1f2",
            "activity_id": "CMIP",
            "source_id": "MIROC",
            "mip_era": "CMIP6Plus",
            "variable_id": "od550aer",
            "table_id": "ACmon",
            "grid_label": "gn",
            "institution_id": "IPSL",
        },
    ),
    DrsTermsGeneratorExpression(
        "cmip6plus",
        DrsType.DATASET_ID,
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
        [],
        [],
        ["r2i2p1f2", "CMIP", "MIROC6", "CMIP6Plus", "amip", "od550aer", "ACmon", "IPSL", "gn"],
    ),
    DrsMappingGeneratorExpression(
        "cmip6plus",
        DrsType.FILE_NAME,
        "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn.nc",
        [],
        [DrsGenerationIssue(MissingTerm, index=7, collection_ids="time_range")],
        {
            "member_id": "r2i2p1f2",
            "activity_id": "CMIP",
            "source_id": "MIROC6",
            "mip_era": "CMIP6Plus",
            "experiment_id": "amip",
            "variable_id": "od550aer",
            "table_id": "ACmon",
            "grid_label": "gn",
            "institution_id": "IPSL",
        },
    ),
    DrsTermsGeneratorExpression(
        "cmip6plus",
        DrsType.FILE_NAME,
        "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201611-201712.nc",
        [],
        [],
        ["r2i2p1f2", "CMIP", "MIROC6", "CMIP6Plus", "amip", "od550aer", "ACmon", "201611-201712", "gn", "IPSL"],
    ),
    DrsMappingGeneratorExpression(
        "cmip6plus",
        DrsType.DIRECTORY,
        "CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923",
        [],
        [],
        {
            "member_id": "r2i2p1f2",
            "activity_id": "CMIP",
            "source_id": "MIROC6",
            "mip_era": "CMIP6Plus",
            "version": "v20190923",
            "variable_id": "od550aer",
            "table_id": "ACmon",
            "grid_label": "gn",
            "institution_id": "NCC",
            "experiment_id": "amip",
        },
    ),
    DrsTermsGeneratorExpression(
        "cmip6plus",
        DrsType.DIRECTORY,
        "CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923",
        [],
        [],
        ["r2i2p1f2", "CMIP", "MIROC6", "CMIP6Plus", "amip", "od550aer", "ACmon", "v20190923", "gn", "NCC"],
    ),
]


def check_id(
    obj: str | DataDescriptor | dict | tuple | list | ProjectSpecs | MatchingTerm | Item | None,
    id: str | None,
    kind: ItemKind | None = None,
    parent_id: str | None = None,
) -> None:
    if id:
        assert obj, f"'{id}' returns no result"  # None and empty list.
    else:
        assert not obj, f"'{id}' returns result but should not!"
        return
    match obj:
        case list():
            found = False
            for item in obj:
                try:
                    check_id(item, id, kind, parent_id)
                except AssertionError:
                    continue
                found = True
                break
            assert found
        case DataDescriptor():
            assert obj.id == id
        case str():
            assert obj == id
        case dict():
            assert obj["id"] == id
        case Item():
            assert obj.id == id
            assert obj.kind == kind
            assert obj.parent_id == parent_id
        case tuple():
            assert obj[0] == id
        case ProjectSpecs():
            assert obj.project_id == id
        case MatchingTerm():
            assert obj.term_id == id


def check_validation(
    val_query: ValidationExpression,
    matching_terms: list[MatchingTerm],
    check_in_collection: bool = False,
    check_in_all_projects: bool = False,
) -> None:
    if check_in_collection:
        print(len(matching_terms), val_query.nb_matching_terms_in_collection)
        assert len(matching_terms) == val_query.nb_matching_terms_in_collection
    elif check_in_all_projects:
        print(len(matching_terms), val_query.nb_matching_terms_in_all_projects)
        assert len(matching_terms) == val_query.nb_matching_terms_in_all_projects
    else:
        print(len(matching_terms), val_query.nb_matching_terms_in_project)
        assert len(matching_terms) == val_query.nb_matching_terms_in_project
    if val_query.nb_matching_terms_in_project > 0:
        check_id(matching_terms, val_query.item.term_id)


def check_drs_validation_issue(issue: DrsIssue, expected_result: DrsValidatorIssue) -> None:
    assert isinstance(issue, expected_result.type)
    match issue:
        case ParsingIssue():
            assert issue.column == expected_result.index
        case TermIssue():
            assert issue.term == expected_result.part
            assert issue.term_position == expected_result.index
            match issue:
                case InvalidTerm():
                    assert issue.collection_id_or_constant_value == expected_result.collection_id
                case ExtraTerm():
                    if expected_result.collection_id:
                        assert issue.collection_id == expected_result.collection_id
                    else:
                        assert issue.collection_id is None
        case MissingTerm():
            assert str(issue.collection_id) == expected_result.collection_id
            assert issue.collection_position == expected_result.index
        case FileNameExtensionIssue():
            pass  # Nothing to do.
        case _:
            raise TypeError(f"unsupported type {expected_result.type}")


def check_drs_validation_expression(val_expression: DrsValidatorExpression, report: DrsValidationReport) -> None:
    assert report.nb_errors == len(val_expression.errors)
    assert report.nb_warnings == len(val_expression.warnings)
    for index in range(0, len(val_expression.errors)):
        check_drs_validation_issue(report.errors[index], val_expression.errors[index])
    for index in range(0, len(val_expression.warnings)):
        check_drs_validation_issue(report.warnings[index], val_expression.warnings[index])


def check_drs_generated_expression(
    expression: DrsMappingGeneratorExpression | DrsTermsGeneratorExpression, report: DrsGenerationReport
) -> None:
    print(expression)
    print(report)
    print(report.errors)
    print(report.warnings)
    assert expression.generated_expression == report.generated_drs_expression
    assert len(expression.errors) == report.nb_errors
    assert len(expression.warnings) == report.nb_warnings
    for index in range(0, len(expression.errors)):
        checker = GenerationIssueChecker(expression.errors[index])
        report.errors[index].accept(checker)
    for index in range(0, len(expression.warnings)):
        checker = GenerationIssueChecker(expression.warnings[index])
        report.warnings[index].accept(checker)


def _provide_project_ids() -> Generator:
    for param in PROJECT_IDS:
        yield param


@pytest.fixture(params=_provide_project_ids())
def project_id(request) -> str:
    return request.param


def _provide_get_parameters() -> Generator:
    for param in GET_PARAMETERS:
        yield param


@pytest.fixture(params=_provide_get_parameters())
def get_param(request) -> Parameter:
    return request.param


def _provide_find_term_parameters() -> Generator:
    for param in FIND_TERM_PARAMETERS:
        yield param


@pytest.fixture(params=_provide_find_term_parameters())
def find_term_param(request) -> FindExpression:
    return request.param


def _provide_find_dd_parameters() -> Generator:
    for param in FIND_DATA_DESCRIPTOR_PARAMETERS:
        yield param


@pytest.fixture(params=_provide_find_dd_parameters())
def find_dd_param(request) -> FindExpression:
    return request.param


def _provide_find_col_parameters() -> Generator:
    for param in FIND_COLLECTION_PARAMETERS:
        yield param


@pytest.fixture(params=_provide_find_col_parameters())
def find_col_param(request) -> FindExpression:
    return request.param


def _provide_find_univ_item_parameters() -> Generator:
    for param in FIND_UNIVERSE_ITEM_PARAMETERS:
        yield param


@pytest.fixture(params=_provide_find_univ_item_parameters())
def find_univ_item_param(request) -> FindExpression:
    return request.param


def _provide_find_proj_item_parameters() -> Generator:
    for param in FIND_PROJECT_ITEM_PARAMETERS:
        yield param


@pytest.fixture(params=_provide_find_proj_item_parameters())
def find_proj_item_param(request) -> FindExpression:
    return request.param


def _provide_val_queries() -> Generator:
    for param in VALIDATION_QUERIES:
        yield param


@pytest.fixture(params=_provide_val_queries())
def val_query(request) -> ValidationExpression:
    return request.param


def _provide_drs_validation_error_less_queries() -> Generator:
    for param in DRS_VALIDATION_ERROR_LESS_QUERIES:
        yield param


@pytest.fixture(params=_provide_drs_validation_error_less_queries())
def drs_validation_error_less_query(request) -> DrsValidatorExpression:
    return request.param


def _provide_drs_validation_directory_typo_warnings() -> Generator:
    for param in DRS_VALIDATION_DIRECTORY_TYPO_WARNINGS:
        yield param


@pytest.fixture(params=_provide_drs_validation_directory_typo_warnings())
def drs_validation_directory_typo_warnings(request) -> DrsValidatorExpression:
    return request.param


def _provide_drs_validation_directory_typo_errors() -> Generator:
    for param in DRS_VALIDATION_DIRECTORY_TYPO_ERRORS:
        yield param


@pytest.fixture(params=_provide_drs_validation_directory_typo_errors())
def drs_validation_directory_typo_error(request) -> DrsValidatorExpression:
    return request.param


def _provide_drs_validation_file_name_warnings() -> Generator:
    for param in DRS_VALIDATION_FILE_NAME_WARNINGS:
        yield param


@pytest.fixture(params=_provide_drs_validation_file_name_warnings())
def drs_validation_file_name_warning(request) -> DrsValidatorExpression:
    return request.param


def _provide_drs_validation_file_name_extension_errors() -> Generator:
    for param in DRS_VALIDATION_FILE_NAME_EXTENSION_ERRORS:
        yield param


@pytest.fixture(params=_provide_drs_validation_file_name_extension_errors())
def drs_validation_file_name_extension_error(request) -> DrsValidatorExpression:
    return request.param


def _provide_drs_validation_file_name_extra_token_errors() -> Generator:
    for param in DRS_VALIDATION_FILE_NAME_EXTRA_TOKEN_ERRORS:
        yield param


@pytest.fixture(params=_provide_drs_validation_file_name_extra_token_errors())
def drs_validation_file_name_extra_token_error(request) -> DrsValidatorExpression:
    return request.param


def _provide_drs_validation_dataset_id_typo_warnings() -> Generator:
    for param in DRS_VALIDATION_DATASET_ID_TYPO_WARNINGS:
        yield param


@pytest.fixture(params=_provide_drs_validation_dataset_id_typo_warnings())
def drs_validation_dataset_id_typo_warning(request) -> DrsValidatorExpression:
    return request.param


def _provide_drs_validation_dataset_id_typo_errors() -> Generator:
    for param in DRS_VALIDATION_DATASET_ID_TYPO_ERRORS:
        yield param


@pytest.fixture(params=_provide_drs_validation_dataset_id_typo_errors())
def drs_validation_dataset_id_typo_error(request) -> DrsValidatorExpression:
    return request.param


def _provide_drs_validation_dataset_id_token_errors() -> Generator:
    for param in DRS_VALIDATION_DATASET_ID_TOKEN_ERRORS:
        yield param


@pytest.fixture(params=_provide_drs_validation_dataset_id_token_errors())
def drs_validation_dataset_id_token_error(request) -> DrsValidatorExpression:
    return request.param


def _provide_drs_validation_dataset_id_errors() -> Generator:
    for param in DRS_VALIDATION_DATASET_ID_ERRORS:
        yield param


@pytest.fixture(params=_provide_drs_validation_dataset_id_errors())
def drs_validation_dataset_id_error(request) -> DrsValidatorExpression:
    return request.param


def _provide_drs_validation_all_queries() -> Generator:
    for param in DRS_VALIDATION_ALL_QUERIES:
        yield param


@pytest.fixture(params=_provide_drs_validation_all_queries())
def drs_validation_query(request) -> DrsValidatorExpression:
    return request.param


def _provide_drs_generation_expressions() -> Generator:
    for param in DRS_GENERATION_EXPRESSIONS:
        yield param


@pytest.fixture(params=_provide_drs_generation_expressions())
def drs_generation_expression(request) -> DrsMappingGeneratorExpression | DrsTermsGeneratorExpression:
    return request.param
