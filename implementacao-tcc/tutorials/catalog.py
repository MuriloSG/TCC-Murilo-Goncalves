"""Conteúdo da central de ajuda: módulos, funcionalidades e passos, cada um com as permissões que exige."""

from dataclasses import dataclass

from accounts import permissions
from ui.navigation import MENU, MenuGroup

DESKTOP = 'computador'
MOBILE = 'celular'
DEVICES = (DESKTOP, MOBILE)


@dataclass(frozen=True)
class Step:
    """Passo de uma funcionalidade; `marks` são os balões da imagem, na ordem dos números dos marcadores."""

    text: str
    alt: str
    marks: tuple = ()
    permissions: tuple = ()


@dataclass(frozen=True)
class Feature:
    """Funcionalidade explicada em passos; `screen` é a rota aberta pelo botão do fim, coberta por `permissions`."""

    slug: str
    title: str
    goal: str
    permissions: tuple
    steps: tuple
    screen: str = ''
    screen_label: str = ''
    note: str = ''

    def image(self, number, device):
        """Caminho estático da imagem do passo `number`, contado no catálogo e não entre os passos liberados."""
        return f'tutorials/{self.slug}/{number}-{device}.webp'


@dataclass(frozen=True)
class Module:
    slug: str
    label: str
    features: tuple


@dataclass(frozen=True)
class Screen:
    """Parte do sistema de onde a ajuda é aberta, ligada à opção do menu pelo mesmo prefixo de rota."""

    prefix: str
    title: str
    features: tuple


NOTIFICATIONS = Feature(
    slug='notificacoes',
    title='Acompanhar as notificações',
    goal='Saber o que mudou nas suas solicitações e ler os comunicados publicados.',
    permissions=(),
    steps=(
        Step(
            text='O sino, no topo de qualquer tela, mostra quantas notificações ainda não foram lidas.',
            alt='Cabeçalho com o sino de notificações destacado.',
            marks=('Notificações não lidas',),
        ),
        Step(
            text='Abra o sino para ver as notificações mais recentes. Escolha uma notificação para abrir a tela relacionada.',
            alt='Painel do sino aberto, com uma notificação destacada.',
            marks=('Notificação recente',),
        ),
        Step(
            text='Use Marcar todas como lidas para zerar o contador do sino.',
            alt='Painel do sino com o botão Marcar todas como lidas destacado.',
            marks=('Marque como lidas',),
        ),
    ),
)

PANEL = Feature(
    slug='painel',
    title='Consultar o painel',
    goal='Ver num só lugar o que pede atenção na agenda e na grade de aulas.',
    permissions=(permissions.PANEL_VIEW,),
    screen='panel',
    screen_label='Abrir o painel',
    note='Cada bloco do painel depende de uma permissão. Quem não tem a permissão do bloco não o vê.',
    steps=(
        Step(
            text='As contagens do topo levam às telas de cada assunto, como as solicitações pendentes.',
            alt='Painel com a contagem de solicitações pendentes destacada.',
            marks=('Solicitações pendentes',),
            permissions=(permissions.BOOKING_REVIEW,),
        ),
        Step(
            text='Em Para decidir ficam as solicitações pendentes, das mais próximas às mais distantes. Escolha uma para analisar.',
            alt='Painel com o bloco Para decidir destacado.',
            marks=('Solicitações para decidir',),
            permissions=(permissions.BOOKING_REVIEW,),
        ),
        Step(
            text='Espaços mais ocupados mostra a ocupação de hoje ou da semana. Troque o período no filtro Ocupação, no topo do painel.',
            alt='Painel com o bloco Espaços mais ocupados destacado.',
            marks=('Ocupação dos espaços',),
            permissions=(permissions.SPACE_ALLOCATION_VIEW,),
        ),
        Step(
            text=(
                'Pendências da grade aponta aulas sem espaço ou sem docente, possíveis conflitos e espaços sem ocupação. '
                'Escolha uma contagem para ver a lista.'
            ),
            alt='Painel com o bloco Pendências da grade destacado.',
            marks=('Pendências da grade',),
            permissions=(permissions.SPACE_ALLOCATION_VIEW,),
        ),
    ),
)

AGENDA_VIEW = Feature(
    slug='consultar-agenda',
    title='Consultar a agenda',
    goal='Ver as aulas e os agendamentos de cada sala, por semana ou por mês.',
    permissions=(permissions.BOOKING_VIEW,),
    screen='agenda_grid',
    screen_label='Abrir a agenda',
    steps=(
        Step(
            text='Escolha a sala e a visualização por semana ou por mês. O semestre já vem escolhido.',
            alt='Agenda com os filtros de sala e de visualização destacados.',
            marks=('Escolha a sala', 'Semana ou mês'),
        ),
        Step(
            text='Use Semana anterior, Hoje e Próxima semana para mudar o período mostrado.',
            alt='Agenda com os botões de navegação entre semanas destacados.',
            marks=('Mude a semana',),
        ),
        Step(
            text='Cada cartão mostra a aula ou o agendamento que ocupa a faixa, com o horário, o curso, a turma e o docente.',
            alt='Grade da Agenda com o cartão de uma aula destacado.',
            marks=('Aula do ensalamento',),
        ),
        Step(
            text='No filtro Agenda, escolha Minha agenda para ver só os seus agendamentos e as aulas em que é docente.',
            alt='Agenda com o filtro Agenda destacado.',
            marks=('Minha agenda',),
        ),
    ),
)

