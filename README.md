# Automatic Essay Writer

This project provides a simple Python script that breaks down a topic into
several themed sections, searches the web for supporting material, summarises
the findings, and produces an essay-style article.

## Features

- Generates a set of subtopics that cover background, developments, practical
  examples, challenges, and future outlook for the requested theme.
- Searches the web through DuckDuckGo and retrieves a handful of relevant
  articles for each subtopic.
- Extracts readable text from each article and summarises it with a lightweight
  frequency-based algorithm (no external AI services required).
- Combines the section summaries into an essay with an introduction, body, and
  conclusion, and lists the discovered sources.

## Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

The first run will download the necessary NLTK data packages automatically.

## Usage

```bash
python auto_writer.py "Your topic here" --sections 4 --word-target 800 \
    --articles-per-section 2 --summary-sentences 5 --output article.txt
```

### Arguments

- `topic` – main subject or writing prompt for the article.
- `--sections` – number of subtopics/sections to create (default: 4).
- `--word-target` – desired word count for the finished article. The script
  reports the approximate count reached (default: 800).
- `--articles-per-section` – maximum number of articles analysed per section
  (default: 2).
- `--summary-sentences` – number of sentences retained in each section summary
  (default: 5).
- `--output` – optional path to save the generated essay to disk.
- `--log-level` – set to `INFO` or `DEBUG` to monitor progress while fetching
  and analysing sources.

Example:

```bash
python auto_writer.py "影响力投资" --sections 5 --word-target 900 --log-level INFO
```

The script prints the essay to the console and, if `--output` is specified,
creates a UTF-8 encoded text file with the same content.

## Notes

- The script depends on external web pages; network access is required during
  execution.
- The summariser operates with a simple extractive technique and may not always
  produce perfect prose. Feel free to edit the resulting article manually for
  tone and clarity.
