from typing import cast

import esgvoc.api.projects as projects
import esgvoc.apps.drs.constants as constants
from esgvoc.api.project_specs import (
    DrsCollection,
    DrsConstant,
    DrsPart,
    DrsPartKind,
    DrsSpecification,
    DrsType,
    ProjectSpecs,
)
from esgvoc.apps.drs.report import (
    BlankTerm,
    ComplianceIssue,
    DrsIssue,
    DrsValidationReport,
    ExtraChar,
    ExtraSeparator,
    ExtraTerm,
    FileNameExtensionIssue,
    InvalidTerm,
    MissingTerm,
    ParsingIssue,
    Space,
    Unparsable,
    ValidationError,
    ValidationWarning,
)
from esgvoc.core.exceptions import EsgvocDbError, EsgvocNotFoundError


class DrsApplication:
    """
    Generic DRS application class.
    """

    def __init__(self, project_id: str, pedantic: bool = False) -> None:
        self.project_id: str = project_id
        """The project id."""
        self.pedantic: bool = pedantic
        """Same as the option of GCC: turn warnings into errors. Default False."""
        project_specs: ProjectSpecs | None = projects.get_project(project_id)
        if not project_specs:
            raise EsgvocNotFoundError(f"unable to find project '{project_id}'")
        for specs in project_specs.drs_specs:
            match specs.type:
                case DrsType.DIRECTORY:
                    self.directory_specs: DrsSpecification = specs
                    """The DRS directory specs of the project."""
                case DrsType.FILE_NAME:
                    self.file_name_specs: DrsSpecification = specs
                    """The DRS file name specs of the project."""
                case DrsType.DATASET_ID:
                    self.dataset_id_specs: DrsSpecification = specs
                    """The DRS dataset id specs of the project."""
                case _:
                    raise EsgvocDbError(f"unsupported DRS specs type '{specs.type}'")

    def _get_full_file_name_extension(self) -> str:
        """
        Returns the full file name extension (the separator plus the extension) of the DRS file
        name specs of the project.

        :returns: The full file name extension.
        :rtype: str
        """
        specs: DrsSpecification = self.file_name_specs
        if specs.properties:
            full_extension = specs.properties[constants.FILE_NAME_EXTENSION_SEPARATOR_KEY] + \
                             specs.properties[constants.FILE_NAME_EXTENSION_KEY]
        else:
            raise EsgvocDbError('missing properties in the DRS file name specifications of the ' +
                                f"project '{self.project_id}'")
        return full_extension