AGENDA_REQUEST = Feature(
    slug='solicitar-agendamento',
    title='Solicitar agendamento',
    goal='Pedir o uso de um espaço numa data e num horário disponíveis.',
    permissions=(permissions.BOOKING_VIEW, permissions.BOOKING_REQUEST),
    screen='agenda_grid',
    screen_label='Abrir a agenda',
    note='Quem cria solicitações em nome de outros usuários vê o formulário de criação ao escolher a faixa.',
    steps=(
        Step(
            text='No menu lateral, escolha Agenda. No celular, toque em Menu, no topo da tela, e depois em Agenda.',
            alt='Menu com a opção Agenda destacada.',
            marks=('Abra a Agenda',),
        ),
        Step(
            text=(
                'Escolha a sala e a visão. A Grade mostra as aulas e os agendamentos aprovados da sala, '
                'e as faixas sem nenhum deles estão disponíveis.'
            ),
            alt='Grade da Agenda com o filtro de sala destacado.',
            marks=('Escolha a sala',),
        ),
        Step(
            text='Escolha uma faixa disponível. Espaço, data e horário chegam preenchidos ao formulário.',
            alt='Grade da Agenda com o botão Solicitar agendamento de uma faixa disponível destacado.',
            marks=('Escolha uma faixa disponível',),
        ),
        Step(
            text=(
                'Informe a descrição do uso e a quantidade de alunos. Curso, disciplina e turma são opcionais. '
                'Depois, escolha Revisar solicitação.'
            ),
            alt='Formulário Solicitar agendamento com a descrição e o botão Revisar solicitação destacados.',
            marks=('Descreva o uso', 'Revise antes de enviar'),
        ),
        Step(
            text='Confira os dados e escolha Enviar solicitação. O horário só fica ocupado depois da aprovação.',
            alt='Revisão da solicitação com o botão Enviar solicitação destacado.',
            marks=('Envie a solicitação',),
        ),
        Step(
            text='A mensagem no topo confirma o envio. A situação da solicitação fica em Minhas solicitações.',
            alt='Agenda com a mensagem de envio e o botão Minhas solicitações destacados.',
            marks=('Envio confirmado', 'Acompanhe a solicitação'),
        ),
    ),
)

AGENDA_FOLLOW = Feature(
    slug='acompanhar-solicitacoes',
    title='Acompanhar as solicitações',
    goal='Ver a situação das suas solicitações e responder à alternativa sugerida.',
    permissions=(permissions.BOOKING_REQUEST,),
    screen='agenda_my_requests',
    screen_label='Abrir minhas solicitações',
    steps=(
        Step(
            text='Na Agenda, escolha Minhas solicitações.',
            alt='Agenda com o botão Minhas solicitações destacado.',
            marks=('Abra suas solicitações',),
        ),
        Step(
            text=(
                'A lista mostra a situação de cada solicitação: pendente, aprovada, rejeitada ou alternativa sugerida. '
                'Escolha uma solicitação para ver os detalhes.'
            ),
            alt='Lista Minhas solicitações com uma solicitação de alternativa sugerida destacada.',
            marks=('Situação da solicitação',),
        ),
        Step(
            text='Quando a análise sugere outro espaço, data ou horário, a alternativa aparece junto com a mensagem de quem analisou.',
            alt='Detalhe da solicitação com o quadro Alternativa sugerida destacado.',
            marks=('Alternativa sugerida',),
        ),
        Step(
            text='Escolha Aceitar alternativa para ficar com os dados sugeridos, ou Recusar alternativa para encerrar a solicitação.',
            alt='Detalhe da solicitação com os botões Aceitar alternativa e Recusar alternativa destacados.',
            marks=('Aceite', 'Ou recuse'),
        ),
        Step(
            text='Confirme a resposta. Ao aceitar, o horário sugerido é conferido de novo e vira agendamento.',
            alt='Confirmação da resposta com o botão de aceitar destacado.',
            marks=('Confirme a resposta',),
        ),
    ),
)

AGENDA_CANCEL = Feature(
    slug='cancelar-agendamento',
    title='Cancelar um agendamento',
    goal='Liberar o espaço de um agendamento aprovado que não vai mais acontecer.',
    permissions=(permissions.BOOKING_REQUEST,),
    screen='agenda_my_requests',
    screen_label='Abrir minhas solicitações',
    steps=(
        Step(
            text='Em Minhas solicitações, abra o agendamento aprovado e escolha Cancelar agendamento.',
            alt='Detalhe de uma solicitação aprovada com o botão Cancelar agendamento destacado.',
            marks=('Cancelar agendamento',),
        ),
        Step(
            text='Informe o motivo, se quiser, e confirme. O cancelamento vale até 1 hora antes do início e deixa o espaço disponível.',
            alt='Confirmação do cancelamento com o botão de confirmar destacado.',
            marks=('Confirme o cancelamento',),
        ),
    ),
)

