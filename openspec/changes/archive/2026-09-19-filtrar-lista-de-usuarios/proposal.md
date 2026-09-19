## Why

A gestão de usuários (RF04) lista todos os usuários numa única tabela, ordenada por nome. Com os docentes do campus cadastrados, encontrar uma pessoa ou ver só quem está inativo passa a exigir rolar a lista inteira. A Change `definir-identidade-visual` desenhou o cartão da lista com espaço para a busca e o filtro, e o autor pediu que eles entrem como funcionalidade, com requisito na spec.

Depende da Change `definir-identidade-visual`, que cria o cartão da lista, os campos e o htmx.

## What Changes

- **Busca por nome ou e-mail** na lista de usuários, sem diferenciar maiúsculas de minúsculas, por trecho do texto.
- **Filtro por situação:** todas, ativos ou inativos.
- **Combinação:** busca e filtro valem juntos, e o estado fica na URL (`?busca=ana&situacao=ativos`), que pode ser salva, compartilhada e usada com o botão Voltar do navegador.
- **Contagem:** o rodapé mostra "Exibindo X de Y usuários", em que Y é o total cadastrado.
- **Estado vazio da busca:** "Nenhum usuário encontrado para a busca." com o link "Limpar busca".
- **Atualização sem recarregar:** com o htmx, a tabela é atualizada enquanto se digita, com intervalo de 300 ms. Sem JavaScript, o formulário é enviado com Enter e funciona do mesmo jeito.
- **Filtros preservados:** depois de uma ação feita em modal a partir da lista filtrada, a lista volta com os mesmos filtros.

### Fora do escopo

- Busca e filtro na lista de perfis, que tem poucos registros.
- Filtro por perfil, paginação e ordenação por coluna.
- Busca sem acentos (por exemplo, "joao" encontrar "João"), que exigiria a extensão `unaccent` do PostgreSQL.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities
- `gestao-usuarios`: novo requisito de busca e filtro na lista de usuários.

## Impact

- **Código alterado:** `UserListView` (filtragem da consulta e contagem), `accounts/forms.py` (formulário de filtros) e `user_list.html` (formulário no cabeçalho do cartão e fragmento da tabela para o htmx).
- **Testes:** novos testes da view de lista.
- **Sem mudança** em models, URLs, permissões ou dependências.

## Alinhamento com o TCC

- **RF04:** a busca apoia a gestão de usuários pelo administrador, sem mudar quem pode gerenciar.
- **RNF05 e Seção 2.3.8:** reconhecimento em vez de memorização. O estado da busca fica visível no formulário e na contagem.
- **P3:** a filtragem é feita pelo ORM, com parâmetros, sem SQL montado a partir do texto digitado.
