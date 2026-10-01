from django.test import SimpleTestCase

from ui import contrast


class ContrastTests(SimpleTestCase):
    def setUp(self):
        self.css = contrast.STYLES.read_text(encoding='utf-8')

    def test_todos_os_pares_atingem_o_minimo(self):
        failures = contrast.all_contrast_failures(self.css)
        self.assertEqual(failures, [], '\n'.join(failures))

    def test_todo_token_de_cor_tem_par_ou_esta_isento(self):
        self.assertEqual(contrast.uncovered_tokens(self.css), [])

    def test_valores_da_tabela_do_design(self):
        colors = contrast.read_colors(self.css)
        for foreground, background, expected in (
            ('text-muted', 'surface', 6.29),
            ('control-border', 'surface', 3.12),
            ('on-sidebar', 'sidebar', 15.12),
            ('on-sidebar-muted', 'sidebar', 5.91),
            ('on-fill', 'action', 5.88),
            ('warning-icon', 'warning-bg', 3.06),
        ):
            with self.subTest(pair=(foreground, background)):
                ratio = contrast.contrast_ratio(colors[foreground], colors[background])
                self.assertAlmostEqual(ratio, expected, places=2)

    def test_barra_lateral(self):
        colors = contrast.read_colors(self.css)
        self.assertGreaterEqual(contrast.contrast_ratio(colors['on-sidebar'], colors['sidebar']), 4.5)
        self.assertGreaterEqual(contrast.contrast_ratio(colors['on-sidebar-muted'], colors['sidebar']), 4.5)
        self.assertGreaterEqual(contrast.contrast_ratio(colors['sidebar-accent'], colors['sidebar']), 3)
        self.assertGreaterEqual(contrast.contrast_ratio(contrast.SYMBOL_GREEN, colors['sidebar']), 3)

    def test_borda_de_campo(self):
        colors = contrast.read_colors(self.css)
        self.assertGreaterEqual(contrast.contrast_ratio(colors['control-border'], colors['surface']), 3)

    def test_tema_escuro_redefine_a_pagina_e_o_texto(self):
        light = contrast.read_colors(self.css)
        dark = contrast.read_colors(self.css, 'dark')
        self.assertNotEqual(dark['page'], light['page'])
        self.assertNotEqual(dark['text'], light['text'])
        self.assertGreater(contrast.luminance(dark['text']), contrast.luminance(dark['page']))

    def test_texto_secundario_do_tema_escuro_abaixo_do_minimo_falha(self):
        css = self.css.replace('--color-text-muted: var(--palette-dark-200);', '--color-text-muted: #595E61;')
        self.assertNotEqual(css, self.css)
        failures = contrast.all_contrast_failures(css)
        self.assertEqual(contrast.contrast_failures(css), [])
        self.assertTrue(any(failure.startswith('tema escuro:') for failure in failures), failures)

    def test_texto_secundario_abaixo_do_minimo_falha(self):
        css = self.css.replace('--color-text-muted: var(--palette-neutral-700);', '--color-text-muted: #7B7677;')
        self.assertNotEqual(css, self.css)
        failures = contrast.contrast_failures(css)
        self.assertTrue(any('text-muted #7B7677 sobre surface #FFFFFF): 4,47:1, mínimo 4,50:1' in failure
                            for failure in failures), failures)

    def test_token_novo_sem_par_e_apontado(self):
        css = self.css.replace('--color-page:', '--color-highlight: var(--palette-green-100);\n  --color-page:')
        self.assertEqual(contrast.uncovered_tokens(css), ['highlight'])
