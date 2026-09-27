"""Contraste WCAG 2.x dos pares de cores da interface (D6).

Os valores vêm do ui/styles/app.css: as variáveis --palette-* e os tokens
--color-*, que apontam para a paleta com var(). O símbolo do IF não é token, e o
verde dele entra como valor literal, tirado dos arquivos oficiais (D3).
"""

import re
from pathlib import Path

STYLES = Path(__file__).resolve().parent / 'styles' / 'app.css'

SYMBOL_GREEN = '#309F41'

CONTRAST_PAIRS = [
    ('text', 'page', 4.5, 'Texto principal sobre a página'),
    ('text', 'surface', 4.5, 'Texto principal sobre a superfície'),
    ('text-muted', 'surface', 4.5, 'Texto secundário e placeholder sobre a superfície'),
    ('text-muted', 'page', 4.5, 'Texto secundário e cabeçalho de tabela sobre a página'),
    ('text-muted', 'hover', 4.5, 'Contador'),
    ('control-border', 'surface', 3, 'Borda de controle sobre a superfície'),
    ('text-muted', 'surface', 3, 'Ícone de ação sobre a superfície'),
    ('text', 'hover', 3, 'Ícone de ação no hover'),
    ('on-tooltip', 'tooltip', 4.5, 'Dica do botão de ícone'),
    ('on-fill', 'action', 4.5, 'Botão primário e link atual da navegação'),
    ('on-fill', 'action-hover', 4.5, 'Botão primário no hover'),
    ('action', 'surface', 4.5, 'Link sobre a superfície'),
    ('focus', 'surface', 3, 'Contorno de foco sobre a superfície'),
    ('focus', 'page', 3, 'Contorno de foco sobre a página'),
    ('action', 'page', 4.5, 'Contagem de permissões selecionadas'),
    ('warning-text', 'page', 4.5, 'Aviso de alterações não salvas'),
    ('on-fill', 'danger', 4.5, 'Botão destrutivo'),
    ('on-fill', 'danger-hover', 4.5, 'Botão destrutivo no hover'),
    ('danger', 'surface', 4.5, 'Ação destrutiva do menu e erro de campo'),
    ('error-border', 'surface', 3, 'Borda de campo com erro'),
    ('on-sidebar', 'sidebar', 4.5, 'Texto da barra lateral'),
    ('on-sidebar', 'sidebar-hover', 4.5, 'Texto da barra lateral no hover'),
    ('on-sidebar-muted', 'sidebar', 4.5, 'Rótulo de seção e campus na barra lateral'),
    ('sidebar-accent', 'sidebar', 3, 'Ícone da navegação'),
    ('sidebar-accent', 'sidebar-hover', 3, 'Ícone da navegação no hover'),
    (SYMBOL_GREEN, 'sidebar', 3, 'Verde do símbolo do IF sobre a barra lateral'),
    ('focus', 'sidebar', 3, 'Contorno de foco sobre a barra lateral'),
    ('on-sidebar-muted', 'sidebar', 3, 'Borda do botão Menu na barra do celular'),
    ('avatar-text', 'avatar-bg', 4.5, 'Avatar de iniciais'),
    ('avatar-text', 'surface', 4.5, 'Avatar de iniciais no rodapé da barra lateral'),
    ('on-brand', 'brand-surface', 4.5, 'Texto do painel do login'),
    ('on-brand-muted', 'brand-surface', 4.5, 'Texto secundário do painel do login'),
    ('success-text', 'success-bg', 4.5, 'Texto de sucesso'),
    ('success-icon', 'success-bg', 3, 'Ícone de sucesso'),
    ('warning-text', 'warning-bg', 4.5, 'Texto de aviso'),
    ('warning-icon', 'warning-bg', 3, 'Ícone de aviso'),
    ('error-text', 'error-bg', 4.5, 'Texto de erro'),
    ('error-icon', 'error-bg', 3, 'Ícone de erro'),
    ('info-text', 'info-bg', 4.5, 'Texto de informação'),
    ('info-icon', 'info-bg', 3, 'Ícone de informação'),
    ('text', 'stage-undergraduate-bg', 4.5, 'Disciplina no card da graduação na Grade'),
    ('text-muted', 'stage-undergraduate-bg', 4.5, 'Docente no card da graduação na Grade'),
    ('stage-undergraduate-bar', 'stage-undergraduate-bg', 3, 'Barra da etapa no card da graduação'),
    ('text', 'stage-secondary-bg', 4.5, 'Disciplina no card do ensino médio na Grade'),
    ('text-muted', 'stage-secondary-bg', 4.5, 'Docente no card do ensino médio na Grade'),
    ('stage-secondary-bar', 'stage-secondary-bg', 3, 'Barra da etapa no card do ensino médio'),
    ('text', 'booking-bg', 4.5, 'Descrição no card do agendamento na Grade'),
    ('text-muted', 'booking-bg', 4.5, 'Horário no card do agendamento na Grade'),
    ('booking-text', 'booking-bg', 4.5, 'Rótulo do tipo no card do agendamento na Grade'),
    ('booking-bar', 'booking-bg', 3, 'Barra e ícone do card do agendamento na Grade'),
    ('text', 'info-bg', 4.5, 'Descrição no card do agendamento na Agenda'),
    ('text-muted', 'info-bg', 4.5, 'Solicitante no card do agendamento na Agenda'),
    ('stage-undergraduate-bar', 'surface', 3, 'Marca da graduação na legenda da Grade'),
    ('stage-secondary-bar', 'surface', 3, 'Marca do ensino médio na legenda da Grade'),
]

