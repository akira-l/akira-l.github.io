# SEO/GEO operating guide

This site's goal is retrieval eligibility and accurate citation, not a promise
that any search engine or model will rank or cite a page. The implementation
follows ordinary search fundamentals and exposes clear, source-supported text
instead of hidden prompts or machine-targeted keyword pages.

## What the site exposes

- One crawlable English URL and one Chinese URL per paper, connected with
  canonical and `hreflang` annotations.
- Exact paper title, ordered author list, venue/status, DOI/arXiv identifiers,
  version dates, official abstract, source-checked interpretation, limitations,
  related-work positioning, and a neutral citation-ready sentence.
- Separate JSON-LD entities for the scholarly paper and this site's explanatory
  article. The CC BY license belongs only to the explainer.
- Google Scholar/Highwire citation meta tags on the English research record.
- BibTeX, RIS, CSL-JSON, an aggregate CSL catalog, Atom feed, XML sitemap, and
  concise/full `llms.txt` discovery files.
- A record-by-record citation audit and CI checks that compare all three
  citation formats against canonical title, author order, version, date,
  container, DOI/arXiv identifier, volume, issue, pagination, and publisher
  fields. Published exports use one version of record rather than mixing in
  related arXiv metadata.
- Visible claim-to-source mappings. There is no hidden crawler-only content,
  prompt injection, fake FAQ schema, or scaled query-variant content.

## Crawler policy

`robots.txt` allows general search crawlers, search/retrieval agents,
user-triggered fetchers, and model-training crawlers. The named agents document
intent, while the `User-agent: *` rule is the compatibility fallback.

- Google Search AI features use normal Googlebot indexing; Google says no
  special AI markup is required and currently ignores `llms.txt` for Search:
  <https://developers.google.com/search/docs/fundamentals/ai-optimization-guide>
- Eligibility for Google's AI search features still depends on indexing,
  snippet eligibility, crawlable text, internal links, and structured data that
  matches visible content:
  <https://developers.google.com/search/docs/appearance/ai-features>
- `Google-Extended` separately controls Gemini model training and grounding in
  Gemini Apps/Vertex; it does not control Google Search ranking:
  <https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers>
- OpenAI separates `OAI-SearchBot`, `GPTBot`, and user-triggered
  `ChatGPT-User`: <https://developers.openai.com/api/docs/bots>
- OpenAI publisher guidance also documents `utm_source=chatgpt.com` referrals:
  <https://help.openai.com/en/articles/12627856-publishers-and-developers-faq>
- Anthropic documents `ClaudeBot`, `Claude-SearchBot`, and `Claude-User`:
  <https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler>
- Perplexity documents `PerplexityBot` and `Perplexity-User`:
  <https://docs.perplexity.ai/docs/resources/perplexity-crawlers>

There is no stable, official Doubao-specific publisher submission interface
identified as of 2026-07-31. Do not claim one. Doubao discoverability should be
treated as an outcome of public crawlability, strong Chinese pages, ordinary
search-engine coverage, and consistent academic identity signals.

## Post-deployment setup

1. Verify the site in Google Search Console, Bing Webmaster Tools, and Baidu
   Search Resource Platform.
2. Submit `https://akira-l.github.io/sitemap.xml` to all three. Do not use the
   Google Indexing API for ordinary publication pages.
3. Use Bing's IndexNow support after publication changes:
   <https://www.bing.com/webmasters/help/indexnow-0z209wby>. The repository
   includes a root key file and `.github/workflows/indexnow.yml`, which submits
   all sitemap URLs after relevant pushes to `master`.
4. Inspect representative URLs in each console after deployment and request
   recrawling only for important changed pages.
5. In Google Search Console, monitor normal Search and the available Generative
   AI performance reporting. In Bing Webmaster Tools, monitor AI Performance
   citation URLs and grounding queries:
   <https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview>.
6. Track visits containing `utm_source=chatgpt.com`, plus referrals from Bing,
   Perplexity, Gemini surfaces, and other identifiable clients. Treat missing
   referral data as unknown, not as proof that a model did not use a page.

## Academic entity cleanup

Use one identity everywhere: **Yuanzhi Liang**, **梁远智**, and **akira-l**.
Do not reintroduce “Yuanzhi (Liam) Liang”.

- Canonical ORCID: <https://orcid.org/0009-0008-2746-5947>
- DBLP: <https://dblp.org/pid/193/8013.html>
- Google Scholar:
  <https://scholar.google.com/citations?user=YUjR-z8AAAAJ>

Update ORCID employment/homepage/works and the Google Scholar homepage link.
Resolve the conflicting legacy ORCID currently associated with the DBLP profile.
Where the author controls an arXiv comment, project page, code repository, or
institutional profile, link back to the canonical local research record. Do not
buy backlinks or mass-post duplicate summaries.

## Monthly retrieval benchmark

For ChatGPT, Gemini, Claude, Perplexity, Bing Copilot, and Doubao, record:

- exact-title lookup;
- acronym plus topic lookup;
- broad topic/survey lookup; and
- a request for related-work citations.

For each prompt, record whether the work was found, which canonical URL was
cited, whether title/authors/venue/version were correct, and whether the summary
matched the paper. Recheck changed records after four to eight weeks; retrieval
and citation are controlled by external systems and cannot be guaranteed.

## Structured-data and Scholar rules

Structured data must describe visible main-page content and must not mislead:
<https://developers.google.com/search/docs/appearance/structured-data/sd-policies>.
The paper entity uses Schema.org `ScholarlyArticle`:
<https://schema.org/ScholarlyArticle>.

Google Scholar expects each paper or abstract on its own URL, a visible
author-written abstract, and supported `citation_*` metadata:
<https://scholar.google.com/intl/en/scholar/inclusion.html>. This site omits
`citation_pdf_url` because it does not host publisher-authorized local PDFs in
the same URL hierarchy.
