from django.views.generic import TemplateView

from tutorials.catalog import entries_for, guide_for, menu_item_of, screen_for


class HelpCenterView(TemplateView):
    """Ajuda da tela de origem (`?tela=`) ou a central completa; o que não é liberado nem chega ao template."""

    template_name = 'tutorials/help_center.html'

    def get_context_data(self, **kwargs):
        user = self.request.user
        screen = screen_for(self.request.GET.get('tela', ''))
        if screen is None:
            return super().get_context_data(modules=guide_for(user), **kwargs)
        item = menu_item_of(screen)
        entries = entries_for(user, screen.features)
        return super().get_context_data(
            screen=screen,
            screen_label=item.label,
            screen_url=item.url_for(user),
            entries=entries,
            nav_groups=[{'label': '', 'features': entries}],
            **kwargs,
        )
