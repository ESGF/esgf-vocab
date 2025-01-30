from typing import cast
from esgvoc.api.project_specs import (ProjectSpecs,
                               DrsType,
                               DrsPart,
                               DrsSpecification,
                               DrsPartKind,
                               DrsCollection,
                               DrsConstant)
import esgvoc.api.projects as projects
import esgvoc.apps.drs.constants as constants
from esgvoc.apps.drs.report import (DrsValidationReport,
                                    DrsIssue,
                                    ParserIssue,
                                    ValidationIssue,
                                    Space,
                                    Unparsable,
                                    ExtraSeparator,
                                    ExtraChar,
                                    BlankToken,
                                    InvalidToken,
                                    ExtraToken,
                                    MissingToken,
                                    FileNameExtensionIssue)


class DrsApplication:
    """
    Generic DRS application class.
    """

    def __init__(self, project_id: str, pedantic: bool = False) -> None:
        self.project_id: str = project_id
        """The project id."""
        self.pedantic: bool = pedantic
        """Same as the option of GCC: turn warnings into errors. Default False."""
        project_specs: ProjectSpecs = projects.get_project_specs(project_id)
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
                    raise ValueError(f'unsupported DRS specs type {specs.type}')

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
            raise ValueError('missing properties in the DRS file name specifications of the ' +
                             f'project {self.project_id}')
        return full_extension
    
    def _get_specs(self, drs_type: DrsType|str) -> DrsSpecification:
        match drs_type:
            case DrsType.DIRECTORY:
                specs = self.directory_specs
            case DrsType.FILE_NAME:
                specs = self.file_name_specs
            case DrsType.DATASET_ID:
                specs = self.dataset_id_specs
            case _:
                raise ValueError(f'unsupported DRS type {drs_type}')
        return specs
    