AGENDA_OCCURRENCE = Feature(
    slug='cancelar-ocorrencia',
    title='Cancelar a ocorrência de uma aula',
    goal='Avisar que uma aula não acontece numa data e deixar o espaço disponível nesse dia.',
    permissions=(permissions.BOOKING_VIEW,),
    screen='agenda_exception_list',
    screen_label='Ver exceções',
    note='Disponível para o docente da aula e para quem pode cancelar qualquer aula do ensalamento.',
    steps=(
        Step(
            text='Na Agenda, encontre a aula e escolha o ícone Cancelar esta ocorrência no cartão.',
            alt='Cartão de uma aula na Agenda com o ícone Cancelar esta ocorrência destacado.',
            marks=('Cancelar esta ocorrência',),
        ),
        Step(
            text='Confira a aula e a data e escolha Cancelar ocorrência. As próximas datas continuam normalmente.',
            alt='Confirmação do cancelamento da ocorrência com o botão Cancelar ocorrência destacado.',
            marks=('Confirme o cancelamento',),
        ),
        Step(
            text='As ocorrências canceladas ficam em Ver exceções, no topo da Agenda.',
            alt='Lista de exceções do ensalamento com a ocorrência cancelada destacada.',
            marks=('Ocorrência cancelada',),
        ),
    ),
)

AGENDA_REVIEW = Feature(
    slug='analisar-solicitacoes',
    title='Analisar as solicitações de agendamento',
    goal='Aprovar, rejeitar ou sugerir outra opção para as solicitações recebidas.',
    permissions=(permissions.BOOKING_REVIEW,),
    screen='agenda_review_list',
    screen_label='Abrir as solicitações para análise',
    steps=(
        Step(
            text='Na Agenda, escolha Solicitações para análise. O painel também mostra as pendentes em Para decidir.',
            alt='Agenda com o botão Solicitações para análise destacado.',
            marks=('Solicitações para análise',),
        ),
        Step(
            text='A lista abre nas solicitações para decidir. Escolha uma solicitação para analisar.',
            alt='Lista de solicitações para análise com uma solicitação destacada.',
            marks=('Escolha a solicitação',),
        ),
        Step(
            text='Confira os dados e o histórico e escolha Rejeitar, Sugerir alternativa ou Aprovar.',
            alt='Detalhe da solicitação com os botões Rejeitar, Sugerir alternativa e Aprovar destacados.',
            marks=('Rejeitar', 'Sugerir alternativa', 'Aprovar'),
        ),
        Step(
            text='Ao aprovar, o horário é conferido de novo e o agendamento é criado para quem solicitou.',
            alt='Confirmação da aprovação com o botão Aprovar solicitação destacado.',
            marks=('Aprove a solicitação',),
        ),
        Step(
            text='Ao rejeitar, informe o motivo. Ele aparece para quem solicitou.',
            alt='Formulário de rejeição com o motivo e o botão Rejeitar solicitação destacados.',
            marks=('Motivo da rejeição', 'Rejeite a solicitação'),
        ),
        Step(
            text='Para sugerir outro espaço, data ou horário, preencha a alternativa e, se quiser, uma mensagem.',
            alt='Formulário Sugerir alternativa com o espaço sugerido e o botão Sugerir alternativa destacados.',
            marks=('Espaço sugerido', 'Envie a alternativa'),
        ),
    ),
)

AGENDA_ON_BEHALF = Feature(
    slug='criar-para-outro-usuario',
    title='Criar solicitação para outro usuário',
    goal='Registrar uma solicitação de agendamento em nome de outra pessoa.',
    permissions=(permissions.BOOKING_VIEW, permissions.BOOKING_CREATE),
    screen='agenda_grid',
    screen_label='Abrir a agenda',
    steps=(
        Step(
            text='Na Agenda, escolha uma faixa disponível. No formulário, escolha o ícone Criar para outro usuário.',
            alt='Formulário Solicitar agendamento com o ícone Criar para outro usuário destacado.',
            marks=('Criar para outro usuário',),
        ),
        Step(
            text='Escolha o usuário e preencha a descrição e a quantidade de alunos. Depois, escolha Revisar solicitação.',
            alt='Formulário Criar solicitação para outro usuário com o campo Usuário e o botão Revisar solicitação destacados.',
            marks=('Escolha o usuário', 'Revise antes de enviar'),
        ),
        Step(
            text='Confira os dados e escolha Enviar solicitação. A solicitação fica em nome do usuário escolhido.',
            alt='Revisão da solicitação criada para outro usuário com o botão Enviar solicitação destacado.',
            marks=('Envie a solicitação',),
        ),
    ),
)

