PROMPTS = {
    "answer_screening_question": "Answer this client screening question using ONLY my portfolio. Search it with search_evidence, cite item ids, and say honestly if I lack experience:\n\nQUESTION: {question}",
    "draft_cover_letter": "Draft a 150-word cover letter for this job. Use search_evidence per requirement and cite evidence ids. Never invent experience.\n\nJOB: {job}",
    "what_have_i_won_with": "Using proposals with outcome=won or replied, tell me which of my past phrasing and projects worked best for {skill}.",
}
