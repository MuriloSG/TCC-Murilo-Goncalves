def add_operation_error(form, error):
    """Leva para o formulário o ValidationError lançado por uma operação do model."""
    if hasattr(error, 'error_dict'):
        for field, errors in error.error_dict.items():
            form.add_error(field if field in form.fields else None, errors)
    else:
        form.add_error(None, error)