TIMETABLE_VIEW = Feature(
    slug='consultar-ensalamento',
    title='Consultar a grade do ensalamento',
    goal='Ver as aulas regulares de cada sala no semestre.',
    permissions=(permissions.SPACE_ALLOCATION_VIEW,),
    screen='space_allocation_grid',
    screen_label='Abrir o ensalamento',
    steps=(
        Step(
            text='No menu lateral, abra Gestão acadêmica e escolha Ensalamento. No celular, toque em Menu antes.',
            alt='Menu com a opção Ensalamento destacada.',
            marks=('Abra o ensalamento',),
        ),
        Step(
            text='Escolha o semestre, a sala e a visualização. A Grade mostra as aulas da sala em cada faixa de horário.',
            alt='Grade do ensalamento com o filtro de sala destacado.',
            marks=('Escolha a sala',),
        ),
        Step(
            text='Cada cartão traz a disciplina, o horário, o curso, a turma e os docentes da aula.',
            alt='Grade do ensalamento com o cartão de uma aula destacado.',
            marks=('Aula',),
        ),
        Step(
            text='Ver exceções lista as ocorrências canceladas. Ver importações abre o histórico das planilhas enviadas.',
            alt='Topo do ensalamento com os botões Ver exceções e Ver importações destacados.',
            marks=('Exceções', 'Importações'),
        ),
    ),
)

TIMETABLE_CHANGES = Feature(
    slug='ajustar-aulas',
    title='Ajustar as aulas do ensalamento',
    goal='Cadastrar, alterar, encerrar ou cancelar aulas sem esperar uma nova planilha.',
    permissions=(permissions.SPACE_ALLOCATION_VIEW,),
    screen='space_allocation_grid',
    screen_label='Abrir o ensalamento',
    note='Toda alteração mostra um resumo antes de gravar e só vale para datas de hoje em diante.',
    steps=(
        Step(
            text='Para cadastrar uma aula que se repete toda semana, escolha uma faixa disponível na Grade.',
            alt='Grade do ensalamento com o botão de cadastrar aula numa faixa disponível destacado.',
            marks=('Cadastrar aula',),
            permissions=(permissions.SPACE_ALLOCATION_CREATE_RECURRENCE,),
        ),
        Step(
            text='Informe a turma, a disciplina, os docentes, a primeira aula e o horário. Depois, escolha Revisar cadastro.',
            alt='Formulário Cadastrar aula com os campos de turma e o botão Revisar cadastro destacados.',
            marks=('Turma', 'Revise antes de gravar'),
            permissions=(permissions.SPACE_ALLOCATION_CREATE_RECURRENCE,),
        ),
        Step(
            text='Para mudar o dia, o horário, a duração, o espaço ou os docentes, escolha Alterar recorrência no cartão da aula.',
            alt='Cartão de uma aula com o ícone Alterar recorrência destacado.',
            marks=('Alterar recorrência',),
            permissions=(permissions.SPACE_ALLOCATION_CHANGE_RECURRENCE,),
        ),
        Step(
            text='Informe a partir de quando valem os dados novos e escolha Revisar alteração. As aulas anteriores não mudam.',
            alt='Formulário Alterar recorrência com a data de início e o botão Revisar alteração destacados.',
            marks=('A partir de', 'Revise antes de gravar'),
            permissions=(permissions.SPACE_ALLOCATION_CHANGE_RECURRENCE,),
        ),
        Step(
            text='Para encerrar uma aula a partir de uma data, escolha Encerrar recorrência no cartão. A confirmação mostra quantas aulas deixam de existir.',
            alt='Confirmação de encerramento da recorrência com o botão Encerrar recorrência destacado.',
            marks=('Encerre a recorrência',),
            permissions=(permissions.SPACE_ALLOCATION_END_RECURRENCE,),
        ),
        Step(
            text='Para cancelar só uma data, escolha Cancelar esta ocorrência no cartão. A aula continua nas próximas semanas.',
            alt='Cartão de uma aula com o ícone Cancelar esta ocorrência destacado.',
            marks=('Cancelar esta ocorrência',),
            permissions=(permissions.SPACE_ALLOCATION_CANCEL_OCCURRENCE,),
        ),
    ),
)

