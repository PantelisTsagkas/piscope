"""Exception hierarchy for the PiScope engine."""


class PiScopeError(Exception):
    """Base class for every error raised by the engine."""


class DatasetNotFoundError(PiScopeError):
    """No dataset manifest exists at the requested location."""


class DatasetIntegrityError(PiScopeError):
    """A manifest or chunk file is missing, malformed or fails its checksum."""


class PositionOutOfRangeError(PiScopeError, IndexError):
    """A requested digit position lies outside the available dataset."""


class GenerationError(PiScopeError):
    """Digit generation failed or produced a result that cannot be trusted."""


class VerificationError(PiScopeError):
    """Generated digits disagree with an independent reference."""


class InvalidPatternError(PiScopeError, ValueError):
    """A search pattern is empty or contains non-digit characters."""
