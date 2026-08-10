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


class ElectionLockedError(Exception):
    """Raised on an admin write attempted while election.status == published.
    Shared by add_position, register_candidate, and delete_candidate — all
    three enforce the same lock."""


class VoterNotFoundError(Exception):
    """No Voter matches the given student_number during candidate
    registration."""


class CandidateHasSelectionsError(Exception):
    """Raised when deleting a candidate who already has recorded votes —
    doing so would silently rewrite a tally."""


class ElectionHasBallotsError(Exception):
    """Raised when deleting an election that already has ballots. Kept
    separate from EnrollmentError's HasBallotsError — that one blocks
    clearing a roster, this one blocks deleting an election entirely."""


class CandidateAlreadyRegisteredError(Exception):
    """Raised when the same voter is already registered as a candidate for
    that position — Candidate's unique_together(election, voter, position)
    is the real defence against a double-submit race."""


class DuplicatePositionTitleError(Exception):
    """Raised when adding a position whose title already exists in that
    election — Position's unique_together(election, title) is the real
    defence against a double-submit race."""