TIMETABLE_IMPORT = Feature(
    slug='importar-ensalamento',
    title='Importar a planilha de horários',
    goal='Trazer para o sistema as aulas do semestre a partir da planilha institucional.',
    permissions=(permissions.SPACE_ALLOCATION_IMPORT,),
    screen='space_allocation_import_list',
    screen_label='Abrir as importações',
    steps=(
        Step(
            text='Em Ensalamento, escolha Ver importações e depois Importar ensalamento.',
            alt='Lista de importações com o botão Importar ensalamento destacado.',
            marks=('Importar ensalamento',),
        ),
        Step(
            text=(
                'Escolha a planilha em XLSX e informe o semestre. Na primeira importação do semestre, informe também '
                'o início e o fim. Depois, escolha Enviar arquivo.'
            ),
            alt='Formulário Importar ensalamento com o arquivo, o semestre e o botão Enviar arquivo destacados.',
            marks=('Planilha', 'Semestre', 'Envie o arquivo'),
        ),
        Step(
            text='O sistema confere a planilha e mostra uma prévia, sem gravar nada. Confira o resumo e as linhas.',
            alt='Prévia da importação com o resumo destacado.',
            marks=('Resumo da prévia',),
        ),
        Step(
            text='Escolha Confirmar importação para gravar as aulas, ou Descartar importação para encerrar sem alterar nada.',
            alt='Prévia da importação com os botões Confirmar importação e Descartar importação destacados.',
            marks=('Confirme', 'Ou descarte'),
        ),
        Step(
            text='Ao terminar, a situação muda para Concluída e as aulas aparecem na Grade.',
            alt='Importação concluída com o resumo destacado.',
            marks=('Importação concluída',),
        ),
    ),
)

SPACES = Feature(
    slug='espacos',
    title='Gerenciar os espaços',
    goal='Consultar e manter o cadastro das salas e dos laboratórios.',
    permissions=(permissions.SPACE_VIEW,),
    screen='spaces_list',
    screen_label='Abrir os espaços',
    steps=(
        Step(
            text='Em Gestão acadêmica, escolha Espaços. Busque pelo nome e filtre pela situação ou pela origem.',
            alt='Lista de espaços com a busca e os filtros destacados.',
            marks=('Busque e filtre',),
        ),
        Step(
            text='Escolha Cadastrar espaço para incluir um espaço que não veio da planilha.',
            alt='Lista de espaços com o botão Cadastrar espaço destacado.',
            marks=('Cadastrar espaço',),
            permissions=(permissions.SPACE_CREATE,),
        ),
        Step(
            text='Informe o nome e, se houver, os outros nomes usados na planilha. Depois, escolha Cadastrar.',
            alt='Formulário Cadastrar espaço com o nome e o botão Cadastrar destacados.',
            marks=('Nome do espaço', 'Cadastre'),
            permissions=(permissions.SPACE_CREATE,),
        ),
        Step(
            text='Nas ações da linha, edite os nomes ou abra Mais ações para desativar, reativar ou excluir o espaço.',
            alt='Lista de espaços com as ações de uma linha destacadas.',
            marks=('Ações do espaço',),
        ),
    ),
)

COURSES = Feature(
    slug='cursos',
    title='Gerenciar os cursos',
    goal='Consultar os cursos e as turmas de cada um.',
    permissions=(permissions.COURSE_VIEW,),
    screen='courses_list',
    screen_label='Abrir os cursos',
    steps=(
        Step(
            text='Em Gestão acadêmica, escolha Cursos. Busque pelo nome e filtre pela etapa de ensino.',
            alt='Lista de cursos com a busca e o filtro destacados.',
            marks=('Busque e filtre',),
        ),
        Step(
            text='Escolha Cadastrar curso e informe o nome, como aparece na planilha, e a etapa de ensino.',
            alt='Formulário Cadastrar curso com o nome e a etapa de ensino destacados.',
            marks=('Nome do curso', 'Etapa de ensino'),
            permissions=(permissions.COURSE_CREATE,),
        ),
        Step(
            text='Escolha um curso na lista para ver as turmas dele.',
            alt='Detalhe de um curso com a lista de turmas destacada.',
            marks=('Turmas do curso',),
        ),
    ),
)

SUBJECTS = Feature(
    slug='disciplinas',
    title='Gerenciar as disciplinas',
    goal='Consultar as disciplinas e as turmas em que são oferecidas.',
    permissions=(permissions.SUBJECT_VIEW,),
    screen='subjects_list',
    screen_label='Abrir as disciplinas',
    note='A lista mostra as disciplinas das turmas em que o seu usuário é docente. Quem pode alcançar todas as disciplinas vê a lista completa.',
    steps=(
        Step(
            text='Em Gestão acadêmica, escolha Disciplinas e busque pelo nome.',
            alt='Lista de disciplinas com a busca destacada.',
            marks=('Busque pelo nome',),
        ),
        Step(
            text='Escolha Cadastrar disciplina e informe o nome.',
            alt='Formulário Cadastrar disciplina com o nome destacado.',
            marks=('Nome da disciplina',),
            permissions=(permissions.SUBJECT_CREATE,),
        ),
        Step(
            text='Escolha uma disciplina na lista para ver as turmas e os docentes de cada semestre.',
            alt='Lista de disciplinas com o nome de uma disciplina destacado.',
            marks=('Abra a disciplina',),
        ),
    ),
)

