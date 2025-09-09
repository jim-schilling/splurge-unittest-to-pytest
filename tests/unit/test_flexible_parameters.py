"""Test the flexible parameter handling for different method types."""

from splurge_unittest_to_pytest.converter import UnittestToPytestTransformer


class TestFlexibleParameterHandling:
    """Test flexible parameter handling for different method types."""

    def test_instance_method_self_removal(self):
        """Test that instance methods with 'self' have self parameter removed."""
        transformer = UnittestToPytestTransformer()

        # Create a mock FunctionDef for an instance method
        func_def = self._create_function_def("test_method", ["self", "arg1"], [])
        
        new_params, new_body = transformer._remove_method_self_references(func_def)
        
        # Should remove 'self' parameter
        assert len(new_params) == 1
        assert new_params[0].name.value == "arg1"

    def test_classmethod_cls_removal(self):
        """Test that classmethods with 'cls' have cls parameter removed."""
        transformer = UnittestToPytestTransformer()

        # Create a mock FunctionDef for a classmethod
        func_def = self._create_function_def("test_method", ["cls", "arg1"], ["classmethod"])
        
        new_params, new_body = transformer._remove_method_self_references(func_def)
        
        # Should remove 'cls' parameter
        assert len(new_params) == 1
        assert new_params[0].name.value == "arg1"

    def test_staticmethod_no_removal(self):
        """Test that staticmethods don't have any parameters removed."""
        transformer = UnittestToPytestTransformer()

        # Create a mock FunctionDef for a staticmethod
        func_def = self._create_function_def("test_method", ["arg1", "arg2"], ["staticmethod"])
        
        new_params, new_body = transformer._remove_method_self_references(func_def)
        
        # Should not remove any parameters
        assert len(new_params) == 2
        assert new_params[0].name.value == "arg1"
        assert new_params[1].name.value == "arg2"

    def test_method_without_conventional_first_param(self):
        """Test methods that don't use 'self' or 'cls' as first parameter."""
        transformer = UnittestToPytestTransformer()

        # Create a mock FunctionDef with unconventional first parameter
        func_def = self._create_function_def("test_method", ["obj", "arg1"], [])
        
        new_params, new_body = transformer._remove_method_self_references(func_def)
        
        # Should not remove any parameters since first param is not 'self'
        assert len(new_params) == 2
        assert new_params[0].name.value == "obj"
        assert new_params[1].name.value == "arg1"

    def test_should_remove_first_param_logic(self):
        """Test the logic for determining if first parameter should be removed."""
        transformer = UnittestToPytestTransformer()

        # Instance method with 'self'
        func_def = self._create_function_def("test_method", ["self", "arg1"], [])
        assert transformer._should_remove_first_param(func_def) is True

        # Classmethod with 'cls'
        func_def = self._create_function_def("test_method", ["cls", "arg1"], ["classmethod"])
        assert transformer._should_remove_first_param(func_def) is True

        # Classmethod with different name
        func_def = self._create_function_def("test_method", ["klass", "arg1"], ["classmethod"])
        assert transformer._should_remove_first_param(func_def) is False

        # Staticmethod
        func_def = self._create_function_def("test_method", ["arg1", "arg2"], ["staticmethod"])
        assert transformer._should_remove_first_param(func_def) is False

        # No decorators, not 'self'
        func_def = self._create_function_def("test_method", ["obj", "arg1"], [])
        assert transformer._should_remove_first_param(func_def) is False

    def _create_function_def(self, name: str, params: list[str], decorators: list[str]):
        """Helper to create a mock FunctionDef for testing."""
        import libcst as cst
        
        # Create parameter nodes
        param_nodes = []
        for param_name in params:
            param_nodes.append(cst.Param(name=cst.Name(param_name)))
        
        # Create decorator nodes
        decorator_nodes = []
        for decorator_name in decorators:
            decorator_nodes.append(cst.Decorator(
                decorator=cst.Name(decorator_name)
            ))
        
        return cst.FunctionDef(
            name=cst.Name(name),
            params=cst.Parameters(params=param_nodes),
            body=cst.IndentedBlock(body=[]),
            decorators=decorator_nodes
        )