class DrsValidator(DrsApplication):
    """
    Valid a DRS directory, dataset id and file name expression against a project.
    """
   
    def validate_directory(self, drs_expression: str) -> DrsValidationReport:
        """
        Validate a DRS directory expression.

        :param drs_expression: A DRS directory expression.
        :type drs_expression: str
        :returns: A validation report.
        :rtype: DrsValidationReport
        """
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

    def validate(self, drs_expression: str, drs_type: DrsType|str) -> DrsValidationReport:
        """
        Validate a DRS expression.

        :param drs_expression: A DRS expression.
        :type drs_expression: str
        :param drs_type: The type of the given DRS expression (directory, file_name or dataset_id)
        :type drs_type: DrsType|str
        :returns: A validation report.
        :rtype: DrsValidationReport
        """
        specs = self._get_specs(drs_type)
        return self._validate(drs_expression, specs)
    
    def _parse(self,
               drs_expression: str,
               separator: str,
               drs_type: DrsType) -> tuple[list[str]|None,  # Tokens
                                           list[DrsIssue],  # Errors
                                           list[DrsIssue]]: # Warnings
        errors: list[DrsIssue] = list()
        warnings: list[DrsIssue] = list()
        cursor_offset = 0
        # Spaces at the beginning/end of expression:
        start_with_space = drs_expression[0].isspace()
        end_with_space = drs_expression[-1].isspace()
        if start_with_space or end_with_space:
            issue: ParserIssue = Space()
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
        tokens = drs_expression.split(separator)
        if len(tokens) < 2:
            errors.append(Unparsable(expected_drs_type=drs_type))
            return None, errors, warnings # Early exit
        max_token_index = len(tokens)
        cursor_position = initial_cursor_position = len(drs_expression) + 1
        has_white_token = False
        for index in range(max_token_index-1, -1, -1):
            token = tokens[index]
            if (is_white_token := token.isspace()) or (not token):
                has_white_token = has_white_token or is_white_token
                cursor_position -= len(token) + 1
                del tokens[index]
                continue
            else:
                break
        if cursor_position != initial_cursor_position:
            max_token_index = len(tokens)
            column = cursor_position+cursor_offset
            if (drs_type == DrsType.DIRECTORY) and (not has_white_token):
                issue = ExtraSeparator(column=column)
                warnings.append(issue)
            else:
                issue = ExtraChar(column=column)
                errors.append(issue)
        for index in range(max_token_index-1, -1, -1):
            token = tokens[index]
            len_token = len(token)
            if not token:
                column = cursor_position + cursor_offset
                issue = ExtraSeparator(column=column)
                if (drs_type != DrsType.DIRECTORY) or self.pedantic or (index == 0):
                    errors.append(issue)
                else:
                    warnings.append(issue)
                del tokens[index]
            if token.isspace():
                column = cursor_position + cursor_offset - len_token
                issue = BlankToken(column=column)
                errors.append(issue)
                del tokens[index]
            cursor_position -= len_token + 1
        
        # Mypy doesn't understand that ParserIssues are DrsIssues...
        sorted_errors = DrsValidator._sort_parser_issues(errors) # type: ignore
        sorted_warnings = DrsValidator._sort_parser_issues(warnings) # type: ignore
        return tokens, sorted_errors, sorted_warnings # type: ignore
    
    @staticmethod
    def _sort_parser_issues(issues: list[ParserIssue]) -> list[ParserIssue]:
        return sorted(issues, key=lambda issue: issue.column if issue.column else 0)

    def _validate_token(self, token: str, part: DrsPart) -> bool:
        match part.kind:
            case DrsPartKind.COLLECTION:
                casted_part: DrsCollection = cast(DrsCollection, part)
                try:
                    matching_terms = projects.valid_term_in_collection(token,
                                                                       self.project_id,
                                                                       casted_part.collection_id)
                except Exception as e:
                    msg = f'problem while validating token: {e}.Abort.'
                    raise ValueError(msg) from e
                if len(matching_terms) > 0:
                    return True
                else:
                    return False
            case DrsPartKind.CONSTANT:
                part_casted: DrsConstant = cast(DrsConstant, part)
                return part_casted.value != token
            case _:
                raise ValueError(f'unsupported DRS specs part type {part.kind}')

    def _create_report(self,
                       type: DrsType,
                       drs_expression: str,
                       errors: list[DrsIssue],
                       warnings: list[DrsIssue]) -> DrsValidationReport:
        return DrsValidationReport(project_id=self.project_id, type=type,
                                   expression=drs_expression, errors=errors, warnings=warnings)

    def _validate(self,
                  drs_expression: str,
                  specs: DrsSpecification) -> DrsValidationReport:
        tokens, errors, warnings = self._parse(drs_expression, specs.separator, specs.type)
        if not tokens:
            return self._create_report(specs.type, drs_expression, errors, warnings) # Early exit.
        token_index = 0
        token_max_index = len(tokens)
        part_index = 0
        part_max_index = len(specs.parts)
        matching_code_mapping = dict()
        while part_index < part_max_index:
            token = tokens[token_index]
            part = specs.parts[part_index]
            if self._validate_token(token, part):
                token_index += 1
                part_index += 1
                matching_code_mapping[part.__str__()] = 0
            elif part.kind == DrsPartKind.CONSTANT or \
                 cast(DrsCollection, part).is_required:
                issue: ValidationIssue = InvalidToken(token=token,
                                                      token_position=token_index+1,
                                                      collection_id_or_constant_value=str(part))
                errors.append(issue)
                matching_code_mapping[part.__str__()] = 1
                token_index += 1
                part_index += 1
            else: # The part is not required so try to match the token with the next part.
                part_index += 1
                matching_code_mapping[part.__str__()] = -1
            if token_index == token_max_index:
                break
        # Cases:
        # - All tokens and collections have been processed.
        # - Not enough token to process all collections.
        # - Extra tokens left whereas all collections have been processed:
        #   + The last collections are required => report extra tokens.
        #   + The last collections are not required and these tokens were not validated by them.
        #     => Should report error even if the collections are not required.
        if part_index < part_max_index: # Missing tokens.
            for index in range(part_index, part_max_index):
                part = specs.parts[index]
                issue = MissingToken(collection_id=str(part), collection_position=index+1)
                if part.kind == DrsPartKind.CONSTANT or \
                   cast(DrsCollection, part).is_required:
                    errors.append(issue)
                else:
                    warnings.append(issue)
        elif token_index < token_max_index: # Extra tokens.
            part_index -= token_max_index - token_index
            for index in range(token_index, token_max_index):
                token = tokens[index]
                part = specs.parts[part_index]
                if part.kind != DrsPartKind.CONSTANT           and \
                   (not cast(DrsCollection, part).is_required) and \
                    matching_code_mapping[part.__str__()] < 0:
                    issue = ExtraToken(token=token, token_position=index, collection_id=str(part))
                else:
                    issue = ExtraToken(token=token, token_position=index, collection_id=None)
                errors.append(issue)
                part_index += 1
        return self._create_report(specs.type, drs_expression, errors, warnings)


if __name__ == "__main__":
    project_id = 'cmip6plus'
    validator = DrsValidator(project_id)
    drs_expressions = [
".CMIP6Plus.CMIP.IPSL.  .MIROC6.amip..r2i2p1f2.ACmon.od550aer. ..gn",
]
    import time
    for drs_expression in drs_expressions:
        start_time = time.perf_counter_ns()
        report = validator.validate_dataset_id(drs_expression)
        stop_time = time.perf_counter_ns()
        print(f'elapsed time: {(stop_time-start_time)/1000000} ms')
        if report.nb_errors > 0:
            print(f'error(s): {report.nb_errors}')
            for error in report.errors:
                print(error)
        else:
            print('error(s): 0')
        if report.nb_warnings > 0:
            print(f'warning(s): {report.nb_warnings}')
            for warning in report.warnings:
                print(warning)
        else:
            print('warning(s): 0')