CLASS_GROUPS = Feature(
    slug='turmas',
    title='Gerenciar as turmas',
    goal='Consultar as turmas de cada curso e as disciplinas delas.',
    permissions=(permissions.CLASS_GROUP_VIEW,),
    screen='class_groups_list',
    screen_label='Abrir as turmas',
    note='A lista mostra as turmas em que o seu usuário é docente. Quem pode alcançar todas as turmas vê a lista completa.',
    steps=(
        Step(
            text='Em Gestão acadêmica, escolha Turmas. Busque pelo rótulo ou pelo curso.',
            alt='Lista de turmas com a busca e o filtro de curso destacados.',
            marks=('Busque e filtre',),
        ),
        Step(
            text='Escolha Cadastrar turma, escolha o curso e informe o rótulo, como 1º ano A.',
            alt='Formulário Cadastrar turma com o curso e o rótulo destacados.',
            marks=('Curso', 'Rótulo da turma'),
            permissions=(permissions.CLASS_GROUP_CREATE,),
        ),
        Step(
            text='Escolha uma turma na lista para ver as disciplinas e os docentes dela.',
            alt='Lista de turmas com o rótulo de uma turma destacado.',
            marks=('Abra a turma',),
        ),
    ),
)

HEATMAP = Feature(
    slug='mapa-de-calor',
    title='Consultar o mapa de calor',
    goal='Ver em que dias e horários os espaços ficam mais e menos ocupados.',
    permissions=(permissions.REPORT_VIEW, permissions.SPACE_ALLOCATION_VIEW),
    screen='report_heatmap',
    screen_label='Abrir o mapa de calor',
    steps=(
        Step(
            text='Em Relatórios, escolha Mapa de calor. Filtre por semestre, origem, etapa de ensino, curso e espaços.',
            alt='Mapa de calor com os filtros destacados.',
            marks=('Filtros do relatório',),
        ),
        Step(
            text='Os indicadores resumem a ocupação média, o horário de pico e o de menor ocupação.',
            alt='Mapa de calor com os indicadores destacados.',
            marks=('Indicadores',),
        ),
        Step(
            text='Cada célula mostra o percentual de espaços ocupados no dia e na faixa. Escolha uma célula para ver os espaços.',
            alt='Mapa de calor com uma célula destacada.',
            marks=('Escolha uma célula',),
        ),
        Step(
            text='A lista mostra os espaços daquela faixa. Abrir na Grade leva à semana da sala.',
            alt='Lista dos espaços de uma faixa do mapa de calor destacada.',
            marks=('Espaços da faixa',),
        ),
    ),
)

REQUESTS_REPORT = Feature(
    slug='relatorio-solicitacoes',
    title='Consultar o relatório de solicitações',
    goal='Acompanhar quantas solicitações chegam, quantas são aprovadas e quanto tempo levam para ser decididas.',
    permissions=(permissions.REPORT_VIEW, permissions.BOOKING_REVIEW),
    screen='report_requests',
    screen_label='Abrir o relatório',
    steps=(
        Step(
            text='Em Relatórios, escolha Solicitações. Filtre por semestre, etapa de ensino, curso e espaços.',
            alt='Relatório de solicitações com os filtros destacados.',
            marks=('Filtros do relatório',),
        ),
        Step(
            text='Os indicadores mostram o total, a taxa de aprovação, o tempo até a decisão e as pendentes.',
            alt='Relatório de solicitações com os indicadores destacados.',
            marks=('Indicadores',),
        ),
        Step(
            text='O gráfico mostra quantas solicitações foram feitas em cada semana do semestre.',
            alt='Relatório de solicitações com o gráfico por semana destacado.',
            marks=('Solicitações por semana',),
        ),
    ),
)

NOTICE_PUBLISH = Feature(
    slug='publicar-notificacao',
    title='Publicar uma notificação',
    goal='Enviar um comunicado que aparece no sino dos usuários escolhidos.',
    permissions=(permissions.NOTICE_PUBLISH,),
    screen='notice_list',
    screen_label='Abrir as notificações',
    steps=(
        Step(
            text='No menu, escolha Notificações e depois Nova notificação.',
            alt='Lista de notificações publicadas com o botão Nova notificação destacado.',
            marks=('Nova notificação',),
        ),
        Step(
            text='Informe o título, que aparece em destaque no sino, e a mensagem.',
            alt='Formulário Nova notificação com o título destacado.',
            marks=('Título e mensagem',),
        ),
        Step(
            text='Escolha o tipo e os destinatários. Depois, escolha Continuar para revisão.',
            alt='Formulário Nova notificação com os destinatários e o botão Continuar para revisão destacados.',
            marks=('Destinatários', 'Continue'),
        ),
        Step(
            text='Confira a prévia e o total de destinatários e escolha Publicar notificação.',
            alt='Revisão da notificação com o botão Publicar notificação destacado.',
            marks=('Publique',),
        ),
    ),
)

