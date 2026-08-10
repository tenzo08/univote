from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from api.models import (
    Ballot,
    BallotSelection,
    Candidate,
    Election,
    ElectionEnrollment,
    Position,
    User,
    Voter,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = ("email", "username", "role", "must_change_password", "is_staff")
    list_filter = ("role", "must_change_password", "is_staff", "is_superuser")
    search_fields = ("email", "username", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Role", {"fields": ("role", "must_change_password")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "role", "password1", "password2"),
            },
        ),
    )


@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ("student_number", "user", "year_level", "degree_program")
    search_fields = ("student_number", "user__email", "user__first_name", "user__last_name")
    list_filter = ("year_level", "degree_program")


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "opens_at", "closes_at", "published_at")
    list_filter = ("status",)
    search_fields = ("title",)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("title", "election", "max_votes", "order")
    list_filter = ("election",)


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("voter", "position", "election", "created_at")
    list_filter = ("election", "position")
    search_fields = ("voter__student_number",)


@admin.register(ElectionEnrollment)
class ElectionEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("voter", "election", "enrolled_at")
    list_filter = ("election",)
    search_fields = ("voter__student_number",)


@admin.register(Ballot)
class BallotAdmin(admin.ModelAdmin):
    list_display = ("receipt_code", "election", "voter", "submitted_at")
    list_filter = ("election",)
    search_fields = ("receipt_code", "voter__student_number")


@admin.register(BallotSelection)
class BallotSelectionAdmin(admin.ModelAdmin):
    list_display = ("ballot", "position", "candidate")
    list_filter = ("position",)
