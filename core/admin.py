from django import forms
from django.contrib import admin

from .models import (
    Contest, ContestAccount, ContestTask, Lead, Section, Submission, TaskTest,
)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "plan", "created_at")
    list_filter = ("plan",)
    search_fields = ("name", "phone")


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("title", "parent", "order", "is_published")
    list_editable = ("order", "is_published")
    list_filter = ("parent", "is_published")
    search_fields = ("title", "content")
    prepopulated_fields = {"slug": ("title",)}


class ContestTaskInline(admin.StackedInline):
    model = ContestTask
    extra = 0
    fields = ("order", "title", "time_limit", "statement")


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ("title", "starts_at", "duration_minutes")
    inlines = [ContestTaskInline]


@admin.register(ContestTask)
class ContestTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "contest", "order", "tests_count")
    list_filter = ("contest",)

    @admin.display(description="Тестов")
    def tests_count(self, obj):
        return obj.tests.count()


@admin.register(TaskTest)
class TaskTestAdmin(admin.ModelAdmin):
    list_display = ("task", "order", "short_input")
    list_filter = ("task",)
    raw_id_fields = ("task",)

    @admin.display(description="Вход")
    def short_input(self, obj):
        return obj.input_data[:60]


class ContestAccountForm(forms.ModelForm):
    new_password = forms.CharField(
        label="Пароль контеста",
        required=False,
        widget=forms.TextInput,
        help_text="Впишите пароль, который выдадите участнику. При редактировании "
                  "оставьте пустым, чтобы не менять текущий.",
    )

    class Meta:
        model = ContestAccount
        fields = ["contest", "full_name", "login", "is_active"]

    def clean_login(self):
        return self.cleaned_data["login"].strip().lower()

    def clean(self):
        cleaned = super().clean()
        if not self.instance.pk and not cleaned.get("new_password"):
            self.add_error("new_password", "Для нового участника нужно задать пароль.")
        return cleaned


@admin.register(ContestAccount)
class ContestAccountAdmin(admin.ModelAdmin):
    form = ContestAccountForm
    list_display = ("login", "full_name", "contest", "is_active")
    list_filter = ("contest", "is_active")
    search_fields = ("login", "full_name")

    def save_model(self, request, obj, form, change):
        password = form.cleaned_data.get("new_password")
        if password:
            obj.set_password(password)
        super().save_model(request, obj, form, change)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "account", "task", "language", "verdict", "passed", "total")
    list_filter = ("task__contest", "task", "verdict", "language")
    search_fields = ("account__login", "account__full_name")
    readonly_fields = [f.name for f in Submission._meta.fields]

    def has_add_permission(self, request):
        return False
