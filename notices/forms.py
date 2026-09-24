"""Formulário da publicação manual de notificações.

O formulário só declara e valida os campos da publicação; quem grava é a operação
do model. Ele também devolve os pares que a etapa de revisão reenvia, para que a
revisão não guarde nada no servidor.
"""

from django import forms

from accounts.models import Role, User
from notices import catalog
from notices.models import MESSAGE_MAX_LENGTH, TITLE_MAX_LENGTH, resolve_recipients
from ui.forms import GroupedCheckboxSelectMultiple


class UserChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f'{obj.name} ({obj.email})'


class NoticeForm(forms.Form):
    title = forms.CharField(
        label='Título da notificação',
        max_length=TITLE_MAX_LENGTH,
        help_text='Aparece em destaque no sino de cada destinatário.',
    )
    message = forms.CharField(
        label='Mensagem',
        max_length=MESSAGE_MAX_LENGTH,
        widget=forms.Textarea(attrs={'rows': 5, 'maxlength': MESSAGE_MAX_LENGTH}),
    )
    type = forms.ChoiceField(
        label='Tipo de notificação',
        choices=catalog.manual_choices,
        initial=catalog.INFORMATION,
        widget=forms.RadioSelect,
    )
    destination = forms.ChoiceField(
        label='Destinatários',
        choices=catalog.destination_choices,
        initial=catalog.ALL_USERS,
    )
    role = forms.ModelChoiceField(
        label='Perfil',
        queryset=Role.objects.order_by('name'),
        required=False,
        empty_label='Escolha o perfil',
        help_text='Usado quando os destinatários são os usuários de um perfil.',
    )
    users = UserChoiceField(
        label='Usuários',
        queryset=User.objects.filter(is_active=True).order_by('name'),
        required=False,
        help_text='Usado quando os destinatários são usuários específicos. Só usuários ativos aparecem aqui.',
        widget=GroupedCheckboxSelectMultiple(
            summary_label='usuários selecionados',
            search_label='Buscar usuário',
            empty_label='Nenhum usuário encontrado para a busca.',
            show_values=False,
        ),
    )

    def type_options(self):
        """Cada tipo do catálogo com a descrição que aparece no cartão de escolha."""
        return [
            {'field': option, 'description': catalog.description(option.data['value'])}
            for option in self['type']
        ]

    def clean(self):
        cleaned = super().clean()
        destination = cleaned.get('destination')
        if destination == catalog.ROLE and not cleaned.get('role'):
            self.add_error('role', 'Escolha o perfil que vai receber a notificação.')
        if destination == catalog.USERS and not cleaned.get('users'):
            self.add_error('users', 'Escolha pelo menos um usuário.')
        return cleaned

    def recipients(self):
        """Destinatários que a escolha alcança agora, para a contagem da revisão."""
        return resolve_recipients(
            self.cleaned_data['destination'],
            role=self.cleaned_data.get('role'),
            users=self.cleaned_data.get('users') or (),
        )

    def destination_label(self):
        return catalog.DESTINATION_LABELS.get(self.cleaned_data['destination'], '')

    def preview(self):
        """A notificação como o destinatário vai vê-la."""
        notice_type = self.cleaned_data['type']
        return {
            'title': self.cleaned_data['title'],
            'message': self.cleaned_data['message'],
            'icon': catalog.icon(notice_type),
            'tone': catalog.tone(notice_type),
            'label': catalog.label(notice_type),
        }

    def resubmit_values(self):
        """Pares de nome e valor que a revisão reenvia ao voltar e ao publicar."""
        data = self.cleaned_data
        values = [
            ('title', data['title']),
            ('message', data['message']),
            ('type', data['type']),
            ('destination', data['destination']),
        ]
        if data.get('role'):
            values.append(('role', data['role'].pk))
        values.extend(('users', user.pk) for user in data.get('users') or [])
        return values