EXEMPT = {
    'divider': 'Borda decorativa de cartões, linhas de tabela e rodapés.',
    'sidebar-border': 'Borda decorativa da barra lateral.',
    'success-border': 'Borda decorativa: o estado vem do texto e do ícone.',
    'warning-border': 'Borda decorativa: o estado vem do texto e do ícone.',
    'error-soft-border': 'Borda decorativa: o estado vem do texto e do ícone.',
    'info-border': 'Borda decorativa: o estado vem do texto e do ícone.',
    'booking-border': 'Borda decorativa do card do agendamento: o tipo vem do rótulo e do ícone.',
    'overlay': 'Fundo atrás do modal. O conteúdo do modal fica sobre a superfície.',
}

HEX = re.compile(r'#[0-9A-Fa-f]{6}')


def read_colors(css):
    """Devolve {token: hexadecimal} dos tokens --color-* do CSS.

    Um token cujo valor não é hexadecimal nem var() da paleta, como o overlay com
    transparência, fica com None.
    """
    palette = dict(re.findall(r'--palette-([\w-]+):\s*(#[0-9A-Fa-f]{6})\s*;', css))
    colors = {}
    for name, value in re.findall(r'--color-([\w-]+):\s*([^;]+);', css):
        value = value.strip()
        reference = re.fullmatch(r'var\(--palette-([\w-]+)\)', value)
        if reference:
            colors[name] = palette[reference.group(1)]
        elif HEX.fullmatch(value):
            colors[name] = value
        else:
            colors[name] = None
    return colors


def luminance(color):
    channels = []
    for index in (1, 3, 5):
        value = int(color[index:index + 2], 16) / 255
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground, background):
    lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def format_ratio(ratio):
    return f'{ratio:.2f}'.replace('.', ',')


def contrast_failures(css):
    """Pares abaixo do mínimo, com o par, o contraste calculado e o mínimo."""
    colors = read_colors(css)
    failures = []
    for foreground, background, minimum, description in CONTRAST_PAIRS:
        front = foreground if foreground.startswith('#') else colors[foreground]
        back = colors[background]
        ratio = contrast_ratio(front, back)
        if ratio < minimum:
            failures.append(
                f'{description} ({foreground} {front} sobre {background} {back}): '
                f'{format_ratio(ratio)}:1, mínimo {format_ratio(minimum)}:1',
            )
    return failures


def uncovered_tokens(css):
    """Tokens de cor que não estão em nenhum par nem na lista de isentos."""
    covered = {token for pair in CONTRAST_PAIRS for token in pair[:2]} | EXEMPT.keys()
    return sorted(set(read_colors(css)) - covered)
