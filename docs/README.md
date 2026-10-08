# Documentação do IFAgenda

Sistema web de agendamento de espaços físicos do IFNMG – Campus Salinas: ensalamento importado da planilha institucional, solicitações de uso eventual e calendário público. Django 5.2, PostgreSQL 17, Docker.

Os documentos descrevem o comportamento do código revisado em 08/10/2026. Para subir o ambiente, comece pelo [`README.md`](../README.md) da raiz.

## Sistema

- [Visão geral](sistema/visao-geral.md): finalidade, usuários, funcionalidades, tecnologias, entidades e limites.

## Arquitetura

- [Visão geral](arquitetura/visao-geral.md): processos, caminho da requisição, apps, extensão por registro, padrões, tempo real.
- [Estrutura do projeto](arquitetura/estrutura-do-projeto.md): diretórios, módulos de cada app, comandos de gerenciamento, `sources/`.
- [Motor de importação](arquitetura/motor-de-importacao.md): contrato, leitura, situações, transições, worker, prévia e confirmação.

## Funcionalidades

| Documento | Conteúdo |
|---|---|
| [Autenticação, usuários e perfis](funcionalidades/autenticacao-e-usuarios.md) | Login, recuperação de senha, usuários, perfis, superadmin, importação de usuários |
| [Ensalamento](funcionalidades/ensalamento.md) | Grade, cancelamento de ocorrência, recorrências, importação da planilha, espaços encontrados |
| [Espaços](funcionalidades/espacos.md) | Cadastro, nomes, situação, exclusão |
| [Disciplinas e turmas](funcionalidades/disciplinas-e-turmas.md) | Cadastros, escopo do docente, ofertas e vínculos |
| [Agenda](funcionalidades/agenda.md) | Solicitações, análise, alternativa, cancelamento, criação para outro usuário |
| [Calendário público](funcionalidades/calendario-publico.md) | Telas sem login, filtros, cache |
| [Painel e relatórios](funcionalidades/painel-e-relatorios.md) | Painel administrativo, mapa de calor, relatório de solicitações |
| [Notificações](funcionalidades/notificacoes.md) | Sino, tempo real, publicação manual |
| [Auditoria](funcionalidades/auditoria.md) | O que é registrado, origem, consulta |
| [E-mails e servidor SMTP](funcionalidades/emails.md) | Outbox, worker, configuração do servidor |

## Regras

- [Regras de negócio](regras/regras-de-negocio.md): todas as regras confirmadas, com o local da implementação, e o que não está implementado.
- [Permissões](regras/permissoes.md): catálogo, perfis do sistema, superadmin, verificações além da rota, menu.

## Desenvolvimento

- Ambiente local: [`README.md`](../README.md) da raiz (pré-requisitos, comandos, variáveis, dependências).
- [Testes](desenvolvimento/testes.md): como rodar, testes transversais, regras para escrever testes.
- [Convenções](desenvolvimento/convencoes.md): idioma, documentação, controle de acesso, organização do código, testes, commits, texto e visual da interface, e os pontos a tocar em cada extensão.

## Operação

- [Configuração](operacao/configuracao.md): variáveis obrigatórias, configuração no banco, o que não está configurado.
- [Banco de dados](operacao/banco-de-dados.md): recursos do PostgreSQL usados, migrations, comandos de dados.
- [Deploy](operacao/deploy.md): o que existe, o que falta, passos depois de subir uma instância.

## Decisões

- [Decisões técnicas](decisoes/README.md): as decisões que explicam a forma do sistema e o motivo registrado de cada uma.

## Outras fontes

| Fonte | Conteúdo |
|---|---|
| [Princípios do TCC](sistema/visao-geral.md#princípios-do-tcc) | Princípios e requisitos não funcionais extraídos do TCC |
| `sources/TCC_REVISADO (1).pdf` | Texto do TCC, fonte do escopo |
