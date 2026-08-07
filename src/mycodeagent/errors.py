"""Domain errors raised by MyCodeAgent."""


class MyCodeAgentError(Exception):
    """Base class for expected workflow failures."""


class ConfigurationError(MyCodeAgentError):
    """Runtime configuration is missing or invalid."""


class TaskParseError(MyCodeAgentError):
    """A task source cannot be converted into a valid task specification."""


class TaskNotFoundError(MyCodeAgentError):
    """The requested task does not exist."""


class ValidationError(MyCodeAgentError):
    """A deterministic validation gate rejected an artifact or transition."""


class AgentExecutionError(MyCodeAgentError):
    """Omnigent could not execute a configured agent role."""


class IterationLimitError(MyCodeAgentError):
    """A sixth implementation-test-review cycle was requested."""

