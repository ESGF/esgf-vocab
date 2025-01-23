from typing import cast, Iterable, Mapping, Any

import esgvoc.api.projects as projects

from esgvoc.api.project_specs import (DrsSpecification,
                               DrsPartKind,
                               DrsCollection,
                               DrsConstant)

from esgvoc.apps.drs.validator import DrsApplication
from esgvoc.apps.drs.report import (DrsGeneratorReport,
                                    GeneratorIssue,
                                    TooManyWordsCollection,
                                    InvalidToken,
                                    MissingToken,
                                    ConflictingCollections,
                                    AssignedWord)


def _get_first_item(items: set[Any]) -> Any:
    result = None
    for result in items:
        break
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
        
        return self.generate_from_mapping(mapping, self.directory_specs)
    
    def generate_directory_from_bag_of_words(self, tokens: Iterable[str]) -> DrsGeneratorReport:
        """
        Generate a directory DRS expression from an unordered bag of tokens.

        :param tokens: An unordered bag of tokens.
        :type tokens: Iterable[str]
        :returns: A generation report.
        :rtype: DrsGeneratorReport
        """
        return self.generate_from_bag_of_words(tokens, self.directory_specs)

    def generate_dataset_id_from_mapping(self, mapping: Mapping[str, str]) -> DrsGeneratorReport:
        """
        Generate a dataset id DRS expression from a mapping of collection ids and tokens.

        :param mapping: A mapping of collection ids (keys) and tokens (values).
        :type mapping: Mapping[str, str]
        :returns: A generation report.
        :rtype: DrsGeneratorReport
        """
        return self.generate_from_mapping(mapping, self.dataset_id_specs)
    
    def generate_dataset_id_from_bag_of_words(self, tokens: Iterable[str]) -> DrsGeneratorReport:
        """
        Generate a dataset id DRS expression from an unordered bag of tokens.

        :param tokens: An unordered bag of tokens.
        :type tokens: Iterable[str]
        :returns: A generation report.
        :rtype: DrsGeneratorReport
        """
        return self.generate_from_bag_of_words(tokens, self.dataset_id_specs)
    

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
        
        report = self.generate_from_mapping(mapping, self.file_name_specs)
        report.computed_drs_expression = report.computed_drs_expression + self.get_full_file_name_extension()
        return report 
    
    def generate_file_name_from_bag_of_words(self, tokens: Iterable[str]) -> DrsGeneratorReport:
        """
        Generate a file name DRS expression from an unordered bag of tokens.
        The file name extension is append automatically, according to the DRS specification,
        so none of the tokens given must include the extension.

        :param tokens: An unordered bag of tokens.
        :type tokens: Iterable[str]
        :returns: A generation report.
        :rtype: DrsGeneratorReport
        """
        report = self.generate_from_bag_of_words(tokens, self.file_name_specs)
        report.computed_drs_expression = report.computed_drs_expression + self.get_full_file_name_extension()
        return report 

    def generate_from_mapping(self, mapping: Mapping[str, str],
                              specs: DrsSpecification) -> DrsGeneratorReport:
        """
        Generate a DRS expression from a mapping of collection ids and tokens.

        :param mapping: A mapping of collection ids (keys) and tokens (values).
        :type mapping: Mapping[str, str]
        :param specs: a DRS project specification (dataset id, file name or directory).
        :type specs: DrsSpecification
        :returns: A generation report.
        :rtype: DrsGeneratorReport
        """
        
        drs_expression, errors, warnings = self._generate_from_mapping(mapping, specs, True)
        if self.pedantic:
            errors.extend(warnings)
            warnings.clear()
        return DrsGeneratorReport(self.project_id, specs.type, mapping, mapping,
                                  drs_expression, errors, warnings)
    
    def generate_from_bag_of_words(self, tokens: Iterable[str], specs: DrsSpecification) \
                                                        -> DrsGeneratorReport:
        """
        Generate a DRS expression from an unordered bag of tokens.

        :param tokens: An unordered bag of tokens.
        :type tokens: Iterable[str]
        :param specs: a DRS project specification (dataset id, file name or directory).
        :type specs: DrsSpecification
        :returns: A generation report.
        :rtype: DrsGeneratorReport
        """
        collection_words_mapping: dict[str, set[str]] = dict()
        for word in tokens:
            matching_terms = projects.valid_term_in_project(word, self.project_id)
            for matching_term in matching_terms:
                if matching_term.collection_id not in collection_words_mapping:
                    collection_words_mapping[matching_term.collection_id] = set()
                collection_words_mapping[matching_term.collection_id].add(word)
        collection_words_mapping, warnings = DrsGenerator._resolve_conflicts(collection_words_mapping)
        mapping, errors = DrsGenerator._check_collection_words_mapping(collection_words_mapping)
        drs_expression, errs, warns = self._generate_from_mapping(mapping, specs, False)
        errors.extend(errs)
        warnings.extend(warns)
        if self.pedantic:
            errors.extend(warnings)
            warnings.clear()
        return DrsGeneratorReport(self.project_id, specs.type, mapping, mapping,
                                  drs_expression, errors, warnings)

    def _generate_from_mapping(self, mapping: Mapping[str, str],
                               specs: DrsSpecification,
                               has_to_valid_terms: bool)\
                                   -> tuple[str, list[GeneratorIssue], list[GeneratorIssue]]:
        errors: list[GeneratorIssue] = list()
        warnings: list[GeneratorIssue] = list()
        drs_expression = ""
        part_position: int = 0
        for part in specs.parts:
            part_position += 1
            if part.kind == DrsPartKind.collection:
                collection_part = cast(DrsCollection, part)
                collection_id = collection_part.collection_id
                if collection_id in mapping:
                    part_value = mapping[collection_id]
                    if has_to_valid_terms:
                        matching_terms = projects.valid_term_in_collection(part_value,
                                                                           self.project_id,
                                                                           collection_id)
                        if not matching_terms:
                            issue = InvalidToken(part_value, part_position, collection_id)
                            errors.append(issue)
                            part_value = DrsGeneratorReport.INVALID_TAG
                else:
                    other_issue = MissingToken(collection_id, part_position)
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
    
    @staticmethod
    def _resolve_conflicts(collection_words_mapping: dict[str, set[str]]) \
                                            -> tuple[dict[str, set[str]], list[GeneratorIssue]]:
        warnings: list[GeneratorIssue] = list()
        conflicting_collection_ids_list: list[list[str]] = list()
        collection_ids: list[str] = list(collection_words_mapping.keys())
        len_collection_ids: int = len(collection_ids)
        
        for l_collection_index in range(0, len_collection_ids - 1):
            conflicting_collection_ids: list[str] = list()
            for r_collection_index in range(l_collection_index + 1, len_collection_ids):
                if collection_words_mapping[collection_ids[l_collection_index]].isdisjoint \
                       (collection_words_mapping[collection_ids[r_collection_index]]):
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
            # 1. Non-conflicting collections with only one word are assigned.
            #    Non-conflicting collections with more than one word will be raise an error
            #    in the _check method.
            
            #    Nothing to do.

            # 2a. Collections with one word that are conflicting to each other will raise an error.
            #     We don't search for collection with more than one word which word sets are exactly
            #     the same, because we cannot choose which word will be removed in 2b.
            #     So stick with one word collections: those collection will be detected in method _check.
            collection_ids_with_len_eq_1_list: list[list[str]] = list()
            for collection_ids in conflicting_collection_ids_list:
                tmp_conflicting_collection_ids: list[str] = list()
                for collection_id in collection_ids:
                    if len(collection_words_mapping[collection_id]) == 1:
                        tmp_conflicting_collection_ids.append(collection_id)
                if len(tmp_conflicting_collection_ids) > 1:
                    collection_ids_with_len_eq_1_list.append(tmp_conflicting_collection_ids)
            # 2b. As it is not possible to resolve collections sharing the same unique word:
            #     raise errors, remove the faulty collections and their word.
            if collection_ids_with_len_eq_1_list:
                for collection_ids_to_be_removed in collection_ids_with_len_eq_1_list:
                    DrsGenerator._remove_ids_from_conflicts(conflicting_collection_ids_list,
                                                            collection_ids_to_be_removed)
                    DrsGenerator._remove_word_from_other_word_sets(collection_words_mapping,
                                                      collection_ids_to_be_removed)
                # Every time conflicting_collection_ids_list is modified, we must restart the loop,
                # as conflicting collections may be resolved.
                continue

            # 3.a For each collections with only one word, assign their word to the detriment of
            #    collections with more than one word.
            wining_collection_ids: list[str] = list()
            for collection_ids in conflicting_collection_ids_list:
                for collection_id in collection_ids:
                    if len(collection_words_mapping[collection_id]) == 1:
                        wining_collection_ids.append(collection_id)
                        word = _get_first_item(collection_words_mapping[collection_id])
                        issue = AssignedWord(collection_id, word)
                        warnings.append(issue)
            # 3.b Update conflicting collections.
            if wining_collection_ids:
                DrsGenerator._remove_ids_from_conflicts(conflicting_collection_ids_list,
                                                        wining_collection_ids)
                DrsGenerator._remove_word_from_other_word_sets(collection_words_mapping,
                                                  wining_collection_ids)
                # Every time conflicting_collection_ids_list is modified, we must restart the loop,
                # as conflicting collections may be resolved.
                continue

            # 4.a For each word set of the remaining conflicting collections, compute their difference.
            #    If the difference is one word, this word is assigned to the collection that owns it.
            wining_id_and_word_pairs: list[tuple[str, str]] = list()
            for collection_ids in conflicting_collection_ids_list:
                for collection_index in range(0, len(collection_ids)):
                    diff: set[str] = collection_words_mapping[collection_ids[collection_index]]\
                                         .difference(
                                                     *[collection_words_mapping[index]
                                               for index in collection_ids[collection_index + 1 :] +\
                                                        collection_ids[:collection_index]
                                                      ]
                                                    )
                    if len(diff) == 1:
                        wining_id_and_word_pairs.append((collection_ids[collection_index],
                                                         _get_first_item(diff)))
            # 4.b Update conflicting collections.
            if wining_id_and_word_pairs:
                wining_collection_ids = list()
                for collection_id, word in wining_id_and_word_pairs:
                    wining_collection_ids.append(collection_id)
                    collection_words_mapping[collection_id].clear()
                    collection_words_mapping[collection_id].add(word)
                    issue = AssignedWord(collection_id, word)
                    warnings.append(issue)
                DrsGenerator._remove_ids_from_conflicts(conflicting_collection_ids_list,
                                                        wining_collection_ids)
                DrsGenerator._remove_word_from_other_word_sets(collection_words_mapping,
                                                               wining_collection_ids)
                continue
            else:
                break # Stop the loop when no progress is made.
        return collection_words_mapping, warnings

    @staticmethod
    def _check_collection_words_mapping(collection_words_mapping: dict[str, set[str]]) \
                                                     -> tuple[dict[str, str], list[GeneratorIssue]]:
        errors: list[GeneratorIssue] = list()
        # 1. Looking for collections that share strictly the same word(s).
        collection_ids: list[str] = list(collection_words_mapping.keys())
        len_collection_ids: int = len(collection_ids)
        faulty_collections_list: list[set[str]] = list()
        for l_collection_index in range(0, len_collection_ids - 1):
            l_collection_id = collection_ids[l_collection_index]
            l_word_set = collection_words_mapping[l_collection_id]
            for r_collection_index in range(l_collection_index + 1, len_collection_ids):
                r_collection_id = collection_ids[r_collection_index]
                r_word_set = collection_words_mapping[r_collection_id]
                # check if the set is empty because the difference will always be an empty set!
                if l_word_set and (not l_word_set.difference(r_word_set)):
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
            words = collection_words_mapping[_get_first_item(faulty_collections)]
            issue = ConflictingCollections(faulty_collections, words)
            errors.append(issue)
            for collection_id in faulty_collections:
                del collection_words_mapping[collection_id]
        
        # 2. Looking for collections with more than one word.
        result: dict[str, str] = dict()
        for collection_id, word_set in collection_words_mapping.items():
            len_word_set = len(word_set)
            if len_word_set == 1:
                result[collection_id] = _get_first_item(word_set)
            elif len_word_set > 1:
                other_issue = TooManyWordsCollection(collection_id, word_set)
                errors.append(other_issue)
            #else: Don't add emptied collection to the result.
        return result, errors

    @staticmethod
    def _remove_word_from_other_word_sets(collection_words_mapping: dict[str, set[str]],
                                          collection_ids_to_be_removed: list[str]) -> None:
        for collection_id_to_be_removed in collection_ids_to_be_removed:
            # Should only be one word.
            word_to_be_removed: str = _get_first_item(collection_words_mapping[collection_id_to_be_removed])
            for collection_id in collection_words_mapping.keys():
                if (collection_id not in collection_ids_to_be_removed):
                    collection_words_mapping[collection_id].discard(word_to_be_removed)

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