USERS = Feature(
    slug='usuarios',
    title='Gerenciar os usuários',
    goal='Cadastrar pessoas, trocar o perfil e controlar quem pode entrar no sistema.',
    permissions=(permissions.USER_VIEW,),
    screen='user_list',
    screen_label='Abrir os usuários',
    steps=(
        Step(
            text='Em Administração, escolha Usuários. Busque por nome, e-mail ou nome de usuário e filtre pela situação.',
            alt='Lista de usuários com a busca e o filtro de situação destacados.',
            marks=('Busque e filtre',),
        ),
        Step(
            text='Escolha Cadastrar usuário.',
            alt='Lista de usuários com o botão Cadastrar usuário destacado.',
            marks=('Cadastrar usuário',),
            permissions=(permissions.USER_CREATE,),
        ),
        Step(
            text=(
                'Informe o nome, o e-mail institucional e o perfil. Para docentes, o nome de usuário é o nome como aparece '
                'no ensalamento. O link para definir a senha vai por e-mail.'
            ),
            alt='Formulário Cadastrar usuário com o e-mail, o perfil e o botão Cadastrar destacados.',
            marks=('E-mail institucional', 'Perfil', 'Cadastre'),
            permissions=(permissions.USER_CREATE,),
        ),
        Step(
            text='Nas ações da linha, edite os dados ou abra Mais ações para trocar o perfil, desativar ou reativar o usuário.',
            alt='Lista de usuários com as ações de uma linha destacadas.',
            marks=('Ações do usuário',),
        ),
    ),
)

USERS_IMPORT = Feature(
    slug='importar-usuarios',
    title='Importar usuários',
    goal='Cadastrar ou atualizar vários usuários de uma vez a partir de um arquivo CSV.',
    permissions=(permissions.USER_IMPORT,),
    screen='user_import_list',
    screen_label='Abrir as importações de usuários',
    steps=(
        Step(
            text='Em Usuários, escolha Importações e depois Importar usuários.',
            alt='Lista de importações de usuários com o botão Importar usuários destacado.',
            marks=('Importar usuários',),
        ),
        Step(
            text=(
                'Escolha o arquivo CSV, separado por ponto e vírgula, com as colunas E-mail, Nome, Perfil e Nome de usuário. '
                'O modelo do arquivo pode ser baixado na mesma tela.'
            ),
            alt='Formulário Importar usuários com o arquivo, o modelo e o botão Enviar arquivo destacados.',
            marks=('Arquivo CSV', 'Modelo do arquivo', 'Envie o arquivo'),
        ),
        Step(
            text='Confira a prévia e escolha Confirmar importação. Cada pessoa nova recebe por e-mail o link para definir a senha.',
            alt='Prévia da importação de usuários com o botão Confirmar importação destacado.',
            marks=('Confirme a importação',),
        ),
    ),
)

ROLES = Feature(
    slug='perfis',
    title='Gerenciar os perfis e as permissões',
    goal='Definir o que cada perfil libera no sistema.',
    permissions=(permissions.ROLE_VIEW,),
    screen='role_list',
    screen_label='Abrir os perfis',
    steps=(
        Step(
            text='Em Administração, escolha Perfis e permissões. Cada perfil reúne as permissões que os usuários dele recebem.',
            alt='Lista de perfis destacada.',
            marks=('Perfis cadastrados',),
        ),
        Step(
            text='Escolha Alterar permissões na linha do perfil.',
            alt='Lista de perfis com o ícone Alterar permissões destacado.',
            marks=('Alterar permissões',),
            permissions=(permissions.ROLE_CHANGE_PERMISSIONS,),
        ),
        Step(
            text='Marque as permissões de cada módulo. A busca encontra uma permissão pelo nome. Depois, salve.',
            alt='Tela de permissões do perfil com a busca e os módulos destacados.',
            marks=('Busque a permissão', 'Permissões por módulo'),
            permissions=(permissions.ROLE_CHANGE_PERMISSIONS,),
        ),
        Step(
            text='Para um perfil novo, escolha Criar perfil e informe o código, o nome e a descrição.',
            alt='Lista de perfis com o botão Criar perfil destacado.',
            marks=('Criar perfil',),
            permissions=(permissions.ROLE_CREATE,),
        ),
    ),
)

AUDIT = Feature(
    slug='auditoria',
    title='Consultar a auditoria',
    goal='Saber quem fez cada alteração no sistema, quando e de onde.',
    permissions=(permissions.AUDIT_VIEW,),
    screen='audit_log_list',
    screen_label='Abrir a auditoria',
    steps=(
        Step(
            text='Em Administração, escolha Auditoria. Filtre por usuário, ação, módulo, origem ou período e escolha Filtrar.',
            alt='Auditoria com os filtros e o botão Filtrar destacados.',
            marks=('Filtros', 'Filtrar'),
        ),
        Step(
            text='Escolha Ver detalhes na linha do registro.',
            alt='Lista da auditoria com o ícone Ver detalhes destacado.',
            marks=('Ver detalhes',),
        ),
        Step(
            text='O detalhe mostra quem fez, o tipo de ação, o módulo, a data e a origem do registro.',
            alt='Detalhe de um registro de auditoria destacado.',
            marks=('Detalhe do registro',),
        ),
    ),
)

