# Testes do app `tutorials`

Central de ajuda. Funcionalidade em [central de ajuda](../../funcionalidades/central-de-ajuda.md). Os testes conferem o catálogo, as imagens e a página.

### `test_catalog.py`

| Classe | O que garante |
|---|---|
| `CatalogTests` | Identificadores únicos e módulos com funcionalidades; permissões das funcionalidades e dos passos no catálogo de `accounts/permissions.py`; todo passo com instrução, texto alternativo e marcadores; as imagens do computador e do celular de cada passo existem; o botão do fim abre uma rota cuja permissão está entre as da funcionalidade; cada `Screen` corresponde a uma opção do menu e cada funcionalidade, menos a de uso geral, está numa tela só |

### `test_views.py`

| Classe | O que garante |
|---|---|
| `HelpCenterTests` | Quem solicita vê a Agenda e o uso geral, e não a administração; o conteúdo sem permissão não chega ao HTML; sem permissões, só o uso geral; o superadmin vê tudo; cada passo segue a própria permissão; funcionalidade sem passo liberado fica de fora; imagens com texto alternativo e versão do celular; botão do fim; o link da ajuda leva a tela de origem; a ajuda da tela mostra só as funcionalidades dela, sem o índice, segue as permissões e aponta a trilha para a tela liberada do menu; tela sem ajuda liberada mostra o aviso; sem tela conhecida, a central completa; a navegação lista só as funcionalidades liberadas e, na ajuda de tela, só aparece com mais de uma |

