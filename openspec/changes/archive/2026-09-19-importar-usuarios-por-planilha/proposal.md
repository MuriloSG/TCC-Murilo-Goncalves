## Why

Hoje cada usuário é cadastrado um a um. No início de cada semestre, o administrador precisa cadastrar os docentes novos e ajustar o perfil de quem mudou de função, repetindo o mesmo formulário dezenas de vezes. O TCC já prevê uma segunda importação, a das planilhas de horários (RF01 e RF02), que terá o mesmo ciclo de ler um arquivo, conferir e aplicar. Por isso esta Change cria um motor de importação reutilizável e o usa primeiro com os usuários, cujo model e cujas regras já estão prontos e testados.

Depende da Change `enviar-emails-por-outbox`, que cria o outbox e o worker de envio de e-mails. A importação registra no outbox o link de definição de senha dos usuários cadastrados e não pode ser implementada antes dela.

## What Changes

- **Motor de importação** num app novo, desacoplado dos apps de domínio:
  - leitura de CSV em UTF-8 (com ou sem BOM), com separador `;`, limite de tamanho e de linhas definido em configuração e conferência do cabeçalho (coluna desconhecida, ausente ou duplicada);
  - **prévia por executar e desfazer:** as operações reais do model rodam numa transação que sofre rollback, e só o plano de cada linha é gravado;
  - **confirmação só com o plano idêntico:** a importação é reexecutada com o executor atual e aplicada numa única transação apenas se o plano for igual ao da prévia. Se divergir, nada é gravado e a nova prévia substitui a anterior;
  - importação persistida com situação (`VALIDADA`, `COM_ERROS`, `CONCLUIDA` e `DESCARTADA`), plano por linha e dados de auditoria, sem guardar o arquivo;
  - classes base de view para envio, prévia, confirmação, descarte, histórico e detalhe.
- **Importação de usuários** em `accounts`:
  - colunas `E-mail`, `Nome` e `Perfil` (código do perfil), todas obrigatórias;
  - cadastro de e-mails novos e atualização de nome e perfil dos existentes (upsert pelo e-mail). O e-mail nunca é alterado e a situação do usuário nunca muda;
  - cada ação da linha exige a permissão correspondente do executor (`USUARIO.CRIAR`, `USUARIO.EDITAR` e `USUARIO.ALTERAR_PERFIL`), e a falta dela vira erro na prévia;
  - continuidade administrativa verificada uma vez, no fim da importação;
  - registro no outbox do link de definição de senha de cada usuário cadastrado;
  - rotas em `usuarios/importacoes/`, com histórico dentro de Usuários e modelo CSV para baixar.
- **Nova permissão `USUARIO.IMPORTAR`**, concedida ao perfil de sistema `ADMINISTRADOR` por migration de dados, fora do conjunto de capacidade administrativa e fora das permissões reservadas ao superadmin.
- **Operações do model de usuários preparadas para lote:** a verificação da continuidade administrativa pode ser adiada para o fim de uma transação externa. O comportamento das telas atuais não muda.

### Fora do escopo

- O outbox e o worker, que são da Change `enviar-emails-por-outbox`.
- A importação de horários.
- Arquivos `.xlsx`, codificações além de UTF-8 e separador por tipo de importação.
- Colunas opcionais, previstas no contrato do motor, mas sem implementação até que uma importação as use.
- Processamento assíncrono, progresso, lotes, cancelamento e o estado de falha.
- Tela genérica "Importações", registro central de tipos e permissão separada para ver o histórico.
- Correção de células pela tela, desativação ou reativação pela importação e vínculo entre o usuário e a importação que o criou.
- Exclusão e limpeza do histórico.

## Capabilities

### New Capabilities
- `importacao-planilhas`: motor de importação de arquivos CSV, com leitura, conferência da estrutura, prévia por executar e desfazer, confirmação condicionada ao plano idêntico, situações da importação, histórico e contrato das importações específicas.

### Modified Capabilities
- `gestao-usuarios`: novo requisito de importação de usuários por planilha; o conjunto de capacidade administrativa passa a ser listado pelos códigos, sem incluir `USUARIO.IMPORTAR`; a continuidade administrativa passa a valer para a importação, verificada no fim dela.
- `controle-acesso`: o catálogo ganha `USUARIO.IMPORTAR`, concedida ao `ADMINISTRADOR`, e a correspondência entre operações e permissões inclui a importação.

## Impact

- **App novo:** motor de importação, com models, migration, views base e templates das telas de importação.
- **`accounts`:** definição da importação de usuários, rotas e views em `usuarios/importacoes/`, constante `USER_IMPORT` no `permissions.py`, migration de dados da permissão, ajuste da continuidade administrativa em `models.py` e botão "Importar usuários" na lista.
- **Testes:** motor, importação de usuários, acesso às rotas e catálogo de permissões (que passa de dez para onze permissões).
- **Dependências:** nenhuma biblioteca nova. A leitura usa o módulo `csv` do Python.
- **Interface:** telas novas de envio, prévia, histórico e detalhe, desenhadas a partir de imagem de referência, conforme a seção 9.8 das convenções.

## Alinhamento com o TCC

- **RF04:** a importação é uma forma de gerenciar usuários e seus perfis, restrita a quem tem a permissão.
- **RF01 e RF02:** o motor é a base da importação de horários, que usa o mesmo ciclo de prévia, confirmação e reimportação.
- **P2 e P4:** a regra de negócio continua só no model. A importação chama as operações existentes e não reescreve validações.
- **P5 e RNF01:** cada ação da planilha exige a mesma permissão que exigiria na tela.
- **P7:** a prévia mostra o que vai acontecer antes de gravar, o que atende às heurísticas de visibilidade do estado e de prevenção de erros.
