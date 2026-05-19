# Sistema Web para Agendamento de Espaços Físicos no IFNMG – Campus Salinas

Este repositório reúne os artefatos do Trabalho de Conclusão de Curso desenvolvido por Murilo Santos Gonçalves no âmbito do Bacharelado em Sistemas de Informação do Instituto Federal do Norte de Minas Gerais – Campus Salinas, sob orientação do professor Arthur Farias Porto e coorientação da professora Jessica Gloria.

Nesta etapa, encontra-se versionada a escrita do TCC 1, correspondente ao projeto de pesquisa. A implementação do sistema está prevista para o TCC 2, ao longo do segundo semestre de 2026, e o respectivo código-fonte será incorporado a este mesmo repositório à medida que o desenvolvimento avançar.

## Sobre o trabalho

A proposta tem origem em um problema concreto identificado no IFNMG – Campus Salinas: o processo de agendamento dos laboratórios e demais espaços compartilhados é conduzido de forma manual. A cada início de semestre, os horários já ocupados pelas aulas regulares precisam ser recadastrados antes que qualquer reserva possa ser efetuada. Como consequência, os docentes não dispõem de autonomia para consultar a disponibilidade dos espaços ou solicitar reservas, e a instituição não possui um registro consolidado sobre a utilização efetiva dos ambientes.

O trabalho propõe a substituição desse processo por um sistema web cujas principais funcionalidades são:

- Importação das planilhas de horários institucionais já produzidas pelo campus, em substituição ao cadastro manual sala por sala;
- Consulta de disponibilidade e submissão de solicitações de reserva pelos próprios docentes;
- Notificação automática por e-mail quando uma solicitação é submetida e quando é aprovada ou rejeitada;
- Geração de relatórios sobre a utilização dos espaços, oferecendo à administração uma visão consolidada da ocupação;
- Consulta pública de disponibilidade, sem necessidade de autenticação, exibindo apenas horários livres e ocupados, sem expor dados pessoais.

O controle de acesso adota o modelo RBAC (*Role-Based Access Control*), com dois perfis autenticados — **Administrador** e **Docente** — e um acesso público de **Visualizador**, restrito à consulta de disponibilidade.

## Tecnologias previstas para o TCC 2

A pilha tecnológica foi definida com base nos requisitos especificados e na busca por manutenibilidade, segurança e baixo acoplamento a bibliotecas externas:

- **Python e Django** — *framework* web que segue o princípio *batteries included*, com arquitetura MTV (*Model-Template-View*), ORM próprio, sistema de *templates*, envio nativo de e-mails e proteções padrão contra CSRF, XSS e injeção de SQL;
- **PostgreSQL** — sistema gerenciador de banco de dados relacional, acessado exclusivamente por meio do ORM do Django;
- **Tailwind CSS** — *framework* de estilos utilitário, adotado na camada de apresentação;
- **django-allauth** — biblioteca responsável pela autenticação, registro, recuperação de senha e gestão de sessões;
- **SMTP (Gmail)** — protocolo e serviço utilizados para o envio das notificações automáticas.

## Estrutura do repositório

```
.
├── README.md
└── TCC/
    ├── main.tex          # Documento principal (modelo ABNTeX2 adotado pelo curso)
    ├── referencias.bib   # Referências em BibTeX
    └── Figuras/          # Imagens utilizadas no texto
```

A pasta `TCC/` concentra o material referente à escrita do TCC 1. O código-fonte do sistema, quando iniciado o desenvolvimento, será organizado em diretório próprio na raiz do repositório.

## Compilação da escrita

A forma mais direta de compilar o documento é por meio do Overleaf, que disponibiliza o pacote ABNTeX2 já configurado, dispensando configurações adicionais.

Para compilação local, é necessário dispor de uma distribuição TeX recente (TeX Live ou MiKTeX) com o pacote `abntex2` instalado. A partir da pasta `TCC/`, executa-se a seguinte sequência:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```
