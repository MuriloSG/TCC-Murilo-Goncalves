# Testes do app `ui`

Layout, navegação, componentes e as varreduras de texto e de classes que valem para todo o projeto. Regras de texto e visual na seção 9 das [convenções](../convencoes.md#9-interface-e-texto); varreduras resumidas em [testes transversais](../testes.md#testes-transversais).

## Auxiliares

- `files.py`: lista os diretórios dos apps e do pacote de configuração, os templates e os módulos Python percorridos pelas varreduras (sem testes, migrations e o `text_rules`).

## Varreduras do projeto

### `test_interface_text.py`

| Classe | O que garante |
|---|---|
| `ProjectTextTests` | Todos os templates e módulos Python seguem as regras de texto |
| `TemplateExtractionTests` | A extração de texto de template aponta linha e trecho, ignora operadores, doctype e comentários do Django, troca variáveis por marcador, considera atributos visíveis, títulos de bloco e o elemento inteiro, e trata `.txt` como todo visível |
| `PythonExtractionTests` | A extração em Python aponta módulo e linha, ignora docstrings e logger e trata f-strings |
| `RenderedPagesTextTests` | Telas renderizadas de gestão, acesso negado, login, senha e logout seguem as regras |

### `test_text_rules.py`

| Classe | O que garante |
|---|---|
| `TextRulesTests` | Cada regra é detectada: exclamação, reticências, travessão, interjeição, saudação, mensagem vaga, "por favor" e "com sucesso", marketing, tratamento impessoal, emoji, glossário, códigos de permissão como dado, maiúsculas em títulos e botões, título com dois pontos |
| `AccountAdapterMessagesTests` | As mensagens sobrescritas do allauth existem na versão instalada |

### `test_template_classes.py`

| Classe | O que garante |
|---|---|
| `ProjectTemplateClassesTests` | Templates usam só a escala de tokens |
| `ClassRulesTests` | A varredura aponta valor arbitrário, cor da paleta padrão, `style=`, passo fora da escala, tamanho de fonte, raio e largura, sombra fora de camada flutuante; aceita tags do Django no atributo e componentes pelo nome |

### `test_contrast.py`

`ContrastTests`: todos os pares de `ui/contrast.py` atingem o mínimo AA nos dois temas; todo token de cor tem par ou está isento; o tema escuro redefine página e texto; texto secundário abaixo do mínimo e token novo sem par fazem o teste falhar.

## Layout e componentes

### `test_base.py`

| Classe | O que garante |
|---|---|
| `AppLayoutTests` | O primeiro focável é o link para o conteúdo; item atual e trilha marcados; sino no cabeçalho e no celular, com o painel do usuário; barra lateral recolhida pelo cookie; confirmação de saída em modal e em página sem JavaScript; navegação sem perfis; htmx e CSRF só nas páginas autenticadas |
| `ExternalResourcesTests` | As páginas só usam endereços do próprio sistema, inclusive as fontes |
| `BrandTests` | Título e ícone do sistema em toda página, com os arquivos presentes |

### `test_navigation.py`

| Classe | O que garante |
|---|---|
| `GroupVisibilityTests` | Cada item do menu segue a própria permissão; um item não libera os demais; visualizar não libera as ações e ação sem visualizar não mostra o item |
| `UserImportEntryTests` | "Usuários" leva à tela permitida, inclusive às importações para quem só importa |
| `CurrentItemTests` | O grupo da página atual abre com o item marcado, na barra lateral e no celular |
| `RoutesTests` | Os links do menu abrem para quem tem acesso; o início abre o primeiro item liberado |

### `test_select.py`

`SelectComponentTests`: o componente `ui/components/select.html` envolve o `select` nativo, começa oculto para o caso sem JavaScript, associa o rótulo e é usado por todo campo de escolha do projeto.

### `test_pagination.py`

`PaginateTests`: primeira página por padrão, última, páginas inválidas ou fora do intervalo; o link da primeira página não leva `page` e mantém os demais parâmetros; página única, singular e vazio; alvo do htmx.

### `test_loading.py`

`GlobalLoadingTests`: o carregamento global existe uma vez, oculto, nas páginas autenticadas, no login e no calendário público.

### `test_formats.py`

`BrazilianFormatsTests`: datas, horas e números no formato brasileiro.
