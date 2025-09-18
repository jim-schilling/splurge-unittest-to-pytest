# Test module inventory — 2025-09-14

This file lists every discovered Python test module under `tests/` (recursive).

## Domain categories

These domain tags are used in the table below (semicolon-delimited). They are conservative, inferred from filenames and directory structure; please review and adjust as needed:

 - integration: end-to-end or multi-module integration tests
 - smoke: smoke/regression quick-check tests
 - converter: code that converts unittest -> pytest (converter logic)
 - generator: code that generates test code or artifacts
 - fixtures: tests around fixtures, builders, injection
 - imports: tests about import handling and injection
 - diagnostics: logging/diagnostic plumbing
 - assertions: assertion rewriting and assertion logic
 - rewriter: code that rewrites AST/assertions or transforms code
 - pipeline: end-to-end pipelines and data flows
 - cli: command-line interface behaviors
 - main: main module / entrypoint logic
 - manager: manager/controller behaviors and snapshotting
 - stages: multi-stage transformation logic
 - goldens: golden file generation / comparison
 - mocks: mocking and aliasing behavior
 - patch: patching/monkeypatch behaviors
 - teardown: teardown/cleanup logic
 - tidy: tidy/formatting helpers
 - naming: name allocation and naming collision behavior
 - parameters: flexible parameters and method params
 - exceptions: raises and ExceptionInfo handling
 - literals: literal inference and handling
 - tranches: tranche based batch tests
 - transform: transformer behavior and guard fixtures
 - validation: validator/postvalidator behaviors
 - bundles: bundle/namedtuple helpers
 - regex: regex or re-related tests
 - general: miscellaneous or uncategorized tests

