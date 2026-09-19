"""Motor de importação de planilhas CSV.

Lê o arquivo, confere a estrutura, gera a prévia executando e desfazendo as
operações e só confirma quando o plano continua idêntico. Não conhece nenhuma
regra de domínio: cada app fornece a sua importação por uma ImportDefinition
(Change importar-usuarios-por-planilha).
"""