EMAIL_SERVER = Feature(
    slug='servidor-de-email',
    title='Configurar o servidor de e-mail',
    goal='Definir por qual servidor saem os e-mails do sistema, como os links de senha.',
    permissions=(permissions.SETTINGS_EDIT,),
    screen='settings_email',
    screen_label='Abrir o servidor de e-mail',
    steps=(
        Step(
            text='Em Configurações, escolha E-mail. A tela mostra a situação do servidor e os e-mails pendentes.',
            alt='Tela Servidor de e-mail com a situação destacada.',
            marks=('Situação do servidor',),
        ),
        Step(
            text='Escolha Cadastrar servidor de e-mail.',
            alt='Tela Servidor de e-mail com o botão Cadastrar servidor de e-mail destacado.',
            marks=('Cadastrar servidor',),
        ),
        Step(
            text='Informe o servidor, a porta, a segurança, a conta e o remetente. Depois, escolha Salvar servidor de e-mail.',
            alt='Formulário do servidor de e-mail com o servidor e o botão Salvar destacados.',
            marks=('Servidor e porta', 'Salve'),
        ),
    ),
)

MODULES = (
    Module('geral', 'Uso geral', (NOTIFICATIONS,)),
    Module('painel', 'Painel', (PANEL,)),
    Module('agenda', 'Agenda', (
        AGENDA_VIEW, AGENDA_REQUEST, AGENDA_FOLLOW, AGENDA_CANCEL, AGENDA_OCCURRENCE, AGENDA_REVIEW, AGENDA_ON_BEHALF,
    )),
    Module('gestao-academica', 'Gestão acadêmica', (
        TIMETABLE_VIEW, TIMETABLE_CHANGES, TIMETABLE_IMPORT, SPACES, COURSES, SUBJECTS, CLASS_GROUPS,
    )),
    Module('relatorios', 'Relatórios', (HEATMAP, REQUESTS_REPORT)),
    Module('notificacoes', 'Notificações', (NOTICE_PUBLISH,)),
    Module('administracao', 'Administração', (USERS, USERS_IMPORT, ROLES, AUDIT)),
    Module('configuracoes', 'Configurações', (EMAIL_SERVER,)),
)


SCREENS = (
    Screen('panel', 'Ajuda do painel', (PANEL,)),
    Screen('agenda_', 'Ajuda da agenda', (
        AGENDA_VIEW, AGENDA_REQUEST, AGENDA_FOLLOW, AGENDA_CANCEL, AGENDA_OCCURRENCE, AGENDA_REVIEW, AGENDA_ON_BEHALF,
    )),
    Screen('space_allocation_', 'Ajuda do ensalamento', (TIMETABLE_VIEW, TIMETABLE_CHANGES, TIMETABLE_IMPORT)),
    Screen('spaces_', 'Ajuda dos espaços', (SPACES,)),
    Screen('courses_', 'Ajuda dos cursos', (COURSES,)),
    Screen('subjects_', 'Ajuda das disciplinas', (SUBJECTS,)),
    Screen('class_groups_', 'Ajuda das turmas', (CLASS_GROUPS,)),
    Screen('report_heatmap', 'Ajuda do mapa de calor', (HEATMAP,)),
    Screen('report_requests', 'Ajuda do relatório de solicitações', (REQUESTS_REPORT,)),
    Screen('notice_', 'Ajuda das notificações', (NOTICE_PUBLISH,)),
    Screen('user_', 'Ajuda dos usuários', (USERS, USERS_IMPORT)),
    Screen('role_', 'Ajuda dos perfis e das permissões', (ROLES,)),
    Screen('audit_', 'Ajuda da auditoria', (AUDIT,)),
    Screen('settings_email', 'Ajuda do servidor de e-mail', (EMAIL_SERVER,)),
)


def features():
    return [feature for module in MODULES for feature in module.features]


def menu_items():
    for item in MENU:
        yield from item.items if isinstance(item, MenuGroup) else (item,)


def screen_for(url_name):
    """Parte do sistema da rota de origem, ou None quando a rota não tem ajuda própria."""
    return next((screen for screen in SCREENS if url_name and url_name.startswith(screen.prefix)), None)


def menu_item_of(screen):
    return next(item for item in menu_items() if item.prefix == screen.prefix)


def entries_for(user, chosen):
    """Funcionalidades liberadas ao usuário, cada uma com os passos liberados; sem passo liberado fica de fora."""
    entries = []
    for feature in chosen:
        if not user.has_perms(feature.permissions):
            continue
        steps = [
            {'step': step, 'desktop': feature.image(number, DESKTOP), 'mobile': feature.image(number, MOBILE)}
            for number, step in enumerate(feature.steps, start=1)
            if user.has_perms(step.permissions)
        ]
        if steps:
            entries.append({'feature': feature, 'steps': steps})
    return entries


def guide_for(user):
    """Módulos com as funcionalidades e os passos liberados ao usuário, para a central completa."""
    modules = []
    for module in MODULES:
        entries = entries_for(user, module.features)
        if entries:
            modules.append({'slug': module.slug, 'label': module.label, 'features': entries})
    return modules
