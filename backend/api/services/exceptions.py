"""Typed exceptions raised by the services layer. Views (Phases 3-6) catch
these and map each to the appropriate HTTP status code — services stay
HTTP-agnostic and testable without a request/response cycle."""


class BallotingError(Exception):
    """Base for everything that can go wrong casting a ballot."""


class ElectionNotOpenError(BallotingError):
    pass


class NotEnrolledError(BallotingError):
    pass


class AlreadyVotedError(BallotingError):
    pass


class InvalidPositionError(BallotingError):
    pass


class InvalidSelectionError(BallotingError):
    pass


class EnrollmentError(Exception):
    """Base for roster-management failures."""


class HasBallotsError(EnrollmentError):
    pass


class ElectionServiceError(Exception):
    """Base for election lifecycle (publish/archive) failures."""


class PublishNotReadyError(ElectionServiceError):
    def __init__(self, reasons):
        self.reasons = list(reasons)
        super().__init__("; ".join(self.reasons))


class CsvImportError(Exception):
    """Base for voter CSV import failures."""


class CsvTooLargeError(CsvImportError):
    pass


class CsvEncodingError(CsvImportError):
    pass
