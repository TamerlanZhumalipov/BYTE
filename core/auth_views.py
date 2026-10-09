from django.contrib.auth.views import LoginView
from .frontend import render_page


class ReactLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

    def render_to_response(self, context, **response_kwargs):
        return render_page(self.request, self.template_name, context, **response_kwargs)