class DrsValidator(DrsApplication):
    """
    Valid a DRS directory, dataset id and file name expression against a project.
    """

    def validate_directory(self, drs_expression: str,
                           prefix: str | None = None) -> DrsValidationReport:
        """
        Validate a DRS directory expression.

        :param drs_expression: A DRS directory expression.
        :type drs_expression: str
        :param prefix: A directory prefix to be removed from the directory expression.
        :type prefix: str|None
        :returns: A validation report.
        :rtype: DrsValidationReport
        """
        if prefix:
            # Remove prefix if present. Always returns a copy.
            drs_expression = drs_expression.removeprefix(prefix)
        return self._validate(drs_expression, self.directory_specs)

    def validate_dataset_id(self, drs_expression: str) -> DrsValidationReport:
        """
        Validate a DRS dataset id expression.

        :param drs_expression: A DRS dataset id expression.
        :type drs_expression: str
        :returns: A validation report.
        :rtype: DrsValidationReport
        """
        return self._validate(drs_expression, self.dataset_id_specs)

    def validate_file_name(self, drs_expression: str) -> DrsValidationReport:
        """
        Validate a file name expression.

        :param drs_expression: A DRS file name expression.
        :type drs_expression: str
        :returns: A validation report.
        :rtype: DrsValidationReport
        """
        full_extension = self._get_full_file_name_extension()
        if drs_expression.endswith(full_extension):
            drs_expression = drs_expression.replace(full_extension, '')
            result = self._validate(drs_expression, self.file_name_specs)
        else:
            issue = FileNameExtensionIssue(expected_extension=full_extension)
            result = self._create_report(self.file_name_specs.type, drs_expression,
                                         [issue], [])
        return result

    def validate(self, drs_expression: str, drs_type: DrsType | str) -> DrsValidationReport:
        """
        Validate a DRS expression.

        :param drs_expression: A DRS expression.
        :type drs_expression: str
        :param drs_type: The type of the given DRS expression (directory, file_name or dataset_id)
        :type drs_type: DrsType|str
        :returns: A validation report.
        :rtype: DrsValidationReport
        """
        match drs_type:
            case DrsType.DIRECTORY:
                return self.validate_directory(drs_expression=drs_expression)
            case DrsType.FILE_NAME:
                return self.validate_file_name(drs_expression=drs_expression)
            case DrsType.DATASET_ID:
                return self.validate_dataset_id(drs_expression=drs_expression)
            case _:
                raise EsgvocDbError(f"unsupported drs type '{drs_type}'")

    def _parse(self,
               drs_expression: str,
               separator: str,
               drs_type: DrsType) -> tuple[list[str] | None,  # terms
                                           list[DrsIssue],  # Errors
                                           list[DrsIssue]]:  # Warnings
        errors: list[DrsIssue] = list()
        warnings: list[DrsIssue] = list()
        cursor_offset = 0
        # Spaces at the beginning/end of expression:
        start_with_space = drs_expression[0].isspace()
        end_with_space = drs_expression[-1].isspace()
        if start_with_space or end_with_space:
            issue: ParsingIssue = Space()
            if self.pedantic:
                errors.append(issue)
            else:
                warnings.append(issue)
            if start_with_space:
                previous_len = len(drs_expression)
                drs_expression = drs_expression.lstrip()
                cursor_offset = previous_len - len(drs_expression)
            if end_with_space:
                drs_expression = drs_expression.rstrip()
        terms = drs_expression.split(separator)
        if len(terms) < 2:
            errors.append(Unparsable(expected_drs_type=drs_type))
            return None, errors, warnings  # Early exit
        max_term_index = len(terms)
        cursor_position = initial_cursor_position = len(drs_expression) + 1
        has_white_term = False
        for index in range(max_term_index-1, -1, -1):
            term = terms[index]
            if (is_white_term := term.isspace()) or (not term):
                has_white_term = has_white_term or is_white_term
                cursor_position -= len(term) + 1
                del terms[index]
                continue
            else:
                break
        if cursor_position != initial_cursor_position:
            max_term_index = len(terms)
            column = cursor_position+cursor_offset
            if (drs_type == DrsType.DIRECTORY) and (not has_white_term):
                issue = ExtraSeparator(column=column)
                if self.pedantic:
                    errors.append(issue)
                else:
                    warnings.append(issue)
            else:
                issue = ExtraChar(column=column)
                errors.append(issue)
        for index in range(max_term_index-1, -1, -1):
            term = terms[index]
            len_term = len(term)
            if not term:
                column = cursor_position + cursor_offset
                issue = ExtraSeparator(column=column)
                if self.pedantic or drs_type != DrsType.DIRECTORY or index == 0:
                    errors.append(issue)
                else:
                    warnings.append(issue)
                del terms[index]
            if term.isspace():
                column = cursor_position + cursor_offset - len_term
                issue = BlankTerm(column=column)
                errors.append(issue)
                del terms[index]
            cursor_position -= len_term + 1

        # Mypy doesn't understand that ParsingIssues are DrsIssues...
        sorted_errors = DrsValidator._sort_parser_issues(errors)  # type: ignore
        sorted_warnings = DrsValidator._sort_parser_issues(warnings)  # type: ignore
        return terms, sorted_errors, sorted_warnings  # type: ignore

    @staticmethod
    def _sort_parser_issues(issues: list[ParsingIssue]) -> list[ParsingIssue]:
        return sorted(issues, key=lambda issue: issue.column if issue.column else 0)

    def _validate_term(self, term: str, part: DrsPart) -> bool:
        match part.kind:
            case DrsPartKind.COLLECTION:
                casted_part: DrsCollection = cast(DrsCollection, part)
                matching_terms = projects.valid_term_in_collection(term,
                                                                   self.project_id,
                                                                   casted_part.collection_id)
                if len(matching_terms) > 0:
                    return True
                else:
                    return False
            case DrsPartKind.CONSTANT:
                part_casted: DrsConstant = cast(DrsConstant, part)
                return part_casted.value != term
            case _:
                raise EsgvocDbError(f"unsupported DRS specs part type '{part.kind}'")

    def _create_report(self,
                       type: DrsType,
                       drs_expression: str,
                       errors: list[DrsIssue],
                       warnings: list[DrsIssue]) -> DrsValidationReport:
        return DrsValidationReport(project_id=self.project_id, type=type,
                                   expression=drs_expression,
                                   errors=cast(list[ValidationError], errors),
                                   warnings=cast(list[ValidationWarning], warnings))

    def _validate(self,
                  drs_expression: str,
                  specs: DrsSpecification) -> DrsValidationReport:
        terms, errors, warnings = self._parse(drs_expression, specs.separator, specs.type)
        if not terms:
            return self._create_report(specs.type, drs_expression, errors, warnings)  # Early exit.
        term_index = 0
        term_max_index = len(terms)
        part_index = 0
        part_max_index = len(specs.parts)
        matching_code_mapping = dict()
        while part_index < part_max_index:
            term = terms[term_index]
            part = specs.parts[part_index]
            if self._validate_term(term, part):
                term_index += 1
                part_index += 1
                matching_code_mapping[part.__str__()] = 0
            elif part.kind == DrsPartKind.CONSTANT or \
                 cast(DrsCollection, part).is_required:  # noqa E127
                issue: ComplianceIssue = InvalidTerm(term=term,
                                                     term_position=term_index+1,
                                                     collection_id_or_constant_value=str(part))
                errors.append(issue)
                matching_code_mapping[part.__str__()] = 1
                term_index += 1
                part_index += 1
            else:  # The part is not required so try to match the term with the next part.
                part_index += 1
                matching_code_mapping[part.__str__()] = -1
            if term_index == term_max_index:
                break
        # Cases:
        # - All terms and collections have been processed.
        # - Not enough term to process all collections.
        # - Extra terms left whereas all collections have been processed:
        #   + The last collections are required => report extra terms.
        #   + The last collections are not required and these terms were not validated by them.
        #     => Should report error even if the collections are not required.
        if part_index < part_max_index:  # Missing terms.
            for index in range(part_index, part_max_index):
                part = specs.parts[index]
                issue = MissingTerm(collection_id=str(part), collection_position=index+1)
                if part.kind == DrsPartKind.CONSTANT or \
                   cast(DrsCollection, part).is_required:
                    errors.append(issue)
                else:
                    warnings.append(issue)
        elif term_index < term_max_index:  # Extra terms.
            part_index -= term_max_index - term_index
            for index in range(term_index, term_max_index):
                term = terms[index]
                part = specs.parts[part_index]
                if part.kind != DrsPartKind.CONSTANT           and \
                   (not cast(DrsCollection, part).is_required) and \
                    matching_code_mapping[part.__str__()] < 0: # noqa E125
                    issue = ExtraTerm(term=term, term_position=index, collection_id=str(part))
                else:
                    issue = ExtraTerm(term=term, term_position=index, collection_id=None)
                errors.append(issue)
                part_index += 1
        return self._create_report(specs.type, drs_expression, errors, warnings)
