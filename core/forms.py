from django import forms

from .models import Lead


class LeadForm(forms.ModelForm):
    privacy_consent = forms.BooleanField(required=True)
    consent_version = forms.CharField(required=True)

    def __init__(self, *args, language="ru", **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["privacy_consent"].error_messages["required"] = (
            "Дербес деректерді жинауға және өңдеуге келісім қажет."
            if language == "kk" else "Подтвердите согласие на сбор и обработку персональных данных."
        )
        self.language = language

    def clean_consent_version(self):
        from .legal import LEGAL_VERSION
        if self.cleaned_data["consent_version"] != LEGAL_VERSION:
            raise forms.ValidationError(
                "Келісім жаңартылды. Бетті жаңартып, қайта оқыңыз."
                if self.language == "kk" else "Согласие обновилось. Обновите страницу и прочитайте его заново."
            )
        return LEGAL_VERSION

    class Meta:
        model = Lead
        fields = ["name", "phone", "plan"]
