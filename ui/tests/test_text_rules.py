from django.test import SimpleTestCase

from ui.text_rules import find_violations


class TextRulesTests(SimpleTestCase):
    def assertViolates(self, text, element=None, excerpt=None):
        violations = find_violations(text, element)
        self.assertTrue(violations, f'Nenhuma violação em {text!r}.')
        if excerpt is not None:
            self.assertIn(excerpt, [violation.excerpt for violation in violations])

    def assertAllowed(self, text, element=None):
        self.assertEqual(find_violations(text, element), [])

    def test_exclamacao(self):
        self.assertViolates('Usuário cadastrado!', excerpt='!')
        self.assertAllowed('Usuário cadastrado.')

    def test_reticencias(self):
        self.assertViolates('Carregando informações...')
        self.assertViolates('Carregando…')
        self.assertAllowed('Usuário ana@ifnmg.edu.br desativado.')

    def test_travessao(self):
        self.assertViolates('—')
        self.assertViolates('Perfis – lista')
        self.assertAllowed('Sem descrição')
        self.assertAllowed('Cadastrar usuário · IFNMG Salinas')

    def test_interjeicao(self):
        self.assertViolates('Ops, algo aconteceu.', excerpt='Ops')
        self.assertViolates('Uau.')
        self.assertAllowed('Operação recusada.')

    def test_saudacao(self):
        self.assertViolates('Olá, VAR', excerpt='Olá')
        self.assertViolates('Bem-vindo de volta.')
        self.assertViolates('Que bom ter VAR aqui.')
        self.assertAllowed('Início')

    def test_mensagem_vaga(self):
        self.assertViolates('Algo deu errado.')
        self.assertViolates('Parece que houve um problema.')
        self.assertViolates('Ocorreu um erro.')
        self.assertAllowed('Este e-mail já pertence a outro usuário. Use outro e-mail.')

    def test_por_favor_e_com_sucesso(self):
        self.assertViolates('Por favor, informe o e-mail.')
        self.assertViolates('Perfil criado com sucesso.', excerpt='com sucesso')
        self.assertAllowed('Perfil COORDENACAO criado.')

    def test_marketing_com_flexoes(self):
        for text in (
            'Uma jornada de reservas.', 'Experiência intuitiva.', 'Descubra o sistema.',
            'É simples.', 'Reserve facilmente.', 'Um sistema poderoso.', 'Incríveis recursos.',
            'Potencialize a gestão.', 'Tudo perfeito.', 'Simplesmente reserve.',
        ):
            with self.subTest(text=text):
                self.assertViolates(text)
        self.assertAllowed('Reserve um laboratório.')

    def test_tratamento_impessoal(self):
        self.assertViolates('Você não tem permissão.', excerpt='Você')
        self.assertViolates('Enviaremos um link.', excerpt='Enviaremos')
        self.assertViolates('Recebemos um e-mail.')
        self.assertViolates('Nós conferimos o e-mail.', excerpt='Nós')
        self.assertAllowed('Os dados ficam guardados nos formulários.')
        self.assertAllowed('Seu perfil não concede esta permissão.')
        self.assertAllowed('Esqueci minha senha', 'a')

    def test_emoji(self):
        self.assertViolates('Reserva aprovada \U0001F389')
        self.assertViolates('Concluído ✅')
        self.assertAllowed('Reserva aprovada')

    def test_glossario(self):
        violations = find_violations('Bloquear', 'button')
        self.assertTrue(any('desativar' in violation.guidance for violation in violations))
        for text, term in (
            ('Usuário suspenso', 'desativar'),
            ('Inativar usuário', 'desativar'),
            ('Solicitação reprovada', 'rejeitar'),
            ('Apagar perfil', 'excluir'),
            ('Remover perfil', 'excluir'),
            ('Deletar', 'excluir'),
            ('Logar no sistema', 'entrar'),
            ('Logout', 'sair'),
            ('Informe o email', 'e-mail'),
            ('Informe o E-Mail', 'e-mail'),
            ('Horário livre', 'disponível'),
            ('Pedido em análise', 'solicitação de reserva'),
            ('Papel do usuário', 'perfil'),
            ('Professor', 'docente'),
        ):
            with self.subTest(text=text):
                violations = find_violations(text)
                self.assertTrue(any(term in violation.guidance for violation in violations), violations)
        self.assertAllowed('Inativo')
        self.assertAllowed('Informe o e-mail.')
        self.assertAllowed('Ir para a página de login')

    def test_codigos_de_permissao_sao_dado(self):
        self.assertAllowed('Use o formato RECURSO.ACAO.')
        self.assertAllowed('USUARIO.ALTERAR_SITUACAO · Desativar e reativar usuário')
        self.assertViolates('Escolha o recurso.')

    def test_maiusculas_em_titulos_e_botoes(self):
        self.assertViolates('Cadastrar Usuário', 'h1', excerpt='Usuário')
        self.assertViolates('Cadastrar Usuário', 'button', excerpt='Usuário')
        self.assertAllowed('Cadastrar Usuário', 'p')
        self.assertAllowed('Cadastrar usuário', 'button')
        self.assertAllowed('VAR usuário', 'h1')
        self.assertAllowed('Desativar VAR?', 'h1')
        self.assertAllowed('Agendamento de espaços · IFNMG Campus Salinas', 'title')
        self.assertAllowed('Perfil ADMINISTRADOR', 'h1')
        self.assertAllowed('Esqueci minha senha', 'a')

    def test_titulo_com_dois_pontos(self):
        self.assertViolates('Usuários: gerencie a equipe', 'h1')
        self.assertAllowed('Reserva das 10:00 às 12:00', 'h1')
        self.assertAllowed('Código: VAR', 'p')
        self.assertAllowed('Nova senha:', 'label')


class AccountAdapterMessagesTests(SimpleTestCase):
    """As mensagens sobrescritas do allauth existem na versão instalada e seguem as regras."""

    def test_chaves_sobrescritas_existem_no_allauth(self):
        from allauth.account.adapter import DefaultAccountAdapter

        from accounts.adapters import AccountAdapter

        overridden = {
            key for key, message in AccountAdapter.error_messages.items()
            if message != DefaultAccountAdapter.error_messages.get(key)
        }
        self.assertEqual(overridden, {'email_password_mismatch', 'too_many_login_attempts', 'rate_limited'})
        self.assertLessEqual(overridden, DefaultAccountAdapter.error_messages.keys())
        for key in overridden:
            with self.subTest(key=key):
                self.assertEqual(find_violations(str(AccountAdapter.error_messages[key])), [])
