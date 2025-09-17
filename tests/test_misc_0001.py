import warnings


def pytest_configure(config):
    warnings.filterwarnings("ignore", message="\\\"is not\\\" with 'int' literal", category=SyntaxWarning)
    warnings.filterwarnings("ignore", category=SyntaxWarning)
