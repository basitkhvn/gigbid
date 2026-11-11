from mcp_servers.portfolio.tools import get_case_study


def case_resource(persona: str, id_: str) -> str:
    it = get_case_study(persona, id_)
    return f"# {it['title']}\n\n{it['text']}\n\nskills: {', '.join(it.get('skills', []))}\nindustry: {it.get('industry')}\ndate: {it.get('date')}"


def proposal_resource(persona: str, id_: str) -> str:
    it = get_case_study(persona, id_)
    return f"Past proposal ({it.get('outcome')}):\n\n{it['text']}"
