# Sistema Web para Agendamento de Espaços Físicos no IFNMG – Campus Salinas

Este repositório reúne os artefatos do Trabalho de Conclusão de Curso desenvolvido por Murilo Santos Gonçalves no âmbito do Bacharelado em Sistemas de Informação do Instituto Federal do Norte de Minas Gerais – Campus Salinas, sob orientação do professor Arthur Farias Porto e coorientação da professora Jessica Gloria.

Aqui estão versionados o texto do TCC, na pasta [`TCC/`](TCC/), e a implementação do sistema, chamado **IFAgenda**, na pasta [`implementacao-tcc/`](implementacao-tcc/), acompanhada da sua documentação técnica.

## Por onde começar

| Quero… | Onde |
|---|---|
| Ler o texto do TCC | [`TCC/main.pdf`](TCC/main.pdf) (fonte em [`TCC/main.tex`](TCC/main.tex)) |
| Rodar o sistema localmente | [`implementacao-tcc/README.md`](implementacao-tcc/README.md) |
| Entender como o sistema funciona | [`implementacao-tcc/docs/README.md`](implementacao-tcc/docs/README.md) |

## Sobre o trabalho

A proposta tem origem em um problema concreto identificado no IFNMG – Campus Salinas: o processo de agendamento dos laboratórios e demais espaços compartilhados é conduzido de forma manual. A cada início de semestre, os horários já ocupados pelas aulas regulares precisam ser recadastrados antes que qualquer reserva possa ser efetuada. Como consequência, os docentes não dispõem de autonomia para consultar a disponibilidade dos espaços ou solicitar reservas, e a instituição não possui um registro consolidado sobre a utilização efetiva dos ambientes.

O trabalho propõe a substituição desse processo por um sistema web cujas principais funcionalidades são:

- Importação das planilhas de horários institucionais já produzidas pelo campus, em substituição ao cadastro manual sala por sala;
- Consulta de disponibilidade e submissão de solicitações de reserva pelos próprios docentes;
- Notificação automática por e-mail quando uma solicitação é submetida e quando é aprovada ou rejeitada;
- Geração de relatórios sobre a utilização dos espaços, oferecendo à administração uma visão consolidada da ocupação;
- Consulta pública de disponibilidade, sem necessidade de autenticação, exibindo apenas horários livres e ocupados, sem expor dados pessoais.

O controle de acesso adota o modelo RBAC (*Role-Based Access Control*), com dois perfis autenticados — **Administrador** e **Docente** — e um acesso público de **Visualizador**, restrito à consulta de disponibilidade.

## Documentação do sistema

A documentação completa fica em [`implementacao-tcc/docs/`](implementacao-tcc/docs/README.md). Os pontos de entrada principais:

- [Visão geral](implementacao-tcc/docs/sistema/visao-geral.md): finalidade, usuários, funcionalidades, tecnologias, entidades e limites.
- [Funcionalidades](implementacao-tcc/docs/README.md#funcionalidades): ensalamento, agenda, espaços, calendário público, painel e relatórios, notificações, auditoria, e-mails e central de ajuda.
- [Regras de negócio](implementacao-tcc/docs/regras/regras-de-negocio.md) e [permissões](implementacao-tcc/docs/regras/permissoes.md): o que o sistema garante e quem pode fazer o quê.
- [Arquitetura](implementacao-tcc/docs/arquitetura/visao-geral.md): apps, padrões e [motor de importação](implementacao-tcc/docs/arquitetura/motor-de-importacao.md) das planilhas.
- [Diagramas](implementacao-tcc/docs/diagramas/README.md): DER conceitual e DER físico, com as restrições do banco.
- [Testes](implementacao-tcc/docs/desenvolvimento/testes.md) e [convenções](implementacao-tcc/docs/desenvolvimento/convencoes.md) de desenvolvimento.
- [Configuração](implementacao-tcc/docs/operacao/configuracao.md), [banco de dados](implementacao-tcc/docs/operacao/banco-de-dados.md) e [deploy](implementacao-tcc/docs/operacao/deploy.md), com os [requisitos de deploy e de e-mails](implementacao-tcc/docs/operacao/requisitos-de-deploy.md).
- [Decisões técnicas](implementacao-tcc/docs/decisoes/README.md): o motivo registrado de cada escolha que dá forma ao sistema.

## Tecnologias

A pilha tecnológica foi definida com base nos requisitos especificados e na busca por manutenibilidade, segurança e baixo acoplamento a bibliotecas externas:

- **Python e Django 5.2** — *framework* web que segue o princípio *batteries included*, com arquitetura MTV (*Model-Template-View*), ORM próprio, sistema de *templates*, envio nativo de e-mails e proteções padrão contra CSRF, XSS e injeção de SQL;
- **PostgreSQL 17** — sistema gerenciador de banco de dados relacional, acessado exclusivamente por meio do ORM do Django;
- **Tailwind CSS 4** — *framework* de estilos utilitário, adotado na camada de apresentação;
- **django-allauth** — biblioteca responsável pela autenticação, recuperação de senha e gestão de sessões;
- **SMTP** — protocolo utilizado para o envio das notificações automáticas;
- **Docker e Docker Compose** — todo o ambiente de desenvolvimento roda em containers, sem instalar Python, Node.js ou PostgreSQL na máquina.

As versões fixadas estão em [`requirements.txt`](implementacao-tcc/requirements.txt) e [`package.json`](implementacao-tcc/package.json).

## Estrutura do repositório

```
.
├── README.md                 # Este arquivo
├── TCC/
│   ├── main.tex              # Documento principal (modelo ABNTeX2 adotado pelo curso)
│   ├── main.pdf              # Texto compilado
│   ├── referencias.bib       # Referências em BibTeX
│   └── Figuras/              # Imagens e diagramas UML utilizados no texto
└── implementacao-tcc/        # Sistema IFAgenda
    ├── README.md             # Ambiente de desenvolvimento
    ├── docs/                 # Documentação do sistema
    ├── config/               # Configuração do projeto Django
    ├── accounts/, bookings/, schedule/, …  # Apps Django
    ├── Makefile              # Comandos do dia a dia
    └── compose.yaml          # Serviços Docker
```

O detalhamento de cada app está em [`estrutura-do-projeto.md`](implementacao-tcc/docs/arquitetura/estrutura-do-projeto.md).

## Execução do sistema

Com Docker e `make` instalados, a partir de `implementacao-tcc/`:

```bash
make up                                # constrói as imagens, sobe os containers e gera o CSS
make migrate                           # aplica as migrations e cria os perfis e as permissões
make manage cmd="create_superadmin"    # cria o primeiro superadmin
```

O calendário público abre em `http://localhost:8000/` e o login em `http://localhost:8000/contas/login/`. Pré-requisitos, comandos, variáveis de ambiente e a configuração de e-mails estão em [`implementacao-tcc/README.md`](implementacao-tcc/README.md#primeira-execução).

## Compilação da escrita

A forma mais direta de compilar o documento é por meio do Overleaf, que disponibiliza o pacote ABNTeX2 já configurado, dispensando configurações adicionais.

Para compilação local, é necessário dispor de uma distribuição TeX recente (TeX Live ou MiKTeX) com o pacote `abntex2` instalado. A partir da pasta `TCC/`, executa-se a seguinte sequência:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```
