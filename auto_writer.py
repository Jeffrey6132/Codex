#!/usr/bin/env python3
"""A simple automatic writing assistant.

This script breaks down a writing task into themed subtopics, performs
DuckDuckGo searches to gather supporting information, summarises the gathered
material, and assembles the result into a short essay-style article.

Usage:
    python auto_writer.py "Topic" --word-target 800 --sections 4

The script prints the final article to standard output and optionally saves it
into a file when ``--output`` is provided.
"""

from __future__ import annotations

import argparse
import html
import logging
import sys
import textwrap
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, List

import nltk
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS


@dataclass
class SectionSummary:
    """Container for a section of the final article."""

    heading: str
    content: str
    sources: List[str]


def ensure_nltk_resources() -> None:
    """Ensure that the required NLTK data packages are available."""

    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)
    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords", quiet=True)


def generate_subtopics(topic: str, desired: int) -> List[str]:
    """Generate subtopic prompts for the provided topic.

    The templates aim to cover background, developments, applications,
    challenges, and future directions. When more sections are required, a few
    additional angles are synthesised in a generic manner.
    """

    templates = [
        "Background and origins of {topic}",
        "Important milestones in the evolution of {topic}",
        "Current applications and real-world examples of {topic}",
        "Benefits, limitations, or controversies around {topic}",
        "Future outlook and emerging trends for {topic}",
    ]

    extra_templates = [
        "Impact of {topic} on society and daily life",
        "Economic or industry implications of {topic}",
        "Notable figures, organisations, or case studies linked to {topic}",
        "Ethical considerations associated with {topic}",
        "Comparisons between {topic} and related fields",
    ]

    prompts: List[str] = []
    for template in templates:
        if len(prompts) >= desired:
            break
        prompts.append(template.format(topic=topic))

    extra_iter = iter(extra_templates)
    while len(prompts) < desired:
        try:
            template = next(extra_iter)
        except StopIteration:
            template = "Additional perspective on {topic}"
        prompts.append(template.format(topic=topic))

    return prompts


def perform_search(query: str, max_results: int) -> List[dict]:
    """Use DuckDuckGo to collect search results for the query."""

    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results, safesearch="moderate"))
    return results


def fetch_article_text(url: str, timeout: float = 10.0) -> str:
    """Fetch and clean main text content from a web page."""

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
    except requests.RequestException:
        return ""

    if not response.ok or "text" not in response.headers.get("Content-Type", ""):
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    for script in soup(["script", "style", "noscript"]):
        script.decompose()

    texts = [
        paragraph.get_text(separator=" ", strip=True)
        for paragraph in soup.find_all("p")
    ]
    cleaned = " ".join(texts)
    cleaned = html.unescape(cleaned)
    return cleaned


def summarise_text(text: str, sentence_count: int = 5) -> str:
    """Return a naive extractive summary using word frequency scoring."""

    if not text:
        return ""

    sentences = nltk.sent_tokenize(text)
    if len(sentences) <= sentence_count:
        return " ".join(sentences)

    words = [word.lower() for word in nltk.wordpunct_tokenize(text)]
    stop_words = set(nltk.corpus.stopwords.words("english"))
    words = [word for word in words if word.isalpha() and word not in stop_words]

    if not words:
        return " ".join(sentences[:sentence_count])

    frequency = Counter(words)

    sentence_scores = {}
    for sentence in sentences:
        sentence_lower = sentence.lower()
        sentence_scores[sentence] = sum(
            frequency[word]
            for word in nltk.wordpunct_tokenize(sentence_lower)
            if word in frequency
        )

    ranked_sentences = sorted(
        sentence_scores.items(), key=lambda item: item[1], reverse=True
    )
    top_sentences = [sentence for sentence, _ in ranked_sentences[:sentence_count]]
    top_sentences.sort(key=lambda sentence: sentences.index(sentence))
    return " ".join(top_sentences)


def gather_information(subtopic: str, max_articles: int, summary_sentences: int) -> SectionSummary:
    """Collect supporting information for a subtopic and summarise it."""

    logging.info("Searching for subtopic: %s", subtopic)
    search_results = perform_search(subtopic, max_results=max_articles * 4)

    collected_texts: List[str] = []
    sources: List[str] = []
    for result in search_results:
        url = result.get("href") or result.get("url")
        if not url:
            continue
        if url in sources:
            continue

        logging.info("Fetching %s", url)
        article_text = fetch_article_text(url)
        if len(article_text) < 500:
            continue

        collected_texts.append(article_text)
        sources.append(url)
        if len(collected_texts) >= max_articles:
            break

    combined_text = " ".join(collected_texts)
    summary = summarise_text(combined_text, sentence_count=summary_sentences)
    return SectionSummary(heading=subtopic, content=summary, sources=sources)


def compose_article(topic: str, sections: Iterable[SectionSummary], word_target: int) -> str:
    """Assemble the final article text."""

    intro = textwrap.fill(
        (
            f"This article explores {topic}, examining several key perspectives "
            "to offer a concise overview based on publicly available sources."
        ),
        width=90,
    )

    paragraphs = [intro, ""]
    total_words = len(intro.split())

    for section in sections:
        if not section.content:
            continue
        heading_line = section.heading
        paragraphs.append(heading_line)
        paragraphs.append("-" * len(heading_line))
        body = textwrap.fill(section.content, width=90)
        paragraphs.append(body)
        paragraphs.append("")
        total_words += len(section.content.split())

    conclusion = textwrap.fill(
        (
            "In summary, the available sources highlight multiple dimensions of "
            f"{topic}. Readers are encouraged to explore the references for "
            "greater detail and the latest updates."
        ),
        width=90,
    )
    paragraphs.append(conclusion)
    total_words += len(conclusion.split())

    paragraphs.append("")
    paragraphs.append("Sources")
    paragraphs.append("-------")
    seen_sources = set()
    for section in sections:
        for url in section.sources:
            if url in seen_sources:
                continue
            paragraphs.append(f"- {url}")
            seen_sources.add(url)

    paragraphs.append("")
    paragraphs.append(f"Approximate word count: {total_words}")
    paragraphs.append(f"Requested word target: {word_target}")

    return "\n".join(paragraphs)


def parse_arguments(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automatic writing assistant")
    parser.add_argument("topic", help="Main topic or prompt for the article")
    parser.add_argument(
        "--sections",
        type=int,
        default=4,
        help="Number of themed sections to generate (default: 4)",
    )
    parser.add_argument(
        "--word-target",
        type=int,
        default=800,
        help="Approximate target word count for the final article",
    )
    parser.add_argument(
        "--articles-per-section",
        type=int,
        default=2,
        help="Maximum number of articles to analyse per section",
    )
    parser.add_argument(
        "--summary-sentences",
        type=int,
        default=5,
        help="Number of sentences to keep in each section summary",
    )
    parser.add_argument(
        "--output",
        help="Optional path to save the generated article",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity (default: WARNING)",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_arguments(argv or sys.argv[1:])
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s")

    ensure_nltk_resources()

    subtopics = generate_subtopics(args.topic, args.sections)
    sections: List[SectionSummary] = []
    for subtopic in subtopics:
        section_summary = gather_information(
            subtopic,
            max_articles=args.articles_per_section,
            summary_sentences=args.summary_sentences,
        )
        sections.append(section_summary)

    article_text = compose_article(args.topic, sections, word_target=args.word_target)
    print(article_text)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(article_text)
        logging.info("Article saved to %s", args.output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