| Test file | Broad behavior / module (inferred) | Domains | Proposed normalized name | Relative path |
|---|---|---|---|---|
| `conftest.py` | conftest | general | `test_general_001.py` | `tests/conftest.py` |
| `test_convert_bak_integration.py` | convert bak integration | integration; converter | `test_integration_converter_001.py` | `tests/integration/test_convert_bak_integration.py` |
| `test_data_conversion_imports.py` | data conversion imports | integration; imports | `test_integration_imports_001.py` | `tests/integration/test_data_conversion_imports.py` |
| `test_end_to_end.py` | end to end | integration | `test_integration_001.py` | `tests/integration/test_end_to_end.py` |
| `test_generator_golden_tuple.py` | generator golden tuple | integration; generator; goldens | `test_integration_generator_goldens_001.py` | `tests/integration/test_generator_golden_tuple.py` |
| `test_generator_integration.py` | generator integration | integration; generator | `test_integration_generator_001.py` | `tests/integration/test_generator_integration.py` |
| `test_generator_integration_extra.py` | generator integration extra | integration; generator | `test_integration_generator_002.py` | `tests/integration/test_generator_integration_extra.py` |
| `test_generator_integration_more.py` | generator integration more | integration; generator; regex | `test_integration_generator_regex_001.py` | `tests/integration/test_generator_integration_more.py` |
| `test_pipeline_integration.py` | pipeline integration | integration; pipeline | `test_integration_pipeline_001.py` | `tests/integration/test_pipeline_integration.py` |
| `test_run_converted.py` | run converted | integration; converter | `test_integration_converter_002.py` | `tests/integration/test_run_converted.py` |
| `test_run_converted_file.py` | run converted file | integration; converter | `test_integration_converter_003.py` | `tests/integration/test_run_converted_file.py` |
| `test_smoke_conversion.py` | smoke conversion | integration; smoke | `test_integration_smoke_001.py` | `tests/integration/test_smoke_conversion.py` |
| `test_smoke_integration.py` | smoke integration | integration; smoke | `test_integration_smoke_002.py` | `tests/integration/test_smoke_integration.py` |
| `autouse_helpers.py` | autouse helpers | general | `test_general_002.py` | `tests/unit/helpers/autouse_helpers.py` |
| `test_annotation_inferer.py` | annotation inferer | regex | `test_regex_001.py` | `tests/unit/test_annotation_inferer.py` |
| `test_annotation_inferer_more.py` | annotation inferer more | regex | `test_regex_002.py` | `tests/unit/test_annotation_inferer_more.py` |
| `test_assertion_dispatch.py` | assertion dispatch | assertions; patch | `test_assertions_patch_001.py` | `tests/unit/test_assertion_dispatch.py` |
| `test_assertion_rewriter.py` | assertion rewriter | assertions; rewriter; regex | `test_assertions_rewriter_regex_001.py` | `tests/unit/test_assertion_rewriter.py` |
| `test_assertion_rewriter_deeper.py` | assertion rewriter deeper | assertions; rewriter; regex | `test_assertions_rewriter_regex_002.py` | `tests/unit/test_assertion_rewriter_deeper.py` |
| `test_assertion_rewriter_helpers.py` | assertion rewriter helpers | assertions; rewriter; regex | `test_assertions_rewriter_regex_003.py` | `tests/unit/test_assertion_rewriter_helpers.py` |
| `test_assertion_rewriter_more.py` | assertion rewriter more | assertions; rewriter; regex | `test_assertions_rewriter_regex_004.py` | `tests/unit/test_assertion_rewriter_more.py` |
| `test_assertion_rewriter_phaseA_extra.py` | assertion rewriter phaseA extra | assertions; rewriter; regex | `test_assertions_rewriter_regex_005.py` | `tests/unit/test_assertion_rewriter_phaseA_extra.py` |
| `test_assertion_rewriter_stage.py` | assertion rewriter stage | assertions; rewriter; stages; regex | `test_assertions_rewriter_stages_001.py` | `tests/unit/test_assertion_rewriter_stage.py` |
| `test_assertion_rewriter_stageA.py` | assertion rewriter stageA | assertions; rewriter; stages; regex | `test_assertions_rewriter_stages_002.py` | `tests/unit/test_assertion_rewriter_stageA.py` |
| `test_assertion_rewriter_various.py` | assertion rewriter various | assertions; rewriter; regex | `test_assertions_rewriter_regex_006.py` | `tests/unit/test_assertion_rewriter_various.py` |
| `test_assertions.py` | assertions | assertions | `test_assertions_001.py` | `tests/unit/test_assertions.py` |
| `test_assertions_and_fixtures.py` | assertions and fixtures | fixtures; assertions; regex | `test_fixtures_assertions_regex_001.py` | `tests/unit/test_assertions_and_fixtures.py` |
| `test_assertions_edgecases_extra.py` | assertions edgecases extra | assertions | `test_assertions_002.py` | `tests/unit/test_assertions_edgecases_extra.py` |
| `test_assertions_helpers.py` | assertions helpers | assertions | `test_assertions_003.py` | `tests/unit/test_assertions_helpers.py` |
| `test_assertions_helpers_extra.py` | assertions helpers extra | assertions | `test_assertions_004.py` | `tests/unit/test_assertions_helpers_extra.py` |
| `test_attr_rewriter.py` | attr rewriter | rewriter; regex | `test_rewriter_regex_001.py` | `tests/unit/test_attr_rewriter.py` |
| `test_autouse_fixture_params.py` | autouse fixture params | fixtures; parameters; regex | `test_fixtures_parameters_regex_001.py` | `tests/unit/test_autouse_fixture_params.py` |
| `test_autouse_helper.py` | autouse helper | general | `test_general_003.py` | `tests/unit/test_autouse_helper.py` |
| `test_bundler_invoker.py` | bundler invoker | bundles | `test_bundles_001.py` | `tests/unit/test_bundler_invoker.py` |
| `test_call_utils.py` | call utils | general | `test_general_004.py` | `tests/unit/test_call_utils.py` |
| `test_class_checks.py` | class checks | general | `test_general_005.py` | `tests/unit/test_class_checks.py` |
| `test_cleanup.py` | cleanup | general | `test_general_006.py` | `tests/unit/test_cleanup.py` |
| `test_cleanup_checks.py` | cleanup checks | general | `test_general_007.py` | `tests/unit/test_cleanup_checks.py` |
| `test_cleanup_checks_extra.py` | cleanup checks extra | general | `test_general_008.py` | `tests/unit/test_cleanup_checks_extra.py` |
| `test_cleanup_helpers.py` | cleanup helpers | general | `test_general_009.py` | `tests/unit/test_cleanup_helpers.py` |
| `test_cleanup_helpers_extra.py` | cleanup helpers extra | general | `test_general_010.py` | `tests/unit/test_cleanup_helpers_extra.py` |
| `test_cleanup_inspect.py` | cleanup inspect | general | `test_general_011.py` | `tests/unit/test_cleanup_inspect.py` |
| `test_cleanup_inspect_extra.py` | cleanup inspect extra | general | `test_general_012.py` | `tests/unit/test_cleanup_inspect_extra.py` |
| `test_cli.py` | cli | cli | `test_cli_001.py` | `tests/unit/test_cli.py` |
| `test_cli_strict_mode.py` | cli strict mode | cli | `test_cli_002.py` | `tests/unit/test_cli_strict_mode.py` |
| `test_collector.py` | collector | general | `test_general_013.py` | `tests/unit/test_collector.py` |
| `test_configurable_api.py` | configurable api | general | `test_general_014.py` | `tests/unit/test_configurable_api.py` |
| `test_conversion_validation.py` | conversion validation | general | `test_general_015.py` | `tests/unit/test_conversion_validation.py` |
| `test_converter.py` | converter | converter | `test_converter_001.py` | `tests/unit/test_converter.py` |
| `test_converter_assertions.py` | converter assertions | converter; assertions | `test_converter_assertions_001.py` | `tests/unit/test_converter_assertions.py` |
| `test_converter_assertions_extra.py` | converter assertions extra | converter; assertions | `test_converter_assertions_002.py` | `tests/unit/test_converter_assertions_extra.py` |
| `test_converter_assertions_more.py` | converter assertions more | converter; assertions; regex | `test_converter_assertions_regex_001.py` | `tests/unit/test_converter_assertions_more.py` |
| `test_converter_cleanup.py` | converter cleanup | converter | `test_converter_002.py` | `tests/unit/test_converter_cleanup.py` |
| `test_converter_edgecases.py` | converter edgecases | converter | `test_converter_003.py` | `tests/unit/test_converter_edgecases.py` |
| `test_converter_fixture_builders.py` | converter fixture builders | converter; fixtures; regex | `test_converter_fixtures_regex_001.py` | `tests/unit/test_converter_fixture_builders.py` |
| `test_converter_fixtures.py` | converter fixtures | converter; fixtures; regex | `test_converter_fixtures_regex_002.py` | `tests/unit/test_converter_fixtures.py` |
| `test_converter_fixtures_deeper.py` | converter fixtures deeper | converter; fixtures; regex | `test_converter_fixtures_regex_003.py` | `tests/unit/test_converter_fixtures_deeper.py` |
| `test_converter_golden.py` | converter golden | converter; goldens | `test_converter_goldens_001.py` | `tests/unit/test_converter_golden.py` |
| `test_converter_golden_strict.py` | converter golden (strict) | converter; goldens | `test_converter_goldens_002.py` | `tests/unit/test_converter_golden_strict.py` |
| `test_converter_goldens_strict.py` | converter goldens strict | converter; goldens | `test_converter_goldens_003.py` | `tests/unit/test_converter_goldens_strict.py` |
| `test_converter_helpers.py` | converter helpers | converter | `test_converter_004.py` | `tests/unit/test_converter_helpers.py` |
| `test_converter_helpers_and_imports.py` | converter helpers and imports | converter; imports | `test_converter_imports_001.py` | `tests/unit/test_converter_helpers_and_imports.py` |
| `test_converter_helpers_imports_more2.py` | converter helpers imports more2 | converter; imports; regex | `test_converter_imports_regex_001.py` | `tests/unit/test_converter_helpers_imports_more2.py` |
| `test_converter_helpers_imports_params.py` | converter helpers imports params | converter; imports; parameters | `test_converter_imports_parameters_001.py` | `tests/unit/test_converter_helpers_imports_params.py` |
| `test_converter_imports.py` | converter imports | converter; imports | `test_converter_imports_002.py` | `tests/unit/test_converter_imports.py` |
| `test_converter_imports_edgecases.py` | converter imports edgecases | converter; imports | `test_converter_imports_003.py` | `tests/unit/test_converter_imports_edgecases.py` |
| `test_converter_improvements.py` | converter improvements | converter | `test_converter_005.py` | `tests/unit/test_converter_improvements.py` |
| `test_converter_method_params.py` | converter method params | converter; parameters | `test_converter_parameters_001.py` | `tests/unit/test_converter_method_params.py` |
| `test_converter_method_params_and_helpers.py` | converter method params and helpers | converter; parameters | `test_converter_parameters_002.py` | `tests/unit/test_converter_method_params_and_helpers.py` |
| `test_converter_more.py` | converter more | converter; regex | `test_converter_regex_001.py` | `tests/unit/test_converter_more.py` |
| `test_converter_name_imports_params_more.py` | converter name imports params more | converter; imports; naming; parameters; regex | `test_converter_imports_naming_001.py` | `tests/unit/test_converter_name_imports_params_more.py` |
| `test_converter_params.py` | converter params | converter; parameters | `test_converter_parameters_003.py` | `tests/unit/test_converter_params.py` |
| `test_converter_public_api.py` | converter public api | converter | `test_converter_006.py` | `tests/unit/test_converter_public_api.py` |
| `test_converter_public_api_extra.py` | converter public api extra | converter | `test_converter_007.py` | `tests/unit/test_converter_public_api_extra.py` |
| `test_converter_raises.py` | converter raises | converter; exceptions | `test_converter_exceptions_001.py` | `tests/unit/test_converter_raises.py` |
| `test_converter_small.py` | converter small | converter | `test_converter_008.py` | `tests/unit/test_converter_small.py` |
| `test_converter_with_helpers.py` | converter with helpers | converter | `test_converter_009.py` | `tests/unit/test_converter_with_helpers.py` |
| `test_core.py` | core | regex | `test_regex_003.py` | `tests/unit/test_core.py` |
| `test_decorator_and_mock_fixes.py` | decorator and mock fixes | mocks | `test_mocks_001.py` | `tests/unit/test_decorator_and_mock_fixes.py` |
| `test_decorator_factory_and_expectedfailure.py` | decorator factory and expectedfailure | regex | `test_regex_004.py` | `tests/unit/test_decorator_factory_and_expectedfailure.py` |
| `test_decorators.py` | decorators | general | `test_general_016.py` | `tests/unit/test_decorators.py` |
| `test_decorators_and_manager.py` | decorators and manager | manager | `test_manager_001.py` | `tests/unit/test_decorators_and_manager.py` |
| `test_diagnostics.py` | diagnostics | diagnostics | `test_diagnostics_001.py` | `tests/unit/test_diagnostics.py` |
| `test_diagnostics_logging.py` | diagnostics logging | diagnostics | `test_diagnostics_002.py` | `tests/unit/test_diagnostics_logging.py` |
| `test_diagnostics_root_override.py` | diagnostics root override | diagnostics | `test_diagnostics_003.py` | `tests/unit/test_diagnostics_root_override.py` |
| `test_exceptioninfo_additional_cases.py` | exceptioninfo additional cases | exceptions | `test_exceptions_001.py` | `tests/unit/test_exceptioninfo_additional_cases.py` |
| `test_exceptioninfo_conversion_regression.py` | exceptioninfo conversion regression | exceptions; regex | `test_exceptions_regex_001.py` | `tests/unit/test_exceptioninfo_conversion_regression.py` |
| `test_filename_attr_replace.py` | filename attr replace | naming; regex | `test_naming_regex_001.py` | `tests/unit/test_filename_attr_replace.py` |
| `test_filename_inferer.py` | filename inferer | naming; regex | `test_naming_regex_002.py` | `tests/unit/test_filename_inferer.py` |
| `test_fix_init_api_conversion.py` | fix init api conversion | general | `test_general_017.py` | `tests/unit/test_fix_init_api_conversion.py` |
| `test_fix_init_api_rhs_preservation.py` | fix init api rhs preservation | regex | `test_regex_005.py` | `tests/unit/test_fix_init_api_rhs_preservation.py` |
| `test_fixture_body.py` | fixture body | fixtures; regex | `test_fixtures_regex_001.py` | `tests/unit/test_fixture_body.py` |
| `test_fixture_builder.py` | fixture builder | fixtures; regex | `test_fixtures_regex_002.py` | `tests/unit/test_fixture_builder.py` |
| `test_fixture_builder_guard.py` | fixture builder guard | fixtures; regex | `test_fixtures_regex_003.py` | `tests/unit/test_fixture_builder_guard.py` |
| `test_fixture_builders.py` | fixture builders | fixtures; regex | `test_fixtures_regex_004.py` | `tests/unit/test_fixture_builders.py` |
| `test_fixture_builders_extra.py` | fixture builders extra | fixtures; regex | `test_fixtures_regex_005.py` | `tests/unit/test_fixture_builders_extra.py` |
| `test_fixture_dependency_detection.py` | fixture dependency detection | fixtures; regex | `test_fixtures_regex_006.py` | `tests/unit/test_fixture_dependency_detection.py` |
| `test_fixture_dependency_detection_attribute_and_subscript.py` | fixture dependency detection attribute and subscript | fixtures; regex | `test_fixtures_regex_007.py` | `tests/unit/test_fixture_dependency_detection_attribute_and_subscript.py` |
| `test_fixture_dependency_detection_more_patterns.py` | fixture dependency detection more patterns | fixtures; regex | `test_fixtures_regex_008.py` | `tests/unit/test_fixture_dependency_detection_more_patterns.py` |
| `test_fixture_function.py` | fixture function | fixtures; regex | `test_fixtures_regex_009.py` | `tests/unit/test_fixture_function.py` |
| `test_fixture_guard_and_autocreate.py` | fixture guard and autocreate | fixtures; regex | `test_fixtures_regex_010.py` | `tests/unit/test_fixture_guard_and_autocreate.py` |
| `test_fixture_injector.py` | fixture injector | fixtures; regex | `test_fixtures_regex_011.py` | `tests/unit/test_fixture_injector.py` |
| `test_fixture_injector_stage.py` | fixture injector stage | fixtures; stages; regex | `test_fixtures_stages_regex_001.py` | `tests/unit/test_fixture_injector_stage.py` |
| `test_fixture_spacing.py` | fixture spacing | fixtures; regex | `test_fixtures_regex_012.py` | `tests/unit/test_fixture_spacing.py` |
| `test_fixtures_edgecases.py` | fixtures edgecases | fixtures; regex | `test_fixtures_regex_013.py` | `tests/unit/test_fixtures_edgecases.py` |
| `test_fixtures_extra.py` | fixtures extra | fixtures; regex | `test_fixtures_regex_014.py` | `tests/unit/test_fixtures_extra.py` |
| `test_fixtures_helpers.py` | fixtures helpers | fixtures; regex | `test_fixtures_regex_015.py` | `tests/unit/test_fixtures_helpers.py` |
| `test_flexible_parameters.py` | flexible parameters | parameters | `test_parameters_001.py` | `tests/unit/test_flexible_parameters.py` |
| `test_generator.py` | generator | generator | `test_generator_001.py` | `tests/unit/test_generator.py` |
| `test_generator_bundle_namedtuple.py` | generator bundle namedtuple | generator; naming; bundles | `test_generator_naming_bundles_001.py` | `tests/unit/test_generator_bundle_namedtuple.py` |
| `test_generator_composite_missing_teardown.py` | generator composite missing teardown | generator; teardown | `test_generator_teardown_001.py` | `tests/unit/test_generator_composite_missing_teardown.py` |
| `test_generator_composite_naming_collision.py` | generator composite naming collision | generator; naming | `test_generator_naming_001.py` | `tests/unit/test_generator_composite_naming_collision.py` |
| `test_generator_composite_three_tuple.py` | generator composite three tuple | generator; regex | `test_generator_regex_001.py` | `tests/unit/test_generator_composite_three_tuple.py` |
| `test_generator_core_finalize.py` | generator core finalize | generator; regex | `test_generator_regex_002.py` | `tests/unit/test_generator_core_finalize.py` |
| `test_generator_edgecases.py` | generator edgecases | generator | `test_generator_002.py` | `tests/unit/test_generator_edgecases.py` |
| `test_generator_exact_annotations.py` | generator exact annotations | generator | `test_generator_003.py` | `tests/unit/test_generator_exact_annotations.py` |
| `test_generator_generator_extra.py` | generator generator extra | generator | `test_generator_004.py` | `tests/unit/test_generator_generator_extra.py` |
| `test_generator_inference.py` | generator inference | generator; regex | `test_generator_regex_003.py` | `tests/unit/test_generator_inference.py` |
| `test_generator_literal_inference.py` | generator literal inference | generator; literals; regex | `test_generator_literals_regex_001.py` | `tests/unit/test_generator_literal_inference.py` |
| `test_generator_nameconflict.py` | generator nameconflict | generator; naming | `test_generator_naming_002.py` | `tests/unit/test_generator_nameconflict.py` |
| `test_generator_naming.py` | generator naming | generator; naming | `test_generator_naming_003.py` | `tests/unit/test_generator_naming.py` |
| `test_generator_nested_inference.py` | generator nested inference | generator; regex | `test_generator_regex_004.py` | `tests/unit/test_generator_nested_inference.py` |
| `test_generator_parts_scaffold.py` | generator parts scaffold | generator | `test_generator_005.py` | `tests/unit/test_generator_parts_scaffold.py` |
| `test_generator_parts_small_helpers.py` | generator parts small helpers | generator | `test_generator_006.py` | `tests/unit/test_generator_parts_small_helpers.py` |
| `test_generator_parts_trancheA.py` | generator parts trancheA | generator; tranches | `test_generator_tranches_001.py` | `tests/unit/test_generator_parts_trancheA.py` |
| `test_generator_stage.py` | generator stage | generator; stages | `test_generator_stages_001.py` | `tests/unit/test_generator_stage.py` |
| `test_generator_stage_composite.py` | generator stage composite | generator; stages | `test_generator_stages_002.py` | `tests/unit/test_generator_stage_composite.py` |
| `test_generator_stage_migrated.py` | generator stage migrated | generator; stages | `test_generator_stages_003.py` | `tests/unit/test_generator_stage_migrated.py` |
| `test_generator_v2.py` | generator v2 | generator | `test_generator_007.py` | `tests/unit/test_generator_v2.py` |
| `test_generator_v2_extra.py` | generator v2 extra | generator | `test_generator_008.py` | `tests/unit/test_generator_v2_extra.py` |
| `test_helpers.py` | helpers | general | `test_general_018.py` | `tests/unit/test_helpers.py` |
| `test_import_and_discovery.py` | import and discovery | imports | `test_imports_001.py` | `tests/unit/test_import_and_discovery.py` |
| `test_import_injection.py` | import injection | imports | `test_imports_002.py` | `tests/unit/test_import_injection.py` |
| `test_import_injector.py` | import injector | imports | `test_imports_003.py` | `tests/unit/test_import_injector.py` |
| `test_import_injector_stage.py` | import injector stage | imports; stages | `test_imports_stages_001.py` | `tests/unit/test_import_injector_stage.py` |
| `test_imports.py` | imports | imports | `test_imports_004.py` | `tests/unit/test_imports.py` |
| `test_imports_helpers.py` | imports helpers | imports | `test_imports_005.py` | `tests/unit/test_imports_helpers.py` |
| `test_known_bad_mapping.py` | known bad mapping | general | `test_general_019.py` | `tests/unit/test_known_bad_mapping.py` |
| `test_literals.py` | literals | literals | `test_literals_001.py` | `tests/unit/test_literals.py` |
| `test_main.py` | main | main | `test_main_001.py` | `tests/unit/test_main.py` |
| `test_main_api.py` | main api | main | `test_main_002.py` | `tests/unit/test_main_api.py` |
| `test_main_guard_removal.py` | main guard removal | main; regex | `test_main_regex_001.py` | `tests/unit/test_main_guard_removal.py` |
| `test_main_module.py` | main module | main | `test_main_003.py` | `tests/unit/test_main_module.py` |
| `test_main_patternconfig.py` | main patternconfig | main | `test_main_004.py` | `tests/unit/test_main_patternconfig.py` |
| `test_manager.py` | manager | manager | `test_manager_002.py` | `tests/unit/test_manager.py` |
| `test_manager_diagnostics.py` | manager diagnostics | diagnostics; manager | `test_diagnostics_manager_001.py` | `tests/unit/test_manager_diagnostics.py` |
| `test_manager_diagnostics_extra.py` | manager diagnostics extra | diagnostics; manager | `test_diagnostics_manager_002.py` | `tests/unit/test_manager_diagnostics_extra.py` |
| `test_manager_register_snapshotting_extra.py` | manager register snapshotting extra | manager; regex | `test_manager_regex_001.py` | `tests/unit/test_manager_register_snapshotting_extra.py` |
| `test_method_params.py` | method params | parameters | `test_parameters_002.py` | `tests/unit/test_method_params.py` |
| `test_method_patterns.py` | method patterns | general | `test_general_020.py` | `tests/unit/test_method_patterns.py` |
| `test_mock_aliasing.py` | mock aliasing | mocks | `test_mocks_002.py` | `tests/unit/test_mock_aliasing.py` |
| `test_mock_star_and_aliases_rewrite.py` | mock star and aliases rewrite | mocks; regex | `test_mocks_regex_001.py` | `tests/unit/test_mock_star_and_aliases_rewrite.py` |
| `test_module_level_names.py` | module level names | naming | `test_naming_001.py` | `tests/unit/test_module_level_names.py` |
| `test_more_assertions_fixtures_pipeline.py` | more assertions fixtures pipeline | fixtures; assertions; pipeline; regex | `test_fixtures_assertions_pipeline_001.py` | `tests/unit/test_more_assertions_fixtures_pipeline.py` |
| `test_name_allocator.py` | name allocator | naming | `test_naming_002.py` | `tests/unit/test_name_allocator.py` |
| `test_name_replacer.py` | name replacer | naming; regex | `test_naming_regex_003.py` | `tests/unit/test_name_replacer.py` |
| `test_new_data_variants.py` | new data variants | general | `test_general_021.py` | `tests/unit/test_new_data_variants.py` |
| `test_params_append.py` | params append | parameters | `test_parameters_003.py` | `tests/unit/test_params_append.py` |
| `test_patch_complex_targets_rewrite.py` | patch complex targets rewrite | patch; regex | `test_patch_regex_001.py` | `tests/unit/test_patch_complex_targets_rewrite.py` |
| `test_pipeline.py` | pipeline | pipeline | `test_pipeline_001.py` | `tests/unit/test_pipeline.py` |
| `test_placement_helpers.py` | placement helpers | general | `test_general_022.py` | `tests/unit/test_placement_helpers.py` |
| `test_postvalidator.py` | postvalidator | validation | `test_validation_001.py` | `tests/unit/test_postvalidator.py` |
| `test_postvalidator_stage.py` | postvalidator stage | stages; validation | `test_stages_validation_001.py` | `tests/unit/test_postvalidator_stage.py` |
| `test_print_diagnostics.py` | print diagnostics | diagnostics | `test_diagnostics_004.py` | `tests/unit/test_print_diagnostics.py` |
| `test_public_api_converter_and_assertion_rewriter.py` | public api converter and assertion rewriter | converter; assertions; rewriter; regex | `test_converter_assertions_rewriter_001.py` | `tests/unit/test_public_api_converter_and_assertion_rewriter.py` |
| `test_public_api_converter_more.py` | public api converter more | converter; regex | `test_converter_regex_002.py` | `tests/unit/test_public_api_converter_more.py` |
| `test_public_api_smoke.py` | public api smoke | smoke | `test_smoke_001.py` | `tests/unit/test_public_api_smoke.py` |
| `test_raises.py` | raises | exceptions | `test_exceptions_002.py` | `tests/unit/test_raises.py` |
| `test_raises_exceptioninfo_value.py` | raises exceptioninfo value | exceptions; validation | `test_exceptions_validation_001.py` | `tests/unit/test_raises_exceptioninfo_value.py` |
| `test_raises_stage.py` | raises stage | stages; exceptions | `test_stages_exceptions_001.py` | `tests/unit/test_raises_stage.py` |
| `test_re_import_injection.py` | re import injection | imports; regex | `test_imports_regex_001.py` | `tests/unit/test_re_import_injection.py` |
| `test_references_attr.py` | references attr | regex | `test_regex_006.py` | `tests/unit/test_references_attr.py` |
| `test_regress_name_collision.py` | regress name collision | naming; regex | `test_naming_regex_004.py` | `tests/unit/test_regress_name_collision.py` |
| `test_remaining_assertions_fixtures_and_e2e.py` | remaining assertions fixtures and e2e | fixtures; assertions; main; regex | `test_fixtures_assertions_main_001.py` | `tests/unit/test_remaining_assertions_fixtures_and_e2e.py` |
| `test_replace_self_param.py` | replace self param | regex | `test_regex_007.py` | `tests/unit/test_replace_self_param.py` |
| `test_rewriter.py` | rewriter | rewriter; regex | `test_rewriter_regex_002.py` | `tests/unit/test_rewriter.py` |
| `test_rewriter_self_param.py` | rewriter self param | rewriter; regex | `test_rewriter_regex_003.py` | `tests/unit/test_rewriter_self_param.py` |
| `test_rewriter_stage.py` | rewriter stage | rewriter; stages; regex | `test_rewriter_stages_regex_001.py` | `tests/unit/test_rewriter_stage.py` |
| `test_self_attr_finder.py` | self attr finder | general | `test_general_023.py` | `tests/unit/test_self_attr_finder.py` |
| `test_setup_parser.py` | setup parser | general | `test_general_024.py` | `tests/unit/test_setup_parser.py` |
| `test_shutil_detector.py` | shutil detector | general | `test_general_025.py` | `tests/unit/test_shutil_detector.py` |
| `test_simple_fixture.py` | simple fixture | fixtures; regex | `test_fixtures_regex_016.py` | `tests/unit/test_simple_fixture.py` |
| `test_simple_fixture_and_injector.py` | simple fixture and injector | fixtures; regex | `test_fixtures_regex_017.py` | `tests/unit/test_simple_fixture_and_injector.py` |
| `test_smoke_tranche1.py` | smoke tranche1 | smoke; tranches | `test_smoke_tranches_001.py` | `tests/unit/test_smoke_tranche1.py` |
| `test_smoke_tranche2.py` | smoke tranche2 | smoke; tranches | `test_smoke_tranches_002.py` | `tests/unit/test_smoke_tranche2.py` |
| `test_smoke_tranche3.py` | smoke tranche3 | smoke; tranches | `test_smoke_tranches_003.py` | `tests/unit/test_smoke_tranche3.py` |
| `test_stage_manager_diagnostics.py` | stage manager diagnostics | diagnostics; manager; stages | `test_diagnostics_manager_stages_001.py` | `tests/unit/test_stage_manager_diagnostics.py` |
| `test_stages_assertion_rewriter.py` | stages assertion rewriter | assertions; rewriter; stages; regex | `test_assertions_rewriter_stages_003.py` | `tests/unit/test_stages_assertion_rewriter.py` |
| `test_stages_assertion_rewriter_batch2.py` | stages assertion rewriter batch2 | assertions; rewriter; stages; regex | `test_assertions_rewriter_stages_004.py` | `tests/unit/test_stages_assertion_rewriter_batch2.py` |
| `test_stages_assertion_rewriter_batch3.py` | stages assertion rewriter batch3 | assertions; rewriter; stages; regex | `test_assertions_rewriter_stages_005.py` | `tests/unit/test_stages_assertion_rewriter_batch3.py` |
| `test_stages_assertion_rewriter_batch4.py` | stages assertion rewriter batch4 | assertions; rewriter; stages; regex | `test_assertions_rewriter_stages_006.py` | `tests/unit/test_stages_assertion_rewriter_batch4.py` |
| `test_stages_assertion_rewriter_more.py` | stages assertion rewriter more | assertions; rewriter; stages; regex | `test_assertions_rewriter_stages_007.py` | `tests/unit/test_stages_assertion_rewriter_more.py` |
| `test_stages_formatting_helpers.py` | stages formatting helpers | stages | `test_stages_001.py` | `tests/unit/test_stages_formatting_helpers.py` |
| `test_stages_formatting_stage2.py` | stages formatting stage2 | stages | `test_stages_002.py` | `tests/unit/test_stages_formatting_stage2.py` |
| `test_stages_generator.py` | stages generator | generator; stages | `test_generator_stages_004.py` | `tests/unit/test_stages_generator.py` |
| `test_stages_generator_helpers.py` | stages generator helpers | generator; stages | `test_generator_stages_005.py` | `tests/unit/test_stages_generator_helpers.py` |
| `test_stages_generator_phaseA.py` | stages generator phaseA | generator; stages | `test_generator_stages_006.py` | `tests/unit/test_stages_generator_phaseA.py` |
| `test_stages_generator_stage2.py` | stages generator stage2 | generator; stages | `test_generator_stages_007.py` | `tests/unit/test_stages_generator_stage2.py` |
| `test_stages_injectors.py` | stages injectors | stages | `test_stages_003.py` | `tests/unit/test_stages_injectors.py` |
| `test_stages_manager.py` | stages manager | manager; stages | `test_manager_stages_001.py` | `tests/unit/test_stages_manager.py` |
| `test_stages_manager_diagnostics.py` | stages manager diagnostics | diagnostics; manager; stages | `test_diagnostics_manager_stages_002.py` | `tests/unit/test_stages_manager_diagnostics.py` |
| `test_stages_raises_rewriter.py` | stages raises rewriter | rewriter; stages; exceptions; regex | `test_rewriter_stages_exceptions_001.py` | `tests/unit/test_stages_raises_rewriter.py` |
| `test_teardown_helpers.py` | teardown helpers | teardown | `test_teardown_001.py` | `tests/unit/test_teardown_helpers.py` |
| `test_tidy.py` | tidy | tidy | `test_tidy_001.py` | `tests/unit/test_tidy.py` |
| `test_tools_print_diagnostics.py` | tools print diagnostics | diagnostics | `test_diagnostics_005.py` | `tests/unit/test_tools_print_diagnostics.py` |
| `test_tranche10_printdiag_generatorparts.py` | tranche10 printdiag generatorparts | generator; tranches | `test_generator_tranches_002.py` | `tests/unit/test_tranche10_printdiag_generatorparts.py` |
| `test_tranche4.py` | tranche4 | tranches | `test_tranches_001.py` | `tests/unit/test_tranche4.py` |
| `test_tranche5_manager_callutils.py` | tranche5 manager callutils | manager; tranches | `test_manager_tranches_001.py` | `tests/unit/test_tranche5_manager_callutils.py` |
| `test_tranche6_diag_manager.py` | tranche6 diag manager | manager; tranches | `test_manager_tranches_002.py` | `tests/unit/test_tranche6_diag_manager.py` |
| `test_tranche7_manager_callutils_more.py` | tranche7 manager callutils more | manager; tranches; regex | `test_manager_tranches_regex_001.py` | `tests/unit/test_tranche7_manager_callutils_more.py` |
| `test_tranche8_manager_diag_more.py` | tranche8 manager diag more | manager; tranches; regex | `test_manager_tranches_regex_002.py` | `tests/unit/test_tranche8_manager_diag_more.py` |
| `test_tranche9_diag_manager_exceptions.py` | tranche9 diag manager exceptions | manager; exceptions; tranches | `test_manager_exceptions_tranches_001.py` | `tests/unit/test_tranche9_diag_manager_exceptions.py` |
| `test_transformer_and_manager_behaviour.py` | transformer and manager behaviour | manager; transform | `test_manager_transform_001.py` | `tests/unit/test_transformer_and_manager_behaviour.py` |
| `test_transformer_guard_fixture_emitted.py` | transformer guard fixture emitted | fixtures; transform; regex | `test_fixtures_transform_regex_001.py` | `tests/unit/test_transformer_guard_fixture_emitted.py` |
| `test_transformers.py` | transformers | transform | `test_transform_001.py` | `tests/unit/test_transformers.py` |
| `test_utils_and_cli_parsing.py` | utils and cli parsing | cli | `test_cli_003.py` | `tests/unit/test_utils_and_cli_parsing.py` |
| `test_value_checks.py` | value checks | validation | `test_validation_002.py` | `tests/unit/test_value_checks.py` |
| `test_with_helpers.py` | with helpers | general | `test_general_026.py` | `tests/unit/test_with_helpers.py` |

---

Notes and next steps
- The "Broad behavior/module" entries were inferred automatically from filenames and directory structure. Please review and refine any entries where the automatic inference is insufficient.
- If you'd like, I can enrich this document with a column linking to the source file (line numbers), or add a short one-line description extracted from each test file's docstring if present.
