from typing import cast, Iterable, Mapping, Any

import esgvoc.api.projects as projects

from esgvoc.api.project_specs import (DrsSpecification,
                               DrsPartKind,
                               DrsCollection,
                               DrsConstant,
                               DrsType)

from esgvoc.apps.drs.validator import DrsApplication
from esgvoc.apps.drs.report import (DrsGeneratorReport,
                                    DrsIssue,
                                    GeneratorIssue,
                                    TooManyTokensCollection,
                                    InvalidToken,
                                    MissingToken,
                                    ConflictingCollections,
                                    AssignedToken)


def _get_first_item(items: set[Any]) -> Any:
    result = None
    for result in items:
        break
    return result


def _transform_set_and_sort(_set: set[Any]) -> list[Any]:
    result = list(_set)
    result.sort()
    return result


class DrsGenerator(DrsApplication):
    """
    Generate a directory, dataset id and file name expression specified by the given project from
    a mapping of collection ids and tokens or an unordered bag of tokens.
    """
    
    def generate_directory_from_mapping(self, mapping: Mapping[str, str]) -> DrsGeneratorReport:
        """
        Generate a directory DRS expression from a mapping of collection ids and tokens.

        :param mapping: A mapping of collection ids (keys) and tokens (values).
        :type mapping: Mapping[str, str]
        :returns: A generation report.
        :rtype: DrsGeneratorReport
        """
        return self._generate_from_mapping(mapping, self.directory_specs)
    
    def generate_directory_from_bag_of_tokens(self, tokens: Iterable[str]) -> DrsGeneratorReport:
        """
        Generate a directory DRS expression from an unordered bag of tokens.

        :param tokens: An unordered bag of tokens.
        :type tokens: Iterable[str]
        :returns: A generation report.
        :rtype: DrsGeneratorReport
        """
        return self._generate_from_bag_of_tokens(tokens, self.directory_specs)

    def generate_dataset_id_from_mapping(self, mapping: Mapping[str, str]) -> DrsGeneratorReport:
        """
        Generate a dataset id DRS expression from a mapping of collection ids and tokens.

        :param mapping: A mapping of collection ids (keys) and tokens (values).
        :type mapping: Mapping[str, str]
        :returns: A generation report.
        :rtype: DrsGeneratorReport
        """
        return self._generate_from_mapping(mapping, self.dataset_id_specs)
    
    def generate_dataset_id_from_bag_of_tokens(self, tokens: Iterable[str]) -> DrsGeneratorReport:
        """
        Generate a dataset id DRS expression from an unordered bag of tokens.

        :param tokens: An unordered bag of tokens.
        :type tokens: Iterable[str]
        :returns: A generation report.
        :rtype: DrsGeneratorReport
        """
        return self._generate_from_bag_of_tokens(tokens, self.dataset_id_specs)
    

    def generate_file_name_from_mapping(self, mapping: Mapping[str, str]) -> DrsGeneratorReport:
        """
        Generate a file name DRS expression from a mapping of collection ids and tokens.
        The file name extension is append automatically, according to the DRS specification,
        so none of the tokens given must include the extension.

        :param mapping: A mapping of collection ids (keys) and tokens (values).
        :type mapping: Mapping[str, str]
        :returns: A generation report.
        :rtype: DrsGeneratorReport
        """
        report = self._generate_from_mapping(mapping, self.file_name_specs)
        report.generated_drs_expression = report.generated_drs_expression + self._get_full_file_name_extension()
        return report 
    
    def generate_file_name_from_bag_of_tokens(self, tokens: Iterable[str]) -> DrsGeneratorReport:
        """
        Generate a file name DRS expression from an unordered bag of tokens.
        The file name extension is append automatically, according to the DRS specification,
        so none of the tokens given must include the extension.

        :param tokens: An unordered bag of tokens.
        :type tokens: Iterable[str]
        :returns: A generation report.
        :rtype: DrsGeneratorReport
        """
        report = self._generate_from_bag_of_tokens(tokens, self.file_name_specs)
        report.generated_drs_expression = report.generated_drs_expression + self._get_full_file_name_extension()
        return report 

    def generate_from_mapping(self, mapping: Mapping[str, str],
                              drs_type: DrsType|str) -> DrsGeneratorReport:
        """
        Generate a DRS expression from a mapping of collection ids and tokens.

        :param mapping: A mapping of collection ids (keys) and tokens (values).
        :type mapping: Mapping[str, str]
        :param drs_type: The type of the given DRS expression (directory, file_name or dataset_id)
        :type drs_type: DrsType|str
        :returns: A generation report.
        :rtype: DrsGeneratorReport
        """
        specs = self._get_specs(drs_type)
        report = self._generate_from_mapping(mapping, specs)
        if DrsType.FILE_NAME == drs_type:
            report.generated_drs_expression = report.generated_drs_expression + self._get_full_file_name_extension()
        return report

    def generate_from_bag_of_tokens(self, tokens: Iterable[str], drs_type: DrsType|str) \
                                                                              -> DrsGeneratorReport:
        """
        Generate a DRS expression from an unordered bag of tokens.

        :param tokens: An unordered bag of tokens.
        :type tokens: Iterable[str]
        :param drs_type: The type of the given DRS expression (directory, file_name or dataset_id)
        :type drs_type: DrsType|str
        :returns: A generation report.
        :rtype: DrsGeneratorReport
        """
        specs = self._get_specs(drs_type)
        return self._generate_from_bag_of_tokens(tokens, specs)


    def _generate_from_mapping(self, mapping: Mapping[str, str], specs: DrsSpecification) \
                                                                              -> DrsGeneratorReport:
        drs_expression, errors, warnings = self.__generate_from_mapping(mapping, specs, True)
        if self.pedantic:
            errors.extend(warnings)
            warnings.clear()
        return DrsGeneratorReport(project_id=self.project_id, type=specs.type,
                                  given_mapping_or_bag_of_tokens=mapping,
                                  mapping_used=mapping,
                                  generated_drs_expression=drs_expression,
                                  errors=cast(list[DrsIssue], errors),
                                  warnings=cast(list[DrsIssue], warnings))

    def __generate_from_mapping(self, mapping: Mapping[str, str],
                                specs: DrsSpecification,
                                has_to_valid_terms: bool)\
                                          -> tuple[str, list[GeneratorIssue], list[GeneratorIssue]]:
        errors: list[GeneratorIssue] = list()
        warnings: list[GeneratorIssue] = list()
        drs_expression = ""
        part_position: int = 0
        for part in specs.parts:
            part_position += 1
            if part.kind == DrsPartKind.COLLECTION:
                collection_part = cast(DrsCollection, part)
                collection_id = collection_part.collection_id
                if collection_id in mapping:
                    part_value = mapping[collection_id]
                    if has_to_valid_terms:
                        matching_terms = projects.valid_term_in_collection(part_value,
                                                                           self.project_id,
                                                                           collection_id)
                        if not matching_terms:
                            issue = InvalidToken(token=part_value,
                                                 token_position=part_position,
                                                 collection_id_or_constant_value=collection_id)
                            errors.append(issue)
                            part_value = DrsGeneratorReport.INVALID_TAG
                else:
                    other_issue = MissingToken(collection_id=collection_id,
                                               collection_position=part_position)
                    if collection_part.is_required:
                        errors.append(other_issue)
                        part_value = DrsGeneratorReport.MISSING_TAG
                    else:
                        warnings.append(other_issue)
                        continue # The for loop.
            else:
                constant_part = cast(DrsConstant, part)
                part_value = constant_part.value
            
            drs_expression += part_value + specs.separator
        
        drs_expression = drs_expression[0:len(drs_expression)-len(specs.separator)]
        return drs_expression, errors, warnings

    def _generate_from_bag_of_tokens(self, tokens: Iterable[str], specs: DrsSpecification) \
                                                                              -> DrsGeneratorReport:
        collection_tokens_mapping: dict[str, set[str]] = dict()
        for token in tokens:
            matching_terms = projects.valid_term_in_project(token, self.project_id)
            for matching_term in matching_terms:
                if matching_term.collection_id not in collection_tokens_mapping:
                    collection_tokens_mapping[matching_term.collection_id] = set()
                collection_tokens_mapping[matching_term.collection_id].add(token)
        collection_tokens_mapping, warnings = DrsGenerator._resolve_conflicts(collection_tokens_mapping)
        mapping, errors = DrsGenerator._check_collection_tokens_mapping(collection_tokens_mapping)
        drs_expression, errs, warns = self.__generate_from_mapping(mapping, specs, False)
        errors.extend(errs)
        warnings.extend(warns)
        if self.pedantic:
            errors.extend(warnings)
            warnings.clear()
        return DrsGeneratorReport(project_id=self.project_id, type=specs.type,
                                  given_mapping_or_bag_of_tokens=tokens,
                                  mapping_used=mapping,generated_drs_expression=drs_expression,
                                  errors=cast(list[DrsIssue], errors),
                                  warnings=cast(list[DrsIssue], warnings))
    
    @staticmethod
    def _resolve_conflicts(collection_tokens_mapping: dict[str, set[str]]) \
                                            -> tuple[dict[str, set[str]], list[GeneratorIssue]]:
        warnings: list[GeneratorIssue] = list()
        conflicting_collection_ids_list: list[list[str]] = list()
        collection_ids: list[str] = list(collection_tokens_mapping.keys())
        len_collection_ids: int = len(collection_ids)
        
        for l_collection_index in range(0, len_collection_ids - 1):
            conflicting_collection_ids: list[str] = list()
            for r_collection_index in range(l_collection_index + 1, len_collection_ids):
                if collection_tokens_mapping[collection_ids[l_collection_index]].isdisjoint \
                       (collection_tokens_mapping[collection_ids[r_collection_index]]):
                    continue
                else:
                    not_registered = True
                    for cc_ids in conflicting_collection_ids_list:
                        if collection_ids[l_collection_index] in cc_ids and \
                           collection_ids[r_collection_index] in cc_ids:
                            not_registered = False
                            break
                    if not_registered:
                        conflicting_collection_ids.append(collection_ids[r_collection_index])
            if conflicting_collection_ids:
                conflicting_collection_ids.append(collection_ids[l_collection_index])
                conflicting_collection_ids_list.append(conflicting_collection_ids)

        # Each time a collection is resolved, we must restart the loop so as to check if others can be,
        # until no progress is made.
        while True:
            # 1. Non-conflicting collections with only one token are assigned.
            #    Non-conflicting collections with more than one token will be raise an error
            #    in the _check method.
            
            #    Nothing to do.

            # 2a. Collections with one token that are conflicting to each other will raise an error.
            #     We don't search for collection with more than one token which token sets are exactly
            #     the same, because we cannot choose which token will be removed in 2b.
            #     So stick with one token collections: those collection will be detected in method _check.
            collection_ids_with_len_eq_1_list: list[list[str]] = list()
            for collection_ids in conflicting_collection_ids_list:
                tmp_conflicting_collection_ids: list[str] = list()
                for collection_id in collection_ids:
                    if len(collection_tokens_mapping[collection_id]) == 1:
                        tmp_conflicting_collection_ids.append(collection_id)
                if len(tmp_conflicting_collection_ids) > 1:
                    collection_ids_with_len_eq_1_list.append(tmp_conflicting_collection_ids)
            # 2b. As it is not possible to resolve collections sharing the same unique token:
            #     raise errors, remove the faulty collections and their token.
            if collection_ids_with_len_eq_1_list:
                for collection_ids_to_be_removed in collection_ids_with_len_eq_1_list:
                    DrsGenerator._remove_ids_from_conflicts(conflicting_collection_ids_list,
                                                            collection_ids_to_be_removed)
                    DrsGenerator._remove_token_from_other_token_sets(collection_tokens_mapping,
                                                      collection_ids_to_be_removed)
                # Every time conflicting_collection_ids_list is modified, we must restart the loop,
                # as conflicting collections may be resolved.
                continue

            # 3.a For each collections with only one token, assign their token to the detriment of
            #    collections with more than one token.
            wining_collection_ids: list[str] = list()
            for collection_ids in conflicting_collection_ids_list:
                for collection_id in collection_ids:
                    if len(collection_tokens_mapping[collection_id]) == 1:
                        wining_collection_ids.append(collection_id)
                        token = _get_first_item(collection_tokens_mapping[collection_id])
                        issue = AssignedToken(collection_id=collection_id, token=token)
                        warnings.append(issue)
            # 3.b Update conflicting collections.
            if wining_collection_ids:
                DrsGenerator._remove_ids_from_conflicts(conflicting_collection_ids_list,
                                                        wining_collection_ids)
                DrsGenerator._remove_token_from_other_token_sets(collection_tokens_mapping,
                                                  wining_collection_ids)
                # Every time conflicting_collection_ids_list is modified, we must restart the loop,
                # as conflicting collections may be resolved.
                continue

            # 4.a For each token set of the remaining conflicting collections, compute their difference.
            #    If the difference is one token, this token is assigned to the collection that owns it.
            wining_id_and_token_pairs: list[tuple[str, str]] = list()
            for collection_ids in conflicting_collection_ids_list:
                for collection_index in range(0, len(collection_ids)):
                    diff: set[str] = collection_tokens_mapping[collection_ids[collection_index]]\
                                         .difference(
                                                     *[collection_tokens_mapping[index]
                                               for index in collection_ids[collection_index + 1 :] +\
                                                        collection_ids[:collection_index]
                                                      ]
                                                    )
                    if len(diff) == 1:
                        wining_id_and_token_pairs.append((collection_ids[collection_index],
                                                         _get_first_item(diff)))
            # 4.b Update conflicting collections.
            if wining_id_and_token_pairs:
                wining_collection_ids = list()
                for collection_id, token in wining_id_and_token_pairs:
                    wining_collection_ids.append(collection_id)
                    collection_tokens_mapping[collection_id].clear()
                    collection_tokens_mapping[collection_id].add(token)
                    issue = AssignedToken(collection_id=collection_id, token=token)
                    warnings.append(issue)
                DrsGenerator._remove_ids_from_conflicts(conflicting_collection_ids_list,
                                                        wining_collection_ids)
                DrsGenerator._remove_token_from_other_token_sets(collection_tokens_mapping,
                                                               wining_collection_ids)
                continue
            else:
                break # Stop the loop when no progress is made.
        return collection_tokens_mapping, warnings

    @staticmethod
    def _check_collection_tokens_mapping(collection_tokens_mapping: dict[str, set[str]]) \
                                                     -> tuple[dict[str, str], list[GeneratorIssue]]:
        errors: list[GeneratorIssue] = list()
        # 1. Looking for collections that share strictly the same token(s).
        collection_ids: list[str] = list(collection_tokens_mapping.keys())
        len_collection_ids: int = len(collection_ids)
        faulty_collections_list: list[set[str]] = list()
        for l_collection_index in range(0, len_collection_ids - 1):
            l_collection_id = collection_ids[l_collection_index]
            l_token_set = collection_tokens_mapping[l_collection_id]
            for r_collection_index in range(l_collection_index + 1, len_collection_ids):
                r_collection_id = collection_ids[r_collection_index]
                r_token_set = collection_tokens_mapping[r_collection_id]
                # check if the set is empty because the difference will always be an empty set!
                if l_token_set and (not l_token_set.difference(r_token_set)):
                    not_registered = True
                    for faulty_collections in faulty_collections_list:
                        if l_collection_id in faulty_collections or \
                           r_collection_id in faulty_collections:
                            faulty_collections.add(l_collection_id)
                            faulty_collections.add(r_collection_id)
                            not_registered = False
                            break
                    if not_registered:
                        faulty_collections_list.append({l_collection_id, r_collection_id})
        for faulty_collections in faulty_collections_list:
            tokens = collection_tokens_mapping[_get_first_item(faulty_collections)]
            issue = ConflictingCollections(collection_ids=_transform_set_and_sort(faulty_collections),
                                           tokens=_transform_set_and_sort(tokens))
            errors.append(issue)
            for collection_id in faulty_collections:
                del collection_tokens_mapping[collection_id]
        
        # 2. Looking for collections with more than one token.
        result: dict[str, str] = dict()
        for collection_id, token_set in collection_tokens_mapping.items():
            len_token_set = len(token_set)
            if len_token_set == 1:
                result[collection_id] = _get_first_item(token_set)
            elif len_token_set > 1:
                other_issue = TooManyTokensCollection(collection_id=collection_id,
                                                     tokens=_transform_set_and_sort(token_set))
                errors.append(other_issue)
            #else: Don't add emptied collection to the result.
        return result, errors

    @staticmethod
    def _remove_token_from_other_token_sets(collection_tokens_mapping: dict[str, set[str]],
                                          collection_ids_to_be_removed: list[str]) -> None:
        for collection_id_to_be_removed in collection_ids_to_be_removed:
            # Should only be one token.
            token_to_be_removed: str = _get_first_item(collection_tokens_mapping[collection_id_to_be_removed])
            for collection_id in collection_tokens_mapping.keys():
                if (collection_id not in collection_ids_to_be_removed):
                    collection_tokens_mapping[collection_id].discard(token_to_be_removed)

    @staticmethod
    def _remove_ids_from_conflicts(conflicting_collection_ids_list: list[list[str]],
                                   collection_ids_to_be_removed: list[str]) -> None:
        for collection_id_to_be_removed in collection_ids_to_be_removed:
            for conflicting_collection_ids in conflicting_collection_ids_list:
                if collection_id_to_be_removed in conflicting_collection_ids:
                    conflicting_collection_ids.remove(collection_id_to_be_removed)


if __name__ == "__main__":
    project_id = 'cmip6plus'
    generator = DrsGenerator(project_id)
    mapping = \
    {
        'member_id': 'r2i2p1f2',
        'activity_id': 'CMIP',
        'source_id': 'MIROC6',
        'mip_era': 'CMIP6Plus',
        'experiment_id': 'amip',
        'variable_id': 'od550aer',
        'table_id': 'ACmon',
        'grid_label': 'gn',
        'institution_id': 'IPSL',
    }
    report = generator.generate_file_name_from_mapping(mapping)
    print(report.warnings)