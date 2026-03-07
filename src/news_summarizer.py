"""Generate ELI5 (Explain Like I'm 5) summaries for research papers."""

from openai import OpenAI


def summarize_research(research: dict, api_key: str) -> dict:
    """
    Generate a simple, jargon-free summary for a research paper.

    Summaries are written so a kid or grandma could understand them.

    Args:
        research: Research paper dictionary with title, description, source, url, authors
        api_key: OpenAI API key

    Returns:
        Research dictionary with added 'summary' field
    """
    if not api_key:
        return research

    client = OpenAI(api_key=api_key)

    authors = research.get("authors", "Unknown")

    prompt = f"""You explain AI research to someone with NO technical background - like a grandma or a kid.

Paper: {research['title']}
Authors: {authors}
Abstract: {research['description']}

Write 4-5 simple sentences explaining:
1. What problem were the researchers trying to solve?
2. What did they build or discover? (use simple analogies)
3. How does it work in simple terms?
4. Why should a regular person care? How might this affect their life someday?

RULES:
- NO jargon (no "transformer", "architecture", "benchmark", "SOTA", "LLM", "neural network", "model", "parameters")
- Use everyday analogies (like teaching, cooking, organizing, finding things, etc.)
- Write like you're explaining to a curious grandma over coffee
- Be warm and conversational

Example good summary:
"You know how it's hard to find exactly what you're looking for when you have a messy desk? Researchers figured out a way to help AI organize information better so it can find the right answer faster. They taught it to sort through piles of information like a librarian who knows exactly where every book is. This could make future AI assistants much quicker at answering your questions - no more waiting around!"

Now write the summary:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7,
        )

        summary = response.choices[0].message.content.strip()
        research_with_summary = research.copy()
        research_with_summary["summary"] = summary
        return research_with_summary

    except Exception as e:
        print(f"Warning: Could not generate summary: {e}")
        return research
