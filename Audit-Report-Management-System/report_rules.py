from config import TEMPLATE_RULES, ENTITY_OPTIONS, OPINION_OPTIONS


def select_template(entity_type: str, small_company: bool, opinion: str) -> str:
    key = (entity_type, bool(small_company), opinion)
    try:
        return TEMPLATE_RULES[key]
    except KeyError:
        raise ValueError(f'No Stage 1 template rule exists for: {key}')


def classification_label(entity_type: str, small_company: bool) -> str:
    base = ENTITY_OPTIONS.get(entity_type, entity_type)
    return f'{base} – Small Company' if small_company else base


def opinion_label(opinion: str) -> str:
    return OPINION_OPTIONS.get(opinion, opinion)
